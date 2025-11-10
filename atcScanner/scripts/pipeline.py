import os
import glob
import subprocess
import time
import signal


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
def process_file(input_file):
    # Change output file name to wav audio file
    output_filename = input_file.split('/')[-1].replace('.cs16', '.wav')
    # Creates file path according to date of the file (taken from filename)
    output_filepath = '../audio_files/' + get_year(output_filename) + '/' + get_month(output_filename) + '/' + get_day(output_filename) + '/'
    os.makedirs(output_filepath, exist_ok=True)

    try:
        subprocess.run(['./decode_cs16.sh', input_file, output_filepath + output_filename], check=True)
    except subprocess.CalledProcessError as e:
        # Prints an error if processing fails
        print('Processing failed!')
        print(e)
        return
    # Delete raw file
    os.remove(input_file)


class GracefulShutdown:
    # Class to let the script finish working and exit
    exit_needed = False

    def __init__(self):
        signal.signal(signal.SIGINT, self.set_exit)
        signal.signal(signal.SIGTERM, self.set_exit)

    def set_exit(self, signum, frame):
        self.exit_needed = True


def main():
    # Path with raw transmission files
    raw_files_path = '../records/'
    # Check if the path exists
    if not os.path.exists(raw_files_path):
        print('Path for raw files not found')

    terminator = GracefulShutdown()

    # Periodically check if there are any new files, exit if requested
    while not terminator.exit_needed:
        raw_files = glob.glob(raw_files_path + '*.cs16')
        print(raw_files)
        for f in raw_files:
            process_file(f)
        time.sleep(5)


if __name__ == '__main__':
    main()
