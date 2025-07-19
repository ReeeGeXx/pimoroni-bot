from flask import Flask, render_template, request, jsonify
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)

TWELVELABS_API_KEY = os.environ.get('TWELVELABS_API_KEY')
UPLOAD_URL = "https://api.twelvelabs.io/v1.3/videos/upload"
SEARCH_URL = "https://api.twelvelabs.io/v1.3/search"
ANALYZE_URL = "https://api.twelvelabs.io/v1.3/analyze"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    file = request.files.get('video')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    save_path = os.path.join('static', file.filename)
    file.save(save_path)
    return jsonify({'message': 'File uploaded', 'path': save_path})

@app.route('/upload_and_process', methods=['POST'])
def upload_and_process():
    file = request.files.get('video')
    query = request.form.get('query', 'Find all sensitive content')
    if not file:
        return jsonify({'error': 'No file uploaded'}), 400
    save_path = os.path.join('static', file.filename)
    file.save(save_path)
    return process_video_internal(query, save_path)

@app.route('/process', methods=['POST'])
def process_video():
    data = request.json
    query = data.get('query')
    video_path = data.get('video_path')
    if not query or not video_path:
        return jsonify({'error': 'Missing query or video_path'}), 400
    return process_video_internal(query, video_path)

def process_video_internal(query, video_path):
    if not TWELVELABS_API_KEY:
        return jsonify({'error': 'Twelvelabs API key not set'}), 500
    # 1. Upload video to Twelvelabs
    try:
        with open(video_path, 'rb') as f:
            files = {'file': f}
            headers = {'x-api-key': TWELVELABS_API_KEY}
            upload_res = requests.post(UPLOAD_URL, files=files, headers=headers)
            upload_res.raise_for_status()
            video_id = upload_res.json().get('video_id')
    except Exception as e:
        return jsonify({'error': f'Video upload failed: {str(e)}'}), 500
    # 2. Run Marengo and Pegasus in the background (sequentially for now)
    results = {}
    try:
        # Marengo (search)
        payload_search = {
            'video_id': video_id,
            'query': query,
            'model': 'marengo-1.3'
        }
        headers = {'x-api-key': TWELVELABS_API_KEY}
        search_res = requests.post(SEARCH_URL, json=payload_search, headers=headers)
        search_res.raise_for_status()
        results['marengo'] = search_res.json()
    except Exception as e:
        results['marengo'] = {'error': f'Search failed: {str(e)}'}
    try:
        # Pegasus (analyze)
        payload_analyze = {
            'video_id': video_id,
            'query': query,
            'model': 'pegasus-1.3'
        }
        headers = {'x-api-key': TWELVELABS_API_KEY}
        analyze_res = requests.post(ANALYZE_URL, json=payload_analyze, headers=headers)
        analyze_res.raise_for_status()
        results['pegasus'] = analyze_res.json()
    except Exception as e:
        results['pegasus'] = {'error': f'Analyze failed: {str(e)}'}
    return jsonify({'query': query, 'video_path': video_path, 'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)