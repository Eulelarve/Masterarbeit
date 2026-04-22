import cv2
import numpy as np

import cv2
import numpy as np

TOP_N = 10

def normalize_top_pixels(frame):
    result = frame.astype(np.float32).copy()

    for c in range(3):  # B, G, R
        channel = frame[:, :, c].flatten()

        # Top-N Pixel finden
        top_values = np.partition(channel, -TOP_N)[-TOP_N:]

        # Durchschnitt der stärksten Pixel
        top_avg = np.mean(top_values)

        # Vermeidung von Division durch 0
        if top_avg < 1:
            continue

        # Skalierungsfaktor
        scale = 255.0 / top_avg

        # Kanal skalieren
        result[:, :, c] *= scale

    # Werte begrenzen
    result = np.clip(result, 0, 255)

    return result.astype(np.uint8)

def normalize_colors(frame):
    # Mittelwerte der Kanäle berechnen
    avg_b = frame[:, :, 0].mean()
    avg_g = frame[:, :, 1].mean()
    avg_r = frame[:, :, 2].mean()

    # Gesamtmittelwert
    avg_gray = (avg_b + avg_g + avg_r) / 3

    # Skalierungsfaktoren
    scale_b = avg_gray / avg_b
    scale_g = avg_gray / avg_g
    scale_r = avg_gray / avg_r

    # Anwenden
    frame[:, :, 0] = np.clip(frame[:, :, 0] * scale_b, 0, 255)
    frame[:, :, 1] = np.clip(frame[:, :, 1] * scale_g, 0, 255)
    frame[:, :, 2] = np.clip(frame[:, :, 2] * scale_r, 0, 255)

    return frame.astype(np.uint8)

def get_dominant_color_hsv(block):
    hsv = cv2.cvtColor(block, cv2.COLOR_BGR2HSV)

    # Mittelwert nehmen
    h = hsv[:, :, 0].mean()
    s = hsv[:, :, 1].mean()
    v = hsv[:, :, 2].mean()

    # Wenn Farbe zu schwach → ignorieren
    if s < 50 or v < 50:
        return (0, 0, 0)  # schwarz / kein Signal

    # Farbklassifikation
    if 35 <= h <= 85:
        return (0, 255, 0)   # Grün
    elif h < 15 or h > 160:
        return (0, 0, 255)   # Rot
    elif 85 < h <= 130:
        return (255, 0, 0)   # Blau
    else:
        # optional: Gelb → als Grün behandeln
        return (0, 255, 0)

# Einstellung
USE_DOMINANT_COLOR = False   # 🔁 Hier umschalten (True = nur Rot/Grün/Blau)
CELL_SIZE = 20

cap = cv2.VideoCapture(1)
loop = 0
while True:
    ret, frame = cap.read()
    # frame = normalize_colors(frame)
    frame = normalize_top_pixels(frame)

    if not ret:
        break

    height, width, _ = frame.shape

    # Ausgabe-Bild (wird neu aufgebaut)
    output = np.zeros_like(frame)

    # Durch alle 20x20 Blöcke gehen
    for y in range(0, height, CELL_SIZE):
        for x in range(0, width, CELL_SIZE):

            # Block ausschneiden
            block = frame[y:y+CELL_SIZE, x:x+CELL_SIZE]

            # Mittelwert berechnen (BGR!)
            avg_color = block.mean(axis=(0, 1))

            if USE_DOMINANT_COLOR:
                color = get_dominant_color_hsv(block)
            else:
                # Mittelwert direkt verwenden
                color = avg_color

            # Block einfärben
            output[y:y+CELL_SIZE, x:x+CELL_SIZE] = color

    cv2.imshow("Farb-Analyse", output)

    # Taste 'm' zum Umschalten
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC
        break
    elif key == ord('m'):
        USE_DOMINANT_COLOR = not USE_DOMINANT_COLOR
        print("Modus:", "Dominante Farbe" if USE_DOMINANT_COLOR else "Mittelwert")

cap.release()
cv2.destroyAllWindows()