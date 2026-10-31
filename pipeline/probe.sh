#!/bin/bash
# Intake probe. Usage: probe.sh raw.mov   -> prints video/audio facts incl. the AAC start offset (A/V offset) you MUST honour.
set -e; f="$1"
sha256sum "$f"
ffprobe -v error -show_entries stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,nb_frames,start_time,sample_rate,channels,color_space,color_transfer,color_primaries:stream_tags=rotate:format=duration,size -of compact "$f"
echo "--- audio start_time (= A/V offset to pad before ASR / VO):"
ffprobe -v error -select_streams a:0 -show_entries stream=start_time -of csv=p=0 "$f"
echo "--- loudness of raw"
ffmpeg -nostats -i "$f" -vn -af ebur128 -f null - 2>&1 | grep -E "I:|LRA:" | tail -2
