from flask import Flask, jsonify, request
import base64
import tempfile
from flask_cors import CORS
from show_analysis import show_detailed_analysis

app = Flask(__name__)
CORS(app)  # Enable CORS if needed for your Chrome extension


@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    data = request.get_json()
    prompt = data.get(
        "prompt",
        "Find clips for inappropriate content in a video such as middle fingers, bad words (audio or visual), license plates, addresses and what not",
    )
    video_base64 = data.get("video")
    print("first  bit", video_base64.keys())
    filename = data.get("filename", "video.mp4")

    if not video_base64:
        return jsonify({"success": False, "error": "No video provided"}), 400

    # Save the Base64 video to a temporary file
    try:
        video_bytes = base64.b64decode(video_base64["vidFile"])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(video_bytes)
            temp_video_path = tmp_file.name
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to decode video: {e}"}), 500

    # Call your integrated analysis function
    try:
        filename, duration = show_detailed_analysis(prompt, temp_video_path)
        return jsonify({"success": True, "filename": filename, "duration": duration})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000)
