#!/bin/bash
# Resumable chunked render (skips finished chunks). Usage: render_all.sh [chunk-starts...]   Run two in parallel on different starts.
cd "$(dirname "$0")"; N=$(python3 -c "import json;print(json.load(open('timeline.json'))['N'])"); CH=${CHUNK:-300}
ALL=$(seq 0 $CH $((N-1))); LIST=${@:-$ALL}
for s in $LIST; do e=$((s+CH)); [ $e -gt $N ] && e=$N; f=$(printf "render/chunk_%04d.mp4" $s)
  [ -f "$f" ] && { echo "skip $f"; continue; }
  python3 composite.py $s $e || exit 1; echo "$(date +%T) composite chunk $s-$e done" >> PROGRESS.txt; done
echo ALLDONE
