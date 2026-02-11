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
        snrs = self.snr_table[:, 0]
        Gzs = self.snr_table[:, 1]
        Gz = np.log(np.mean(np.abs(audio) + 1.0)) - np.mean(np.log(np.abs(audio) + 1.0))
        pos = np.argmin(np.abs(Gzs - Gz))
        return snrs[pos]

    def get_snr(self):
        # Check if file is loaded correctly and uses correct sample rate
        if self.sr not in [8000, 16000]:
            logging.warning(f"Silero expects 8000/16000 Hz sample rate. Audio has sample rate of {self.sr} Hz.")
            return -100

        if len(self.sig) == 0:
            return -100

        # Data preprocessing for VAD
        data = self.sig.mean(axis=1) if len(self.sig.shape) > 1 else self.sig

        # Normalize Input to 0.0 - 1.0
        if np.issubdtype(data.dtype, np.integer):
            max_int = np.iinfo(data.dtype).max
            vad_audio = data.astype(np.float32) / max_int
        else:
            vad_audio = data.astype(np.float32)

        # Force normalization
        file_peak = np.max(np.abs(vad_audio))
        if file_peak > 0:
            vad_audio = vad_audio / file_peak

        # Silero VAD
        window_size = 512 if self.sr == 16000 else 256
        state = np.zeros((2, 1, 128), dtype=np.float32)
        is_speech = np.zeros(len(data), dtype=bool)

        for i in range(0, len(vad_audio), window_size):
            chunk = vad_audio[i: i + window_size]
            if len(chunk) < window_size: break

            chunk_tensor = np.expand_dims(chunk, axis=0)
            ort_inputs = {
                'input': chunk_tensor,
                'sr'   : np.array(self.sr, dtype=np.int64),
                'state': state
            }
            out, state = self.session.run(None, ort_inputs)

            prob = out[0][0]

            chunk_peak = np.max(np.abs(chunk))
            # Check if flagged voice is not complete silence
            # Otherwise SNR estimation won't work
            if prob > 0.05 and chunk_peak > 0.10:
                is_speech[i: i + window_size] = True

        # 4. EXTRACT & SCALE
        speech_raw = data[is_speech]

        if len(speech_raw) > 0:
            speech_final = speech_raw.astype(np.float32)

            # Remove DC Offset
            speech_final = speech_final - np.mean(speech_final)

            # Force Target Loudness (~30,000) if file was loaded as float
            current_peak = np.max(np.abs(speech_final))
            if current_peak > 0:
                target_peak = 30000.0
                speech_final = speech_final * (target_peak / current_peak)

            # Add Dither to make sure there is no zero value
            dither = np.random.normal(0, 1.0, len(speech_final))
            speech_final = speech_final + dither

            return self.estimate_snr(speech_final)
        else:
            logging.warning(f"No speech detected in {self.filename}")
            return -100
