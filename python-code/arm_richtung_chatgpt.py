import cv2
import mediapipe as mp
import math

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

def calculate_angles(shoulder, wrist):
    # Differenzen
    dx = wrist.x - shoulder.x
    dy = wrist.y - shoulder.y
    dz = wrist.z - shoulder.z  # Tiefe!

    # Horizontaler Winkel (links/rechts)
    horizontal_angle = math.degrees(math.atan2(dx, -dz))

    # Vertikaler Winkel (oben/unten)
    vertical_angle = math.degrees(math.atan2(-dy, -dz))

    return horizontal_angle, vertical_angle, dz

cap = cv2.VideoCapture(0)

with mp_pose.Pose(min_detection_confidence=0.5,
                  min_tracking_confidence=0.5) as pose:

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        # Erkennt Körperpunkte (z. B. Schulter, Ellbogen, Hand)
        results = pose.process(rgb)
        # Wenn Körper erkannt wurde
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark # Alle Punkte holen
            # Schulter & Handgelenk auswählen ...rechten Arm
            shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]

            h_angle, v_angle, depth = calculate_angles(shoulder, wrist)

            # Anzeige
            cv2.putText(frame, f"H: {int(h_angle)} deg",
                        (30, 50), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            cv2.putText(frame, f"V: {int(v_angle)} deg",
                        (30, 100), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            cv2.putText(frame, f"Depth: {depth:.2f}",
                        (30, 150), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            # Interpretation
            if depth < -0.1:
                text = "zeigt zur Kamera"
            elif depth > 0.1:
                text = "zeigt weg"
            else:
                text = "seitlich"

            cv2.putText(frame, text,
                        (30, 200), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 255), 2)

            mp_drawing.draw_landmarks(
                frame,
                results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )

        cv2.imshow("Arm Winkel Tracking", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()