from flask import Flask, jsonify, request
import requests
from flask_cors import CORS
from show_analysis import show_detailed_analysis

app = Flask(__name__)
CORS(app)  # Enable CORS if needed for your Chrome extension

@app.route("/analyze-video", methods=["POST"])
def analyze_video():
    data = request.get_json()
    prompt = data.get("prompt", "Find inappropriate content")

    try:
        result = show_detailed_analysis(prompt)
        return jsonify({"success": True, "results": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000)
