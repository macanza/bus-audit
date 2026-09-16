import os
import time
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

# 2. Set RunningMode to VIDEO for high speed
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

print(">>> High-Speed Tracking Active! Press 'q' to exit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Flip horizontally for intuitive mirror view
    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape

    # --- CALCULATE REAL-TIME FPS ---
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = 1 / time_diff if time_diff > 0 else 0
    prev_time = curr_time

    # Monotonically increasing timestamp for MediaPipe Video mode
    frame_timestamp_ms += int(time_diff * 1000) if time_diff > 0 else 1

    # Convert image format for MediaPipe
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # Fast video inference
    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

    # Draw Hand Tracking if detected
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            # Draw green hand joints
            for lm in hand_landmarks:
                lx, ly = int(lm.x * width), int(lm.y * height)
                cv2.circle(frame, (lx, ly), 3, (0, 255, 0), -1)

            # Draw Index Finger Tip cyan target ring
            index_tip = hand_landmarks[8]
            x, y = int(index_tip.x * width), int(index_tip.y * height)

            cv2.circle(frame, (x, y), 15, (255, 255, 0), -1)
            cv2.putText(
                frame,
                f"Cursor: ({x}, {y})",
                (x + 20, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2
            )

    # --- DRAW SOLID HIGH-CONTRAST FPS HUD BOX (TOP-LEFT CORNER) ---
    # Black background rectangle
    cv2.rectangle(frame, (10, 10), (160, 60), (0, 0, 0), -1)
    # Cyan border box
    cv2.rectangle(frame, (10, 10), (160, 60), (255, 255, 0), 2)
    # Bright Green FPS Text
    cv2.putText(
        frame,
        f"FPS: {int(fps)}",
        (25, 45),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2
    )

    cv2.imshow("Lesson 1: Hand Coordinate Cursor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
