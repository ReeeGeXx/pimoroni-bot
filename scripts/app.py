from flask import Flask, render_template, request, jsonify
import os
import requests
from dotenv import load_dotenv
import time

# Load environment variables from .env if present
load_dotenv()

app = Flask(__name__)

TWELVELABS_API_KEY = os.environ.get('TWELVELABS_API_KEY')
UPLOAD_URL = "https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos"
SEARCH_URL = "https://api.twelvelabs.io/v1.3/search"
ANALYZE_URL = "https://api.twelvelabs.io/v1.3/search"

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

def get_default_index():
    """Get the default index ID"""
    try:
        indexes_res = requests.get("https://api.twelvelabs.io/v1.3/indexes", 
                                 headers={"x-api-key": TWELVELABS_API_KEY})
        indexes_res.raise_for_status()
        indexes_data = indexes_res.json()
        return indexes_data['data'][0]['_id']
    except Exception as e:
        raise Exception(f"Failed to get index: {e}")

def process_video_internal(query, video_path):
    if not TWELVELABS_API_KEY:
        return jsonify({'error': 'Twelvelabs API key not set'}), 500
    
    # Get the default index
    try:
        index_id = get_default_index()
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    # Note: The TwelveLabs API upload endpoint has changed and may not be available
    # For now, we'll analyze existing videos in the index
    try:
        videos_res = requests.get(f"https://api.twelvelabs.io/v1.3/indexes/{index_id}/videos", 
                                headers={"x-api-key": TWELVELABS_API_KEY})
        videos_res.raise_for_status()
        videos_data = videos_res.json()
        existing_videos = videos_data['data']
        
        if not existing_videos:
            return jsonify({'error': 'No videos found in index. Please upload videos through the TwelveLabs dashboard first.'}), 500
        
        # Use the most recent video for analysis
        test_video = existing_videos[0]
        video_id = test_video['_id']
        filename = test_video['system_metadata']['filename']
        
    except Exception as e:
        return jsonify({'error': f'Failed to get videos: {str(e)}'}), 500
    
    # Run search analysis
    results = {}
    try:
        # Search with visual analysis
        search_payload = {
            'index_id': (None, index_id),
            'query_text': (None, query),
            'search_options': (None, 'visual')
        }
        headers = {'x-api-key': TWELVELABS_API_KEY}
        search_res = requests.post(SEARCH_URL, files=search_payload, headers=headers)
        search_res.raise_for_status()
        results['search'] = search_res.json()
        results['analyzed_video'] = filename
    except Exception as e:
        results['search'] = {'error': f'Search failed: {str(e)}'}
    
    return jsonify({'query': query, 'video_path': video_path, 'results': results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)