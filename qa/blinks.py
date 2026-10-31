"""Blink + face landmark scan of the RAW take (MediaPipe FaceLandmarker blendshapes). Usage: python blinks.py [face_landmarker.task]
Download the model once: https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
Writes scratch/blinks_raw.json (per raw frame: blink score, face centroid/width) and scratch/blink_groups.json ([first,last] raw frames, blink>0.45)."""
import cv2, numpy as np, json, subprocess, sys, os, mediapipe as mp
from mediapipe.tasks import python as mpp
from mediapipe.tasks.python import vision
cfg = json.load(open("config.json")); model = sys.argv[1] if len(sys.argv) > 1 else "face_landmarker.task"
lm = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(base_options=mpp.BaseOptions(model_asset_path=model),
     output_face_blendshapes=True, running_mode=vision.RunningMode.VIDEO, num_faces=1))
W, H = 540, 960; os.makedirs("scratch", exist_ok=True)
p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", cfg["raw"], "-vf", f"scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
res = []; n = 0
while True:
    b = p.stdout.read(W * H * 3)
    if len(b) < W * H * 3: break
    f = np.frombuffer(b, np.uint8).reshape(H, W, 3)
    r = lm.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(f)), int(n * 1000 / 30))
    if r.face_blendshapes:
        bs = {c.category_name: c.score for c in r.face_blendshapes[0]}; pts = np.array([(q.x, q.y) for q in r.face_landmarks[0]])
        res.append(dict(n=n, blink=round((bs["eyeBlinkLeft"] + bs["eyeBlinkRight"]) / 2, 3), jaw=round(bs["jawOpen"], 3),
                        cx=round(float(pts[:, 0].mean()), 4), cy=round(float(pts[:, 1].mean()), 4), w=round(float(np.ptp(pts[:, 0])), 4)))
    else: res.append(dict(n=n, blink=None))
    n += 1
json.dump(res, open("scratch/blinks_raw.json", "w"))
g = []
for k in [r["n"] for r in res if r["blink"] is not None and r["blink"] > 0.45]:
    if g and k - g[-1][1] <= 2: g[-1][1] = k
    else: g.append([k, k])
json.dump(g, open("scratch/blink_groups.json", "w")); print(n, "frames", len(g), "blinks; long (>=7 fr, must be covered by B-roll/panel):", [x for x in g if x[1] - x[0] >= 6])
