import cv2

# Example: Replace with real detection results from backend
# Each item: (start_frame, end_frame, x, y, w, h)
detections = [
    (0, 100, 100, 100, 200, 100),  # Blur region in frames 0-100
]

VIDEO_PATH = "recorded_video.mp4"
OUTPUT_PATH = "blurred_video.mp4"

cap = cv2.VideoCapture(VIDEO_PATH)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(OUTPUT_PATH, fourcc, 20.0, (640, 480))

frame_idx = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    for det in detections:
        start_f, end_f, x, y, w, h = det
        if start_f <= frame_idx <= end_f:
            roi = frame[y:y+h, x:x+w]
            roi = cv2.GaussianBlur(roi, (51, 51), 0)
            frame[y:y+h, x:x+w] = roi
    out.write(frame)
    frame_idx += 1
cap.release()
out.release()
print(f"Blurred video saved to {OUTPUT_PATH}")