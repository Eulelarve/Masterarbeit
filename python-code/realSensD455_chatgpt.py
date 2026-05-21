import pyrealsense2 as rs
import numpy as np
import cv2

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
        # Frames holen
        frames = pipeline.wait_for_frames()

        depth_frame = frames.get_depth_frame()
        color_frame = frames.get_color_frame()

        if not depth_frame or not color_frame:
            continue

        # In numpy konvertieren
        color_image = np.asanyarray(color_frame.get_data())

        # Tiefenbild einfärben
        depth_colormap = np.asanyarray(
            colorizer.colorize(depth_frame).get_data()
        )

        # Anzeigen
        cv2.imshow("RGB Bild", color_image)
        cv2.imshow("Tiefenbild", depth_colormap)

        key = cv2.waitKey(1)

        # ESC zum Beenden
        if key == 27:
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()