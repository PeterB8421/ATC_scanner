"""
Author: Bc. Petr Balok
"""

import os
import sys
import glob
import subprocess
import time
import signal
import json
import logging
import django
import plugins  # This import is needed to register plugins from plugins.py
from BaseProcessor import get_plugin
from SNR import SNR
from scipy.io import wavfile
from datetime import datetime

ACTIVE_PLUGINS = {
    # ASR API polling plugin
    # "asr_api_polling": {
    # If ASR API is running on the same machine, use domain: http://host.docker.internal:11000
    #     "url": "http://host.docker.internal:11000"
    # },
    # ASR API webhook plugin
    # "asr_api_webhook": {
    #     "url": "http://host.docker.internal:11000"
    # }
}

# Import shared config function
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config_utils import get_config


# Gets year from filename
def get_year(filename):
    part = filename.split('_')[-2]
    return part[:4]


# Gets month from filename
def get_month(filename):
    part = filename.split('_')[-2]
    return part[4:6]


# Gets day from filename
def get_day(filename):
    part = filename.split('_')[-2]
    return part[-2:]


def get_hour(filename):
    part = filename.split('_')[-1]
    part = part.split('.')[0]
    return part[:2]


def get_min(filename):
    part = filename.split('_')[-1]
    part = part.split('.')[0]
    return part[2:4]


def get_sec(filename):
    part = filename.split('_')[-1]
    part = part.split('.')[0]
    return part[-2:]


def log_deletion(file_path, reason, settings, duration=None, snr=None):
    from mainApp.models import Deleted
    Deleted.objects.create(
        file_path=file_path,
        reason=reason,
        snr_thres=settings['snr_thres'],
        short_limit=settings['min_audio_len'],
        long_limit=settings['max_audio_len'],
        date=datetime.now(),
        duration=duration,
        snr=snr
    )


def get_metadata_from_filepath(filepath, airport_data):
    """
    Extracts the base filename from a full path and searches the
    airport configuration dictionary to find the matching metadata.
    """
    # Strip the directories, get just the file name
    filename = os.path.basename(filepath)

    # Loop through every configured airport
    for identifier, metadata in airport_data.items():

        # Check if the filename starts with this identifier
        if filename.startswith(identifier) or filename.startswith(metadata['template']):
            return metadata

    # If no match is found
    return None


def remove_output_files(output_filename):
    try:
        os.remove(output_filename.replace('.wav', '_RAW.wav'))
    except Exception:
        pass
    os.remove(output_filename)


