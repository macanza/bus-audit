import cv2
import time
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# 1. Initialize MediaPipe Gesture Recognizer
base_options = python.BaseOptions(model_asset_path='gesture_recognizer.task')
options = vision.GestureRecognizerOptions(
    base_options=base_options,
    num_hands=2,
    running_mode=vision.RunningMode.VIDEO
)

recognizer = vision.GestureRecognizer.create_from_options(options)

# 2. Open Webcam Feed
cap = cv2.VideoCapture(0)
p_time = 0

print("Starting Hand Tracking... Press 'q' to quit.")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("Camera feed unavailable.")
        continue

    # Flip frame horizontally for mirror view
    frame = cv2.flip(frame, 1)

    # Convert OpenCV BGR to MediaPipe Image format
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

    # Calculate timestamp in milliseconds
    frame_timestamp_ms = int(time.time() * 1000)

    # Detect gestures
    result = recognizer.recognize_for_video(mp_image, frame_timestamp_ms)

    # Draw detected landmarks and gestures
    if result.gestures and result.hand_landmarks:
        for idx, gesture_list in enumerate(result.gestures):
            hand_landmarks = result.hand_landmarks[idx]
            gesture_name = gesture_list[0].category_name

            h, w, _ = frame.shape

            # Draw green circles on hand joint landmarks
            for lm in hand_landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 5, (0, 255, 0), -1)

            # Draw gesture name on wrist position
            wrist = hand_landmarks[0]
            wx, wy = int(wrist.x * w), int(wrist.y * h)

            display_text = gesture_name if gesture_name != "None" else "Hand Tracking"
            cv2.putText(
                frame,
                f"Gesture: {display_text}",
                (wx - 30, wy + 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 255),
                2
            )

    # Calculate and render FPS
    c_time = time.time()
    fps = 1 / (c_time - p_time) if (c_time - p_time) > 0 else 0
    p_time = c_time
    cv2.putText(frame, f"FPS: {int(fps)}", (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

    cv2.imshow("Hand Tracking & Gesture Detection", frame)

    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
