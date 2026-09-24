#!/usr/bin/env bash
# Slice the mini coupon of problem glyphs under one set of process overrides and score it.
# usage: demo/tune.sh <tag> [key=value ...]
set -euo pipefail
cd /mnt/f/code/beadjoint
tag=$1; shift
sets=()
for kv in "$@"; do sets+=(--set "$kv"); done
cadpy demo/demo_plate.py --chars 'zwt#fXKNV&ł+yk' --out "demo/tune/$tag" --layout-out "demo/tune/$tag.layout.json" "${sets[@]}" | tail -1
cadpy demo/demo_check.py --slice "demo/tune/$tag" --layout "demo/tune/$tag.layout.json" --tag "tune-$tag" | head -2
