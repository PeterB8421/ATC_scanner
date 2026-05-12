"""
Author: Bc. Petr Balok
"""
import json


# This is in separate file because it is used in both Django and pipeline
def get_config():
    """ Loads configuration from JSON file and returns dict with loaded settings """
    config_file = '/scripts/conf/pipeline.json'
    with open(config_file, 'r') as f:
        settings = json.load(f)
    return settings
