import cv2
import numpy as np

cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # In HSV-Farbraum umwandeln (besser für Farberkennung)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # Grünbereich definieren (kannst du anpassen!)
    lower_green = np.array([40, 50, 50])
    upper_green = np.array([80, 255, 255])

    # Maske erstellen (nur grüne Pixel bleiben)
    mask = cv2.inRange(hsv, lower_green, upper_green)

    # Rauschen entfernen
    mask = cv2.GaussianBlur(mask, (5, 5), 0)

    # Konturen finden
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        if cv2.contourArea(contour) < 500:
            continue

        x, y, w, h = cv2.boundingRect(contour)

        # Rechteck zeichnen
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Text anzeigen
        cv2.putText(frame, "Gruen",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6, (0, 255, 0), 2)

    cv2.imshow("Gruen-Erkennung", frame)
    # cv2.imshow("Maske", mask)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()