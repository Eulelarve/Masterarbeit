#!/usr/bin/env python3

import cv2
import time
import math

import pyrealsense2 as rs
import numpy as np
from datetime import datetime

from Detector_Modules.HandDetectorModule_changed import HandDetector as hdm
from Detector_Modules.PoseDetectorModule_changed import poseDetector as pdm
from own_funktions import get_hand_center, ProcessHandAperture, HandOpenClosedBuffer, ValueBuffer, SaveFrameStatus, CSVWriter, tolist, screenshot

def main(fps_cap=30, show_fps=True, show_processing=True,source=0, 
         pause_frames:list=None, 
         capture_status_manually:bool=False, 
         capture_status_comparison:bool=False,
         roi_size:int=100,
         start_frame:int = None,
         end_frame:int=None,
         foto_name:str='hand_detection',
         foto_frames:list=None,
         ):
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
    # check input parameters
    
    pause_frames = tolist(pause_frames)
    foto_frames = tolist(foto_frames)

    if start_frame is None:
        start_frame = 0
    
    # create variables
    return_value = True

    window_name = "Hand and Pose Detection"

    frame_counter_processed = 0
    frame_counter_pose = 0
    frame_counter_hand = 0
    current_frame = start_frame - 1

    paused = False
    process = True
    frame = None
    process_ones = False
    upper_body_size = ValueBuffer(40)
    hand_aperture_smoother = ProcessHandAperture()
    hand_status_buffer = HandOpenClosedBuffer(buffer_size=10)
    open_close_status_capturer = SaveFrameStatus(keys=(ord('1'), ord('2'), ord('3')), status=('hand open', 'hand closed', None)) 

    previous_time = time.perf_counter()
    last_frame_time = time.perf_counter()

    fps_limit = fps_cap
    frame_interval = 1.0 / fps_limit
    fps_sum = 0

    hand_detector = hdm()
    pose_detector = pdm()

    time.sleep(0.5)

    cv2.setUseOptimized(True)

    use_realsense = source in ["realsense", "realsense_depth", "realsense_d"]
    show_depth = source in ["realsense_depth", "realsense_d"]
    is_video_file = isinstance(source, str) and not use_realsense
    
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

    else: # other webcams or video input

        video_capture = cv2.VideoCapture(source)
        

        success, frame = video_capture.read()

        if not video_capture.isOpened():
            print(f"Cannot open source: {source}")
            return


    frame_x=frame.shape[1] 
    frame_y=frame.shape[0]

    # set to start frame / reset to frame 0
    if is_video_file:
            if start_frame > 1:
                video_capture.set(cv2.CAP_PROP_POS_FRAMES, start_frame -1)
            else:
                video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)


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

        time_stemp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # --------------------------------------------------
        # FPS handling
        # --------------------------------------------------
        if not paused and not process_ones:
            current_time = time.perf_counter()
            # --------------------------------------------------
            # FPS cap

            delta_time = current_time - last_frame_time

            if delta_time < frame_interval:
                continue # skip the reading and processing if the next frame and all other stuff in the loop 

            # --------------------------------------------------
            # FPS calculation
            if delta_time: # just in case 1/0
                fps = 1.0 /(current_time - last_frame_time)
            else:
                print('Error delta_time is',delta_time)

            last_frame_time = time.perf_counter()
            
            fps_sum += fps

        # --------------------------------------------------
        # Keyboard controls
        # --------------------------------------------------
        key = cv2.waitKey(1) & 0xFF
        
        # # empty the key buffer to prevent overflow if key stays pressed down, but miss sume keys
        # while cv2.waitKey(1) != -1:
        #     pass

        if key == 27: # esc
            return_value = False
            break

        elif key == ord(' '): # space -> Pause
            paused = not paused

        elif key == 13: # enter -> processing on/off
            process = not process

        elif key == ord('p'): # p -> screen shot
            screenshot(frame=frame, name=foto_name)

        # --------------------------------------------------
        # Video frame navigation
        # --------------------------------------------------

        if is_video_file:
            if chr(key) in 'wasd':
                if paused:
                    process_ones = True
                
                # A = step back 200 frame
                if key == ord('a'):
                    current_frame = max(0, current_frame-200)

                # D = step forward 200 frame
                elif key == ord('d'):
                    current_frame += 200 

                # S = step back 1 frames
                elif key == ord('s'):
                    current_frame = max(0, current_frame - 1) 

                # W = step forward 1 frames
                elif key == ord('w'):
                    current_frame += 1 
                
                current_frame -= 1 # -1 because each loop adds one frame, by it self
                # set frame in video
                video_capture.set(
                        cv2.CAP_PROP_POS_FRAMES,
                        current_frame 
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
        # currend frame
        # --------------------------------------------------
        if is_video_file:
            current_frame = int(video_capture.get(cv2.CAP_PROP_POS_FRAMES))
        elif not paused: # live stream not paused
            current_frame += 1
        

        # --------------------------------------------------
        # Pose detection
        # --------------------------------------------------
        if not paused and process:

            # choose between 2D and 3D pose estimation
            _3D = False 
            draw_pose = False
            draw_landmarks = False
            draw_angles = False

            frame = pose_detector.findPose(
                frame=frame,
                draw=show_processing and draw_pose
            )
   
            pose_landmarks = pose_detector.findPosePosition(
                    frame=frame,
                    draw=show_processing and draw_landmarks
                )
                    
            if len(pose_landmarks) > 0:
                # pose detected in frame
                frame_counter_pose += 1

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
                
                # # draw hand points from mediapipe pose landmarks
                # hands = [15, 21,19,17, 16, 22, 20, 18,   7,8,0]
                # pose_detector.draw_landmarks(
                #     frame=frame,
                #     landmark_ids=hands,
                # )
        # --------------------------------------------------
        # chose ROI for hand detection
        # --------------------------------------------------
        if not paused and process:
            roi_hand = None

            # --------------------------------------------------
            # hand ROI size from body length
            # pixel = int(pose_detector.get_upper_body_length())
            # upper_budy_pixel_len = upper_body_size.add_and_get_average(pixel)
            # roi_size = int(upper_budy_pixel_len * 1.5)
            
            # --------------------------------------------------
            # hand ROI size from frame size
            # roi_size =  frame.shape[0] // 5

            # --------------------------------------------------
            # difine hand ROI area in frame
            if len(pose_landmarks) > 0 and roi_size:
                roi_width = roi_size
                roi_height = roi_size

                # dont try if less then min window size
                min_width = 50
                min_height = 50

                hand_center = get_hand_center(
                    pose_landmarks=pose_landmarks,
                    left_right_top="top",
                    mirrored=not is_video_file
                )

                start_x = hand_center[0] - roi_width // 2
                start_y = hand_center[1] - roi_height // 2
                end_x = start_x + roi_width
                end_y = start_y + roi_height
                # ensure the ROI is within the frame boundaries
                start_x = max(0, start_x)
                start_y = max(0, start_y)
                end_x = min(frame.shape[1], end_x)
                end_y = min(frame.shape[0], end_y)
                # update width and height based on the adjusted ROI
                roi_width = end_x - start_x
                roi_height = end_y - start_y
                # only use the ROI if it is large enough
                if roi_width >= min_width and roi_height >= min_height:
                    roi_hand = (start_x, start_y, roi_width, roi_height)
       
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
            if roi_hand or not roi_size: 
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
                    # hand detected in frame
                    frame_counter_hand += 1

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
        # capture status comparsion 
        # --------------------------------------------------
        if not paused:
            if capture_status_comparison:
                open_close_status_capturer.add_comparison_status(open_closed)
        
        # --------------------------------------------------
        # capture status manually
        # --------------------------------------------------
        if capture_status_manually:
            wrong_frame = open_close_status_capturer.add(current_frame, key)
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
        # frame is fully processed 
        # --------------------------------------------------
        if not paused:
            if process:
                frame_counter_processed += 1
        
        # ==================================================
        # Status overlay - end of video processing
        # ==================================================

        # FPS overlay
        if not paused:
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

        text = f"Frame: {current_frame}"

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
        # pause at frame or later if skiped
        # --------------------------------------------------
        if pause_frames:
            pause_frame = min(pause_frames)
            if current_frame >= pause_frame:
                if not paused:
                    print(f"currend frame {current_frame} reached pause frame {pause_frame}")
                    paused = True
                    pause_frames.remove(pause_frame)
        
        # --------------------------------------------------
        # pause at frame or later if skiped
        # --------------------------------------------------
        if foto_frames:
            foto_frame = min(foto_frames)
            if current_frame == foto_frame:
                print(f"reached foto frame {foto_frame}")
                foto_frames.remove(foto_frame)

                hand_rate = round(frame_counter_hand / frame_counter_processed *100, 1)
                pose_rate = round(frame_counter_pose / frame_counter_processed *100, 1)
                fps_mean = round(fps_sum / frame_counter_processed, 1)

                screenshot(frame=frame, name=source,
                           info=[
                                    frame_x, frame_y,
                                    roi_size, 
                                    frame_counter_processed,
                                    frame_counter_pose, pose_rate,
                                    frame_counter_hand, hand_rate,
                                    fps_mean,
                                ]
                           )

        # --------------------------------------------------
        # stop if end frame is reached
        # --------------------------------------------------
        if not paused:
            if end_frame is not None:
                if current_frame >= end_frame:
                    print(f'currend frame {current_frame} reached end frame {end_frame} -> end this loop')
                    break

        # --------------------------------------------------
        # stop if the window is closed
        # --------------------------------------------------
        open_windows = cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE)
        if current_frame > start_frame + 1: # wate for forst frame, to open up the window
            if open_windows < 1: # if no wiendow is open
                print('window closed by user')
                break # end programm

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

        
    # ==================================================
    # finaly and closing - loop ended
    # ==================================================
    # closing cv2 or realsens 
    if use_realsense:
        pipeline.stop()
    else:
        video_capture.release()
    cv2.destroyAllWindows()

    # --------------------------------------------------
    # post-processing

    # anti_delay_shift = -int(0.2*fps)
    # lust = open_close_status_capturer.shift_all_by(anti_delay_shift,)
    name = source+f"_frame_and_open_close_manual_status"
    end = '.txt'
    if capture_status_manually:
        open_close_status_capturer.save_to_file(name+end)

    if capture_status_comparison:
        open_close_status_capturer.load_from_file(name+end)
        open_close_status_capturer.save_comp_to_file(name+'_comp_'+end)
    
    hand_rate = round(frame_counter_hand / frame_counter_processed *100, 1)
    pose_rate = round(frame_counter_pose / frame_counter_processed *100, 1)
    fps_mean = round(fps_sum / frame_counter_processed, 1)

    # --------------------------------------------------
    # print analyse stats
    print(f"pose detektet in {frame_counter_pose} of {frame_counter_processed} frames ({pose_rate} %)")
    print(f"hand detektet in {frame_counter_hand} of {frame_counter_processed} frames ({hand_rate} %)")
    print(f"used ROI size {roi_size} in frame with {frame_x} x {frame_y} pixel")
    print(f'performance {fps_mean} fps mean')

    # --------------------------------------------------
    # save analyse stats
    CSVWriter.write('HAND_FPS_TEST.csv',
        name=source,
        frame_x=frame_x, frame_y=frame_y,
        roi_size=roi_size, 
        frame_counter_processed=frame_counter_processed,
        frame_counter_pose=frame_counter_pose, pose_rate=pose_rate,
        frame_counter_hand=frame_counter_hand, hand_rate=hand_rate,
        fps_mean=fps_mean
    )
    # --------------------------------------------------
    # end mesage
    print(f"Video Detection with source: {source}")
    print(f"Video Detection End")
    return return_value


