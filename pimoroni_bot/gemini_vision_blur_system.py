#!/usr/bin/env python3

import cv2
import numpy as np
import os
import time
import requests
import json
import base64
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GeminiVisionBlur:
    """Gemini API-powered blurring system for intelligent content detection"""
    
    def __init__(self):
        # Gemini API configuration
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
        self.api_key = os.getenv('GENAPI_API_KEY')  #Using the same key for now
        
        if not self.api_key:
            print("Warning: GENAPI_API_KEY not found in .env file")
            print("   Please add your Gemini API key to .env file")
            print("   Example: GENAPI_API_KEY=your_gemini_api_key_here")
        
        # Blur settings
        self.blur_strength = 51
        self.pixelation_size = 20
        
        # Current prompt and settings
        self.current_prompt = "detect and blur faces, IDs, and sensitive documents"
        self.is_streaming = False
        self.frame_count = 0
        self.detection_stats = {
            'faces': 0,
            'ids': 0,
            'documents': 0,
            'sensitive_content': 0
        }
        
        # Recording settings
        self.recording = False
        self.recorded_frames = []
        
        # Cache for API responses to avoid repeated calls
        self.detection_cache = {}
        self.cache_duration = 10.0  #much longer cache
        self.frame_skip = 60  #Only analyze every 60 frames (2 seconds at 30fps)
        self.last_analysis_frame = 0
        
    def encode_frame_for_api(self, frame):
        """Encode frame as base64 for API transmission"""
        # Resize frame to reduce API payload size
        height, width = frame.shape[:2]
        if width > 480:  # Smaller size for faster processing
            scale = 480 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            frame = cv2.resize(frame, (new_width, new_height))
        
        #Encode as JPEG with lower quality for faster transmission
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return jpg_as_text
    
    def call_gemini_analysis(self, frame, prompt):
        """Call Gemini API to analyze frame"""
        if not self.api_key:
            print("❌ No Gemini API key configured")
            return []
        
        try:
            # Encode frame
            encoded_frame = self.encode_frame_for_api(frame)
            
            # Prepare API request for Gemini
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": f"Analyze this image and detect sensitive content. {prompt} Look specifically for ID cards, passports, driver's licenses, credit cards, and faces. Return ONLY a JSON response with exact pixel coordinates for bounding boxes. Format: {{\"detections\": [{{\"bbox\": [x, y, width, height], \"type\": \"face|id|document|sensitive\", \"confidence\": 0.0-1.0}}]}} where x,y are top-left corner coordinates and width,height are the dimensions. Be precise with coordinates."
                            },
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": encoded_frame
                                }
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 1024
                }
            }
            
            print(f"Calling Gemini API with prompt: '{prompt}'")
            
            # Make API call
            url = f"{self.gemini_url}?key={self.api_key}"
            response = requests.post(url, json=payload, timeout=15)
            
            if response.status_code == 200:
                result = response.json()
                print(f"Gemini response received")
                return self.parse_gemini_response(result)
            else:
                print(f"Gemini error: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            print(f"Gemini call failed: {str(e)}")
            return []
    
    def parse_gemini_response(self, response):
        """Parse Gemini API response into detection regions"""
        detections = []
        
        try:
            if 'candidates' in response and response['candidates']:
                candidate = response['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content']:
                    text_response = candidate['content']['parts'][0].get('text', '')
                    
                    print(f"Raw Gemini response: {text_response[:200]}...")
                    
                    # Try to extract JSON from response
                    try:
                        # Look for JSON in the response
                        start_idx = text_response.find('{')
                        end_idx = text_response.rfind('}') + 1
                        if start_idx != -1 and end_idx != 0:
                            json_str = text_response[start_idx:end_idx]
                            parsed = json.loads(json_str)
                            
                            if 'detections' in parsed:
                                for detection in parsed['detections']:
                                    bbox = detection.get('bbox', [0, 0, 0, 0])
                                    if len(bbox) == 4:
                                        # Ensure coordinates are reasonable
                                        x, y, w, h = bbox
                                        if 0 <= x <= 1000 and 0 <= y <= 1000 and w > 0 and h > 0:
                                            detections.append({
                                                'bbox': tuple(bbox),
                                                'type': detection.get('type', 'unknown'),
                                                'confidence': detection.get('confidence', 0.0)
                                            })
                                            print(f"Parsed detection: {detection.get('type')} at {bbox}")
                                        else:
                                            print(f"Skipping invalid coordinates: {bbox}")
                    except json.JSONDecodeError:
                        print(f"Could not parse JSON from Gemini response: {text_response[:100]}...")
                        
        except Exception as e:
            print(f"Error parsing Gemini response: {str(e)}")
        
        return detections
    
    def process_detections(self, detections, frame_shape):
        """Process detections into blur regions"""
        blur_regions = []
        
        for detection in detections:
            # Extract bounding box coordinates
            bbox = detection.get('bbox', (0, 0, 0, 0))
            x, y, w, h = bbox
            
            # Ensure coordinates are within frame bounds
            height, width = frame_shape[:2]
            x = max(0, min(x, width - 1))
            y = max(0, min(y, height - 1))
            w = min(w, width - x)
            h = min(h, height - y)
            
            if w > 10 and h > 10:  # Filter very small detections
                blur_regions.append({
                    'bbox': (x, y, w, h),
                    'type': detection.get('type', 'unknown'),
                    'confidence': detection.get('confidence', 0.0)
                })
        
        return blur_regions
    
    def apply_blur(self, frame, region, blur_type='gaussian'):
        """Apply blur to a specific region"""
        x, y, w, h = region
        
        if blur_type == 'gaussian':
            roi = frame[y:y+h, x:x+w]
            blurred_roi = cv2.GaussianBlur(roi, (self.blur_strength, self.blur_strength), 0)
            frame[y:y+h, x:x+w] = blurred_roi
        
        elif blur_type == 'pixelate':
            roi = frame[y:y+h, x:x+w]
            # Resize down and up to create pixelation effect
            small = cv2.resize(roi, (w//self.pixelation_size, h//self.pixelation_size))
            pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
            frame[y:y+h, x:x+w] = pixelated
        
        elif blur_type == 'black':
            frame[y:y+h, x:x+w] = 0
        
        elif blur_type == 'white':
            frame[y:y+h, x:x+w] = 255
        
        return frame
    
    def process_frame_with_gemini(self, frame, prompt):
        """Process frame using Gemini API for intelligent detection"""
        processed_frame = frame.copy()
        frame_stats = {
            'faces': 0,
            'ids': 0,
            'documents': 0,
            'sensitive_content': 0
        }
        
        # Only analyze every N frames to improve performance
        should_analyze = (self.frame_count - self.last_analysis_frame) >= self.frame_skip
        
        if should_analyze:
            # Check cache first
            cache_key = f"{hash(prompt)}_{self.frame_count // 120}"  # Cache every 120 frames (4 seconds)
            current_time = time.time()
            
            if cache_key in self.detection_cache:
                cache_time, cached_detections = self.detection_cache[cache_key]
                if current_time - cache_time < self.cache_duration:
                    print(f"Using cached detection for frame {self.frame_count}")
                    blur_regions = self.process_detections(cached_detections, frame.shape)
                else:
                    # Cache expired, call API
                    print(f"Analyzing frame {self.frame_count} with Gemini...")
                    detections = self.call_gemini_analysis(frame, prompt)
                    
                    # If Gemini returns no detections, use fallback
                    if not detections:
                        print("Gemini returned no detections, using OpenCV fallback...")
                        detections = self.fallback_opencv_detection(frame)
                    
                    self.detection_cache[cache_key] = (current_time, detections)
                    blur_regions = self.process_detections(detections, frame.shape)
                    self.last_analysis_frame = self.frame_count
            else:
                # No cache, call API
                print(f"Analyzing frame {self.frame_count} with Gemini...")
                detections = self.call_gemini_analysis(frame, prompt)
                
                # If Gemini returns no detections, use fallback
                if not detections:
                    print("Gemini returned no detections, using OpenCV fallback...")
                    detections = self.fallback_opencv_detection(frame)
                
                self.detection_cache[cache_key] = (current_time, detections)
                blur_regions = self.process_detections(detections, frame.shape)
                self.last_analysis_frame = self.frame_count
        else:
            # Use the most recent cached detections
            cache_key = f"{hash(prompt)}_{(self.frame_count // 120)}"
            if cache_key in self.detection_cache:
                _, cached_detections = self.detection_cache[cache_key]
                blur_regions = self.process_detections(cached_detections, frame.shape)
            else:
                blur_regions = []
        
        # Apply blurring to detected regions
        for region in blur_regions:
            bbox = region['bbox']
            detection_type = region['type']
            confidence = region['confidence']
            
            # Apply blur
            processed_frame = self.apply_blur(processed_frame, bbox, 'gaussian')
            
            # Update stats
            if 'face' in detection_type.lower():
                frame_stats['faces'] += 1
            elif 'id' in detection_type.lower() or 'document' in detection_type.lower():
                frame_stats['ids'] += 1
            elif 'person' in detection_type.lower():
                frame_stats['faces'] += 1
            else:
                frame_stats['sensitive_content'] += 1
            
            if should_analyze:  # Only print during analysis frames
                print(f"Blurred {detection_type} (confidence: {confidence:.2f}) at {bbox}")
        
        # Update global stats
        for key, value in frame_stats.items():
            self.detection_stats[key] += value
        
        return processed_frame, frame_stats
    
    def fallback_opencv_detection(self, frame):
        """Fallback to OpenCV detection when Gemini fails"""
        detections = []
        
        # Face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            detections.append({
                'bbox': (x, y, w, h),
                'type': 'face',
                'confidence': 0.7
            })
        
        # Text detection for potential IDs
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            
            # Look for card-like rectangles
            if 1.5 <= aspect_ratio <= 3.0 and w > 80 and h > 40:
                detections.append({
                    'bbox': (x, y, w, h),
                    'type': 'id_document',
                    'confidence': 0.6
                })
        
        return detections
    
    def add_status_overlay(self, frame, frame_stats):
        """Add status information overlay to frame"""
        # Prompt info
        cv2.putText(frame, f"Gemini: {self.current_prompt[:30]}...", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Frame counter
        cv2.putText(frame, f"Frame: {self.frame_count}", (10, 60), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Detection stats
        y_offset = 90
        for detection_type, count in frame_stats.items():
            if count > 0:
                color = (0, 255, 0) if count > 0 else (128, 128, 128)
                cv2.putText(frame, f"{detection_type}: {count}", (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                y_offset += 20
        
        # API status
        status_color = (0, 255, 0) if self.api_key else (0, 0, 255)
        status_text = "Gemini: Connected" if self.api_key else "Gemini: No API Key"
        cv2.putText(frame, status_text, (10, y_offset), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)
        
        # Recording status
        if self.recording:
            cv2.putText(frame, "RECORDING", (10, y_offset + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Controls info
        cv2.putText(frame, "Q: Quit | P: Change Prompt | R: Record | S: Stop", (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    
    def start_gemini_stream(self, camera_index=0):
        """Start Gemini-powered video stream"""
        print(f"Gemini-Powered Blur Stream")
        print(f"Current prompt: '{self.current_prompt}'")
        print("Controls: Q=Quit, P=Change Prompt, R=Record, S=Stop")
        
        if not self.api_key:
            print("⚠️  No Gemini API key found. Please add GENAPI_API_KEY to .env file")
            return
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return
        
        self.is_streaming = True
        
        try:
            while self.is_streaming:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                self.frame_count += 1
                
                # Process frame with Gemini
                processed_frame, frame_stats = self.process_frame_with_gemini(frame, self.current_prompt)
                
                # Add status overlay
                self.add_status_overlay(processed_frame, frame_stats)
                
                # Record frame if recording
                if self.recording:
                    self.recorded_frames.append(processed_frame.copy())
                
                # Show the stream
                cv2.imshow('Gemini-Powered Blur', processed_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    self.change_prompt()
                elif key == ord('r'):
                    self.start_recording()
                elif key == ord('s'):
                    self.stop_recording()
                
                time.sleep(0.01)  # ~100 FPS - much faster
                
        except KeyboardInterrupt:
            print("\n⏹️  Stopping Gemini stream...")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.is_streaming = False
    
    def change_prompt(self):
        """Change the current Gemini prompt"""
        print(f"\nCurrent prompt: '{self.current_prompt}'")
        print("Example prompts:")
        print("• 'detect and blur all faces'")
        print("• 'find and blur ID cards and passports'")
        print("• 'detect sensitive documents and personal information'")
        print("• 'blur faces, IDs, and any personal documents'")
        print()
        
        new_prompt = input("Enter new prompt (or press Enter to keep current): ").strip()
        if new_prompt:
            self.current_prompt = new_prompt
            print(f"Changed prompt to: '{self.current_prompt}'")
            # Clear cache when prompt changes
            self.detection_cache.clear()
    
    def start_recording(self):
        """Start recording video segments"""
        if not self.recording:
            self.recording = True
            self.recorded_frames = []
            print(f"Started recording")
    
    def stop_recording(self):
        """Stop recording and save video"""
        if self.recording:
            self.recording = False
            print(f"Stopped recording. Frames captured: {len(self.recorded_frames)}")
            
            if self.recorded_frames:
                self.save_recorded_video()
    
    def save_recorded_video(self):
        """Save recorded frames as video file"""
        if not self.recorded_frames:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gemini_recording_{timestamp}.mp4"
        
        # Create video writer
        height, width = self.recorded_frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))
        
        # Write frames
        for frame in self.recorded_frames:
            out.write(frame)
        
        out.release()
        print(f"Saved recording: {filename}")
        
        # Clear recorded frames
        self.recorded_frames = []
    
    def get_detection_summary(self):
        """Get summary of all detections"""
        total_frames = self.frame_count
        summary = {
            'total_frames': total_frames,
            'detection_stats': self.detection_stats.copy(),
            'current_prompt': self.current_prompt
        }
        
        if total_frames > 0:
            summary['average_detections_per_frame'] = {
                key: value / total_frames for key, value in self.detection_stats.items()
            }
        
        return summary

def main():
    blur_system = GeminiVisionBlur()
    
    print("Gemini-Powered Blur System")
    print("=" * 40)
    print("This system uses Gemini API for intelligent content detection")
    print("and applies OpenCV blurring to sensitive regions.")
    print()
    
    if not blur_system.api_key:
        print("No Gemini API key found!")
        print("Please add your Gemini API key to the .env file:")
        print("GENAPI_API_KEY=your_gemini_api_key_here")
        return
    
    # Set initial prompt
    initial_prompt = input("Enter Gemini prompt (or press Enter for default): ").strip()
    if initial_prompt:
        blur_system.current_prompt = initial_prompt
    
    print(f"Starting with prompt: '{blur_system.current_prompt}'")
    print("Controls:")
    print("- Q: Quit")
    print("- P: Change prompt")
    print("- R: Start recording")
    print("- S: Stop recording")
    print()
    
    # Start the Gemini stream
    blur_system.start_gemini_stream()
    
    # Show summary when done
    summary = blur_system.get_detection_summary()
    print(f"\nDetection Summary:")
    print(f"   Total frames processed: {summary['total_frames']}")
    print(f"   Final prompt: '{summary['current_prompt']}'")
    print(f"   Total detections:")
    for detection_type, count in summary['detection_stats'].items():
        if count > 0:
            print(f"     - {detection_type}: {count}")

if __name__ == "__main__":
    main() 