import os
import time
import math
import cv2
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Download Face Landmarker model if missing
MODEL_PATH = "face_landmarker.task"
if not os.path.exists(MODEL_PATH):
    print("Downloading Face Tracking Model...")
    url = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task"
    urllib.request.urlretrieve(url, MODEL_PATH)

# 2. Setup High-Speed Face Detector
base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_faces=1
)
detector = vision.FaceLandmarker.create_from_options(options)

# 3. Setup Webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

prev_time = time.time()
frame_timestamp_ms = 0
spin_angle = 0.0

# Key Facial Landmark Node Groups
FACE_OVAL_INDICES = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378,
                     400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]
LEFT_EYEBROW = [70, 63, 105, 66, 107]
RIGHT_EYEBROW = [336, 296, 334, 293, 300]
NOSE_BRIDGE = [168, 6, 197, 195, 5]

print("==================================================")
print(">>> CYBERPUNK FACE MESH HUD ENGINE ONLINE!")
print("🎯 Look at Camera -> Real-time Eye & Pose Reticles")
print("😮 Open Mouth   -> Trigger Energy Overdrive Shield")
print("==================================================")

try:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape

        # FPS Calculation
        curr_time = time.time()
        time_diff = curr_time - prev_time
        fps = 1 / time_diff if time_diff > 0 else 0
        prev_time = curr_time
        frame_timestamp_ms += int(time_diff * 1000) if time_diff > 0 else 1

        spin_angle = (spin_angle + 5.0) % 360

        # MediaPipe Detection
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection_result = detector.detect_for_video(
            mp_image, frame_timestamp_ms)

        shield_active = False

        if detection_result.face_landmarks:
            for face_landmarks in detection_result.face_landmarks:
                # Helper function to get pixel coordinates
                def get_pt(idx):
                    lm = face_landmarks[idx]
                    return int(lm.x * width), int(lm.y * height)

                # Key Points
                nose_tip = get_pt(1)
                nose_top = get_pt(168)
                l_eye_outer, l_eye_inner = get_pt(33), get_pt(133)
                r_eye_outer, r_eye_inner = get_pt(263), get_pt(362)
                l_cheek, r_cheek = get_pt(234), get_pt(454)
                top_lip, bot_lip = get_pt(13), get_pt(14)

                # Eye Center Points
                lx_center = int((l_eye_outer[0] + l_eye_inner[0]) / 2)
                ly_center = int((l_eye_outer[1] + l_eye_inner[1]) / 2)

                rx_center = int((r_eye_outer[0] + r_eye_inner[0]) / 2)
                ry_center = int((r_eye_outer[1] + r_eye_inner[1]) / 2)

                # --- 1. MOUTH TRIGGER (ENERGY SHIELD) ---
                lip_dist = math.hypot(
                    top_lip[0] - bot_lip[0], top_lip[1] - bot_lip[1])
                face_width = math.hypot(
                    l_cheek[0] - r_cheek[0], l_cheek[1] - r_cheek[1])
                mouth_ratio = lip_dist / max(1.0, face_width)

                if mouth_ratio > 0.12:
                    shield_active = True

                hud_color = (0, 0, 255) if shield_active else (
                    255, 255, 0)  # Red if Shield, Cyan normal

                # --- 2. FACIAL CONTOUR WIREFRAME ---
                # Draw Face Oval
                for i in range(len(FACE_OVAL_INDICES) - 1):
                    p1 = get_pt(FACE_OVAL_INDICES[i])
                    p2 = get_pt(FACE_OVAL_INDICES[i+1])
                    cv2.line(frame, p1, p2, hud_color, 1)

                # Draw Eyebrows & Nose Bridge
                for group in [LEFT_EYEBROW, RIGHT_EYEBROW, NOSE_BRIDGE]:
                    for i in range(len(group) - 1):
                        cv2.line(frame, get_pt(group[i]), get_pt(
                            group[i+1]), (0, 255, 255), 1)

                # --- 3. TARGETING EYE RETICLES ---
                for eye_x, eye_y in [(lx_center, ly_center), (rx_center, ry_center)]:
                    # Outer Ring
                    cv2.circle(frame, (eye_x, eye_y), 18, hud_color, 1)
                    cv2.circle(frame, (eye_x, eye_y), 4, (0, 255, 0), -1)

                    # Rotating Crosshair Ticks
                    rad = math.radians(spin_angle)
                    dx = int(24 * math.cos(rad))
                    dy = int(24 * math.sin(rad))
                    cv2.line(frame, (eye_x - dx, eye_y - dy),
                             (eye_x + dx, eye_y + dy), hud_color, 1)

                # --- 4. NOSE VECTOR HEAD POSE TRACKER ---
                vec_x = (nose_tip[0] - nose_top[0]) * 3
                vec_y = (nose_tip[1] - nose_top[1]) * 3
                target_pt = (nose_tip[0] + vec_x, nose_tip[1] + vec_y)

                cv2.line(frame, nose_tip, target_pt, (0, 255, 255), 2)
                cv2.circle(frame, target_pt, 8, (0, 255, 255), 1)
                cv2.circle(frame, target_pt, 2, (0, 255, 255), -1)

        # --- 5. OVERDRIVE SHIELD OVERLAY ---
        if shield_active:
            # Flashing Red Alert Border
            cv2.rectangle(frame, (10, 10), (width - 10,
                          height - 10), (0, 0, 255), 6)
            cv2.putText(
                frame,
                "!!! OVERDRIVE ENERGY SHIELD ACTIVE !!!",
                (int(width * 0.15), height - 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        # Header Status Bar
        status_msg = "OVERDRIVE MODE" if shield_active else "TRACKING TARGET"
        cv2.rectangle(frame, (0, 0), (width, 40), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"CYBER HUD: {status_msg} | FPS: {int(fps)}",
            (15, 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255) if shield_active else (0, 255, 255),
            2
        )

        cv2.imshow("Cyberpunk Face Mesh HUD", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
