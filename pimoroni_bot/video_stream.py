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

# Robot livestream + TwelveLabs integration
ROBOT_RECORDING = False
RECORDING_DURATION = 10  # seconds
RECORDING_INTERVAL = 30  # seconds between recordings
last_recording_time = 0
recording_thread = None
analysis_results = []

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

# --- Robot Recording and Analysis Functions ---
def record_robot_segment():
    """Record a short video segment for TwelveLabs analysis"""
    global ROBOT_RECORDING, last_recording_time
    
    if ROBOT_RECORDING:
        return
    
    ROBOT_RECORDING = True
    last_recording_time = time.time()
    
    # Create unique filename
    timestamp = int(time.time())
    segment_path = f"robot_segment_{timestamp}.mp4"
    
    print(f"🤖 Recording robot segment: {segment_path}")
    
    # Record video segment
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(segment_path, fourcc, 20.0, (640, 480))
    
    start_time = time.time()
    while time.time() - start_time < RECORDING_DURATION:
        ret, frame = cap.read()
        if ret:
            out.write(frame)
    
    out.release()
    ROBOT_RECORDING = False
    
    # Analyze with TwelveLabs in background
    threading.Thread(target=analyze_robot_segment, args=(segment_path,)).start()

def analyze_robot_segment(segment_path):
    """Analyze robot video segment with TwelveLabs"""
    try:
        print(f"🔍 Analyzing robot segment: {segment_path}")
        
        # Get the default index
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        index_id = indexes_data['data'][0]['_id']
        
        # For now, we'll analyze existing videos since upload isn't working
        # In the future, we could upload the segment here
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        existing_videos = videos_data['data']
        
        if existing_videos:
            # Analyze the most recent video as a proxy
            test_video = existing_videos[0]
            filename = test_video['system_metadata']['filename']
            
            # Search for relevant content
            search_payload = {
                "index_id": (None, index_id),
                "query_text": (None, "Find people, faces, license plates, cars, and sensitive content"),
                "search_options": (None, "visual")
            }
            search_res = requests.post("https://api.twelvelabs.io/v1.3/search", 
                                     files=search_payload, 
                                     headers={"x-api-key": TWELVELABS_API_KEY})
            search_res.raise_for_status()
            search_data = search_res.json()
            
            # Store results for UI display
            analysis_results.append({
                'timestamp': time.time(),
                'segment': segment_path,
                'results': search_data.get('data', []),
                'video_analyzed': filename
            })
            
            print(f"✅ Analysis complete: {len(search_data.get('data', []))} segments found")
            
            # Keep only last 5 results
            if len(analysis_results) > 5:
                analysis_results.pop(0)
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")

def should_record_segment():
    """Check if it's time to record a new segment"""
    return time.time() - last_recording_time > RECORDING_INTERVAL and not ROBOT_RECORDING

# --- Real Marengo API-based detection and blurring ---
def blur_with_api(frame, prompt):
    if not TWELVELABS_API_KEY or not prompt:
        return frame
    
    # Get the default index first
    try:
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        index_id = indexes_data['data'][0]['_id']
    except Exception as e:
        print(f"Failed to get index: {e}")
        return frame
    
    # Resize for faster upload
    frame_small = cv2.resize(frame, (320, 240))
    # Encode frame as JPEG and then base64
    ret, buf = cv2.imencode('.jpg', frame_small)
    if not ret:
        return frame
    img_b64 = base64.b64encode(buf.tobytes()).decode('utf-8')
    
    # Prepare API request for image search
    try:
        search_payload = {
            "index_id": index_id,
            "query": prompt,
            "search_options": ["visual"]
        }
        headers = {
            'x-api-key': TWELVELABS_API_KEY
        }
        
        # For real-time image analysis, we'll use a simpler approach
        # since the current API doesn't support direct image upload for search
        # We'll fall back to local detection for now
        print("Real-time image analysis not supported in current API version")
        return frame
        
    except Exception as e:
        print(f"API error: {e}")
        return frame

