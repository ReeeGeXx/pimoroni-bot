from flask import Flask, jsonify
from flask_cors import CORS
from show_analysis import show_detailed_analysis

app = Flask(__name__)

@app.route("/analyze-video", methods=["GET"])
def analyze_video():
    try:
        result = show_detailed_analysis()
        return jsonify({ "success": result }), 200
    except Exception as e:
        return jsonify({ "success": False, "error": str(e) }), 500

if __name__ == "__main__":
    app.run(port=5001)
