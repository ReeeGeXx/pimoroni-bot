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
import re

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

def analyze_with_twelvelabs(video_path):
    """Upload video to TwelveLabs and get analysis"""
    if not TWELVELABS_API_KEY:
        return "No API key available"
    
    # Upload video to TwelveLabs
    with open(video_path, "rb") as f:
        files = {"file": f}
        headers = {"x-api-key": TWELVELABS_API_KEY}
        try:
            upload_res = requests.post("https://api.twelvelabs.io/v1.3/videos", files=files, headers=headers)
            upload_res.raise_for_status()
            video_id = upload_res.json().get("video_id")
        except Exception as e:
            return f"Upload failed: {e}"
    
    # Wait for indexing
    status = "processing"
    while status != "ready":
        time.sleep(5)
        try:
            res = requests.get(f"https://api.twelvelabs.io/v1.3/videos/{video_id}", headers=headers)
            res.raise_for_status()
            status = res.json().get("status")
            if status == "failed":
                return "Indexing failed"
        except Exception as e:
            return f"Status check failed: {e}"
    
    # Get analysis using the analyze endpoint
    analyze_payload = {
        "video_id": video_id,
        "query": "Describe all objects, people, faces, license plates, and sensitive content in this video",
        "model": "pegasus-1.3"
    }
    try:
        analyze_res = requests.post("https://api.twelvelabs.io/v1.3/analyze", json=analyze_payload, headers=headers)
        analyze_res.raise_for_status()
        analysis = analyze_res.json()
        return analysis.get("data", {}).get("text", "No analysis available")
    except Exception as e:
        return f"Analysis failed: {e}"

def parse_analysis_for_detection(analysis_text):
    """Parse TwelveLabs analysis to determine what to detect locally"""
    analysis_lower = analysis_text.lower()
    detection_types = []
    
    # Check for different types of content
    if any(word in analysis_lower for word in ["face", "faces", "person", "people", "human"]):
        detection_types.append("faces")
    if any(word in analysis_lower for word in ["license plate", "license plates", "plate", "plates", "car", "vehicle"]):
        detection_types.append("license_plates")
    if any(word in analysis_lower for word in ["text", "sign", "document", "paper"]):
        detection_types.append("text")
    if any(word in analysis_lower for word in ["sensitive", "private", "confidential"]):
        detection_types.append("sensitive")
    
    return detection_types

def detect_and_blur_locally(video_path, detection_types):
    """Use local OpenCV to detect objects based on TwelveLabs analysis"""
    cap = cv2.VideoCapture(video_path)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(BLURRED_PATH, fourcc, 20.0, (640, 480))
    
    # Load detection models
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Apply detection based on TwelveLabs analysis
        if "faces" in detection_types:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            for (x, y, w, h) in faces:
                roi = frame[y:y+h, x:x+w]
                roi = cv2.GaussianBlur(roi, (51, 51), 0)
                frame[y:y+h, x:x+w] = roi
        
        # Add more detection types here as needed
        # if "license_plates" in detection_types:
        #     # Add license plate detection
        #     pass
        
        out.write(frame)
        frame_idx += 1
    
    cap.release()
    out.release()
    return BLURRED_PATH

@app.route('/record_and_analyze', methods=['POST'])
def record_and_analyze():
    data = request.get_json()
    prompt = data.get('prompt', '').strip() or 'Analyze this video for faces, license plates, and sensitive content'
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
    
    # 2. Analyze with TwelveLabs
    analysis = analyze_with_twelvelabs(VIDEO_PATH)
    if analysis.startswith("Upload failed") or analysis.startswith("Indexing failed") or analysis.startswith("Analysis failed"):
        return jsonify({"error": analysis}), 500
    
    # 3. Parse analysis for detection types
    detection_types = parse_analysis_for_detection(analysis)
    
    # 4. Detect and blur locally based on analysis
    blurred_path = detect_and_blur_locally(VIDEO_PATH, detection_types)
    
    return jsonify({
        "twelvelabs_analysis": analysis,
        "detection_types": detection_types,
        "blurred_video": blurred_path
    })

@app.route('/')
def index():
    # UI with prompt input and Record & Analyze button
    return '''
    <h1>TwelveLabs Analysis + Local Detection</h1>
    <p>Record a video, analyze with TwelveLabs, then detect and blur locally based on the analysis.</p>
    <form id="promptForm">
        <label>Analysis Prompt:</label>
        <input type="text" id="blurPrompt" name="blurPrompt" placeholder="e.g. Analyze for faces and license plates">
        <button type="button" onclick="recordAndAnalyze()">Record & Analyze</button>
    </form>
    <div id="status"></div>
    <div id="analysis"></div>
    <div id="videoResult"></div>
    <script>
    async function recordAndAnalyze() {
        document.getElementById('status').innerText = 'Recording and analyzing...';
        document.getElementById('analysis').innerText = '';
        const prompt = document.getElementById('blurPrompt').value;
        const res = await fetch('/record_and_analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        if (data.blurred_video) {
            document.getElementById('status').innerText = 'Done!';
            document.getElementById('analysis').innerHTML = '<h3>TwelveLabs Analysis:</h3><p>' + data.twelvelabs_analysis + '</p><h3>Detection Types:</h3><p>' + data.detection_types.join(', ') + '</p>';
            document.getElementById('videoResult').innerHTML = '<h3>Blurred Video:</h3><video src="/' + data.blurred_video + '" controls width="480"></video>';
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