# Processes a new raw file
def process_file(input_file, settings):
    from mainApp.models import Recording, Deleted
    reason = Deleted.DeletionReason
    if os.path.getsize(input_file) == 0:
        logging.info(f'File {os.path.basename(input_file)} is empty, deleting.')
        log_deletion(input_file, reason.EMPTY_FILE, settings)
        os.remove(input_file)
        return
    # Change output file name to wav audio file
    output_filename = input_file.split('/')[-1].replace(settings['file_ext'], '.wav')
    # Creates file path according to date of the file (taken from filename)
    output_filepath = os.path.join('/data/out', get_year(output_filename), get_month(output_filename), get_day(output_filename))
    os.makedirs(output_filepath, exist_ok=True)
    output_filename = os.path.join(output_filepath, output_filename)

    try:
        logging.info('Processing file ' + output_filename.replace('.wav', settings['file_ext']))
        subprocess.run([os.path.join('/scripts', settings['script_name']), input_file, output_filename], check=True)
    except subprocess.CalledProcessError as e:
        # Prints an error if processing fails
        logging.error('Failed to decode file ' + output_filename.replace('.wav', settings['file_ext']))
        return

    # Calculate the duration of the audio file
    sample_rate, data = wavfile.read(output_filename)
    duration_sec = data.shape[0] / sample_rate
    if duration_sec < settings['min_audio_len']:
        # Delete the file if it is too short
        logging.info(f'Removing {os.path.basename(output_filename)}, too short. Audio duration: {duration_sec} s, min. duration: {settings["min_audio_len"]} s')
        log_deletion(input_file, reason.TOO_SHORT, settings, duration=duration_sec)
        os.remove(input_file)
        os.remove(output_filename.replace('.wav', '_RAW.wav'))
        os.remove(output_filename)
        return

    if duration_sec > settings['max_audio_len'] and settings['max_audio_len'] != 0:
        # Delete file if it is too long
        logging.info(f'Removing {os.path.basename(output_filename)}, too long. Audio duration: {duration_sec} s, max. duration: {settings["max_audio_len"]} s')
        log_deletion(input_file, reason.TOO_LONG, settings, duration=duration_sec)
        os.remove(input_file)
        remove_output_files(output_filename)
        return

    snr = SNR(output_filename.replace('.wav', '_RAW.wav')).get_snr()
    os.remove(output_filename.replace('.wav', '_RAW.wav'))
    # Delete automatically if there is too much noise
    if snr < settings['snr_thres']:
        logging.info(f'Removing {output_filename} SNR = {snr}, thres = {settings["snr_thres"]}')
        log_deletion(input_file, reason.SNR, settings, duration_sec, snr)
        os.remove(output_filename)
        os.remove(input_file)
        return

    # Get date and time from file name
    rec_datetime = datetime(int(get_year(input_file)), int(get_month(input_file)), int(get_day(input_file)),
                            int(get_hour(input_file)), int(get_min(input_file)), int(get_sec(input_file)))
    airport_info = get_metadata_from_filepath(input_file, settings['airports'])
    if airport_info is None:
        airport_info = {
            'code': "",
            'frequency': 0.0,
        }
    metadata = {
        'date': rec_datetime.isoformat(),
        'file_path': output_filename,
        'country': settings['country'],
        'location': settings['location'],
        'center_freq': settings['center_freq'],
        'airport_codes': settings['airport_codes'],
        'snr': snr,
        'duration': duration_sec,
        'transcript': "[Processing...]",
        'code': airport_info['code'],
        'freq': airport_info['frequency'],
    }
    # Save JSON metadata next to wav file
    with open(output_filename.replace('.wav', '.json'), 'w') as f:
        json.dump(metadata, f, indent=2, sort_keys=True)

    # Try saving to database, if saving fails, continue
    try:
        recording = Recording.objects.create(
            file_path=metadata['file_path'],
            country=metadata['country'],
            location=metadata['location'],
            center_freq=metadata['center_freq'],
            airport_codes=metadata['airport_codes'],
            date=rec_datetime,
            snr=metadata['snr'],
            duration=metadata['duration'],
            transcript=metadata['transcript'],
            code=metadata['code'],
            freq=metadata['freq'],
        )
        recording.save()
    except Exception as e:
        logging.error(f'Failed to save recording to database: {str(e)}')

    loaded_plugins = []
    # Get all loaded plugins specified in ACTIVE_PLUGINS
    for plugin_name, plugin_config in ACTIVE_PLUGINS.items():
        loaded_plugins.append(get_plugin(plugin_name, plugin_config))

    for plugin in loaded_plugins:
        try:
            # Run each plugin
            plugin.process(output_filename)
        except Exception as e:
            # Log an error if one occurred
            logging.error(f"Plugin '{plugin.__class__.__name__} failed: {e}")

    if settings['in_autodelete']:
        # Delete raw file
        os.remove(input_file)
    else:
        # Move file to processed directory
        os.makedirs('/data/in/processed', exist_ok=True)
        os.replace(input_file, '/data/in/processed/' + os.path.basename(input_file))


class GracefulShutdown:
    # Class to let the script finish working and exit
    exit_needed = False
    restart = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.set_exit)
        signal.signal(signal.SIGTERM, self.set_exit)

    def set_exit(self, signum, frame):
        self.exit_needed = True

    def set_restart(self):
        self.restart = True


def main():
    # Logging settings
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # /app
    sys.path.append(project_root)
    # Do Django setup, without this, saving to database won't work
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'atcScanner.settings')
    django.setup()

    logging.info('Pipeline started')
    # Path with input transmission files
    input_files_path = '/data/in'
    logging.info('input_file_path: ' + input_files_path)
    # Check if the path exists
    if not os.path.exists(input_files_path):
        logging.critical('Raw files path does not exist!')

    settings = get_config()

    terminator = GracefulShutdown()

    restart_flag = '/app/shared/restart_pipeline.flag'

    elapsed_time_sec = 0
    # Periodically check if there are any new files, exit if requested
    while not terminator.exit_needed:
        # If settings were changed, reload pipeline settings
        if os.path.exists(restart_flag):
            logging.info('Reloading settings')
            os.remove(restart_flag)
            settings = get_config()

        if elapsed_time_sec >= settings['sleep_time']:
            elapsed_time_sec = 0
            if settings['in_dated_subdirs']:
                now = datetime.now()
                input_files_path = f'/data/in/{now.strftime("%Y")}/{now.strftime("%m")}/{now.strftime("%d")}'
                if not os.path.exists(input_files_path):
                    logging.warning(f'Input file path does not exist! Path: {input_files_path}')
            raw_files = glob.glob(os.path.join(input_files_path,  '*' + settings['file_ext']))
            for f in raw_files:
                process_file(f, settings)
        # Sleep for 1 second to restart or shutdown quicker
        time.sleep(1)
        elapsed_time_sec += 1

    logging.info('Pipeline terminated')


if __name__ == '__main__':
    main()
