import logging
from BaseProcessor import BaseProcessor, register_plugin


@register_plugin("whisper_asr")
class WhisperASR(BaseProcessor):
    def process(self, file_path: str):
        logging.debug(f'Sending file {file_path} for ASR')
