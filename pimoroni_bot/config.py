import os
from dotenv import load_dotenv

load_dotenv()

TWELVELABS_API_KEY = os.getenv('TWELVELABS_API_KEY')
BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:5000/upload_and_process')
VIDEO_PATH = os.getenv('VIDEO_PATH', 'recorded_video.mp4')
BLURRED_PATH = os.getenv('BLURRED_PATH', 'blurred_video.mp4') 