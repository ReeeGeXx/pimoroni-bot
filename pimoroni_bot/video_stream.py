import cv2
from flask import Flask, Response, request, jsonify
from pimoroni_bot.blur import blur_faces
import threading
import os
import requests
from pimoroni_bot.config import TWELVELABS_API_KEY
import numpy as np
import base64
import time

VIDEO_PATH = "recorded_video.mp4"
BLURRED_PATH = "blurred_video.mp4"

app = Flask(__name__)
cap = cv2.VideoCapture(0)

RECORD_VIDEO = False
out = None

# Shared state for prompt and detection mode
DETECTION_MODE = 'local'  # 'local' or 'api'
DETECTION_PROMPT = ''

# --- Real Marengo API-based detection and blurring ---
def blur_with_api(frame, prompt):
    if not TWELVELABS_API_KEY or not prompt:
        return frame
    # Resize for faster upload
    frame_small = cv2.resize(frame, (320, 240))
    # Encode frame as JPEG and then base64
    ret, buf = cv2.imencode('.jpg', frame_small)
    if not ret:
        return frame
    img_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
    # Prepare API request
    url = "https://api.twelvelabs.io/v1.3/search"
    headers = {
        'x-api-key': TWELVELABS_API_KEY,
        'Content-Type': 'application/json'
    }
    payload = {
        "query": prompt,
        "image": img_b64,
        "model": "marengo-1.3"
    }
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        res.raise_for_status()
        data = res.json()
        # Parse bounding boxes from Marengo response
        # (Assume response format: data['results'][0]['bbox'] = [x, y, w, h] in 320x240 space)
        for result in data.get('results', []):
            bbox = result.get('bbox')
            if bbox and len(bbox) == 4:
                x, y, w, h = map(int, bbox)
                # Scale bbox to original frame size
                x = int(x * frame.shape[1] / 320)
                w = int(w * frame.shape[1] / 320)
                y = int(y * frame.shape[0] / 240)
                h = int(h * frame.shape[0] / 240)
                roi = frame[y:y+h, x:x+w]
                roi = cv2.GaussianBlur(roi, (51, 51), 0)
                frame[y:y+h, x:x+w] = roi
    except Exception as e:
        print(f"API error: {e}")
    return frame

# --- Video stream generator ---
def gen_frames():
    while True:
        success, frame = cap.read()
        if not success:
            break
        if DETECTION_MODE == 'local':
            frame = blur_faces(frame)
        elif DETECTION_MODE == 'api' and DETECTION_PROMPT:
            frame = blur_with_api(frame, DETECTION_PROMPT)
        if RECORD_VIDEO and out:
            out.write(frame)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/record_and_analyze', methods=['POST'])
def record_and_analyze():
    data = request.get_json()
    prompt = data.get('prompt', '').strip() or 'Find all faces'
    duration = int(data.get('duration', 10))  # seconds
    # 1. Record video
    cap = cv2.VideoCapture(0)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(VIDEO_PATH, fourcc, 20.0, (640, 480))
    start = time.time()
    while time.time() - start < duration:
        ret, frame = cap.read()
        if ret:
            out.write(frame)
    cap.release()
    out.release()
    # 2. Upload to TwelveLabs
    with open(VIDEO_PATH, "rb") as f:
        files = {"file": f}
        headers = {"x-api-key": TWELVELABS_API_KEY}
        upload_res = requests.post("https://api.twelvelabs.io/v1.3/videos/upload", files=files, headers=headers)
        upload_res.raise_for_status()
        video_id = upload_res.json().get("video_id")
    # 3. Wait for indexing
    status = "processing"
    while status != "ready":
        time.sleep(5)
        res = requests.get(f"https://api.twelvelabs.io/v1.3/videos/{video_id}", headers=headers)
        res.raise_for_status()
        status = res.json().get("status")
        if status == "failed":
            return jsonify({"error": "Indexing failed"}), 500
    # 4. Search with prompt
    search_payload = {
        "video_id": video_id,
        "query": prompt,
        "model": "marengo-1.3"
    }
    search_res = requests.post("https://api.twelvelabs.io/v1.3/search", json=search_payload, headers=headers)
    search_res.raise_for_status()
    results = search_res.json()
    # 5. Blur detected regions (assume results['results'] contains segments with bounding boxes and timestamps)
    detections = []
    for seg in results.get('results', []):
        # Example: adjust keys to match actual API response
        start_frame = int(seg.get('start_frame', 0))
        end_frame = int(seg.get('end_frame', 0))
        for obj in seg.get('objects', []):
            x, y, w, h = obj['x'], obj['y'], obj['w'], obj['h']
            detections.append((start_frame, end_frame, x, y, w, h))
    # Blur video
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
    return jsonify({"blurred_video": BLURRED_PATH})

@app.route('/')
def index():
    # UI with prompt input and Record & Analyze button
    return '''
    <h1>Record & Analyze with TwelveLabs</h1>
    <p>Click the button to record a short video, analyze with your prompt, and blur detected regions.</p>
    <form id="promptForm">
        <label>Blur Prompt (leave blank for face blur):</label>
        <input type="text" id="blurPrompt" name="blurPrompt" placeholder="e.g. license plates">
        <button type="button" onclick="recordAndAnalyze()">Record & Analyze</button>
    </form>
    <div id="status"></div>
    <div id="videoResult"></div>
    <script>
    async function recordAndAnalyze() {
        document.getElementById('status').innerText = 'Recording and analyzing...';
        const prompt = document.getElementById('blurPrompt').value;
        const res = await fetch('/record_and_analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (data.blurred_video) {
            document.getElementById('status').innerText = 'Done!';
            document.getElementById('videoResult').innerHTML = `<video src="/${data.blurred_video}" controls width="480"></video>`;
        } else {
            document.getElementById('status').innerText = 'Error: ' + (data.error || 'Unknown error');
        }
    }
    </script>
    '''

# --- Endpoint to set blur prompt and detection mode ---
@app.route('/set_prompt', methods=['POST'])
def set_prompt():
    global DETECTION_MODE, DETECTION_PROMPT
    data = request.get_json()
    prompt = data.get('prompt', '').strip()
    if prompt:
        DETECTION_MODE = 'api'
        DETECTION_PROMPT = prompt
    else:
        DETECTION_MODE = 'local'
        DETECTION_PROMPT = ''
    return jsonify({'mode': DETECTION_MODE, 'prompt': DETECTION_PROMPT}) 