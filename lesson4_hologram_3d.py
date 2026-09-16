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

# --- 3D CUBE GEOMETRY ---
vertices_3d = [
    [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
    [-1, -1,  1], [1, -1,  1], [1, 1,  1], [-1, 1,  1]
]

edges = [
    (0, 1), (1, 2), (2, 3), (3, 0),  # Back face
    (4, 5), (5, 6), (6, 7), (7, 4),  # Front face
    (0, 4), (1, 5), (2, 6), (3, 7)   # Connecting lines
]

# --- SMOOTHING & STATE VARIABLES ---
target_x, target_y = 320, 240  # Where the hand wants to move
curr_x, curr_y = 320, 240      # Actual smoothed render position
curr_scale = 55.0              # Smoothed size
target_scale = 55.0

angle_x, angle_y = 0.0, 0.0
is_grabbed = False

# Smoothing Factor (0.1 = super smooth/floaty, 0.3 = fast & tight)
SMOOTH_FACTOR = 0.22

print(">>> Upgraded Smooth 3D Engine Active! Try grabbing and gliding the core.")

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

    # Auto-rotate 3D cube
    angle_x += 0.025
    angle_y += 0.035

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

    # Process Hand Interaction
    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]

            tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)

            # Pinch distance
            pinch_dist = math.hypot(ix - tx, iy - ty)

            # Center point between thumb and index finger
            pinch_center_x = (ix + tx) // 2
            pinch_center_y = (iy + ty) // 2

            # Distance from pinch center to current hologram center
            dist_to_core = math.hypot(
                pinch_center_x - curr_x, pinch_center_y - curr_y)

            # --- DOUBLE THRESHOLD (HYSTERESIS) LOGIC ---
            if not is_grabbed:
                # Grab require tight pinch (<35px) near the core
                if pinch_dist < 35 and dist_to_core < (curr_scale + 50):
                    is_grabbed = True
            else:
                # Release requires spreading fingers wide (>65px)
                if pinch_dist > 65:
                    is_grabbed = False

            # Update target position & scale when grabbed
            if is_grabbed:
                target_x, target_y = pinch_center_x, pinch_center_y
                # Smooth scale mapping
                target_scale = max(25.0, min(140.0, pinch_dist * 2.0))

            # Cursor Drawing
            cursor_color = (255, 0, 255) if is_grabbed else (255, 255, 0)
            cv2.line(frame, (tx, ty), (ix, iy), cursor_color, 2)
            cv2.circle(frame, (ix, iy), 8, cursor_color, -1)
            cv2.circle(frame, (tx, ty), 8, cursor_color, -1)

    # --- LERP SMOOTHING (Glides smoothly to target position) ---
    curr_x += (target_x - curr_x) * SMOOTH_FACTOR
    curr_y += (target_y - curr_y) * SMOOTH_FACTOR
    curr_scale += (target_scale - curr_scale) * SMOOTH_FACTOR

    render_x = int(curr_x)
    render_y = int(curr_y)
    render_scale = int(curr_scale)

    # --- RENDER 3D HOLOGRAPHIC WIREFRAME ---
    projected_2d = []
    cube_color = (255, 0, 255) if is_grabbed else (255, 255, 0)

    for vertex in vertices_3d:
        vx, vy, vz = vertex[0], vertex[1], vertex[2]

        # Rotate Y
        x1 = vx * math.cos(angle_y) + vz * math.sin(angle_y)
        z1 = -vx * math.sin(angle_y) + vz * math.cos(angle_y)

        # Rotate X
        y2 = vy * math.cos(angle_x) - z1 * math.sin(angle_x)
        z2 = vy * math.sin(angle_x) + z1 * math.cos(angle_x)

        # Screen Projection using smoothed coordinates
        px = int(render_x + x1 * render_scale)
        py = int(render_y + y2 * render_scale)
        projected_2d.append((px, py))

    # Draw 12 Edges
    for edge in edges:
        p1 = projected_2d[edge[0]]
        p2 = projected_2d[edge[1]]
        cv2.line(frame, p1, p2, cube_color, 2)

    # Core Center Reactor Dot
    cv2.circle(frame, (render_x, render_y), 6, cube_color, -1)

    # Status Label
    state_label = "[ 3D CORE: LOCKED ]" if is_grabbed else "[ 3D CORE ENGINE ]"
    cv2.putText(
        frame,
        state_label,
        (render_x - render_scale, render_y - render_scale - 15),
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

    cv2.imshow("Lesson 4: Smooth 3D Holographic Engine", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
