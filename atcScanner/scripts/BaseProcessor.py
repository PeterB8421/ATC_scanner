import abc
from typing import Dict, Any


class BaseProcessor(abc.ABC):
    """
    Abstract class for plugins to process data from pipeline.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config

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
