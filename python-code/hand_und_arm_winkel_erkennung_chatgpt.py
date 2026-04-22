import cv2
import mediapipe as mp
import math

flip = True

mp_pose = mp.solutions.pose
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


class MajorStatus:
    def __init__(self, max_length=5, majority_by:int=3):
        self.max_length = max_length
        self.majority_by = majority_by
        self.values = []
        
    
    def add(self, value):
        self.values.append(value)
        if len(self.values) > self.max_length:
            self.values.pop(0)
    
    def get(self):
        if not self.values:
            return None
        counts = {}
        for v in self.values:
            counts[v] = counts.get(v, 0) + 1
        for v, count in counts.items():
            if count >= self.majority_by:
                return v
        return None

class AverageOfN:
    def __init__(self, max_length=5):
        self.max_length = max_length
        self.values = []
    
    def add(self, value):
        self.values.append(value)
        if len(self.values) > self.max_length:
            self.values.pop(0)
    
    def get(self):
        if not self.values:
            return None
        return sum(self.values) / len(self.values)
    
def calculate_direction_angle(shoulder, wrist):
    dx = wrist.x - shoulder.x
    dy = wrist.y - shoulder.y
    angle = math.degrees(math.atan2(-dy, dx))
    return angle

def get_hand_status(hand_landmarks):
    lm = hand_landmarks.landmark

    fingers = []

    # Daumen
    if lm[4].x < lm[3].x:
        fingers.append(1)
    else:
        fingers.append(0)

    # Andere Finger
    tips = [8, 12, 16, 20]
    pips = [6, 10, 14, 18]

    for tip, pip in zip(tips, pips):
        if lm[tip].y < lm[pip].y:
            fingers.append(1)
        else:
            fingers.append(0)

    count = sum(fingers)

    if count >= 4:
        return "offen"
    elif count <= 1:
        return "zu"
    else:
        return "teilweise"

# Kamera testen
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print("Kamera gefunden auf Index:", i)
        cap.release()

cap = cv2.VideoCapture(1)

with mp_pose.Pose(min_detection_confidence=0.5,
                  min_tracking_confidence=0.5) as pose, \
     mp_hands.Hands(max_num_hands=1,
                    min_detection_confidence=0.6,
                    min_tracking_confidence=0.6) as hands:

    if not cap.isOpened():
        print("Stream konnte nicht geöffnet werden!")
    
    hand_status = MajorStatus(7, 5)  # 7 Werte, Mehrheit ab 5
    average_angle = AverageOfN(7)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        if flip:
            frame = cv2.flip(frame, 1)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # --- POSE ---
        pose_results = pose.process(rgb)

        # --- HAND ---
        hand_results = hands.process(rgb)

        # ===== ARM-RICHTUNG =====
        if pose_results.pose_landmarks:
            landmarks = pose_results.pose_landmarks.landmark

            if not flip:
                shoulder = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
                wrist = landmarks[mp_pose.PoseLandmark.RIGHT_WRIST]
            else:
                shoulder = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
                wrist = landmarks[mp_pose.PoseLandmark.LEFT_WRIST]

            angle = calculate_direction_angle(shoulder, wrist)
            average_angle.add(angle)

            cv2.putText(frame, f"Angle: {int(average_angle.get())} deg",
                        (30, 50),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 0), 2)

            if -45 <= angle <= 45:
                direction = "rechts"
            elif 45 < angle <= 135:
                direction = "vorne"
            elif angle > 135 or angle < -135:
                direction = "links"
            else:
                direction = "hinten"

            cv2.putText(frame, direction,
                        (30, 100),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0, 255, 255), 2)

            mp_drawing.draw_landmarks(
                frame,
                pose_results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS
            )

        # ===== HAND STATUS =====

        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                hand_status.add(get_hand_status(hand_landmarks))

                mp_drawing.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

        # Anzeige oben rechts
        hand_text = "keine Hand"
        hand_averaged = hand_status.get()
        if hand_averaged:
            hand_text = hand_averaged
        cv2.putText(frame, hand_text,
                    (frame.shape[1] - 200, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2)

        cv2.imshow("Top-Down Arm Direction + Hand", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

cap.release()
cv2.destroyAllWindows()