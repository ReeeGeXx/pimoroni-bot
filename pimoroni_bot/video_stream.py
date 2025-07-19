import cv2
from flask import Flask, Response, request, jsonify
from pimoroni_bot.blur import blur_faces
from pimoroni_bot.robot import RobotController
import threading
import os
import requests
from pimoroni_bot.config import TWELVELABS_API_KEY

app = Flask(__name__)
cap = cv2.VideoCapture(0)

RECORD_VIDEO = False
out = None

# Robot controller instance (set externally if needed)
robot_controller = RobotController()

# Shared state for prompt and detection mode
DETECTION_MODE = 'local'  # 'local' or 'api'
DETECTION_PROMPT = ''
API_DETECTIONS = []
API_FRAME_IDX = 0

# --- API-based detection helper ---
def blur_with_api(frame, prompt):
    # This is a placeholder for API-based detection and blurring
    # In production, send the frame to the API, get detections, and blur accordingly
    # For now, just return the frame unchanged
    # You can implement batching and caching for efficiency
    # Example (pseudo):
    #   response = requests.post(api_url, files={'frame': ...}, data={'prompt': prompt}, headers=...)
    #   detections = response.json()['detections']
    #   for det in detections: ...
    return frame

# --- Video stream generator ---
def gen_frames():
    global API_FRAME_IDX
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
        API_FRAME_IDX += 1

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    # Simple UI with robot controls and prompt input
    return '''
    <h1>Robot Mode: Live Stream (Blurred)</h1>
    <p>This is the embedded robot mode. The robot moves and streams live video with real-time blur.</p>
    <img src="/video_feed" style="max-width: 100%; height: auto; border: 1px solid #ccc;"><br><br>
    <form id="promptForm">
        <label>Blur Prompt (leave blank for face blur):</label>
        <input type="text" id="blurPrompt" name="blurPrompt" placeholder="e.g. license plates">
        <button type="submit">Set Blur Prompt</button>
    </form>
    <p id="detectionMode"></p>
    <div>
        <button onclick="sendCommand('forward')">Forward</button>
        <button onclick="sendCommand('left')">Left</button>
        <button onclick="sendCommand('right')">Right</button>
        <button onclick="sendCommand('stop')">Stop</button>
    </div>
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
    async function sendCommand(cmd) {
        await fetch('/robot_command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd })
        });
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

# --- Endpoint to control the robot ---
@app.route('/robot_command', methods=['POST'])
def robot_command():
    data = request.get_json()
    cmd = data.get('command')
    if not robot_controller:
        return jsonify({'status': 'error', 'message': 'Robot not available'}), 400
    # Run robot commands in a thread to avoid blocking
    def do_cmd():
        if cmd == 'forward':
            robot_controller.move_forward(speed=0.5, duration=1)
        elif cmd == 'left':
            if hasattr(robot_controller.tbot, 'left'):
                robot_controller.tbot.left(0.5)
                import time; time.sleep(1)
                robot_controller.tbot.stop()
        elif cmd == 'right':
            if hasattr(robot_controller.tbot, 'right'):
                robot_controller.tbot.right(0.5)
                import time; time.sleep(1)
                robot_controller.tbot.stop()
        elif cmd == 'stop':
            robot_controller.tbot.stop()
    threading.Thread(target=do_cmd).start()
    return jsonify({'status': 'ok', 'command': cmd})

# --- API-based detection and blurring (placeholder) ---
# You can implement actual API calls here using the TwelveLabs API or similar 