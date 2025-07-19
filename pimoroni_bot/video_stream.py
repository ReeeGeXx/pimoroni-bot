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
import atexit

# Import Trilobot for motor control
try:
    from trilobot import Trilobot
    tbot = Trilobot()
    TRILOBOT_AVAILABLE = True
except ImportError:
    print("Trilobot not available - motor control will be simulated")
    tbot = None
    TRILOBOT_AVAILABLE = False

# Cleanup function to stop motors on exit
def cleanup_motors():
    if TRILOBOT_AVAILABLE and tbot:
        print("Stopping motors and cleaning up...")
        tbot.stop()
        tbot.coast()

# Register cleanup function
atexit.register(cleanup_motors)

VIDEO_PATH = "recorded_video.mp4"
BLURRED_PATH = "blurred_video.mp4"

app = Flask(__name__)
cap = cv2.VideoCapture(0)

RECORD_VIDEO = False
out = None

# Shared state for prompt and detection mode
DETECTION_MODE = 'local'  # 'local' or 'api'
DETECTION_PROMPT = ''

# Motor control functions
def move_forward(speed=0.5):
    if TRILOBOT_AVAILABLE:
        tbot.forward(speed)
    else:
        print(f"SIMULATION: Moving forward at speed {speed}")

def move_backward(speed=0.5):
    if TRILOBOT_AVAILABLE:
        tbot.backward(speed)
    else:
        print(f"SIMULATION: Moving backward at speed {speed}")

def turn_left(speed=0.5):
    if TRILOBOT_AVAILABLE:
        tbot.turn_left(speed)
    else:
        print(f"SIMULATION: Turning left at speed {speed}")

def turn_right(speed=0.5):
    if TRILOBOT_AVAILABLE:
        tbot.turn_right(speed)
    else:
        print(f"SIMULATION: Turning right at speed {speed}")

