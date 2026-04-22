import cv2
import mediapipe as mp
import math

flip = True

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calculate_direction_angle(shoulder, wrist):
    # Vektor vom Schulterpunkt zur Hand
    dx = wrist.x - shoulder.x
    dy = wrist.y - shoulder.y

    # Wichtig: dy invertieren, weil Bildkoordinaten nach unten wachsen
    angle = math.degrees(math.atan2(-dy, dx))

    return angle

for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print("Kamera gefunden auf Index:", i)
        cap.release()

# cap = cv2.VideoCapture("http://192.168.178.108:4747/video", cv2.CAP_FFMPEG) # for droidCAM
cap = cv2.VideoCapture(1) # webcam or iVCam

with mp_pose.Pose(min_detection_confidence=0.5,
                  min_tracking_confidence=0.5) as pose:
    if not cap.isOpened():
        print("Stream konnte nicht geöffnet werden!")
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if flip:
            frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = pose.process(rgb)

        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark

            if not flip:
                shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            else:
                shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
                wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]

            angle = calculate_direction_angle(shoulder, wrist)

            # Winkel anzeigen
            cv2.putText(frame, f"Angle: {int(angle)} deg",
                        (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            # Richtungstext (optional)
            if -45 <= angle <= 45:
                direction = "rechts"
            elif 45 < angle <= 135:
                direction = "vorne"
            elif angle > 135 or angle < -135:
                direction = "links"
            else:
                direction = "hinten"

           

            # Skelett zeichnen
            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )
            
            
            cv2.putText(frame, direction,
                        (30, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 255), 2)

        cv2.imshow("Top-Down Arm Direction", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()