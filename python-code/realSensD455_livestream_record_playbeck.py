import pyrealsense2 as rs
import numpy as np
import cv2
from datetime import datetime
from Vision_Robotic_Arm_Gesture_Recognition.analyse import find_files
from importlib.metadata import version

print(version("pyrealsense2"))
### settings
capture = True
live_stream = False
replay = True
show_depth = True
show_color = True
align = True
mirrowed = True
realtime = False
video_formet = 1280,720
video_name = "d03_0deg_1280x720p_15deg_grapping_left"
save_folder ="../test_videos (gitignore)/"
ending = '.bag' # db3 or dag datei depens on rs version, >=2.57 -> db3
time_stemp = False
###

time_stemp = "_"+datetime.now().strftime("%Y%m%d_%H%M%S") if time_stemp else ""

path = save_folder+video_name+time_stemp+ending

last_color = None
last_depth = None

mouse_x, mouse_y = -1, -1
click_x, click_y = -1, -1
clicked = False

def mouse_callback(event, x, y, flags, param):
    global mouse_x, mouse_y
    global click_x, click_y, clicked

    if event == cv2.EVENT_MOUSEMOVE:
        mouse_x, mouse_y = x, y

    elif event == cv2.EVENT_LBUTTONDOWN:
        click_x, click_y = x, y
        clicked = True



def show_stream(show_color , show_depth, align=True, mirrowed = False):
    if show_color:
        cv2.namedWindow("RGB")
        cv2.setMouseCallback("RGB", mouse_callback)
    if show_depth:
        cv2.namedWindow("Depth")
        cv2.setMouseCallback("Depth", mouse_callback)
    paused = False
    while True:
        if not paused:
            frames = pipeline.wait_for_frames()

            if align:
                frames = aligner.process(frames)

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            depth_intrinsics = depth_frame.profile.as_video_stream_profile().intrinsics

            if not color_frame or not depth_frame:
                print('not color or depth frame... break')
                break

            last_color = np.asanyarray(color_frame.get_data())
            last_depth = np.asanyarray(depth_frame.get_data())

        color = last_color.copy()
        depth = last_depth.copy()

        if mirrowed:
            # Optional spiegeln
            color = cv2.flip(color, 1)

        depth_colormap = cv2.applyColorMap(
            cv2.convertScaleAbs(depth, alpha=0.03),
            cv2.COLORMAP_JET
        )
        if mirrowed:
            depth_colormap = cv2.flip(depth_colormap, 1)

        # Mauskreuz
        if mouse_x >= 0 and mouse_y >= 0:
            cv2.drawMarker(color, (mouse_x, mouse_y),
                        (0, 255, 0), cv2.MARKER_CROSS, 20, 2)
            cv2.drawMarker(depth_colormap, (mouse_x, mouse_y),
                        (255, 255, 255), cv2.MARKER_CROSS, 20, 2)

        if show_color:
            cv2.imshow("RGB", color)
        if show_depth:
            cv2.imshow("Depth", depth_colormap)

        global clicked

        if clicked:
            x = click_x
            y = click_y

            # Falls Bild gespiegelt wird
            if mirrowed:
                x = depth.shape[1] - 1 - x

            distance = depth_frame.get_distance(x, y)   # Meter

            if distance > 0:
                point = rs.rs2_deproject_pixel_to_point(
                    depth_intrinsics,
                    [x, y],
                    distance
                )

                print(
                    f"Pixel ({click_x}, {click_y}) -> "
                    f"X={point[0]:.3f} m, "
                    f"Y={point[1]:.3f} m, "
                    f"Z={point[2]:.3f} m"
                )
            else:
                print("Keine gültige Tiefeninformation.")
        clicked = False

        key = cv2.waitKey(20) & 0xFF

        if key == 27:          # ESC
            break
        elif key == 32:        # Leertaste
            paused = not paused

if not show_color:
    print('show color frame is off')
if not show_depth:
    print('show depth frame is off')

if capture or live_stream:

    # Pipeline konfigurieren
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_stream(rs.stream.color, *video_formet, rs.format.bgr8, 30)
    config.enable_stream(rs.stream.depth, *video_formet, rs.format.z16, 30)

    if capture:
        # Aufnahme in BAG-Datei
        config.enable_record_to_file(path)

    pipeline.start(config)
    if align:
        aligner = rs.align(rs.stream.color)

    try:
        show_stream(show_color,show_depth,align,mirrowed)

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()


if replay:
    path = find_files(save_folder,ending,video_name,)[0]
    print('replay:', path)
    pipeline = rs.pipeline()
    config = rs.config()

    config.enable_device_from_file(path, repeat_playback=False)

    profile = pipeline.start(config)

    playback = profile.get_device().as_playback()

    playback.set_real_time(realtime) 

    if align:
        aligner = rs.align(rs.stream.color)

    try:
        show_stream(show_color,show_depth,align,mirrowed)

    finally:
        pipeline.stop()
        cv2.destroyAllWindows()

