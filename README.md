# Post Guardian & Pimoroni Bot: AI-Powered Privacy Protection

## System Overview

**Post Guardian** is a dual-system project for privacy and content risk protection, powered by state-of-the-art AI APIs:

- **1. Chrome Extension (Post Guardian):**
  - Real-time privacy/content risk feedback for social media posts (e.g., Twitter/X)
  - Uses **TwelveLabs** and **Google Gemini Gen API** for advanced, multimodal detection of risky or sensitive content
- **2. Robot CV System (Pimoroni Bot):**
  - Raspberry Pi-based robot with live video streaming, remote control, and AI-powered privacy-preserving video blurring
  - Uses **Google Gemini Gen API** for intelligent, context-aware detection and blurring of sensitive content in video streams

---

## Project Structure

- `frontend/` — Chrome extension (Post Guardian) for real-time privacy risk feedback on social media.
    - `src/` — Main extension source code (content scripts, config, manifest, popup).
    - `dist/` — Built extension for loading into Chrome.
    - `README.md` — Extension-specific documentation.
- `pimoroni_bot/` — Embedded robot CV system for live video streaming, AI-powered blurring, and robot control.
    - `video_stream.py` — Flask server, video streaming, robot endpoints.
    - `gemini_vision_blur_system.py` — **Gemini Vision Blur System** (AI-powered blurring with Gemini Gen API).
    - `robot.py` — Robot control logic.
    - `blur.py`, `config.py` — Blurring and configuration utilities.
- `web/` — Web UI assets for the robot system.
- `scripts/` — Standalone scripts for experiments and batch processing.
- `requirements.txt` — Python dependencies for the robot system.
- `README.md` — This documentation.

---

## AI APIs Used

- **TwelveLabs API:**
  - Used in the Chrome extension for advanced video and text content analysis, especially for detecting risky or sensitive information in social media posts.
- **Google Gemini Gen API:**
  - Used in both the Chrome extension and the Robot CV system for AI-powered, context-aware detection and blurring of sensitive content in text and video streams.

---

## System Details

### 1. Chrome Extension: Post Guardian

- **Purpose:** Real-time privacy and content risk feedback as users compose posts on platforms like Twitter/X.
- **Features:**
  - Real-time text and video analysis using **TwelveLabs** and **Gemini Gen API**
  - Multimodal detection of risky keywords, phrases, and visuals
  - Color-coded risk banners and actionable recommendations
  - Minimal data sent to API, no permanent storage
- **How to Use:**
  - See `frontend/README.md` for full setup and usage instructions.

### 2. Robot CV System: Pimoroni Bot

- **Purpose:** Embedded robot system for live video streaming, AI-powered blurring, and remote robot control.
- **Blurring Mode:**
  - **Gemini Vision Blur System (`gemini_vision_blur_system.py`):**
    - AI-powered detection and blurring using **Google Gemini Gen API**.
    - Detects faces, ID cards, documents, and other sensitive content based on user prompt.
    - Context-aware and highly flexible; fallback to local detection if API fails (for robustness, but not the main pitch).
- **How to Use:**
  - Install Python dependencies (`pip3 install -r requirements.txt`).
  - Run the main script (`python3 scripts/robot_livestream_blur.py`).
  - Access the web UI on your network to control the robot and view the live, blurred video stream.

---

## Module Pitches

### Gemini Vision Blur System (`gemini_vision_blur_system.py`)
An advanced, AI-powered content detection and blurring engine for video streams. Uses **Google’s Gemini Gen API** to intelligently analyze each frame and identify sensitive content—including faces, ID cards, documents, and more—based on a customizable prompt. Provides context-aware, precise blurring and can fall back to local detection if needed.

---

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
- **Blur prompt:** Enter a custom prompt (e.g., "ID cards, faces") to use Gemini Gen API-based detection and blurring.
- **Detection mode indicator:** Shows whether Gemini Gen API-based detection is active.

## Notes
- The robot will move as commanded from the UI.
- The video stream is blurred in real time using Gemini Gen API-powered detection by default.
- If a prompt is set, the system will use Gemini Gen API-based detection (see code for integration details).
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
- API Key Authentication: Working correctly
- Index Management: Can retrieve and use existing indexes
- Video Analysis: Can analyze existing videos in the index
- Search Functionality: Can perform visual search queries

### How to Use:
1. Upload Videos: Upload videos through the TwelveLabs dashboard at https://app.twelvelabs.io/
2. Analysis: The system will analyze the most recent video in your default index
3. Search: Use the "Record & Analyze" button in the web UI to perform analysis

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