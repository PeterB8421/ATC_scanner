"""
Author: Bc. Petr Balok
"""
import json


# This is in separate file because it is used in both Django and pipeline
def get_config(config_file):
    """ Loads configuration from JSON file and returns dict with loaded settings """
    with open(config_file, 'r') as f:
        settings = json.load(f)
    return settings
