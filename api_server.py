from flask import Flask, jsonify, request
import base64
import tempfile
from flask_cors import CORS
from show_analysis import show_detailed_analysis

app = Flask(__name__)
CORS(app)  # Allow Chrome extension to call this API

@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    data = request.get_json()
    prompt = data.get(
        "prompt",
        "computer screen"
        #"Find inappropriate content in a video such as middle fingers, bad words (audio or visual), license plates, addresses, etc.",
    )
    video_data = data.get("video")

    if not video_data:
        return jsonify({"success": False, "error": "No video provided"}), 400

    # Handle if the client sends { "vidFile": "base64..." } or just "base64..."
    if isinstance(video_data, dict) and "vidFile" in video_data:
        video_b64 = video_data["vidFile"]
    else:
        video_b64 = video_data

    # Save Base64 video to a temporary file
    try:
        video_bytes = base64.b64decode(video_b64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            tmp_file.write(video_bytes)
            temp_video_path = tmp_file.name
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to decode video: {e}"}), 500

    # Call analysis
    try:
        results = show_detailed_analysis(prompt, temp_video_path)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        import traceback
        traceback.print_exc()  # <-- dump full stacktrace in terminal
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