if __name__ == "__main__":

    # Webcam input
    # main(source=0)
    v0 = r"C:/Users/Ampelman/Desktop/3D-Audio-Raum.MOV"
    v1 = r"C:/Users/Ampelman/Desktop/v1_20260609_19_51_56_Pro.mp4"
    v2 = r"C:\Users\Ampelman\Desktop\v2_20260622_15_27_19_Pro.mp4"
    v3 = r"C:\Users\Ampelman\Desktop\v3_20260622_15_24_46_Pro.mp4"
    v4 = r"C:\Users\Ampelman\Desktop\v4_20260622_14_46_06_Pro.mp4"
    v5 = r"C:\Users\Ampelman\Desktop\v5_20260622_14_50_01_Pro.mp4"
    rs = 'realsens'
    # Video file input
    for v in (v1,v2,v3,v4,v5):
        for roi_size in [None,50,100,300]:
            r = main(
                fps_cap=60,
                show_fps=True,
                source=v,
                pause_frames=None,
                show_processing=True,
                capture_status_manually=False,
                capture_status_comparison = False,
                roi_size = roi_size,
                start_frame=250,
                end_frame = None,
                foto_name='234§4$%"!_:hand_detection',
                foto_frames=None,
            )
            if r == False:
                break
        if r == False:
                break
    