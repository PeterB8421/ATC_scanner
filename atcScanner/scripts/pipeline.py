import os
import sys
import glob
import subprocess
import time
import signal
import json
import logging
import django
from SNR import SNR
from datetime import datetime


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


# Processes a new raw file
def process_file(input_file, settings):
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

    snr = SNR(output_filename).get_snr()
    # Delete automatically if there is too much noise
    if snr < settings['snr_thres']:
        logging.info(f'Removing {output_filename} SNR = {snr}, thres = {settings["snr_thres"]}')
        os.remove(output_filename)
        os.remove(input_file)
        return

    # Get date and time from file name
    rec_datetime = datetime(int(get_year(input_file)), int(get_month(input_file)), int(get_day(input_file)),
                            int(get_hour(input_file)), int(get_min(input_file)), int(get_sec(input_file)))
    metadata = {
        'date': rec_datetime.isoformat(),
        'file_path': output_filename,
        'country': settings['country'],
        'location': settings['location'],
        'center_freq': settings['center_freq'],
        'airport_codes': settings['airport_codes'],
        'snr': snr,
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
        )
        recording.save()
    except Exception as e:
        logging.error(f'Failed to save recording to database: {str(e)}')

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
    global Recording # Expose Recording class as global for data insertion
    from mainApp.models import Recording
    logging.info('Pipeline started')
    # Path with raw transmission files
    raw_files_path = '/data/in'
    logging.info('raw_file_paths: ' + raw_files_path)
    # Check if the path exists
    if not os.path.exists(raw_files_path):
        logging.critical('Raw files path does not exist!')

    settings = get_config()
    sleep_time = settings['sleep_time']

    terminator = GracefulShutdown()

    restart_flag = '/app/shared/restart_pipeline.flag'

    elapsed_time_sec = 0
    # Periodically check if there are any new files, exit if requested
    while not terminator.exit_needed and not terminator.restart:
        # If settings were changed, restart pipeline
        if os.path.exists(restart_flag):
            logging.info('Restart signal received')
            os.remove(restart_flag)
            terminator.set_restart()

        if elapsed_time_sec >= settings['sleep_time']:
            elapsed_time_sec = 0
            raw_files = glob.glob(os.path.join(raw_files_path,  '*' + settings['file_ext']))
            logging.info('Raw files: ' + str(raw_files))
            for f in raw_files:
                process_file(f, settings)
        # Sleep for 1 second to restart or shutdown quicker
        time.sleep(1)
        elapsed_time_sec += 1

    if terminator.restart:
        logging.info('Restarting pipeline')
        exit(2)
    else:
        logging.info('Pipeline terminated')


if __name__ == '__main__':
    main()
