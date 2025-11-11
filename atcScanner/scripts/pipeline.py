import os
import glob
import subprocess
import time
import signal
import json
import logging


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


# Processes a new raw file
def process_file(input_file, file_ext):
    # Change output file name to wav audio file
    output_filename = input_file.split('/')[-1].replace(file_ext, '.wav')
    # Creates file path according to date of the file (taken from filename)
    output_filepath = '../audio_files/' + get_year(output_filename) + '/' + get_month(output_filename) + '/' + get_day(output_filename) + '/'
    os.makedirs(output_filepath, exist_ok=True)

    try:
        logging.info('Processing file ' + output_filename.replace('.wav', file_ext))
        subprocess.run(['./decode_cs16.sh', input_file, output_filepath + output_filename], check=True)
    except subprocess.CalledProcessError as e:
        # Prints an error if processing fails
        logging.error('Failed to decode file ' + output_filename.replace('.wav', file_ext))
        return
    # Delete raw file
    os.remove(input_file)


def get_config():
    config_file = 'conf/pipeline.json'
    with open(config_file, 'r') as f:
        settings = json.load(f)
    return settings


class GracefulShutdown:
    # Class to let the script finish working and exit
    exit_needed = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.set_exit)
        signal.signal(signal.SIGTERM, self.set_exit)

    def set_exit(self, signum, frame):
        self.exit_needed = True


def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logging.info('Pipeline started')
    # Path with raw transmission files
    raw_files_path = '../records/'
    # Check if the path exists
    if not os.path.exists(raw_files_path):
        logging.critical('Raw files path does not exist!')

    settings = get_config()
    sleep_time = settings['sleep_time']
    file_ext = settings['file_ext']

    terminator = GracefulShutdown()

    # Periodically check if there are any new files, exit if requested
    while not terminator.exit_needed:
        raw_files = glob.glob(raw_files_path + '*' + file_ext)
        for f in raw_files:
            process_file(f, file_ext)
        time.sleep(sleep_time)
    logging.info('Pipeline terminated')


if __name__ == '__main__':
    main()
