"""
Author: Bc. Petr Balok
"""

import abc
import os
import sys
from typing import Dict, Any

# Import shared config function
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config_utils import get_config

class BaseProcessor(abc.ABC):
    """
    Abstract class for plugins to process data from pipeline.
    """
    def __init__(self, config_path: Dict[str, Any]):
        self.config = get_config(config_path)

    @abc.abstractmethod
    def process(self, file_path: str):
        """
        This function will be called to process one file.
        :param file_path: Path to an audio file
        :return:
        """
        pass


_PLUGIN_REGISTRY = {}


def register_plugin(name: str):
    """Decorator to add plugins"""
    def wrapper(cls):
        _PLUGIN_REGISTRY[name] = cls
        return cls
    return wrapper


def get_plugin(name: str, config: Dict[str, Any]) -> BaseProcessor:
    """Get plugin from registry"""
    if name not in _PLUGIN_REGISTRY:
        raise ValueError(f"Plugin '{name}' is not registered.")
    return _PLUGIN_REGISTRY[name](config)
