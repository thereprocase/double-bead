#!/usr/bin/env bash
# Frodo r3: run tune.sh for each "tag k=v k=v" line on stdin, 3 at a time, then analyze each.
cd /mnt/f/code/beadjoint
SP=/tmp/claude-1000/-mnt-f-code/730f7725-c659-4873-9f2b-a19162bddb3e/scratchpad
mkdir -p $SP
run() { tag=$1; shift; demo/tune.sh "$tag" "$@" > $SP/$tag.log 2>&1; cadpy review/frodo-r3/analyze.py --slice demo/tune/$tag --layout demo/tune/$tag.layout.json --out review/frodo-r3/an-$tag.json > /dev/null 2>&1; echo "done $tag"; }
n=0
while read -r line; do
  [ -z "$line" ] && continue
  run $line &
  n=$((n+1)); if [ $((n % 3)) -eq 0 ]; then wait; fi
done
wait
python3 review/frodo-r3/score.py
