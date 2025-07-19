import cv2
from flask import Flask, Response, request, jsonify
from pimoroni_bot.blur import blur_faces
import threading
import os
import requests
from pimoroni_bot.config import TWELVELABS_API_KEY
import numpy as np
import base64

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

@app.route('/')
def index():
    # Simple UI with prompt input only
    return '''
    <h1>Live Stream (Blurred)</h1>
    <p>Prompt-based blurring using TwelveLabs Marengo API.</p>
    <img src="/video_feed" style="max-width: 100%; height: auto; border: 1px solid #ccc;"><br><br>
    <form id="promptForm">
        <label>Blur Prompt (leave blank for face blur):</label>
        <input type="text" id="blurPrompt" name="blurPrompt" placeholder="e.g. license plates">
        <button type="submit">Set Blur Prompt</button>
    </form>
    <p id="detectionMode"></p>
    <script>
    document.getElementById('promptForm').onsubmit = async function(e) {
        e.preventDefault();
        const prompt = document.getElementById('blurPrompt').value;
        const res = await fetch('/set_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        document.getElementById('detectionMode').innerText = 'Detection mode: ' + data.mode + (data.prompt ? ' ("' + data.prompt + '")' : '');
    };
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