#!/usr/bin/env python3

import cv2
import numpy as np
import os
import time
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EnhancedOpenCVBlur:
    """Enhanced OpenCV blurring system with custom prompt support"""
    
    def __init__(self):
        # Load detection models
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades +'haarcascade_frontalface_default.xml')
        self.eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
        self.body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades+ 'haarcascade_fullbody.xml')
        
        # Color detection ranges
        self.color_ranges = {
            'red': [([0, 100, 100], [10, 255, 255]), ([160, 100, 100], [180, 255, 255])],
            'blue': [([100, 100, 100], [130, 255, 255])],
            'green': [([40, 100, 100], [80, 255, 255])],
            'yellow': [([20, 100, 100], [40, 255, 255])],
            'white': [([0, 0, 200], [180, 30, 255])],
            'black': [([0, 0, 0], [180, 255, 30])]
        }
        
        # Text detection (simple edge-based)
        self.text_kernel=np.ones((2, 2), np.uint8)
        
        # Blur settings
        self.blur_strength=51
        self.pixelation_size=20
        
    def parse_prompt(self,prompt):
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
        if any(word in prompt_lower for word in ['text', 'sign', 'document', 'paper', 'writing', 'license plate']):
            detection_types.append('text')
        
        # License plate detection
        if any(word in prompt_lower for word in ['license plate', 'plate', 'car', 'vehicle', 'number plate']):
            detection_types.append('license_plates')
        
        # Object detection (general)
        if any(word in prompt_lower for word in ['object', 'item', 'thing', 'detect', 'find']):
            detection_types.append('objects')
        
        # Sensitive content
        if any(word in prompt_lower for word in ['sensitive', 'private', 'confidential', 'blur', 'hide']):
            detection_types.append('sensitive')
        
        return detection_types
    
    def detect_faces(self, frame):
        """Detect faces in frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3,5)
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
        
        print(f"🔍 Processing frame with prompt: '{prompt}'")
        print(f"   Detection types: {detection_types}")
        
        # Apply detections based on prompt
        for detection_type in detection_types:
            if detection_type == 'faces':
                faces = self.detect_faces(frame)
                for (x, y, w, h) in faces:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    print(f"   ✅ Blurred face at ({x}, {y})")
            
            elif detection_type == 'eyes':
                eyes = self.detect_eyes(frame)
                for (x, y, w, h) in eyes:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    print(f"   ✅ Blurred eye at ({x}, {y})")
            
            elif detection_type == 'bodies':
                bodies = self.detect_bodies(frame)
                for (x, y, w, h) in bodies:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    print(f"   ✅ Blurred body at ({x}, {y})")
            
            elif detection_type.startswith('color_'):
                color_name = detection_type.replace('color_', '')
                color_contours = self.detect_colors(frame, color_name)
                for contour in color_contours:
                    x, y, w, h = cv2.boundingRect(contour)
                    if w > 20 and h > 20:  # Filter small regions
                        processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                        print(f"   ✅ Blurred {color_name} region at ({x}, {y})")
            
            elif detection_type == 'text':
                text_regions = self.detect_text_regions(frame)
                for (x, y, w, h) in text_regions:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    print(f"   ✅ Blurred text region at ({x}, {y})")
            
            elif detection_type == 'license_plates':
                plates = self.detect_license_plates(frame)
                for (x, y, w, h) in plates:
                    processed_frame = self.apply_blur(processed_frame, (x, y, w, h), 'gaussian')
                    print(f"   ✅ Blurred license plate at ({x}, {y})")
            
            elif detection_type == 'sensitive':
                # For sensitive content, blur the entire frame
                processed_frame = cv2.GaussianBlur(processed_frame, (self.blur_strength, self.blur_strength), 0)
                print(f"   ✅ Applied sensitive content blur")
        
        return processed_frame
    
    def start_livestream_with_prompt(self, camera_index=0, prompt="blur faces and license plates"):
        """Start livestream with custom prompt-based blurring"""
        print(f"🎥 Starting enhanced livestream with prompt: '{prompt}'")
        print("Press 'q' to quit, 'p' to change prompt")
        
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print("❌ Cannot open camera")
            return
        
        current_prompt = prompt
        frame_count = 0
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    print("❌ Failed to read frame")
                    break
                
                frame_count += 1
                
                # Process frame with current prompt
                processed_frame = self.process_frame_with_prompt(frame, current_prompt)
                
                # Add status overlay
                cv2.putText(processed_frame, f"Prompt: {current_prompt[:30]}...", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(processed_frame, f"Frame: {frame_count}", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(processed_frame, "Press 'p' to change prompt, 'q' to quit", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
                
                # Show the stream
                cv2.imshow('Enhanced OpenCV Blur', processed_frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('p'):
                    new_prompt = input("\nEnter new prompt: ").strip()
                    if new_prompt:
                        current_prompt = new_prompt
                        print(f"🔄 Changed prompt to: '{current_prompt}'")
                
                time.sleep(0.03)  # ~30 FPS
                
        except KeyboardInterrupt:
            print("\n⏹️  Stopping livestream...")
        finally:
            cap.release()
            cv2.destroyAllWindows()

def main():
    blur_system = EnhancedOpenCVBlur()
    
    print("🎯 Enhanced OpenCV Blur System")
    print("=" * 40)
    print("Available detection types:")
    print("• faces, eyes, bodies")
    print("• colors: red, blue, green, yellow, white, black")
    print("• text, license_plates")
    print("• sensitive (blurs entire frame)")
    print()
    
    # Example prompts
    print("Example prompts:")
    print("• 'blur faces and license plates'")
    print("• 'detect and blur red objects'")
    print("• 'hide all text and sensitive content'")
    print("• 'blur eyes and blue items'")
    print()
    
    prompt = input("Enter your blur prompt (or press Enter for default): ").strip()
    if not prompt:
        prompt = "blur faces and license plates"
    
    blur_system.start_livestream_with_prompt(prompt=prompt)

if __name__ == "__main__":
    main() 