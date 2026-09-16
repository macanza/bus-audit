import os
import time
import math
import cv2
import urllib.request
import pyautogui
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- PYAUTOGUI CONFIGURATION ---
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True
SCREEN_WIDTH, SCREEN_HEIGHT = pyautogui.size()

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

# 3. Open webcam & set low-latency 640x480 resolution
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

prev_time = time.time()
frame_timestamp_ms = 0

curr_mouse_x, curr_mouse_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
target_mouse_x, target_mouse_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

# --- ANTI-VIBRATION & STABILITY SETTINGS ---
SMOOTH_FACTOR = 0.18    # Lower factor filters out camera noise and jitter
DEADZONE_PIXELS = 4     # Ignores movements under 4px to eliminate micro-tremors

is_mouse_down = False
is_system_active = False

print("==================================================")
print(">>> STABLE OS CONTROLLER (ANTI-JITTER ENGINE) ONLINE!")
print("🖐️ Open Hand  -> UNLOCK system & move cursor")
print("✊ Closed Fist -> LOCK system immediately")
print("🤏 Pinch Finger -> Left Click & Drag")
print("==================================================")

try:
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        frame = cv2.flip(frame, 1)
        height, width, _ = frame.shape

        curr_time = time.time()
        time_diff = curr_time - prev_time
        fps = 1 / time_diff if time_diff > 0 else 0
        prev_time = curr_time
        frame_timestamp_ms += int(time_diff * 1000) if time_diff > 0 else 1

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        detection_result = detector.detect_for_video(
            mp_image, frame_timestamp_ms)

        if detection_result.hand_landmarks:
            for hand_landmarks in detection_result.hand_landmarks:
                # Key Landmark Nodes
                wrist = hand_landmarks[0]
                thumb_tip = hand_landmarks[4]
                index_tip = hand_landmarks[8]
                middle_mcp = hand_landmarks[9]
                middle_tip = hand_landmarks[12]
                ring_tip = hand_landmarks[16]
                pinky_tip = hand_landmarks[20]

                tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
                ix, iy = int(index_tip.x * width), int(index_tip.y * height)

                # --- HAND SCALE INVARIANT METRIC ---
                ref_len = math.hypot(
                    (middle_mcp.x - wrist.x) * width, (middle_mcp.y - wrist.y) * height)
                if ref_len < 1:
                    ref_len = 1.0

                # Normalized Distance from Wrist to Fingertips
                d_index = math.hypot(
                    (index_tip.x - wrist.x) * width, (index_tip.y - wrist.y) * height) / ref_len
                d_middle = math.hypot(
                    (middle_tip.x - wrist.x) * width, (middle_tip.y - wrist.y) * height) / ref_len
                d_ring = math.hypot(
                    (ring_tip.x - wrist.x) * width, (ring_tip.y - wrist.y) * height) / ref_len
                d_pinky = math.hypot(
                    (pinky_tip.x - wrist.x) * width, (pinky_tip.y - wrist.y) * height) / ref_len

                # Normalized Pinch Ratio
                raw_pinch_dist = math.hypot(ix - tx, iy - ty)
                pinch_ratio = raw_pinch_dist / ref_len

                # --- GESTURE STATE MACHINE ---
                is_open_hand = (d_middle > 1.25) and (
                    d_ring > 1.25) and (d_pinky > 1.25)
                is_fist = (d_index < 1.05) and (d_middle < 1.05) and (
                    d_ring < 1.05) and (d_pinky < 1.05)

                if is_fist:
                    is_system_active = False  # Lock System
                    if is_mouse_down:
                        pyautogui.mouseUp()
                        is_mouse_down = False
                elif is_open_hand:
                    is_system_active = True   # Unlock System

                # --- OS MOUSE CONTROL & PINCH CLICKING ---
                if is_system_active:
                    # Screen Padding Margins
                    margin = 0.12
                    norm_x = (index_tip.x - margin) / (1.0 - 2 * margin)
                    norm_y = (index_tip.y - margin) / (1.0 - 2 * margin)

                    norm_x = max(0.0, min(1.0, norm_x))
                    norm_y = max(0.0, min(1.0, norm_y))

                    target_mouse_x = norm_x * SCREEN_WIDTH
                    target_mouse_y = norm_y * SCREEN_HEIGHT

                    # Scale-Normalized Click Hysteresis
                    if pinch_ratio < 0.28:
                        if not is_mouse_down:
                            pyautogui.mouseDown()
                            is_mouse_down = True
                    elif pinch_ratio > 0.42:
                        if is_mouse_down:
                            pyautogui.mouseUp()
                            is_mouse_down = False

                    # Visual Reticles
                    click_color = (
                        255, 0, 255) if is_mouse_down else (0, 255, 0)
                    cv2.line(frame, (tx, ty), (ix, iy), click_color, 2)
                    cv2.circle(frame, (ix, iy), 8, click_color, -1)
                    cv2.circle(frame, (tx, ty), 8, click_color, -1)

        # Update OS Mouse Position with Deadzone Filter
        if is_system_active:
            move_dist_x = abs(target_mouse_x - curr_mouse_x)
            move_dist_y = abs(target_mouse_y - curr_mouse_y)

            if move_dist_x > DEADZONE_PIXELS or move_dist_y > DEADZONE_PIXELS:
                curr_mouse_x += (target_mouse_x - curr_mouse_x) * SMOOTH_FACTOR
                curr_mouse_y += (target_mouse_y - curr_mouse_y) * SMOOTH_FACTOR
                try:
                    pyautogui.moveTo(int(curr_mouse_x), int(curr_mouse_y))
                except pyautogui.FailSafeException:
                    break

        # Header Status Bar
        if is_system_active:
            status_text = f"SYSTEM: UNLOCKED [ACTIVE] | FPS: {int(fps)}"
            hud_color = (0, 255, 0)
        else:
            status_text = f"SYSTEM: LOCKED [SHOW OPEN HAND] | FPS: {int(fps)}"
            hud_color = (0, 0, 255)

        cv2.rectangle(frame, (0, 0), (width, 40), (0, 0, 0), -1)
        cv2.putText(
            frame,
            status_text,
            (15, 27),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            hud_color,
            2
        )

        cv2.imshow("Minority Report OS Mouse Controller", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    # Always release left click safely on exit
    pyautogui.mouseUp()
    cap.release()
    cv2.destroyAllWindows()