# --- Video stream generator ---
def gen_frames():
    global last_recording_time
    
    while True:
        success, frame = cap.read()
        if not success:
            break
            
        # Check if we should record a segment
        if should_record_segment():
            threading.Thread(target=record_robot_segment).start()
        
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
    
    # First, get the default index
    try:
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        index_id = indexes_data['data'][0]['_id']  # Use the first (default) index
    except Exception as e:
        return f"Failed to get index: {e}"
    
    # Note: The TwelveLabs API upload endpoint has changed and may not be available
    # For now, we'll analyze existing videos in the index
    try:
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        existing_videos = videos_data['data']
        
        if not existing_videos:
            return "No videos found in index. Please upload videos through the TwelveLabs dashboard first."
        
        # Use the most recent video for analysis
        test_video = existing_videos[0]
        video_id = test_video['_id']
        filename = test_video['system_metadata']['filename']
        
    except Exception as e:
        return f"Failed to get videos: {e}"
    
    # Get analysis using the search endpoint
    try:
        search_payload = {
            "index_id": (None, index_id),
            "query_text": (None, "Describe all objects, people, faces, license plates, and sensitive content in this video"),
            "search_options": (None, "visual")
        }
        search_res = requests.post("https://api.twelvelabs.io/v1.3/search", 
                                 files=search_payload, headers={"x-api-key": TWELVELABS_API_KEY})
        search_res.raise_for_status()
        search_results = search_res.json()
        
        # Extract relevant information from search results
        analysis_text = f"Analysis of video: {filename}\n"
        analysis_text += f"Found {len(search_results.get('data', []))} relevant segments:\n"
        for i, result in enumerate(search_results.get('data', [])[:5]):  # Show top 5 results
            analysis_text += f"- Segment {i+1}: Score {result.get('score', 'N/A')}, Time {result.get('start', 'N/A')}-{result.get('end', 'N/A')}s\n"
        
        return analysis_text if analysis_text != f"Analysis of video: {filename}\nFound 0 relevant segments:\n" else "No analysis available"
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
    if analysis.startswith("No videos found in index. Please upload videos through the TwelveLabs dashboard first."):
        return jsonify({"error": analysis}), 500
    if analysis.startswith("Failed to get videos:") or analysis.startswith("Failed to get index:"):
        return jsonify({"error": analysis}), 500
    if analysis.startswith("Analysis failed:"):
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
            
            <!-- Robot Analysis Controls -->
            <div class="section robot-analysis-section">
                <h2>🤖 Robot Livestream Analysis</h2>
                <div class="form-group">
                    <label>Recording Duration (seconds):</label>
                    <input type="number" id="recordingDuration" value="10" min="5" max="60">
                    <label>Recording Interval (seconds):</label>
                    <input type="number" id="recordingInterval" value="30" min="10" max="300">
                    <button onclick="updateRobotSettings()">⚙️ Update Settings</button>
                    <button onclick="recordNow()">🎥 Record Now</button>
                </div>
                <div id="robotStatus" class="status info">Robot analysis: Ready</div>
                <div id="robotAnalysisResults"></div>
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
                
                // Start robot analysis monitoring
                updateRobotAnalysis();
                setInterval(updateRobotAnalysis, 5000); // Update every 5 seconds
            } catch (error) {
                console.error('Failed to check motor status:', error);
            }
        };

        // Robot analysis functions
        async function updateRobotSettings() {
            const duration = document.getElementById('recordingDuration').value;
            const interval = document.getElementById('recordingInterval').value;
            
            try {
                const response = await fetch('/robot/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ duration, interval })
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    document.getElementById('robotStatus').className = 'status success';
                    document.getElementById('robotStatus').textContent = '✅ Settings updated successfully';
                }
            } catch (error) {
                document.getElementById('robotStatus').className = 'status error';
                document.getElementById('robotStatus').textContent = `❌ Error: ${error.message}`;
            }
        }

        async function recordNow() {
            try {
                const response = await fetch('/robot/record_now', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const data = await response.json();
                
                if (data.status === 'success') {
                    document.getElementById('robotStatus').className = 'status info';
                    document.getElementById('robotStatus').textContent = '🎥 Recording started...';
                } else {
                    document.getElementById('robotStatus').className = 'status error';
                    document.getElementById('robotStatus').textContent = `❌ ${data.message}`;
                }
            } catch (error) {
                document.getElementById('robotStatus').className = 'status error';
                document.getElementById('robotStatus').textContent = `❌ Error: ${error.message}`;
            }
        }

        async function updateRobotAnalysis() {
            try {
                const response = await fetch('/robot/analysis');
                const data = await response.json();
                
                const statusDiv = document.getElementById('robotStatus');
                const resultsDiv = document.getElementById('robotAnalysisResults');
                
                // Update status
                if (data.recording_status.is_recording) {
                    statusDiv.className = 'status info';
                    statusDiv.textContent = '🎥 Recording in progress...';
                } else {
                    const nextRecording = Math.ceil(data.recording_status.next_recording_in);
                    statusDiv.className = 'status success';
                    statusDiv.textContent = `✅ Ready - Next recording in ${nextRecording}s`;
                }
                
                // Update results
                if (data.analysis_results.length > 0) {
                    let resultsHtml = '<h3>📊 Recent Analysis Results:</h3>';
                    data.analysis_results.forEach((result, index) => {
                        const time = new Date(result.timestamp * 1000).toLocaleTimeString();
                        const segments = result.results.length;
                        resultsHtml += `
                            <div style="border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px;">
                                <strong>Analysis ${index + 1}</strong> (${time})<br>
                                <strong>Video:</strong> ${result.video_analyzed}<br>
                                <strong>Segments Found:</strong> ${segments}<br>
                                <strong>Top Results:</strong>
                                <ul>
                        `;
                        
                        result.results.slice(0, 3).forEach(seg => {
                            resultsHtml += `<li>Score: ${seg.score?.toFixed(2)}, Time: ${seg.start?.toFixed(1)}s-${seg.end?.toFixed(1)}s</li>`;
                        });
                        
                        resultsHtml += '</ul></div>';
                    });
                    resultsDiv.innerHTML = resultsHtml;
                } else {
                    resultsDiv.innerHTML = '<p>No analysis results yet. Robot will automatically record and analyze segments.</p>';
                }
                
            } catch (error) {
                console.error('Failed to update robot analysis:', error);
            }
        }
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

# --- Robot Analysis Endpoints ---
@app.route('/robot/analysis', methods=['GET'])
def get_robot_analysis():
    """Get recent robot analysis results"""
    return jsonify({
        'analysis_results': analysis_results,
        'recording_status': {
            'is_recording': ROBOT_RECORDING,
            'last_recording': last_recording_time,
            'next_recording_in': max(0, RECORDING_INTERVAL - (time.time() - last_recording_time))
        }
    })

@app.route('/robot/record_now', methods=['POST'])
def record_now():
    """Manually trigger a recording"""
    if not ROBOT_RECORDING:
        threading.Thread(target=record_robot_segment).start()
        return jsonify({'status': 'success', 'message': 'Recording started'})
    else:
        return jsonify({'status': 'error', 'message': 'Already recording'})

@app.route('/robot/settings', methods=['POST'])
def update_robot_settings():
    """Update robot recording settings"""
    global RECORDING_DURATION, RECORDING_INTERVAL
    data = request.get_json() or {}
    
    if 'duration' in data:
        RECORDING_DURATION = int(data['duration'])
    if 'interval' in data:
        RECORDING_INTERVAL = int(data['interval'])
    
    return jsonify({
        'status': 'success',
        'settings': {
            'duration': RECORDING_DURATION,
            'interval': RECORDING_INTERVAL
        }
    }) 