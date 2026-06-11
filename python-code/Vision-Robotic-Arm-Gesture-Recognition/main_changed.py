#!/usr/bin/env python3

import cv2
import time
import math

from Detector_Modules.HandDetectorModule import HandDetector as hdm
from Detector_Modules.PoseDetectorModule import poseDetector as pdm


def main(fps_cap=30, show_fps=True, source=0):
    """
    Video processing entry point.

    Parameters
    ----------
    fps_cap : int
        Maximum processing frame rate.

    show_fps : bool
        Enable FPS overlay.

    source :
        0,1,2,...   -> webcam device
        "video.mp4" -> video file
    """
    window_name = "Hand and Pose Detection"

    hand_detector = hdm()
    pose_detector = pdm()

    time.sleep(0.5)

    cv2.setUseOptimized(True)

    video_capture = cv2.VideoCapture(source)

    if not video_capture.isOpened():
        print(f"Cannot open source: {source}")
        return

    is_video_file = isinstance(source, str)

    first_loop = True
    paused = False
    frame = None

    previous_time = time.perf_counter()
    last_frame_time = time.perf_counter()

    fps_limit = fps_cap
    frame_interval = 1.0 / fps_limit


    while True:

        key = cv2.waitKey(1) & 0xFF

        # --------------------------------------------------
        # Keyboard controls
        # --------------------------------------------------

        if key == 27:
            break

        elif key == ord(' '):
            paused = not paused

        # --------------------------------------------------
        # Video frame navigation
        # --------------------------------------------------

        elif paused and is_video_file:

            current_frame = int(
                video_capture.get(cv2.CAP_PROP_POS_FRAMES)
            )

            # A/← = step back 1 frame
            if key in (ord('a'), 81):  # 81 is the left arrow key code

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    max(0, current_frame - 1)
                )

                success, frame = video_capture.read()

            # D/→ = step forward 1 frame
            elif key in (ord('d'), 83):  # 83 is the right arrow key code

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    current_frame + 1
                )

                success, frame = video_capture.read()

            # S/↓ = step back 10 frames
            elif key in (ord('s'), 82):  # 82 is the down arrow key code

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    max(0, current_frame - 10)
                )

                success, frame = video_capture.read()

            # W/↑ = step forward 10 frames
            elif key in (ord('w'), 80):  # 80 is the up arrow key code

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    current_frame + 10
                )

                success, frame = video_capture.read()

        # --------------------------------------------------
        # Live processing
        # --------------------------------------------------

        if not paused:

            delta_time = time.perf_counter() - last_frame_time

            if delta_time < frame_interval:
                continue

            last_frame_time = time.perf_counter()

            success, frame = video_capture.read()

            if not success:
                print("End of video stream reached.")
                break

        if frame is None:
            continue

        # --------------------------------------------------
        # FPS calculation
        # --------------------------------------------------
        if not paused:
            current_time = time.perf_counter()

            fps = 1.0 / max(
                (current_time - previous_time),
                1e-6
            )

            previous_time = current_time

        # --------------------------------------------------
        # Hand detection
        # --------------------------------------------------
        if not paused:
            frame = hand_detector.findHands(
                frame=frame,
                draw=True
            )

            hand_landmarks, frame = hand_detector.findHandPosition(
                    frame=frame, 
                    hand_num=0, 
                    draw=False
                )
            
            if len(hand_landmarks) > 0:
                frame, aperture = hand_detector.findHandAperture(
                        frame=frame, 
                        verbose=True, 
                        show_aperture=True
                    )
    

        # --------------------------------------------------
        # Pose detection
        # --------------------------------------------------
        if not paused:
            frame = pose_detector.findPose(
                frame=frame,
                draw=False
            )

            pose_landmarks = pose_detector.findPosePosition(
                    frame=frame,
                    draw=False
                )

            if len(pose_landmarks) > 0:

                elbow_angle = pose_detector.findAngle(
                    frame,
                    12,
                    14,
                    16,
                    angle3d=False,
                    draw=True
                )

                elbow_angle_rad = math.radians(elbow_angle)

                shoulder_angle = pose_detector.findAngle(
                    frame,
                    24,
                    12,
                    14,
                    angle3d=False,
                    draw=True
                )

        # --------------------------------------------------
        # Status overlay
        # --------------------------------------------------

        if show_fps:

            cv2.putText(
                frame,
                f"FPS: {round(fps, 1)}",
                (10, 40),
                cv2.FONT_HERSHEY_PLAIN,
                2,
                (255, 255, 255),
                2
            )

        status = "LIVE"

        if paused:
            status = "PAUSED"

        cv2.putText(
            frame,
            status,
            (10, 80),
            cv2.FONT_HERSHEY_PLAIN,
            2,
            (0, 255, 0),
            2
        )

        # --------------------------------------------------
        # Video information overlay
        # --------------------------------------------------

        if is_video_file:

            current_frame_index = int(
                video_capture.get(
                    cv2.CAP_PROP_POS_FRAMES
                )
            )

            total_frames = int(
                video_capture.get(
                    cv2.CAP_PROP_FRAME_COUNT
                )
            )

            cv2.putText(
                frame,
                f"Frame: {current_frame_index}/{total_frames}",
                (10, 120),
                cv2.FONT_HERSHEY_PLAIN,
                2,
                (255, 255, 255),
                2
            )

            cv2.putText(
                frame,
                "SPACE=Pause | A/D=±1 frame | W/S=±10 frames",
                (10, 160),
                cv2.FONT_HERSHEY_PLAIN,
                1.5,
                (255, 255, 255),
                1
            )

        # --------------------------------------------------
        # Display output
        # --------------------------------------------------
        # stop if the window is closed
        if first_loop:
            first_loop = False
        elif cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) < 1:
            break

        cv2.imshow(
            window_name,
            frame
        )



    video_capture.release()
    cv2.destroyAllWindows()

    print("Application terminated.")


if __name__ == "__main__":

    # Webcam input
    # main(source=0)
    v1 = "C:/Users/Ampelman/Desktop/3D-Audio-Raum.MOV"
    v2 = "C:/Users/Ampelman/Desktop/WIN_20260609_19_51_56_Pro.mp4"
    # Video file input
    main(
        fps_cap=30,
        show_fps=True,
        source=v1
    )