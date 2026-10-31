#!/usr/bin/env bash
# finish.sh in.mp4 cues.json out.mp4   -> optional border, ducked bed, effects, loudness from the cue file, then checks
set -e; D="$(cd "$(dirname "$0")" && pwd)"
python3 "$D/finish.py" "$1" "$2" "$3"
python3 "$D/../qa/verify.py" "$3" "$2"
