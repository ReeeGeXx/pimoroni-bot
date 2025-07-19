# Pimoroni Bot - Embedded Robot Video System

This project is designed for a Raspberry Pi-based Pimoroni Trilobot robot. It provides:
- Robot movement control (from the web UI)
- Live video streaming from the Pi camera
- Real-time blurring of detected faces in the video stream
- Optionally, prompt-based blurring using an API (e.g., TwelveLabs)
- Modular code for easy maintenance and extension

## Project Structure

- `pimoroni_bot/` - Main Python package with all core logic
    - `robot.py` - Robot (Trilobot) control logic
    - `video_stream.py` - Video streaming, Flask server, robot endpoints, and blurring logic
    - `blur.py` - Real-time blurring/detection logic (OpenCV)
    - `config.py` - Centralized configuration (loads from `.env`)
- `scripts/` - Standalone scripts for running or testing features
    - `robot_livestream_blur.py` - Main entry point for robot mode (move, stream, blur, UI)
    - `auto_blur_pipeline.py`, `robot_record_and_upload.py`, etc. - Other scripts for experiments or batch processing
- `web/` - Web UI assets (if needed)
    - `static/` - Static files (JS, CSS)
    - `templates/` - HTML templates
- `requirements.txt` - Python dependencies
- `README.md` - This documentation
- `.env` - Environment variables (API keys, etc.)

## How to Run (on the Pi)

1. Make sure the Pi camera is enabled and connected.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the main robot mode:
   ```bash
   python3 scripts/robot_livestream_blur.py
   ```
4. Open a browser on your network and go to:
   ```
   http://<pi-ip>:5002
   ```
   to view the live, blurred video stream and control the robot.

## Web UI Features
- **Live video stream:** See what the robot sees in real time.
- **Robot controls:** Use the Forward, Left, Right, and Stop buttons to control the robot from your browser.
- **Blur prompt:** Enter a custom prompt (e.g., "license plates") to use API-based detection and blurring. Leave blank to use fast, local face blurring.
- **Detection mode indicator:** Shows whether local or API-based detection is active.

## Notes
- The robot will move as commanded from the UI.
- The video stream is blurred in real time using OpenCV face detection by default.
- If a prompt is set, the system will attempt to use API-based detection (see code for integration details).
- If the Trilobot hardware is not detected, the code will run in simulated mode (no movement).
- All configuration (API keys, backend URLs, etc.) can be set in the `.env` file or in `pimoroni_bot/config.py`.

## Other Scripts
- `auto_blur_pipeline.py`, `robot_record_and_upload.py`, etc. are for batch processing or experiments and are not needed for basic robot mode.

---
This README is focused on documentation and clarity. For advanced features (cloud analysis, web UI, etc.), see the relevant scripts and modules.