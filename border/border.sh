#!/usr/bin/env bash
# One command: input video in, bordered video out.   border/border.sh in.mp4 out.mp4
exec python3 "$(dirname "$0")/border.py" "$1" "$2"
