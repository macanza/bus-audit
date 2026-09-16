import os
import time
import math
import cv2
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Download MediaPipe model if missing
MODEL_PATH = "hand_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading hand tracking model...")
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

# 2. Setup Fast Hand Detector
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5
)
detector = vision.HandLandmarker.create_from_options(options)

# 3. Setup Low-Latency Webcam Capture
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

prev_time = time.time()
frame_timestamp_ms = 0

# --- 3D GEOMETRY DEFINITION ---
OUTER_CUBE = [
    [-1, -1, -1], [1, -1, -1], [1,  1, -1], [-1,  1, -1],
    [-1, -1,  1], [1, -1,  1], [1,  1,  1], [-1,  1,  1]
]

OUTER_EDGES = [
    (0, 1), (1, 2), (2, 3), (3, 0),
    (4, 5), (5, 6), (6, 7), (7, 4),
    (0, 4), (1, 5), (2, 6), (3, 7)
]

INNER_CORE = [
    [0, -1.2, 0], [0, 1.2, 0],
    [-1.2, 0, 0], [1.2, 0, 0],
    [0, 0, -1.2], [0, 0, 1.2]
]

INNER_EDGES = [
    (0, 2), (0, 3), (0, 4), (0, 5),
    (1, 2), (1, 3), (1, 4), (1, 5),
    (2, 4), (4, 3), (3, 5), (5, 2)
]

# --- FAST 3D ROTATION ---


def rotate_point(x, y, z, rx, ry, rz):
    # Radian Conversion
    rad_x, rad_y, rad_z = math.radians(rx), math.radians(ry), math.radians(rz)
    cx, sx = math.cos(rad_x), math.sin(rad_x)
    cy, sy = math.cos(rad_y), math.sin(rad_y)
    cz, sz = math.cos(rad_z), math.sin(rad_z)

    # X-axis rotation
    y, z = y * cx - z * sx, y * sx + z * cx
    # Y-axis rotation
    x, z = x * cy + z * sy, -x * sy + z * cy
    # Z-axis rotation
    x, y = x * cz - y * sz, x * sz + y * cz

    return x, y, z


def project_3d_to_2d(x, y, z, center_x, center_y, scale, focal_length=400):
    distance = 350
    z_eff = z * scale + distance
    if z_eff <= 0:
        z_eff = 1.0

    proj_x = int((x * scale * focal_length) / z_eff + center_x)
    proj_y = int((y * scale * focal_length) / z_eff + center_y)
    return proj_x, proj_y, z  # Return z for depth shading


auto_spin_angle = 0.0
holo_scale = 50.0

print(">>> HIGH-FPS 3D HOLO-ENGINE RUNNING!")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    frame = cv2.flip(frame, 1)
    height, width, _ = frame.shape

    # FPS Calc
    curr_time = time.time()
    time_diff = curr_time - prev_time
    fps = 1 / time_diff if time_diff > 0 else 0
    prev_time = curr_time
    frame_timestamp_ms += int(time_diff * 1000) if time_diff > 0 else 1

    auto_spin_angle = (auto_spin_angle + 3.0) % 360

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            wrist = hand_landmarks[0]
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            index_mcp = hand_landmarks[5]
            middle_mcp = hand_landmarks[9]
            pinky_mcp = hand_landmarks[17]

            palm_x = int((wrist.x + index_mcp.x + pinky_mcp.x) / 3 * width)
            palm_y = int((wrist.y + index_mcp.y + pinky_mcp.y) / 3 * height)

            # Hand tilt angles
            hand_pitch = (wrist.y - middle_mcp.y) * 120.0
            hand_roll = math.atan2(
                (pinky_mcp.y - index_mcp.y), (pinky_mcp.x - index_mcp.x)) * (180.0 / math.pi)

            # Pinch scale
            tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)
            pinch_dist = math.hypot(ix - tx, iy - ty)

            target_scale = max(25.0, min(110.0, pinch_dist * 0.8))
            holo_scale += (target_scale - holo_scale) * 0.25

            rot_x, rot_y, rot_z = hand_pitch, auto_spin_angle, hand_roll

            # --- RENDER OUTER CUBE WITH Z-DEPTH SHADING ---
            proj_outer = []
            for vertex in OUTER_CUBE:
                rx, ry, rz = rotate_point(
                    vertex[0], vertex[1], vertex[2], rot_x, rot_y, rot_z)
                px, py, pz = project_3d_to_2d(
                    rx, ry, rz, palm_x, palm_y, holo_scale)
                proj_outer.append((px, py, pz))

            for edge in OUTER_EDGES:
                p1, p2 = proj_outer[edge[0]], proj_outer[edge[1]]
                # Z-depth shading: Calculate average Z of edge
                avg_z = (p1[2] + p2[2]) / 2.0

                # Deeper z = darker/thinner, closer z = brighter/thicker
                thickness = 3 if avg_z < 0 else 1
                color_val = max(100, min(255, int(255 - (avg_z * 80))))
                edge_color = (color_val, color_val, 0)  # Dynamic cyan depth

                cv2.line(frame, (p1[0], p1[1]),
                         (p2[0], p2[1]), edge_color, thickness)

            for px, py, pz in proj_outer:
                cv2.circle(frame, (px, py), 4, (0, 255, 255), -1)

            # --- RENDER INNER CORE WITH COUNTER-ROTATION ---
            proj_inner = []
            for vertex in INNER_CORE:
                rx, ry, rz = rotate_point(
                    vertex[0], vertex[1], vertex[2], -rot_x, -rot_y * 1.5, rot_z)
                px, py, pz = project_3d_to_2d(
                    rx, ry, rz, palm_x, palm_y, holo_scale * 0.5)
                proj_inner.append((px, py, pz))

            for edge in INNER_EDGES:
                p1, p2 = proj_inner[edge[0]], proj_inner[edge[1]]
                cv2.line(frame, (p1[0], p1[1]),
                         (p2[0], p2[1]), (255, 0, 255), 1)

            # Palm Anchor Indicator
            cv2.circle(frame, (palm_x, palm_y), 8, (0, 255, 0), 2)

    # Top Status Bar
    hud_fps_color = (0, 255, 0) if fps >= 20 else (0, 0, 255)
    cv2.rectangle(frame, (0, 0), (width, 40), (0, 0, 0), -1)
    cv2.putText(
        frame,
        f"3D HOLO-ENGINE | FPS: {int(fps)}",
        (15, 27),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        hud_fps_color,
        2
    )

    cv2.imshow("3D Interactive Hologram Engine", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
