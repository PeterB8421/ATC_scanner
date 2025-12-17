#!/usr/bin/env bash
cf32=$1
file_out=$2
cat $cf32 | csdr amdemod_cf | csdr dcblock_ff | sox -t raw -r8k -c1 -b32 -e float - -t wav $file_out
