#!/bin/bash
# Crossfade two 1080x1920 30fps b-roll clips (used for montage/tour joins: 0.5 s; shot-to-shot inside a b-roll beat: 9 frames = 0.3 s).
# Usage: broll_xfade.sh a.mp4 b.mp4 out.mp4 [xfade_seconds=0.5]
set -e; A="$1"; B="$2"; O="$3"; X="${4:-0.5}"
DA=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$A"); OFF=$(python3 -c "print(round($DA-$X,4))")
ffmpeg -v error -y -i "$A" -i "$B" -filter_complex "[0:v]settb=AVTB,fps=30[a];[1:v]settb=AVTB,fps=30[b];[a][b]xfade=transition=fade:duration=$X:offset=$OFF,format=yuv420p[v]" \
  -map "[v]" -c:v libx264 -crf 14 -preset medium -an "$O"
# Tour/stitch grade we used: -vf "eq=contrast=1.04:saturation=1.06,vignette=PI/5" and a 0.6 s fade-out at the end (fade=t=out:st=<dur-0.6>:d=0.6)
