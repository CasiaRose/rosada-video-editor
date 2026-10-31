#!/bin/bash
# Concat chunks (with explicit durations, or the concat demuxer drifts), mux the mix, tag BT.709, faststart, then the phone copy.
# Usage: assemble.sh <out_master.mp4> [phone_out.mp4]
set -e; cd "$(dirname "$0")"; OUT="$1"; PHONE="${2:-${OUT%.mp4}-phone.mp4}"
N=$(python3 -c "import json;print(json.load(open('timeline.json'))['N'])"); DUR=$(python3 -c "print(f'{$N/30:.4f}')")
python3 - <<PY
import glob, os
fs = sorted(f for f in glob.glob('render/chunk_*.mp4') if 'part' not in f); st = [int(f[-8:-4]) for f in fs] + [$N]
open('render/list.txt', 'w').write(''.join(f"file '{os.path.basename(f)}'\nduration {(st[i+1]-st[i])/30:.6f}\n" for i, f in enumerate(fs)))
PY
ffmpeg -v error -y -f concat -safe 0 -i render/list.txt -c copy render/video_noaudio.mp4
ffmpeg -v error -y -i render/video_noaudio.mp4 -i audio/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -bsf:v h264_metadata=colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1:video_full_range_flag=0 \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -movflags +faststart -t "$DUR" "$OUT"
# phone preview copy (~15-18 MB for ~60 s): re-encode, crf 25.5 slow, AAC 128k, faststart
ffmpeg -v error -y -i "$OUT" -c:v libx264 -profile:v high -preset slow -crf ${PHONE_CRF:-25.5} -pix_fmt yuv420p \
  -color_primaries bt709 -color_trc bt709 -colorspace bt709 -color_range tv -c:a aac -b:a 128k -movflags +faststart "$PHONE"
ls -l "$OUT" "$PHONE"; ffprobe -v error -show_entries stream=codec_type,nb_frames:format=duration,size -of compact "$OUT"
