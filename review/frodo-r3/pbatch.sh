#!/usr/bin/env bash
# Frodo r3: slice prototype sets under profile overrides, 3 at a time: stdin lines "tag proto k=v ...".
cd /mnt/f/code/beadjoint
SP=/tmp/claude-1000/-mnt-f-code/730f7725-c659-4873-9f2b-a19162bddb3e/scratchpad
run() { tag=$1; proto=$2; shift 2; sets=(); for kv in "$@"; do sets+=(--set "$kv"); done
  cadpy review/frodo-r3/plate.py --proto $proto --out review/frodo-r3/sl/$tag --layout-out review/frodo-r3/sl/$tag.layout.json "${sets[@]}" > $SP/$tag.log 2>&1
  cadpy review/frodo-r3/analyze.py --slice review/frodo-r3/sl/$tag --layout review/frodo-r3/sl/$tag.layout.json --out review/frodo-r3/sl/an-$tag.json >> $SP/$tag.log 2>&1; echo "done $tag"; }
n=0
while read -r line; do [ -z "$line" ] && continue; run $line & n=$((n+1)); [ $((n % 3)) -eq 0 ] && wait; done
wait
