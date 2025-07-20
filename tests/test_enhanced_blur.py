#!/usr/bin/env python3

import cv2
import numpy as np
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_test_image():
    """Create a test image with various elements to detect"""
    print("Creating test image...")
    
    # Create a test image
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add a face-like shape (circle)
    cv2.circle(img, (200, 150), 50, (255, 200, 150), -1)  # Face
    cv2.circle(img, (180, 130), 8, (255, 255, 255), -1)   # Left eye
    cv2.circle(img, (220, 130), 8, (255, 255, 255), -1)   # Right eye
    
    # Add text
    cv2.putText(img, "TEST TEXT", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(img, "LICENSE PLATE", (400, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    # Add colored rectangles
    cv2.rectangle(img, (50, 350), (150, 450), (0, 0, 255), -1)  # Red
    cv2.rectangle(img, (500, 50), (600, 150), (255, 0, 0), -1)  # Blue
    cv2.rectangle(img, (50, 50), (150, 150), (0, 255, 0), -1)   # Green
    
    # Add a license plate-like rectangle
    cv2.rectangle(img, (400, 350), (600, 380), (128, 128, 128), -1)
    cv2.putText(img, "ABC123", (420, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return img

def test_prompt_parsing():
    """Test the prompt parsing functionality"""
    print("Testing prompt parsing...")
    
    # Import the enhanced blur system
    from pimoroni_bot.enhanced_opencv_blur import EnhancedOpenCVBlur
    
    blur_system = EnhancedOpenCVBlur()
    
    test_prompts = [
        "blur faces and license plates",
        "detect and blur red objects",
        "hide all text and sensitive content",
        "blur eyes and blue items",
        "detect faces, bodies, and text",
        "blur everything sensitive"
    ]
    
    for prompt in test_prompts:
        detection_types = blur_system.parse_prompt(prompt)
        print(f"   '{prompt}' → {detection_types}")
    
    print("Prompt parsing test complete!")

def test_detection_on_image():
    """Test detection on a test image"""
    print("Testing detection on test image...")
    
    # Import the enhanced blur system
    from pimoroni_bot.enhanced_opencv_blur import EnhancedOpenCVBlur
    
    blur_system = EnhancedOpenCVBlur()
    
    # Create test image
    test_img = create_test_image()
    
    # Test different prompts
    test_prompts = [
        "blur faces",
        "blur text",
        "blur red objects",
        "blur license plates",
        "blur faces and text"
    ]
    
    for i, prompt in enumerate(test_prompts):
        print(f"\nTesting prompt: '{prompt}'")
        
        # Process image with prompt
        processed_img = blur_system.process_frame_with_prompt(test_img, prompt)
        
        # Save result
        filename = f"test_result_{i+1}_{prompt.replace(' ', '_')}.jpg"
        cv2.imwrite(filename, processed_img)
        print(f"    Saved: {filename}")
    
    print("Detection test complete!")

def test_blur_types():
    """Test different blur types"""
    print("Testing different blur types...")
    
    # Create a simple test image
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), (255, 255, 255), -1)
    
    # Import the enhanced blur system
    from pimoroni_bot.enhanced_opencv_blur import EnhancedOpenCVBlur
    
    blur_system = EnhancedOpenCVBlur()
    
    # Test different blur types
    blur_types = ['gaussian', 'pixelate', 'black', 'white']
    
    for blur_type in blur_types:
        print(f"   Testing {blur_type} blur...")
        
        # Apply blur
        blurred_img = blur_system.apply_blur(img.copy(), (50, 50, 100, 100), blur_type)
        
        # Save result
        filename = f"blur_test_{blur_type}.jpg"
        cv2.imwrite(filename, blurred_img)
        print(f"    Saved: {filename}")
    
    print("Blur types test complete!")

def main():
    print("Enhanced OpenCV Blur System Test")
    print("=" * 50)
    
    print("This test demonstrates the enhanced OpenCV blurring system")
    print("that can handle custom prompts for privacy protection.")
    print()
    
    # Test 1: Prompt parsing
    test_prompt_parsing()
    print()
    
    # Test 2: Detection on image
    test_detection_on_image()
    print()
    
    # Test 3: Blur types
    test_blur_types()
    print()
    
    print("All tests complete!")
    print()
    print("Generated files:")
    print("• test_result_*.jpg - Detection test results")
    print("• blur_test_*.jpg - Blur type examples")
    print()
    print("To test with live camera:")
    print("   python3 pimoroni_bot/enhanced_opencv_blur.py")
    print("   python3 pimoroni_bot/robot_enhanced_blur.py")

if __name__ == "__main__":
    main() 