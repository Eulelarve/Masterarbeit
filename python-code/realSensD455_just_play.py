import pyrealsense2 as rs
import numpy as np
import cv2

# Pfad zur BAG-Datei
bag_file = r"C:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\test_videos (gitignore)\test_aligned_20260731_135056.db3"

# Pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_device_from_file(bag_file, repeat_playback=False)

pipeline.start(config)

# Depth auf Color ausrichten
align = rs.align(rs.stream.color)

try:
    while True:
        try:
            frames = pipeline.wait_for_frames()
        except RuntimeError:
            # Ende der Aufnahme
            break

        frames = align.process(frames)

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()

        if not color_frame or not depth_frame:
            continue

        color = np.asanyarray(color_frame.get_data())
        depth = np.asanyarray(depth_frame.get_data())

        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth, alpha=0.03),
            cv2.COLORMAP_JET
        )

        cv2.imshow("RGB", color)
        cv2.imshow("Depth (aligned)", depth_colormap)

        if cv2.waitKey(1) == 27:  # ESC
            break

finally:
    pipeline.stop()
    cv2.destroyAllWindows()