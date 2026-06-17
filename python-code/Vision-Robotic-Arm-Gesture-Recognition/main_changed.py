#!/usr/bin/env python3

import cv2
import time
import math

from Detector_Modules.HandDetectorModule_changed import HandDetector as hdm
from Detector_Modules.PoseDetectorModule_changed import poseDetector as pdm
from own_funktions import get_hand_center, ProcessHandStatus


def main(fps_cap=30, show_fps=True, source=0, pause_frame:int=None):
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

    first_loop = True
    paused = False
    frame = None
    hand_status_smoother = ProcessHandStatus()

    previous_time = time.perf_counter()
    last_frame_time = time.perf_counter()

    fps_limit = fps_cap
    frame_interval = 1.0 / fps_limit

    hand_detector = hdm()
    pose_detector = pdm()

    time.sleep(0.5)

    cv2.setUseOptimized(True)

    video_capture = cv2.VideoCapture(source)
    success, frame = video_capture.read()

    if not video_capture.isOpened():
        print(f"Cannot open source: {source}")
        return

    is_video_file = isinstance(source, str)

    # -------------------------------------------------------
    # ROI - Define region of interest for video files
    # -------------------------------------------------------
    # if is_video_file:
    #     print(f"Processing video file: {source}")
    #     y_start_pixel, y_end_pixel = int(0.1 * frame.shape[0]), int(0.75 * frame.shape[0])
    #     x_start_pixel, x_end_pixel = int(0.3 * frame.shape[1]), int(0.7 * frame.shape[1])
    # else:
    #     print(f"Processing webcam source: {source}")
    #     video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    #     video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    # -------------------------------------------------------
    # Main processing loop
    # -------------------------------------------------------

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

        elif is_video_file:

            current_frame = int(
                video_capture.get(cv2.CAP_PROP_POS_FRAMES)
            )

            # A = step back 200 frame
            if key == ord('a'):

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    max(0, current_frame - 200)
                )

                success, frame = video_capture.read()

            # D = step forward 200 frame
            elif key == ord('d'):
                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    current_frame + 200
                )

                success, frame = video_capture.read()

            # S = step back 1 frames
            elif key == ord('s'):

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    max(0, current_frame - 1)
                )

                success, frame = video_capture.read()

            # W = step forward 1 frames
            elif key == ord('w'):

                video_capture.set(
                    cv2.CAP_PROP_POS_FRAMES,
                    current_frame + 1
                )

                success, frame = video_capture.read()

        # --------------------------------------------------
        # Live / Video Live processing
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

            if not is_video_file:
                frame = cv2.flip(frame, 1) # mirror the frame for better user interaction, in livestream
            else:                          # define region of intrest (ROI)
                # frame = frame[
                #     y_start_pixel: y_end_pixel,
                #     x_start_pixel: x_end_pixel]
                pass

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
        # Pose detection
        # --------------------------------------------------
        if not paused:

            # choose between 2D and 3D pose estimation
            _3D = True 

            frame = pose_detector.findPose(
                frame=frame,
                draw=False
            )
   
            pose_landmarks = pose_detector.findPosePosition(
                    frame=frame,
                    draw=False
                )
                    
            if len(pose_landmarks) > 0:

                if _3D:
                    pose_detector.find3DPosePosition(
                        draw=False
                    )

                elbow_angle = pose_detector.findAngle(
                    frame,
                    12,
                    14,
                    16,
                    angle3d=_3D,
                    draw=True
                )

                elbow_angle_rad = math.radians(elbow_angle)

                shoulder_angle = pose_detector.findAngle(
                    frame,
                    24,
                    12,
                    14,
                    angle3d=_3D,
                    draw=True
                )
                
                # # draw hand points from mediapipe pose landmarks
                # hands = [15, 21,19,17, 16, 22, 20, 18]
                # pose_detector.draw_landmarks(
                #     frame=frame,
                #     landmark_ids=hands,
                # )
        # --------------------------------------------------
        # chose ROI for hand detection
        # --------------------------------------------------
        if not paused:
            
            roi_hand = None

            if len(pose_landmarks) > 0:

                width = 100
                height = 100

                min_width = width // 2
                min_height = height // 2

                hand_center = get_hand_center(
                    pose_landmarks=pose_landmarks,
                    left_right_top="top",
                    mirrored=not is_video_file
                )

                start_x = hand_center[0] - width // 2
                start_y = hand_center[1] - height // 2
                end_x = start_x + width
                end_y = start_y + height
                # ensure the ROI is within the frame boundaries
                start_x = max(0, start_x)
                start_y = max(0, start_y)
                end_x = min(frame.shape[1], end_x)
                end_y = min(frame.shape[0], end_y)
                # update width and height based on the adjusted ROI
                width = end_x - start_x
                height = end_y - start_y
                # only use the ROI if it is large enough
                if width >= min_width and height >= min_height:
                    roi_hand = (start_x, start_y, width, height)

        # --------------------------------------------------
        # Hand detection
        # --------------------------------------------------
        if not paused:
            
            aperture = None

            frame = hand_detector.findHands(
                frame=frame,
                roi=roi_hand,
                draw_landmarks=True
            )

            # _, index = hand_detector.choose_hand("top")

            hand_landmarks, frame = hand_detector.findHandPosition(
                    frame=frame, 
                    # hand_num=index, 
                    draw=False
                )
            
            if len(hand_landmarks) > 0:
                frame, aperture = hand_detector.findHandAperture(
                        frame=frame, 
                        verbose=True, 
                        show_aperture=True
                    )

            hand_status_smoother.add(aperture)
            hand_major = hand_status_smoother.get_major()
            # show hand status
            cv2.putText(
                frame,
                hand_major['text'],
                (10, 200),
                cv2.FONT_HERSHEY_PLAIN,
                2,
                hand_major['color'],
                2
            )

        # --------------------------------------------------
        # Status overlay
        # --------------------------------------------------

        if show_fps:
            x = frame.shape[1] - 170
            y = 40
            cv2.putText(
                frame,
                f"FPS: {round(fps, 1)}",
                (x, y),
                cv2.FONT_HERSHEY_PLAIN,
                2,
                (0, 255, 0),
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
            x, y = 10, frame.shape[0] - 20
            cv2.putText(
                frame,
                "SPACE=Pause | W/S=+/-1 frame | A/D=+/-200 frames",
                (x, y),
                cv2.FONT_HERSHEY_PLAIN,
                1.5,
                (0, 255, 0),
                2
            )

        # --------------------------------------------------
        # pause at frame
        # --------------------------------------------------
        if pause_frame is not None and is_video_file:
            if current_frame_index == pause_frame:
                if not paused:
                    print(f"Reached pause frame: {pause_frame}")
                    paused = True

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
        source=v2,
        pause_frame=None
    )