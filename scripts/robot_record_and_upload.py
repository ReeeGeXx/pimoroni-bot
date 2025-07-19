from trilobot import Trilobot
import cv2
import time
import requests

# --- CONFIG ---
VIDEO_PATH = "recorded_video.mp4"
BACKEND_URL = "http://<YOUR_BACKEND_IP>:5000/upload_and_process"  # <-- Set your backend IP here
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
print("Uploading video to backend for processing...")
with open(VIDEO_PATH, "rb") as f:
    files = {"video": f}
    data = {"query": QUERY}
    response = requests.post(BACKEND_URL, files=files, data=data)
    print("Backend response:")
    print(response.json())