#!/usr/bin/env python3

import cv2
import time
import math

import pyrealsense2 as rs
import numpy as np

from Detector_Modules.HandDetectorModule_changed import HandDetector as hdm
from Detector_Modules.PoseDetectorModule_changed import poseDetector as pdm
from own_funktions import get_hand_center, ProcessHandAperture, HandOpenClosedBuffer, ValueBuffer, SaveFrameStatus


def main(fps_cap=30, show_fps=True, show_processing=True,source=0, pause_frame:int=None, capture_status_manually:bool=False):
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

    frame_counter = 0
    paused = False
    process = False
    frame = None
    process_ones = False
    hand_aperture_smoother = ProcessHandAperture()
    hand_status_buffer = HandOpenClosedBuffer(buffer_size=10)
    open_close_manual_status = SaveFrameStatus(keys=(ord('1'), ord('2'), ord('3')), status=('hand open', 'hand closed', None)) 

    previous_time = time.perf_counter()
    last_frame_time = time.perf_counter()

    fps_limit = fps_cap
    frame_interval = 1.0 / fps_limit

    hand_detector = hdm()
    pose_detector = pdm()

    time.sleep(0.5)

    cv2.setUseOptimized(True)

    use_realsense = source in ["realsense", "realsense_depth", "realsense_d"]
    show_depth = source in ["realsense_depth", "realsense_d"]

    if use_realsense:

        pipeline = rs.pipeline()
        config = rs.config()

        config.enable_stream(
            rs.stream.color,
            640,
            480,
            rs.format.bgr8,
            30
        )

        if show_depth:
            config.enable_stream(
                rs.stream.depth,
                640,
                480,
                rs.format.z16,
                30
            )

        pipeline.start(config)

        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()

        frame = np.asanyarray(color_frame.get_data())

        success = True

    else:

        video_capture = cv2.VideoCapture(source)

        success, frame = video_capture.read()

        if not video_capture.isOpened():
            print(f"Cannot open source: {source}")
            return

    is_video_file = isinstance(source, str) and not use_realsense

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
        # --------------------------------------------------
        # FPS handling
        # --------------------------------------------------
        if not paused and not process_ones:
            current_time = time.perf_counter()
            # --------------------------------------------------
            # FPS cap

            delta_time = current_time - last_frame_time

            if delta_time < frame_interval:
                continue # skip the reading and processing if the next frrame

            # --------------------------------------------------
            # FPS calculation
            fps = 1.0 / max(
                (current_time - last_frame_time),
                1e-6
            )

            last_frame_time = time.perf_counter()


        # --------------------------------------------------
        # Keyboard controls
        # --------------------------------------------------
        key = cv2.waitKey(1) & 0xFF
        
        # # empty the key buffer to prevent overflow if key stays pressed down, but miss sume keys
        # while cv2.waitKey(1) != -1:
        #     pass

        if key == 27: # esc
            break

        elif key == ord(' '): # space
            paused = not paused
        elif key == 13: # enter
            process = not process

        # --------------------------------------------------
        # Video frame navigation
        # --------------------------------------------------

        if is_video_file:
            if chr(key) in 'wasd':
                if paused:
                    process_ones = True
                
                # A = step back 200 frame
                if key == ord('a'):
                    frame_counter = max(0, frame_counter -200)

                # D = step forward 200 frame
                elif key == ord('d'):
                    frame_counter += 200 

                # S = step back 1 frames
                elif key == ord('s'):
                    frame_counter = max(0, frame_counter - 1) 

                # W = step forward 1 frames
                elif key == ord('w'):
                    frame_counter += 1 
                
                # set frame in video
                video_capture.set(
                        cv2.CAP_PROP_POS_FRAMES,
                        frame_counter 
                    )
                
        # --------------------------------------------------
        # process one frame - unpausing for one frame when paused
        # --------------------------------------------------

        if process_ones:
            if paused:
                paused = False
            else:
                paused = True
                process_ones = False

        # --------------------------------------------------
        # frame counter
        # --------------------------------------------------
        if not paused:
            if is_video_file:
                frame_counter = int(video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            else:
                frame_counter += 1
        # --------------------------------------------------
        # Live / Video Live processing
        # --------------------------------------------------

        if not paused:
            
            if use_realsense:

                frames = pipeline.wait_for_frames()

                color_frame = frames.get_color_frame()

                if not color_frame:
                    continue

                frame = np.asanyarray(color_frame.get_data())

                if show_depth:

                    depth_frame = frames.get_depth_frame()

                    if depth_frame:

                        depth_image = np.asanyarray(
                            depth_frame.get_data()
                        )

                        depth_colormap = cv2.applyColorMap(
                            cv2.convertScaleAbs(
                                depth_image,
                                alpha=0.03
                            ),
                            cv2.COLORMAP_JET
                        )
            else:

                success, frame = video_capture.read()

                if not success:
                    print("End of video stream reached.")
                    break

            if not is_video_file:
                frame = cv2.flip(frame, 1)
            else:                          # define region of intrest (ROI)
                        # frame = frame[
                        #     y_start_pixel: y_end_pixel,
                        #     x_start_pixel: x_end_pixel]
                        pass

            if frame is None:
                continue
        
        # --------------------------------------------------
        # capture status manually
        # --------------------------------------------------
        if capture_status_manually:
            wrong_frame = open_close_manual_status.add(frame_counter, key)
            if type(wrong_frame) == int:
                if is_video_file:
                    if paused:
                        process_ones = True
            
                    # set frame in video
                    video_capture.set(
                            cv2.CAP_PROP_POS_FRAMES,
                            wrong_frame-1 
                        )

        # --------------------------------------------------
        # Pose detection
        # --------------------------------------------------
        if not paused and process:

            # choose between 2D and 3D pose estimation
            _3D = True 
            draw_pose = True
            draw_landmarks = True
            draw_angles = True

            frame = pose_detector.findPose(
                frame=frame,
                draw=show_processing and draw_pose
            )
   
            pose_landmarks = pose_detector.findPosePosition(
                    frame=frame,
                    draw=show_processing and draw_landmarks
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
                    draw=show_processing and draw_angles
                )

                elbow_angle_rad = math.radians(elbow_angle)

                shoulder_angle = pose_detector.findAngle(
                    frame,
                    24,
                    12,
                    14,
                    angle3d=_3D,
                    draw=show_processing and draw_angles
                )
                
                # draw hand points from mediapipe pose landmarks
                hands = [15, 21,19,17, 16, 22, 20, 18,   7,8,0]
                pose_detector.draw_landmarks(
                    frame=frame,
                    landmark_ids=hands,
                )
        # --------------------------------------------------
        # chose ROI for hand detection
        # --------------------------------------------------
        if not paused and process:
            
            roi_hand = None

            if len(pose_landmarks) > 0:

                width = 170
                height = 170

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
        # Hand depth value
        # --------------------------------------------------
        if not paused and process:
            if roi_hand:
                if show_depth:
                    cx, cy = hand_center

                    distance_m = depth_frame.get_distance(
                        int(cx),
                        int(cy)
                    )

                    print(f"Distance: {distance_m:.3f} m")
        # --------------------------------------------------
        # Hand detection
        # --------------------------------------------------
        if not paused and process:
            hand_status = None 

            # if no roi_hand is there, no hand schoult be in the frame
            if roi_hand: 
                draw_landmarks = True
                draw_aperture = True
                draw_roi = True
               

                aperture = None
                open_closed = None

                frame = hand_detector.findHands(
                    frame=frame,
                    roi=roi_hand,
                    draw_landmarks=show_processing and draw_landmarks,
                    draw_roi=show_processing and draw_roi,
                )

                # _, index = hand_detector.choose_hand("top")

                hand_landmarks, frame = hand_detector.findHandPosition(
                        frame=frame, 
                        # hand_num=index, 
                        draw=False
                    )
                
                if len(hand_landmarks) > 0:
                    if 0:
                        frame, aperture = hand_detector.findHandAperture(
                                frame=frame, 
                                verbose=True, 
                                show_aperture=show_processing and draw_aperture
                            )
                    else:
                        open_closed = hand_detector.open_or_close(frame,
                                                                show_processing and draw_aperture)
                        # hand_aperture_smoother.add(aperture)
                        # hand_major = hand_aperture_smoother.get_major()

           
                # --------------------------------------------------
                # smoothing hand status
                hand_status = hand_status_buffer.add_and_get(open_closed)

            # --------------------------------------------------
            # draw hand status

            no_hand_status = {'text':"no hand", 'color':(250,250,250)}
            open_status = {'text':"open", 'color':(0,0,255)}
            close_status = {'text':"closed", 'color':(255,0,0)}
            
            if hand_status == None: # no hand in screen
                text, color = no_hand_status['text'], no_hand_status['color']
            elif hand_status == 1: # open
                text, color = open_status['text'], open_status['color']
            elif hand_status == 0: # closed 
                text, color = close_status['text'], close_status['color']
            
 

            # show hand status
            cv2.putText(
                frame,
                text,
                (10, 200),
                cv2.FONT_HERSHEY_PLAIN,
                2,
                color,
                2
            )

       


        # --------------------------------------------------
        # pause at frame
        # --------------------------------------------------

        if pause_frame is not None and is_video_file:
            if frame_counter == pause_frame:
                if not paused:
                    print(f"Reached pause frame: {pause_frame}")
                    paused = True


        # --------------------------------------------------
        # Status overlay
        # --------------------------------------------------
        # FPS overlay
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

        # --------------------------------------------------
        #  video status overlay
        
        status = "LIVE" if not is_video_file else "VIDEO"

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
        # pause status
        
        if paused:
            cv2.putText(
                frame,
                "PAUSED",
                (120, 80),
                cv2.FONT_HERSHEY_PLAIN,
                2,
                (0, 0, 255),
                2
            )

        # --------------------------------------------------
        # frame counter overlay

        text = f"Frame: {frame_counter}"

        if is_video_file:
            text += '/'
            text += str(int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT)))

        cv2.putText(
            frame,
            text,
            (10, 120),
            cv2.FONT_HERSHEY_PLAIN,
            2,
            (255, 255, 255),
            2
        )

        # --------------------------------------------------
        # controls overlay

        text = "SPACE=Pause | ENTER=processing on/off"
        cv2.putText(
            frame,
            text,
            (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_PLAIN,
            1,
            (0, 255, 0),
            1
        )

        # video file controls
        if is_video_file:
            text = "W/S=+/-1 frame | A/D=+/-200 frames"

            cv2.putText(
                frame,
                text,
                (10, frame.shape[0] - 25),
                cv2.FONT_HERSHEY_PLAIN,
                1,
                (0, 255, 0),
                1
            )

        # --------------------------------------------------
        # stop if the window is closed
        # --------------------------------------------------
        open_windows = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if open_windows < 1 and frame_counter > 1:
            break

        # --------------------------------------------------
        # Display the processed frame - opens a window 
        # --------------------------------------------------
        cv2.imshow(
            window_name,
            frame
        )

        if show_depth:
            cv2.imshow(
                "Depth",
                depth_colormap
            )


    # --------------------------------------------------
    # finaly and closing
    # --------------------------------------------------
    if use_realsense:
        pipeline.stop()
    else:
        video_capture.release()
    cv2.destroyAllWindows()

    # anti_delay_shift = -int(0.2*fps)
    # lust = open_close_manual_status.shift_all_by(anti_delay_shift,)
    open_close_manual_status.save_to_file(source+f"frame_and_open_close_manual_status.txt")

    print("Application terminated.")


if __name__ == "__main__":

    # Webcam input
    # main(source=0)
    v1 = r"C:/Users/Ampelman/Desktop/3D-Audio-Raum.MOV"
    v2 = r"C:/Users/Ampelman/Desktop/WIN_20260609_19_51_56_Pro.mp4"
    v3 = r"C:\Users\Ampelman\Desktop\WIN_20260622_15_27_19_Pro.mp4"
    v4 = r"C:\Users\Ampelman\Desktop\WIN_20260622_15_24_46_Pro.mp4"
    v5 = r"C:\Users\Ampelman\Desktop\WIN_20260622_14_46_06_Pro.mp4".replace("\\","/")
    v6 = r"C:\Users\Ampelman\Desktop\WIN_20260622_14_50_01_Pro.mp4".replace("\\","/")
    rs = 'realsens'
    # Video file input
    main(
        fps_cap=30,
        show_fps=True,
        source=v6,
        pause_frame=None,
        show_processing=True,
        capture_status_manually=False,

    )
    