"""
Author: Bc. Petr Balok
"""

import logging
import os
import numpy as np
import onnxruntime
from scipy.io import wavfile


class SNR:
    def __init__(self, filename):
        self.filename = filename
        try:
            self.sr, self.sig = wavfile.read(filename)
        except ValueError:
            logging.error(f"Error reading {filename}")
            self.sr = 0
            self.sig = np.array([])

        current_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(current_dir, 'silero_vad.onnx')

        opts = onnxruntime.SessionOptions()
        opts.log_severity_level = 3
        self.session = onnxruntime.InferenceSession(model_path, sess_options=opts)

        self.snr_table = np.loadtxt('/app/scripts/SNR_table_-100_100.tab')

    def estimate_snr(self, audio):
        """
        This function was provided by the thesis supervisor.
        And edited by Bc. Petr Balok.
        :param audio: audio signal
        :return: SNR estimate in dB
        """
        # Remove DC Offset
        audio_float = audio - np.mean(audio)

        # Frame-Based Squelch Filter
        chunk_size = int(self.sr * 0.03)
        active_chunks = []

        for i in range(0, len(audio_float), chunk_size):
            chunk = audio_float[i: i + chunk_size]
            # Calculate the power of the chunk.
            # If it's greater than 1.0, clip it
            if np.mean(chunk ** 2) > 1.0:
                active_chunks.extend(chunk)

        active_audio = np.array(active_chunks)

        # If no speech was found, return NaN
        if len(active_audio) == 0:
            return float('nan')

        snrs = self.snr_table[:, 0]
        Gzs = self.snr_table[:, 1]

        audio_abs = np.abs(active_audio)

        Gz = np.log(np.mean(audio_abs + 1.0)) - np.mean(np.log(audio_abs + 1.0))
        pos = np.argmin(np.abs(Gzs - Gz))

        return snrs[pos]

    def get_snr(self):
        return self.estimate_snr(self.sig)