def stop_motors():
    if TRILOBOT_AVAILABLE:
        tbot.stop()
    else:
        print("SIMULATION: Stopping motors")

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
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pimoroni Bot Control</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
            .container { max-width: 1200px; margin: 0 auto; }
            .section { background: white; padding: 20px; margin: 20px 0; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .video-container { text-align: center; }
            .video-feed { max-width: 100%; border: 2px solid #333; border-radius: 5px; }
            .motor-controls { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; max-width: 300px; margin: 20px auto; }
            .motor-btn { padding: 15px; font-size: 18px; border: none; border-radius: 5px; cursor: pointer; transition: background 0.3s; }
            .motor-btn:hover { opacity: 0.8; }
            .forward { background: #4CAF50; color: white; grid-column: 2; }
            .backward { background: #f44336; color: white; grid-column: 2; }
            .left { background: #2196F3; color: white; grid-column: 1; grid-row: 2; }
            .right { background: #2196F3; color: white; grid-column: 3; grid-row: 2; }
            .stop { background: #FF9800; color: white; grid-column: 2; grid-row: 3; }
            .analysis-section { margin-top: 20px; }
            .form-group { margin: 10px 0; }
            .form-group input, .form-group button { padding: 10px; margin: 5px; border: 1px solid #ddd; border-radius: 3px; }
            .form-group button { background: #007bff; color: white; cursor: pointer; }
            .form-group button:hover { background: #0056b3; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .status.success { background: #d4edda; color: #155724; }
            .status.error { background: #f8d7da; color: #721c24; }
            .status.info { background: #d1ecf1; color: #0c5460; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Pimoroni Bot Control</h1>
            
            <!-- Live Video Stream -->
            <div class="section">
                <h2>📹 Live Video Stream</h2>
                <div class="video-container">
                    <img src="/video_feed" class="video-feed" alt="Live video feed">
                </div>
            </div>
            
            <!-- Motor Controls -->
            <div class="section">
                <h2>🎮 Motor Controls</h2>
                <div class="motor-controls">
                    <button class="motor-btn forward" onclick="controlMotor('forward')">⬆️ Forward</button>
                    <button class="motor-btn backward" onclick="controlMotor('backward')">⬇️ Backward</button>
                    <button class="motor-btn left" onclick="controlMotor('left')">⬅️ Left</button>
                    <button class="motor-btn right" onclick="controlMotor('right')">➡️ Right</button>
                    <button class="motor-btn stop" onclick="controlMotor('stop')">⏹️ Stop</button>
                </div>
                <div id="motorStatus" class="status info">Motor status: Ready</div>
            </div>
            
            <!-- Analysis Controls -->
            <div class="section analysis-section">
                <h2>🔍 Video Analysis & Blurring</h2>
                <div class="form-group">
                    <label>Analysis Prompt:</label>
                    <input type="text" id="blurPrompt" placeholder="e.g. Analyze for faces and license plates">
                    <button onclick="recordAndAnalyze()">🎬 Record & Analyze</button>
                </div>
                <div id="analysisStatus" class="status"></div>
                <div id="analysisResults"></div>
            </div>
        </div>

        <script>
        // Motor control functions
        async function controlMotor(action) {
            const statusDiv = document.getElementById('motorStatus');
            statusDiv.className = 'status info';
            statusDiv.textContent = `Executing: ${action}...`;
            
            try {
                const response = await fetch(`/motor/${action}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ speed: 0.5 })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    statusDiv.className = 'status success';
                    statusDiv.textContent = `✅ ${action} executed successfully`;
                } else {
                    throw new Error('Motor control failed');
                }
            } catch (error) {
                statusDiv.className = 'status error';
                statusDiv.textContent = `❌ Error: ${error.message}`;
            }
        }

        // Analysis functions
        async function recordAndAnalyze() {
            const statusDiv = document.getElementById('analysisStatus');
            const resultsDiv = document.getElementById('analysisResults');
            
            statusDiv.className = 'status info';
            statusDiv.textContent = 'Recording and analyzing...';
            resultsDiv.innerHTML = '';
            
            const prompt = document.getElementById('blurPrompt').value;
            
            try {
                const res = await fetch('/record_and_analyze', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });
                const data = await res.json();
                
                if (data.blurred_video) {
                    statusDiv.className = 'status success';
                    statusDiv.textContent = '✅ Analysis complete!';
                    resultsDiv.innerHTML = `
                        <h3>📊 TwelveLabs Analysis:</h3>
                        <p>${data.twelvelabs_analysis}</p>
                        <h3>🎯 Detection Types:</h3>
                        <p>${data.detection_types.join(', ')}</p>
                        <h3>🎥 Blurred Video:</h3>
                        <video src="/${data.blurred_video}" controls width="480"></video>
                    `;
                } else {
                    throw new Error(data.error || 'Unknown error');
                }
            } catch (error) {
                statusDiv.className = 'status error';
                statusDiv.textContent = `❌ Error: ${error.message}`;
            }
        }

        // Check motor status on page load
        window.onload = async function() {
            try {
                const response = await fetch('/motor/status');
                const data = await response.json();
                const statusDiv = document.getElementById('motorStatus');
                
                if (data.trilobot_available) {
                    statusDiv.className = 'status success';
                    statusDiv.textContent = '✅ Trilobot connected and ready';
                } else {
                    statusDiv.className = 'status info';
                    statusDiv.textContent = '⚠️ Trilobot not available - running in simulation mode';
                }
            } catch (error) {
                console.error('Failed to check motor status:', error);
            }
        };
        </script>
    </body>
    </html>
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

# --- Motor Control Endpoints ---
@app.route('/motor/forward', methods=['POST'])
def motor_forward():
    data = request.get_json() or {}
    speed = data.get('speed', 0.5)
    move_forward(speed)
    return jsonify({'status': 'success', 'action': 'forward', 'speed': speed})

@app.route('/motor/backward', methods=['POST'])
def motor_backward():
    data = request.get_json() or {}
    speed = data.get('speed', 0.5)
    move_backward(speed)
    return jsonify({'status': 'success', 'action': 'backward', 'speed': speed})

@app.route('/motor/left', methods=['POST'])
def motor_left():
    data = request.get_json() or {}
    speed = data.get('speed', 0.5)
    turn_left(speed)
    return jsonify({'status': 'success', 'action': 'left', 'speed': speed})

@app.route('/motor/right', methods=['POST'])
def motor_right():
    data = request.get_json() or {}
    speed = data.get('speed', 0.5)
    turn_right(speed)
    return jsonify({'status': 'success', 'action': 'right', 'speed': speed})

@app.route('/motor/stop', methods=['POST'])
def motor_stop():
    stop_motors()
    return jsonify({'status': 'success', 'action': 'stop'})

@app.route('/motor/status', methods=['GET'])
def motor_status():
    return jsonify({
        'trilobot_available': TRILOBOT_AVAILABLE,
        'status': 'ready'
    }) 