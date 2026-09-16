import os
import time
import math
import cv2
import urllib.request
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# --- WINDOWS AUDIO CONTROL (PYCAW) ---
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

try:
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume_control = interface.QueryInterface(IAudioEndpointVolume)
    curr_vol_scalar = volume_control.GetMasterVolumeLevelScalar()
except Exception as e:
    print(f"Audio Initialization Warning: {e}")
    volume_control = None
    curr_vol_scalar = 0.5

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

# 3. Open webcam & set 640x480 resolution
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

prev_time = time.time()
frame_timestamp_ms = 0

# --- VOLUME CONTROL & STATE VARIABLES ---
target_vol_scalar = curr_vol_scalar
SMOOTH_FACTOR = 0.20
is_volume_active = False  # Starts locked by default

print("==================================================")
print(">>> GESTURE VOLUME ENGINE (PRE-LOCK GUARD) ONLINE!")
print("🖐️ Open Hand  -> UNLOCK and adjust volume")
print("✊ Closed Fist -> LOCK and freeze current volume")
print("==================================================")

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

    # MediaPipe Tracking
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
    detection_result = detector.detect_for_video(mp_image, frame_timestamp_ms)

    if detection_result.hand_landmarks:
        for hand_landmarks in detection_result.hand_landmarks:
            wrist = hand_landmarks[0]
            thumb_tip = hand_landmarks[4]
            index_tip = hand_landmarks[8]
            middle_mcp = hand_landmarks[9]
            middle_tip = hand_landmarks[12]
            ring_tip = hand_landmarks[16]
            pinky_tip = hand_landmarks[20]

            tx, ty = int(thumb_tip.x * width), int(thumb_tip.y * height)
            ix, iy = int(index_tip.x * width), int(index_tip.y * height)

            # --- SCALE INVARIANT VECTOR METRICS ---
            ref_len = math.hypot((middle_mcp.x - wrist.x)
                                 * width, (middle_mcp.y - wrist.y) * height)
            if ref_len < 1:
                ref_len = 1.0

            d_index = math.hypot(
                (index_tip.x - wrist.x) * width, (index_tip.y - wrist.y) * height) / ref_len
            d_middle = math.hypot(
                (middle_tip.x - wrist.x) * width, (middle_tip.y - wrist.y) * height) / ref_len
            d_ring = math.hypot((ring_tip.x - wrist.x) * width,
                                (ring_tip.y - wrist.y) * height) / ref_len
            d_pinky = math.hypot(
                (pinky_tip.x - wrist.x) * width, (pinky_tip.y - wrist.y) * height) / ref_len

            raw_dist = math.hypot(ix - tx, iy - ty)
            pinch_ratio = raw_dist / ref_len

            # --- GESTURE EVALUATION ---
            # Open Hand: Middle, Ring, Pinky extended UP/OUT
            is_open_hand = (d_middle > 1.20) and (
                d_ring > 1.20) and (d_pinky > 1.20)

            # Fist: All fingers folded tightly toward wrist
            is_fist = (d_index < 1.05) and (d_middle < 1.05) and (
                d_ring < 1.05) and (d_pinky < 1.05)

            if is_fist:
                is_volume_active = False  # Lock System
            elif is_open_hand:
                is_volume_active = True   # Unlock System

            # --- PRE-LOCK GUARD: UPDATE VOLUME ONLY IF OPEN HAND IS FULLY VALID ---
            # If fingers start curling to make a fist, volume calculations are completely skipped!
            if is_volume_active and is_open_hand:
                min_ratio, max_ratio = 0.25, 1.60
                norm_val = (pinch_ratio - min_ratio) / (max_ratio - min_ratio)
                target_vol_scalar = max(0.0, min(1.0, norm_val))

                # Visual Reticles
                cv2.line(frame, (tx, ty), (ix, iy), (0, 255, 255), 3)
                cv2.circle(frame, (tx, ty), 9, (255, 0, 255), -1)
                cv2.circle(frame, (ix, iy), 9, (255, 0, 255), -1)

    # LERP smoothing to audio hardware
    curr_vol_scalar += (target_vol_scalar - curr_vol_scalar) * SMOOTH_FACTOR

    if volume_control:
        try:
            volume_control.SetMasterVolumeLevelScalar(curr_vol_scalar, None)
        except Exception:
            pass

    # --- HOLOGRAPHIC VOLUME HUD ---
    vol_percent = int(curr_vol_scalar * 100)

    bar_x1, bar_y1 = 40, 100
    bar_x2, bar_y2 = 70, 380
    bar_height = bar_y2 - bar_y1
    fill_y = int(bar_y2 - (curr_vol_scalar * bar_height))

    bar_color = (0, 255, 0) if is_volume_active else (0, 0, 255)

    # Outer Bar
    cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (50, 50, 50), -1)
    cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), bar_color, 2)

    # Filled Level
    cv2.rectangle(frame, (bar_x1 + 4, fill_y),
                  (bar_x2 - 4, bar_y2 - 4), bar_color, -1)

    # Text Display
    cv2.putText(
        frame,
        f"{vol_percent}%",
        (bar_x1 - 5, bar_y2 + 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    # Header Bar
    if is_volume_active:
        status_text = f"VOLUME: ADJUSTING ({vol_percent}%) | [FIST TO LOCK]"
        hud_color = (0, 255, 0)
    else:
        status_text = f"VOLUME: LOCKED ({vol_percent}%) | [OPEN HAND TO UNLOCK]"
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

    cv2.imshow("Gestural Audio Volume Engine", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
