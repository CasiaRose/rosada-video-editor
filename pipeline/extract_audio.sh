#!/bin/bash
# Put the audio on the VIDEO clock (pad the AAC start offset), so every timestamp downstream is video time.
# Usage: extract_audio.sh raw.mov [outdir]   -> audio/raw48_vc.wav (48k mono f32) + audio/audio_vc_16k.wav (for ASR)
set -e; f="$1"; o="${2:-audio}"; mkdir -p "$o"
off=$(ffprobe -v error -select_streams a:0 -show_entries stream=start_time -of csv=p=0 "$f"); ms=$(python3 -c "print(round(float('${off:-0}')*1000))")
echo "A/V offset ${ms} ms"
ffmpeg -v error -y -i "$f" -vn -af "adelay=${ms}:all=1,aresample=48000" -ac 1 -c:a pcm_f32le "$o/raw48_vc.wav"
ffmpeg -v error -y -i "$o/raw48_vc.wav" -ar 16000 -ac 1 -c:a pcm_s16le "$o/audio_vc_16k.wav"
echo "$ms" > "$o/av_offset_ms.txt"
