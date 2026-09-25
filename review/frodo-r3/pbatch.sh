#!/usr/bin/env bash
# Frodo r3: slice prototype sets under profile overrides, 3 at a time: stdin lines "tag proto k=v ...".
cd "$(dirname "$0")/../.."
SP="${FILLAPRINT_SCRATCH:-/tmp/fillaprint-review}"
run() { tag=$1; proto=$2; shift 2; sets=(); for kv in "$@"; do sets+=(--set "$kv"); done
  "${PYTHON:-python3}" review/frodo-r3/plate.py --proto $proto --out review/frodo-r3/sl/$tag --layout-out review/frodo-r3/sl/$tag.layout.json "${sets[@]}" > $SP/$tag.log 2>&1
  "${PYTHON:-python3}" review/frodo-r3/analyze.py --slice review/frodo-r3/sl/$tag --layout review/frodo-r3/sl/$tag.layout.json --out review/frodo-r3/sl/an-$tag.json >> $SP/$tag.log 2>&1; echo "done $tag"; }
n=0
while read -r line; do [ -z "$line" ] && continue; run $line & n=$((n+1)); [ $((n % 3)) -eq 0 ] && wait; done
wait
