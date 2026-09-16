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

# --- HOLOGRAPHIC OBJECT INITIAL STATE ---
box_x, box_y = 320, 240  # Initial position (center of screen)
box_size = 70            # Box radius/half-width
is_grabbed = False

print(">>> Lesson 3 Active! Pinch your fingers near the glowing hologram to grab & move it.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape

    # Calculate Real-Time FPS
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

    # Process Hand Interactions
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]

            tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)

            # Pinch distance math
            pinch_dist = math.hypot(ix - tx, iy - ty)
            is_pinching = pinch_dist < 40

            # --- HIT DETECTION & DRAG LOGIC ---
            # Distance between index finger cursor and the center of the Hologram
            dist_to_box = math.hypot(ix - box_x, iy - box_y)

            # If pinching while close to the box OR already holding it
            if is_pinching and (dist_to_box < box_size + 30 or is_grabbed):
                is_grabbed = True
                box_x, box_y = ix, iy  # Drag box to finger position
            else:
                is_grabbed = False

            # Draw Hand Finger Points & Pinch Line
            cursor_color = (255, 0, 255) if is_grabbed else (255, 255, 0)
            cv2.line(frame, (tx, ty), (ix, iy), cursor_color, 2)
            cv2.circle(frame, (ix, iy), 12, cursor_color, 2)

    # --- DRAW SCI-FI HOLOGRAPHIC OBJECT ---
    cube_color = (255, 0, 255) if is_grabbed else (255, 255, 0)  # BGR

    # Outer Glowing Frame
    cv2.rectangle(
        frame,
        (box_x - box_size, box_y - box_size),
        (box_x + box_size, box_y + box_size),
        cube_color,
        2
    )

    # Corner Target Reticles
    cv2.circle(frame, (box_x, box_y), 8, cube_color, -1)
    cv2.circle(frame, (box_x, box_y), box_size // 2, cube_color, 1)

    # Hologram Label Text
    state_label = "[ LOCKED ON ]" if is_grabbed else "[ CORE ENGINE V-01 ]"
    cv2.putText(
        frame,
        state_label,
        (box_x - box_size, box_y - box_size - 10),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        cube_color,
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

    cv2.imshow("Lesson 3: Hologram Drag & Drop Interface", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
