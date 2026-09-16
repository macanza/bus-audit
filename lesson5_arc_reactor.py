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

# --- HOLOGRAM STATE & SMOOTHING ---
curr_x, curr_y = 320, 240
target_x, target_y = 320, 240

curr_scale = 1.0
target_scale = 1.0

# Grab Offset (prevents hologram from jumping/snapping on pinch)
offset_x = 0
offset_y = 0

angle1, angle2, angle3 = 0.0, 0.0, 0.0
is_grabbed = False
SMOOTH_FACTOR = 0.20

# Helper function to project and draw 3D Ring


def draw_3d_ring(frame, num_points, radius, ang_x, ang_y, ang_z, cx, cy, scale, color, thickness=1):
    points_2d = []
    for i in range(num_points):
        theta = (2 * math.pi / num_points) * i
        vx = radius * math.cos(theta)
        vy = radius * math.sin(theta)
        vz = 0.0

        # Rotate Z
        x1 = vx * math.cos(ang_z) - vy * math.sin(ang_z)
        y1 = vx * math.sin(ang_z) + vy * math.cos(ang_z)
        z1 = vz

        # Rotate Y
        x2 = x1 * math.cos(ang_y) + z1 * math.sin(ang_y)
        z2 = -x1 * math.sin(ang_y) + z1 * math.cos(ang_y)
        y2 = y1

        # Rotate X
        y3 = y2 * math.cos(ang_x) - z2 * math.sin(ang_x)
        z3 = y2 * math.sin(ang_x) + z2 * math.cos(ang_x)
        x3 = x2

        # 2D Screen Projection
        px = int(cx + x3 * scale)
        py = int(cy + y3 * scale)
        points_2d.append((px, py))

    # Connect points in a loop
    for i in range(num_points):
        p1 = points_2d[i]
        p2 = points_2d[(i + 1) % num_points]
        cv2.line(frame, p1, p2, color, thickness)

    return points_2d


print(">>> Precision Arc Reactor Online! Pinch to move, push/pull hand to scale.")

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

    # Spin rotation angles
    spin_speed = 2.0 if is_grabbed else 1.0
    angle1 += 0.03 * spin_speed
    angle2 -= 0.04 * spin_speed
    angle3 += 0.02 * spin_speed

    # MediaPipe Tracking
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            wrist = hand_landmarks[0]
            middle_mcp = hand_landmarks[9]

            tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)
            wx, wy = int(wrist.x * width), int(wrist.y * height)
            mx, my = int(middle_mcp.x * width), int(middle_mcp.y * height)

            pinch_dist = math.hypot(ix - tx, iy - ty)
            pinch_cx = (ix + tx) // 2
            pinch_cy = (iy + ty) // 2

            # Distance from palm/wrist to middle knuckle (Measures hand depth/distance to camera)
            hand_span = math.hypot(mx - wx, my - wy)

            # Distance from pinch point to current core position
            dist_to_core = math.hypot(pinch_cx - curr_x, pinch_cy - curr_y)

            # --- SMOOTH LOCKING & OFFSET LOGIC ---
            if not is_grabbed:
                # Grab when pinching close to the core
                if pinch_dist < 40 and dist_to_core < (90 * curr_scale + 50):
                    is_grabbed = True
                    # Record offset so it doesn't snap!
                    offset_x = curr_x - pinch_cx
                    offset_y = curr_y - pinch_cy
            else:
                # Release only when fingers spread wide open
                if pinch_dist > 60:
                    is_grabbed = False

            # Update position & scale when holding
            if is_grabbed:
                target_x = pinch_cx + offset_x
                target_y = pinch_cy + offset_y
                # Scale smoothly maps to physical hand distance to camera
                target_scale = max(0.4, min(2.5, hand_span / 110.0))

            # Render Cursor Points
            cursor_color = (255, 0, 255) if is_grabbed else (255, 255, 0)
            cv2.line(frame, (tx, ty), (ix, iy), cursor_color, 2)
            cv2.circle(frame, (ix, iy), 8, cursor_color, -1)
            cv2.circle(frame, (tx, ty), 8, cursor_color, -1)

    # Apply Lerp Smoothing
    curr_x += (target_x - curr_x) * SMOOTH_FACTOR
    curr_y += (target_y - curr_y) * SMOOTH_FACTOR
    curr_scale += (target_scale - curr_scale) * SMOOTH_FACTOR

    rx, ry = int(curr_x), int(curr_y)
    theme_color = (255, 0, 255) if is_grabbed else (255, 255, 0)

    # --- RENDER ARC REACTOR RINGS ---
    draw_3d_ring(frame, 16, 80, angle1, angle1*0.5, angle1,
                 rx, ry, curr_scale, theme_color, 2)
    draw_3d_ring(frame, 12, 55, angle2*0.7, angle2, -
                 angle2, rx, ry, curr_scale, theme_color, 2)
    inner_pts = draw_3d_ring(frame, 8, 30, angle3, -angle3 *
                             0.8, angle3*1.2, rx, ry, curr_scale, theme_color, 1)

    # Energy Rays
    for pt in inner_pts:
        cv2.line(frame, (rx, ry), pt, theme_color, 1)

    # Glowing Center
    cv2.circle(frame, (rx, ry), int(10 * curr_scale), theme_color, -1)
    cv2.circle(frame, (rx, ry), int(18 * curr_scale), theme_color, 2)

    # Tech Label
    status_msg = "[ LOCKED & PARKED ]" if not is_grabbed else "[ ENGAGED & DRAGGING ]"
    cv2.putText(
        frame,
        f"ARC REACTOR {status_msg}",
        (rx - int(80 * curr_scale), ry - int(95 * curr_scale)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        theme_color,
        2
    )

    # --- FPS HUD BOX ---
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

    cv2.imshow("Sci-Fi Precision Arc Reactor", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
