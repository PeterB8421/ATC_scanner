#!/usr/bin/env bash
cf32=$1
file_out=$2
file_out_raw="${file_out%.*}_RAW.wav"
cat $cf32 | csdr amdemod_cf | csdr dcblock_ff | csdr fastagc_ff | sox -t raw -r 8000 -e float -b 32 -c 1 - "$file_out" highpass 300 lowpass 3400 vad -t 5 -p 0.5

cat $cf32 | csdr amdemod_cf | csdr dcblock_ff | sox -t raw -r 8000 -e float -b 32 -c 1 - -t wav -e signed-integer -b 16 "$file_out_raw" highpass 300 lowpass 3400
