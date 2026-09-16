import os
import time
import math
import cv2
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Download model file if missing
MODEL_PATH = "hand_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading hand tracking model...")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

# 2. Setup High-Speed Video Mode
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1
)
detector = vision.HandLandmarker.create_from_options(options)

# 3. Open webcam & setup variables
cap = cv2.VideoCapture(0)
prev_time = time.time()
frame_timestamp_ms = 0

print(">>> Lesson 2 Active! Try pinching your thumb and index finger together.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Flip horizontally for mirror view
    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape

    # --- CALCULATE FPS ---
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = 1 / time_diff if time_diff > 0 else 0
    prev_time = curr_time
    frame_timestamp_ms += int(time_diff * 1000) if time_diff > 0 else 1

    # Convert image format for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # Fast video inference
    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

    # Process hand gestures
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            # Get Thumb Tip (4) and Index Tip (8)
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]

            # Convert to screen pixel coordinates
            tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)

            # --- MATH: Calculate Euclidean distance between Thumb and Index ---
            distance = math.hypot(ix - tx, iy - ty)

            # Determine gesture state based on distance threshold (40 pixels)
            is_pinched = distance < 40

            # HUD Theme: Magenta when GRABBED, Cyan when TRACKING
            hud_color = (255, 0, 255) if is_pinched else (255, 255, 0)  # BGR
            status_text = "JARVIS: SYSTEM GRABBED" if is_pinched else "JARVIS: SEARCHING..."

            # --- DRAW GESTURE GRAPHICS ---
            # 1. Line connecting thumb and index finger
            cv2.line(frame, (tx, ty), (ix, iy), hud_color, 2)
            # 2. Target dot on thumb
            cv2.circle(frame, (tx, ty), 8, hud_color, -1)
            # 3. Outer target ring on index finger
            cv2.circle(frame, (ix, iy), 18, hud_color, 2)
            cv2.circle(frame, (ix, iy), 6, hud_color, -1)

            # 4. Floating HUD text next to finger
            cv2.putText(
                frame,
                status_text,
                (ix + 25, iy + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                hud_color,
                2
            )

    # --- DRAW FPS HUD BOX ---
    cv2.rectangle(frame, (10, 10), (160, 60), (0, 0, 0), -1)
    cv2.rectangle(frame, (10, 10), (160, 60), (255, 255, 0), 2)
    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2
    )

    cv2.imshow("Lesson 2: Gesture Math & Pinch Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
