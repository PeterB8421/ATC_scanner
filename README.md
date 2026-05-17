# Automated system for ATC data collecton running on RPi
## Author: Bc. Petr Balok
## Supervisor: Ing. Igor Szöke PhD.
Pipeline for automatic processing of ATC data created by RTL Airband with web user interface, designed to run on Raspberry Pi. This repository is the implementation part of my Master's thesis.

### Requirements
Docker is required to run this project. Installation guide for Docker can be found [here](https://docs.docker.com/engine/install/). For Raspberry Pi it is recommended to install the Debian package.

### Overview
This project consists of two Docker containers. Container `atcScanner` that contains implemented pipeline and web user interface and container `atcTranscriber` that contains an example API for automatic speech recognition (this container is **not** meant to be run on Raspberry Pi due to hardware requirements for NeMo ASR).

---

#### atcScanner
Directories:
- `atcScanner/` - Django project configuration and settings
- `mainApp/` - Django app, here is the web server backend
    - `migrations/` - Database schema migrations
    - `static/mainApp/` - Static files (for frontend)
        - `css/` - CSS styles
        - `js/` - Javascript files
- `scripts/` - Pipeline implementation
    - `conf/` - Pipeline and plugin config files
- `templates/` - Django template files (for frontend)

##### Setup
After cloning this repository, there are a few steps to do before building the Docker conatiner.
**IMPORTANT**: Before building, ensure that the scripts `decode_cf32.sh` and `decode_cs16.sh` located in `atcScanner/mainApp/scripts/` direcotory have execute system permissions.

To check this simply head to the specified directory using `cd atcScanner/scripts/`. Then run command `chmod +x decode_cf32.sh` and `chmod +x decode_cs16.sh`. This ensures that the Docker conatiner can run these scripts.

After checking the execute permissions, you can go back to `atcScanner` (where `docker-compose.yml` file is located). Then edit the `.env` file and specify `INPUT_DIR` to point to the directory set as output for RTL Airband (in Docker this directory is mapped to `/data/in/`).

The `OUTPUT_DIR` specifies a directory where processed files will be located (in Docker this directory is mapped to `/data/out/`).

And `EXPORT_DIR` specifies a directory where exported zip archives conatining processed data will be saved (in Docker this directory is mapped to `/data/export/`).

To build and run this conatiner, use command `docker compose up --build -d` (`docker-compose.yml` must be in the same directory, where you run this command from). To stop the conatiner use command `docker compose down`.
Starting the Docker conatiner can take a few minutes. After the container is built, open the web UI at `[RPi IP]:10000`. Then open the settings page and upload you RTL Airband config file. After uploading don't forget to check the imported metadata and click save. You can also tweak the settings for pipeline.

`Sleep time`: period in seconds for scanning new files.

`Input file type`: This pipeline supports only `cf32` and `cs16` files for processing.

`Minimum/Maximum audio length`: Specifies desired length of processed recordings (files shorter/longer than this interval will be deleted).

`SNR thershold`: Files with measured SNR lower than this thershold will be deleted.

`Delete input files (cs16/cf32) after processing?`: Input files will be deleted after processing if this box is checked (moved to directory `processed/` if unchecked).

`Check this box if using dates subdirectories for input files (cs16/cf32)`: If your input files are divided into subdirectories based on date (e. g. `2026/05/18/`), check this box. This will automatically scan for files in the subdirectory for current day.

After clicking save the pipeline service will be automatically reloaded with new settings.

There are a few webpages made to create an overview of your pipeline.

`Homepage`: Here are all recordings, you can use filters to check for specific dates, times, frequencies and airport codes. You can go to recording detail to see all metadata and download the recording.

`Settings`: Pipeline settings as mentioned before.

`Deleted files log`: Log of deleted files and reasons why a specific file was deleted.

`Statistics`: Graphs of pipeline statistics.

`Export data`: Webpage where you can create exports of your collected data (in day or hour intervals).

###### Using atcTranscriber

If you want to use `atcTranscriber` to create transcriptions for recordings, uncomment one of the example plugins in `scripts/pipeline.py`. Don't forget to set the correct IP addresss (or domain) in the specified config file.

This is an example ASR API server, you can write your own plugins in `scripts/plugins.py`. To create your own plugin, create a class that inherits `BaseProcessor` class. This class needs to implement the `process()` method which will be called for each processed file. After creating this new class, add deocrator `@register_plugin("[PLUGIN NAME]")` and add this `"[PLUGIN NAME]"` to active plugins in `scripts/pipeline.py` along with path to the plugin config.

---

#### atcTranscriber
This conatiner is supposed to run on a machine capable of running NeMo ASR's Parakeet models.
##### Setup
You can use your own NeMo model. Simply put the model in the `models/` directory and change the `MODEL_PATH` path in `main.py` to you model name. If you do not have your own model, atcTranscriber will use a pretrained NeMo model for English.

To run this container use command `docker compose up --build -d` in the same directory as `docker-compose.yml`. Building this container can take several minutes. To stop this container use command `docker compose down`.
