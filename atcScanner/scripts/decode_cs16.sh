#!/usr/bin/env bash
# This file was provided by the thesis supervisor
# Edited by: Bc. Petr Balok
file_in=$1
file_out=$2

cat "$file_in" | csdr convert_s16_f | csdr amdemod_cf | csdr dcblock_ff | python /app/scripts/adjust_volume_clip_convert_f_s16.py | sox -t raw -r16k -c1 -b16 -e signed-integer - -t wav "$file_out"
