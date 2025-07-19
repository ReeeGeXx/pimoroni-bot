from trilobot import Trilobot
import cv2
import time
import requests
import os
from dotenv import load_dotenv

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

# --- CONFIG ---
VIDEO_PATH = "recorded_video.mp4"
BLURRED_PATH = "blurred_video.mp4"
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:5000/upload_and_process")
QUERY = "Find all faces and license plates"

# --- MOVEMENT & RECORDING ---
tbot = Trilobot()
cap = cv2.VideoCapture(0)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(VIDEO_PATH, fourcc, 20.0, (640, 480))

print("Moving forward and recording video...")
tbot.forward(0.5)
start = time.time()
while time.time() - start < 5:
    ret, frame = cap.read()
    if ret:
        out.write(frame)
tbot.stop()
cap.release()
out.release()
print("Video recorded and robot stopped.")

# --- UPLOAD TO BACKEND ---
print(f"Uploading video to backend for processing at {BACKEND_URL} ...")
with open(VIDEO_PATH, "rb") as f:
    files = {"video": f}
    data = {"query": QUERY}
    response = requests.post(BACKEND_URL, files=files, data=data)
    result = response.json()
    print("Backend response:")
    print(result)

# --- PARSE DETECTIONS ---
def parse_detections(result):
    detections = []
    # Example for Marengo results with bounding boxes and timestamps
    marengo = result.get('results', {}).get('marengo', {})
    if 'segments' in marengo:
        for seg in marengo['segments']:
            # Example: adjust these keys to match your backend's response format
            start_frame = int(seg.get('start_frame', 0))
            end_frame = int(seg.get('end_frame', 0))
            for obj in seg.get('objects', []):
                x, y, w, h = obj['x'], obj['y'], obj['w'], obj['h']
                detections.append((start_frame, end_frame, x, y, w, h))
    # You can add similar parsing for Pegasus if needed
    return detections

detections = parse_detections(result)
if not detections:
    print("No detections found to blur.")
    exit(0)

# --- BLUR VIDEO ---
print("Blurring detected regions in video...")
cap = cv2.VideoCapture(VIDEO_PATH)
out = cv2.VideoWriter(BLURRED_PATH, fourcc, 20.0, (640, 480))
frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    for det in detections:
        start_f, end_f, x, y, w, h = det
        if start_f <= frame_idx <= end_f:
            roi = frame[y:y+h, x:x+w]
            roi = cv2.GaussianBlur(roi, (51, 51), 0)
            frame[y:y+h, x:x+w] = roi
    out.write(frame)
    frame_idx += 1
cap.release()
out.release()
print(f"Blurred video saved to {BLURRED_PATH}")

# To use a custom backend URL, set BACKEND_URL in your .env file:
# BACKEND_URL=http://<YOUR_BACKEND_IP>:5000/upload_and_process