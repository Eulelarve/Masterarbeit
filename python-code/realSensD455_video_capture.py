import pyrealsense2 as rs
import numpy as np
import cv2
from datetime import datetime
from Vision_Robotic_Arm_Gesture_Recognition.analyse import find_files



### settings
capture = True
replay = False
time_stemp =True
video_formet = 1280,720
video_name = "d1_0_deg_1280x720p_15_deg_grapoing_left"
save_folder ="../test_videos (gitignore)/"
ending = '.db3'
###

time_stemp = "_"+datetime.now().strftime("%Y%m%d_%H%M%S") if time_stemp else ""

path = save_folder+video_name+time_stemp+ending

if capture:
    # Pipeline konfigurieren
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, *video_formet, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, *video_formet, rs.format.z16, 30)

    # Aufnahme in BAG-Datei
    config.enable_record_to_file(path)

    pipeline.start(config)

    try:
        while True:
            frames = pipeline.wait_for_frames()

            color_frame = frames.get_color_frame()
            if not color_frame:
                continue

            color_image = np.asanyarray(color_frame.get_data())

            # RGB-Bild anzeigen
            cv2.imshow("RGB", color_image)

            # ESC beendet
            key = cv2.waitKey(1)
            if key == 27:
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if replay:
    path = find_files(save_folder,ending,video_name,)[0]

    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_device_from_file(path, repeat_playback=False)

    pipeline.start(config)

    try:
        while True:
            frames = pipeline.wait_for_frames()

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()

            if not color_frame or not depth_frame:
                break

            color = np.asanyarray(color_frame.get_data())
            depth = np.asanyarray(depth_frame.get_data())

            depth_colormap = cv2.applyColorMap(
                cv2.convertScaleAbs(depth, alpha=0.03),
                cv2.COLORMAP_JET
            )

            cv2.imshow("RGB", color)
            cv2.imshow("Depth", depth_colormap)

            if cv2.waitKey(1) == 27:
                break

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()