#!/usr/bin/env python3

# ATCO2 EU project. License: Apache 2.0.
# Copyright 2020 Brno University of Technology (author: Karel Vesely).

import sys, io
import numpy as np

def adjust_volume(audio_):
    audio = np.array(audio_)

    # adjust to 'minimal standard deviation' as automatic gain/volume control
    # the complete dynamic range of the signal here is (-1,+1)
    lower_bound_std = 0.04

    std_dev = max(np.std(audio), lower_bound_std / 500.)
    if std_dev < lower_bound_std:
        re_scaler = lower_bound_std / std_dev
        print("Note: audio re-scaler %f" % re_scaler, file=sys.stderr)
        audio *= re_scaler
    else:
        print("Note: No audio re-scaling... std_def %f" % std_dev, file=sys.stderr)

    # clip the audio,
    num_clipped = np.sum(audio > 1.0) + np.sum(audio < -1.0)
    audio[audio > 1.0] = 1.0
    audio[audio < -1.0] = -1.0

    if num_clipped != 0:
        print("WARNING: we clipped %d/%d samples!" % (num_clipped, len(audio)), file=sys.stderr)

    return audio

def main():
    # read the audio (raw audio, as 32bit floats)
    audio = np.frombuffer(sys.stdin.buffer.read(), dtype='f4')

    # adjust volume to target standard deviation, if signal is too silent
    # (it also does clipping)
    audio_volume = adjust_volume(audio)

    # write the audio, convert to 16bit signed-int,
    with open("/dev/stdout", "wb") as output:
        output.write((audio_volume * 32767.0).astype(np.int16))

if __name__ == "__main__":
    # execute only if run as a script,
    main()

