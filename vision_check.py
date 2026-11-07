import time
import cv2

import time
import cv2

def analyze_user_behavior(duration_seconds: int = 5) -> str:
    """
    Analyzes webcam feed for a short window (duration_seconds):
    Returns:
      - 'WAVE_SHUTDOWN': Hand wave gesture detected (intentionally requesting shutdown).
      - 'FACE_KEEP_AWAKE': Face detected quietly without waving (user is watching/reading, keep laptop on).
      - 'NONE': No face or waving detected (user is away or asleep).
    """
    cap = None
    try:
        # DirectShow for instant camera start on Windows
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return "NONE"

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)

        start_time = time.time()
        prev_gray = None
        prev_cx = None
        last_dir = 0
        direction_changes = 0
        wave_detected = False
        face_detected_count = 0

        while time.time() - start_time < duration_seconds:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (15, 15), 0)

            # 1. Face Detection
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.2,
                minNeighbors=4,
                minSize=(35, 35)
            )
            if len(faces) > 0:
                face_detected_count += 1

            # 2. Hand Wave Detection (Oscillating horizontal motion)
            if prev_gray is not None:
                delta = cv2.absdiff(prev_gray, blurred)
                thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for c in contours:
                    area = cv2.contourArea(c)
                    if 1800 < area < 45000:
                        M = cv2.moments(c)
                        if M["m00"] > 0:
                            cx = int(M["m10"] / M["m00"])

                            # Ignore motion inside the detected face region
                            in_face = False
                            for (fx, fy, fw, fh) in faces:
                                if fx <= cx <= fx + fw:
                                    in_face = True
                                    break

                            if not in_face:
                                if prev_cx is not None:
                                    dx = cx - prev_cx
                                    if abs(dx) > 18:
                                        current_dir = 1 if dx > 0 else -1
                                        if last_dir != 0 and current_dir != last_dir:
                                            direction_changes += 1
                                            if direction_changes >= 2:
                                                wave_detected = True
                                                break
                                        last_dir = current_dir
                                prev_cx = cx
                if wave_detected:
                    break

            prev_gray = blurred
            time.sleep(0.06)

        if wave_detected:
            return "WAVE_SHUTDOWN"
        elif face_detected_count >= 2:
            return "FACE_KEEP_AWAKE"
        else:
            return "NONE"

    except Exception:
        return "NONE"
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass

def check_user_presence(duration_seconds: int = 5) -> str:
    return analyze_user_behavior(duration_seconds)

if __name__ == "__main__":
    print("Testing behavior analysis for 5 seconds...")
    res = analyze_user_behavior(5)
    print(f"Result: {res}")
