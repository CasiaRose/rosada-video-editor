# Progress border
- One command: `./border.sh in.mp4 out.mp4`. It reads the frame count, draws a Primary→Coral stroke clockwise from the top-left so it closes on the last frame, and copies the audio.
- Overlay approach: `python3 border.py --overlay <frames> border.mov` gives a transparent qtrle MOV. Then run `ffmpeg -i in.mp4 -i border.mov -filter_complex "[0][1]overlay" ...`. The overlay must have the same frame count as the video.
- Geometry (approved): inset 12.35 px, stroke 6, radius 26, 10% Paper track, glow σ6.4, Paper head dot r7 with a Coral glow.
