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
   pip3 install -r requirements.txt
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

## Troubleshooting & Setup History (Raspberry Pi)

### Camera Issues
- **libcamera-hello worked, but OpenCV could not access the camera**
  - Solution: Ensure `/dev/video0` exists. If not, enable V4L2 with `sudo modprobe bcm2835-v4l2` and add to `/etc/modules` for persistence.
  - If using Bookworm or later, you may need to use the legacy camera stack for OpenCV compatibility (edit `/boot/config.txt` and reboot).

### OpenCV Import/Camera Issues
- If `import cv2` fails, run `pip3 install opencv-python`.
- If OpenCV test script returns `Success: False`, check camera permissions and V4L2 setup.

### Python Package Issues
- If you see `ModuleNotFoundError: No module named 'dotenv'`, run `pip3 install python-dotenv`.
- If you see `ModuleNotFoundError: No module named 'pimoroni_bot'`, run from the project root or set `PYTHONPATH`:
  ```bash
  export PYTHONPATH="$PWD:$PYTHONPATH"
  python3 scripts/robot_livestream_blur.py
  ```

### evdev/Trilobot Build Issues
- If you see errors building `evdev`, install the system package:
  ```bash
  sudo apt install python3-evdev
  ```
- If you see linker errors or missing build tools, run:
  ```bash
  sudo apt install --reinstall gcc g++ python3-dev python3-pip python3-setuptools python3-wheel libevdev-dev libc6
  ```

### PWM Object Already Exists (Trilobot)
- If you see `RuntimeError: A PWM object already exists for this GPIO channel`:
  - Reboot the Pi to reset GPIO state: `sudo reboot`
  - Make sure only one instance of `Trilobot()` is created in your code.
  - Ensure no other Python scripts are running that use the GPIO.
  - The main script now automatically cleans up GPIO on exit using `atexit` to prevent this error.

### General Tips
- Always run scripts from the project root for local imports to work.
- Use `pip3 install -r requirements.txt` to install all dependencies.
- If you see permission errors uninstalling system packages, use `sudo pip3 uninstall ...`.
- If you see multiple `/dev/video*` devices, make sure you are using the correct one (usually `/dev/video0`).

---
This section documents all the real-world issues and fixes encountered to get this project running on a Raspberry Pi with Trilobot and camera hardware.

## TwelveLabs API Integration

The project includes integration with the TwelveLabs API for video analysis. **Note: The API structure has changed significantly, and the upload endpoint is currently not available through the API.** 

### Current Status:
- ✅ **API Key Authentication**: Working correctly
- ✅ **Index Management**: Can retrieve and use existing indexes
- ✅ **Video Analysis**: Can analyze existing videos in the index
- ✅ **Search Functionality**: Can perform visual search queries
- ❌ **Video Upload**: Currently not available through API (use TwelveLabs dashboard)

### How to Use:
1. **Upload Videos**: Upload videos through the TwelveLabs dashboard at https://app.twelvelabs.io/
2. **Analysis**: The system will analyze the most recent video in your default index
3. **Search**: Use the "Record & Analyze" button in the web UI to perform analysis

### API Configuration:
- Set your TwelveLabs API key in the `.env` file:
  ```
  TWELVELABS_API_KEY=your_api_key_here
  ```
- The system will automatically use your default index

### Analysis Results:
The system provides:
- Video filename and metadata
- Number of relevant segments found
- Timestamps and confidence scores for each segment
- Visual search results based on your query

### Future Updates:
When the upload endpoint becomes available again, the system will be updated to support:
- Direct video upload from the robot
- Real-time video analysis
- Automatic blurring based on API results