import cv2
import mediapipe as mp

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7,
                       min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Bild spiegeln
    frame = cv2.flip(frame, 1)

    h, w, c = frame.shape

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    finger_count = 0

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

            landmarks = hand_landmarks.landmark

            # Finger-Tips (Daumen, Zeige, Mittel, Ring, kleiner Finger)
            tip_ids = [4, 8, 12, 16, 20]

            # Daumen (x-Vergleich wegen Spiegelung)
            if landmarks[tip_ids[0]].x < landmarks[tip_ids[0] - 1].x:
                finger_count += 1

            # Andere 4 Finger (y-Vergleich)
            for i in range(1, 5):
                if landmarks[tip_ids[i]].y < landmarks[tip_ids[i] - 2].y:
                    finger_count += 1

    # Zahl anzeigen (oben links)
    cv2.rectangle(frame, (0,0), (200,100), (0,0,0), -1)
    cv2.putText(frame, f"Finger: {finger_count}", (20,70),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0,255,0), 3)

    cv2.imshow("Finger Counter", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC
        break

cap.release()
cv2.destroyAllWindows()