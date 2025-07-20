#!/usr/bin/env python3

import cv2
import numpy as np
import os
import time
import threading
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RobotEnhancedBlur:
    """Enhanced robot video stream with OpenCV prompt-based blurring"""
    
    def __init__(self):
        # Load detection models
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_fullbody.xml')
        
        # Color detection ranges
        self.color_ranges = {
            'red': [([0, 100, 100], [10, 255, 255]), ([160, 100, 100], [180, 255, 255])],
            'blue': [([100, 100, 100], [130, 255, 255])],
            'green': [([40, 100, 100], [80, 255, 255])],
            'yellow': [([20, 100, 100], [40, 255, 255])],
            'white': [([0, 0, 200], [180, 30, 255])],
            'black': [([0, 0, 0], [180, 255, 30])]
        }
        
        # Blur settings
        self.blur_strength = 51
        self.pixelation_size = 20
        
        # Current prompt and settings
        self.current_prompt = "blur faces and license plates"
        self.is_streaming = False
        self.frame_count = 0
        self.detection_stats = {
            'faces': 0,
            'eyes': 0,
            'bodies': 0,
            'text_regions': 0,
            'license_plates': 0,
            'color_regions': 0
        }
        
        # Recording settings
        self.recording = False
        self.recorded_frames = []
        self.recording_duration = 30  # seconds
        
    def parse_prompt(self, prompt):
        """Parse custom prompt to determine what to detect"""
        prompt_lower = prompt.lower()
        detection_types = []
        
        # Face detection
        if any(word in prompt_lower for word in ['face', 'faces', 'person', 'people', 'human', 'head']):
            detection_types.append('faces')
        
        # Body detection
        if any(word in prompt_lower for word in ['body', 'bodies', 'full body', 'person']):
            detection_types.append('bodies')
        
        # Eye detection
        if any(word in prompt_lower for word in ['eye', 'eyes', 'gaze']):
            detection_types.append('eyes')
        
        # Color detection
        for color in self.color_ranges.keys():
            if color in prompt_lower:
                detection_types.append(f'color_{color}')
        
        # Text detection
        if any(word in prompt_lower for word in ['text', 'sign', 'document', 'paper', 'writing']):
            detection_types.append('text')
        
        # License plate detection
        if any(word in prompt_lower for word in ['license plate', 'plate', 'car', 'vehicle', 'number plate']):
            detection_types.append('license_plates')
        
        # Sensitive content
        if any(word in prompt_lower for word in ['sensitive', 'private', 'confidential', 'blur', 'hide']):
            detection_types.append('sensitive')
        
        return detection_types
    
    def detect_faces(self, frame):
        """Detect faces in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        return faces
    
    def detect_eyes(self, frame):
        """Detect eyes in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        eyes = self.eye_cascade.detectMultiScale(gray, 1.3, 5)
        return eyes
    
    def detect_bodies(self, frame):
        """Detect full bodies in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        bodies = self.body_cascade.detectMultiScale(gray, 1.3, 5)
        return bodies
    
    def detect_colors(self, frame, color_name):
        """Detect specific colors in frame"""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        color_ranges = self.color_ranges.get(color_name, [])
        
        masks = []
        for lower, upper in color_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            masks.append(mask)
        
        if masks:
            combined_mask = sum(masks)
            contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            return contours
        return []
    
    def detect_text_regions(self, frame):
        """Detect potential text regions using edge detection"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Morphological operations to connect text lines
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (20, 5))
        text_regions = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(text_regions, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours by size (likely text regions)
        text_contours = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 50 and h > 10 and w < 300 and h < 100:  # Text-like dimensions
                text_contours.append((x, y, w, h))
        
        return text_contours
    
    def detect_license_plates(self, frame):
        """Detect potential license plates"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Look for rectangular shapes (license plate candidates)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        plate_candidates = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            aspect_ratio = w / h if h > 0 else 0
            
            # License plates typically have aspect ratio between 2:1 and 5:1
            if 2.0 <= aspect_ratio <= 5.0 and w > 60 and h > 15:
                plate_candidates.append((x, y, w, h))
        
        return plate_candidates
    
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
    
    def process_frame_with_prompt(self, frame, prompt):
        """Process frame based on custom prompt"""
        detection_types = self.parse_prompt(prompt)
        processed_frame = frame.copy()
        
        # Reset stats for this frame
        frame_stats = {
            'faces': 0,
            'eyes': 0,
            'bodies': 0,
            'text_regions': 0,
            'license_plates': 0,
            'color_regions': 0
        }
        
        # Apply detections based on prompt
        for detection_type in detection_types:
            if detection_type == 'faces':
                faces = self.detect_faces(frame)
                for (x, y, w, h) in faces:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    frame_stats['faces'] += 1
            
            elif detection_type == 'eyes':
                eyes = self.detect_eyes(frame)
                for (x, y, w, h) in eyes:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    frame_stats['eyes'] += 1
            
            elif detection_type == 'bodies':
                bodies = self.detect_bodies(frame)
                for (x, y, w, h) in bodies:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    frame_stats['bodies'] += 1
            
            elif detection_type.startswith('color_'):
                color_name = detection_type.replace('color_', '')
                color_contours = self.detect_colors(frame, color_name)
                for contour in color_contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 20 and h > 20:  # Filter small regions
                        processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                        frame_stats['color_regions'] += 1
            
            elif detection_type == 'text':
                text_regions = self.detect_text_regions(frame)
                for (x, y, w, h) in text_regions:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    frame_stats['text_regions'] += 1
            
            elif detection_type == 'license_plates':
                plates = self.detect_license_plates(frame)
                for (x, y, w, h) in plates:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    frame_stats['license_plates'] += 1
            
            elif detection_type == 'sensitive':
                # For sensitive content, blur the entire frame
                processed_frame = cv2.GaussianBlur(processed_frame, (self.blur_strength, self.blur_strength), 0)
        
        # Update global stats
        for key, value in frame_stats.items():
            self.detection_stats[key] += value
        
        return processed_frame, frame_stats
    
    def add_status_overlay(self, frame, frame_stats):
        """Add status information overlay to frame"""
        # Prompt info
        cv2.putText(frame, f"Prompt: {self.current_prompt[:25]}...", (10, 30), 
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
        
        # Recording status
        if self.recording:
            cv2.putText(frame, "RECORDING", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Controls info
        cv2.putText(frame, "Q: Quit | P: Change Prompt | R: Record | S: Stop", (10, frame.shape[0] - 20), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    
    def start_robot_stream(self, camera_index=0):
        """Start robot video stream with enhanced blurring"""
        print(f"🤖 Starting Robot Enhanced Blur Stream")
        print(f"📝 Current prompt: '{self.current_prompt}'")
        print("Controls: Q=Quit, P=Change Prompt, R=Record, S=Stop")
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return
        
        self.is_streaming = True
        start_time = time.time()
        
        try:
            while self.is_streaming:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                self.frame_count += 1
                
                # Process frame with current prompt
                processed_frame, frame_stats = self.process_frame_with_prompt(frame, self.current_prompt)
                
                # Add status overlay
                self.add_status_overlay(processed_frame, frame_stats)
                
                # Record frame if recording
                if self.recording:
                    self.recorded_frames.append(processed_frame.copy())
                
                # Show the stream
                cv2.imshow('Robot Enhanced Blur', processed_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    self.change_prompt()
                elif key == ord('r'):
                    self.start_recording()
                elif key == ord('s'):
                    self.stop_recording()
                
                time.sleep(0.03)  # ~30 FPS
                
        except KeyboardInterrupt:
            print("\n⏹️  Stopping robot stream...")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.is_streaming = False
    
    def change_prompt(self):
        """Change the current blur prompt"""
        print(f"\n🔄 Current prompt: '{self.current_prompt}'")
        print("Available detection types:")
        print("• faces, eyes, bodies")
        print("• colors: red, blue, green, yellow, white, black")
        print("• text, license_plates")
        print("• sensitive (blurs entire frame)")
        print()
        
        new_prompt = input("Enter new prompt (or press Enter to keep current): ").strip()
        if new_prompt:
            self.current_prompt = new_prompt
            print(f"✅ Changed prompt to: '{self.current_prompt}'")
    
    def start_recording(self):
        """Start recording video segments"""
        if not self.recording:
            self.recording = True
            self.recorded_frames = []
            print(f"🎬 Started recording (duration: {self.recording_duration}s)")
    
    def stop_recording(self):
        """Stop recording and save video"""
        if self.recording:
            self.recording = False
            print(f"⏹️  Stopped recording. Frames captured: {len(self.recorded_frames)}")
            
            if self.recorded_frames:
                self.save_recorded_video()
    
    def save_recorded_video(self):
        """Save recorded frames as video file"""
        if not self.recorded_frames:
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"robot_recording_{timestamp}.mp4"
        
        # Create video writer
        height, width = self.recorded_frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(filename, fourcc, 30.0, (width, height))
        
        # Write frames
        for frame in self.recorded_frames:
            out.write(frame)
        
        out.release()
        print(f"💾 Saved recording: {filename}")
        
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
    robot = RobotEnhancedBlur()
    
    print("🤖 Robot Enhanced Blur System")
    print("=" * 40)
    print("This system provides real-time OpenCV blurring based on custom prompts.")
    print("Perfect for privacy protection on your Pimoroni robot!")
    print()
    
    # Set initial prompt
    initial_prompt = input("Enter blur prompt (or press Enter for default): ").strip()
    if initial_prompt:
        robot.current_prompt = initial_prompt
    
    print(f"🎯 Starting with prompt: '{robot.current_prompt}'")
    print("Controls:")
    print("• Q: Quit")
    print("• P: Change prompt")
    print("• R: Start recording")
    print("• S: Stop recording")
    print()
    
    # Start the robot stream
    robot.start_robot_stream()
    
    # Show summary when done
    summary = robot.get_detection_summary()
    print(f"\n📊 Detection Summary:")
    print(f"   Total frames processed: {summary['total_frames']}")
    print(f"   Final prompt: '{summary['current_prompt']}'")
    print(f"   Total detections:")
    for detection_type, count in summary['detection_stats'].items():
        if count > 0:
            print(f"     • {detection_type}: {count}")

if __name__ == "__main__":
    main() 