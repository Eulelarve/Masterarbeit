import pyrealsense2 as rs
import numpy as np
import cv2
from datetime import datetime

recording = False
video_writer = None

# Pipeline erstellen
pipeline = rs.pipeline()

# Konfiguration
config = rs.config()

# RGB Stream
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Tiefen-Stream
config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)

# Kamera starten
pipeline.start(config)

# Colorizer für schönes Tiefenbild
colorizer = rs.colorizer()

try:
    while True:
        frames = pipeline.wait_for_frames()

        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        # RGB Bild
        color_image = np.asanyarray(color_frame.get_data())

        # Originale Tiefendaten (16 Bit)
        depth_image = np.asanyarray(depth_frame.get_data())

        # Nur zur Anzeige eingefärbt
        depth_colormap = np.asanyarray(
            colorizer.colorize(depth_frame).get_data()
        )

        cv2.imshow("RGB Bild", color_image)
        cv2.imshow("Tiefenbild", depth_colormap)

        key = cv2.waitKey(1) & 0xFF

        # Video aufnehmen
        if recording:
            video_writer.write(color_image)

        # V = Aufnahme starten/stoppen
        if key == ord("v"):

            if not recording:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                video_name = f"video_{timestamp}.mp4"

                fourcc = cv2.VideoWriter_fourcc(*"mp4v")

                video_writer = cv2.VideoWriter(
                    video_name,
                    fourcc,
                    30,
                    (640, 480)
                )

                recording = True
                print(f"Videoaufnahme gestartet: {video_name}")

            else:
                recording = False

                if video_writer is not None:
                    video_writer.release()
                    video_writer = None

                print("Videoaufnahme gestoppt")

        # S = Speichern
        if key == ord("s"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            rgb_name = f"rgb_{timestamp}.png"
            depth_name = f"depth_{timestamp}.png"

            cv2.imwrite(rgb_name, color_image)
            cv2.imwrite(depth_name, depth_image)

            print(f"Gespeichert: {rgb_name}")
            print(f"Gespeichert: {depth_name}")

        # ESC = Beenden
        elif key == 27:
            break

finally:
    if video_writer is not None:
        video_writer.release()

    cv2.destroyAllWindows()
    pipeline.stop()