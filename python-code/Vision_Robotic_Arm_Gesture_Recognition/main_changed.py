#!/usr/bin/env python3

import cv2
import time
import math

import pyrealsense2 as rs
import numpy as np
from datetime import datetime


from own_functions import ProcessHandAperture, HandOpenClosedBuffer, ValueBuffer, CSVWriter, tolist, screenshot, close_to, MoveDetector, get_globe_timeline_curvs, angle_between_points, draw_angle_between_points


from HandDetectorModule_changed import HandDetector as hdm
from PoseDetectorModule_changed import poseDetector as pdm
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

def main(fps_cap=30, show_fps=True, show_processing=True,source=0, 
         pause_frames:list=None, 
         capture_status_manually:bool=False, 
         capture_status:bool=False,
         roi_size:int=100,
         start_frame:int = None,
         end_frame:int=None,
         foto_name:str='hand_detection',
         foto_frames:list=None,
         hand_not_found_means=None,
         skip_hand_move_detection=False,
         show_globe = False

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
    red = (0, 0, 255)
    blue = (255, 0, 0)
    white = (250,250,250)
    return_value = True

    window_name = "Hand and Pose Detection"

    frame_counter_processed = 0
    frame_counter_pose = 0
    frame_counter_hand = 0
    current_frame = start_frame - 1
    size_sum = 0
    open_closed = None
    hand_status = None 

    hand_status_dict = {'aperture':None, 'aperture_width':None,  'len_width_thr_1.2':None, 'len_width_thr_1.4':None, 'distance_dif_0.3':None,'distance_dif_0.4':None}
    hand_status_detected = {'aperture':[], 'aperture_width':[],  'len_width_thr_1.2':[], 'len_width_thr_1.4':[], 'distance_dif_0.3':[], 'distance_dif_0.4':[]}
    hand_status_buffer_dict = {'aperture':HandOpenClosedBuffer(buffer_size=S.hand_status_buffer_size), 'aperture_width':HandOpenClosedBuffer(buffer_size=S.hand_status_buffer_size), 
                                'len_width_thr_1.2':HandOpenClosedBuffer(buffer_size=S.hand_status_buffer_size), 'len_width_thr_1.4':HandOpenClosedBuffer(buffer_size=S.hand_status_buffer_size), 
                                'distance_dif_0.3':HandOpenClosedBuffer(buffer_size=1), 'distance_dif_0.4':HandOpenClosedBuffer(buffer_size=1)}
    


    paused = False
    process = True
    frame = None
    process_ones = False
    upper_body_size = ValueBuffer(40)
    hand_aperture_smoother = ValueBuffer(5)
    hand_move = MoveDetector(min_speed=2, max_speed_change=20, buffer_size=5)
    hand_status_buffer = HandOpenClosedBuffer(buffer_size=S.hand_status_buffer_size)
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
            screenshot(frame=frame, name=foto_name, ask_name=True)

        # --------------------------------------------------
        # Video frame navigation
        # --------------------------------------------------

        if is_video_file:
            if chr(key) in 'wasd':
                if paused:
                    process_ones = True
                
                # A = step back x frame
                if key == ord('a'):
                    current_frame = max(0, current_frame- S.skip_frames)

                # D = step forward x frame
                elif key == ord('d'):
                    current_frame += S.skip_frames

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
            _3D = True 
            draw_pose = False
            draw_landmarks = False

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

                
                # draw hand points from mediapipe pose landmarks
                if show_processing and draw_landmarks:
                    hands = [15, 21,19,17, 16, 22, 20, 18, ]
                    pose_detector.draw_landmarks(
                        frame=frame,
                        landmark_ids=hands,
                    )

        # --------------------------------------------------
        # get hand center and coresponding shulder and max arm length, relative arm length
        # --------------------------------------------------
        if not paused and process:
            if len(pose_landmarks) > 0:
                # hand and shulder
                pose_detector.find_specific_limbs(_3D)
                hand_center = pose_detector.hand_center
                shulder = pose_detector.shulder
                # arm
                pose_detector.calibrate_arm_length(time_to_calibrate=2)
                rel_arm_len = math.dist(hand_center, shulder)
        # --------------------------------------------------
        # hand (pose landmarks) is moving
        # --------------------------------------------------
        if not paused and process:
            if len(pose_landmarks) > 0:
                hand_stands_still = hand_move.stands_still(hand_center)

        # --------------------------------------------------
        # Analyze arm angle / pointing direction
        # --------------------------------------------------
        if not paused and process:
            if len(pose_landmarks) > 0:
                draw_angles = True

                # if hasattr(pose_detector,'arm_len'): # if arm length alreaddy calibrated
                #     pass

                x = pose_detector.lm_list[16][1] 
                y = pose_detector.lm_list[16][2]
                if pose_detector.lm_3dlist[16][3] < pose_detector.lm_3dlist[12][3] -0.05:
                    color = red
                    print('Vorne', pose_detector.lm_3dlist[16][3], pose_detector.lm_3dlist[12][3])
                else:
                    color = blue
                    print('Hinten',  pose_detector.lm_3dlist[16][3], pose_detector.lm_3dlist[12][3])

                cv2.circle(frame,(x,y),30,color,-1)

                # --------------------------------------------------
                # azimuth

                arm_azimuth = pose_detector.findAngle(
                    frame,
                    11,
                    12,
                    16,
                    angle3d=_3D,
                    draw=show_processing and draw_angles,
                    text_pos=(50,-50)

                )
                p3 = list(shulder)
                if _3D:
                    p3[2]*= -1
                else:
                    pass
                    # p3[2]*= -1

                # arm_azimuth = angle_between_points()
                # if show_processing and draw_angles:
                #     pass
                # --------------------------------------------------
                # elovation

                arm_elovation = pose_detector.findAngle(
                    frame,
                    24,
                    12,
                    16,
                    angle3d=_3D,
                    draw=show_processing and draw_angles,
                )
        # --------------------------------------------------
        # draw glode limelines
        # --------------------------------------------------
        if not paused and process:
            if len(pose_landmarks) > 0:
                if show_globe:
                    r = 260
                    get_globe_timeline_curvs(r,
                                             *shulder,
                                             frame=frame,
                                             draw=show_globe
                                             )
        
        # --------------------------------------------------
        # chose ROI for hand detection
        # --------------------------------------------------
        if not paused and process:
            roi_hand = None
            
            if len(pose_landmarks) > 0:
                # --------------------------------------------------
                # just take inmutparameter ROI size 
                _roi_size = roi_size

                # --------------------------------------------------
                # hand ROI size from body length
                pixel = int(pose_detector.get_upper_body_length())
                upper_budy_pixel_len = upper_body_size.add_and_get_average(pixel)
                _roi_size = int(upper_budy_pixel_len * 1)
                size_sum += _roi_size
                
                # --------------------------------------------------
                # hand ROI size from frame size
                if roi_size:
                    _roi_size =  frame.shape[0] // roi_size

                # --------------------------------------------------
                # difine hand ROI area in frame
                if _roi_size:
                    roi_width = _roi_size
                    roi_height = _roi_size

                    # dont try if less then min window size
                    min_width = 50
                    min_height = 50

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
            # if no roi_hand is there, no hand schoult be in the frame
            if roi_hand or not _roi_size: 
                draw_landmarks = True
                draw_aperture = True
                draw_roi = True
                draw_max_distance = True
               



                frame = hand_detector.findHands(
                    frame=frame,
                    roi=roi_hand,
                    draw_landmarks=show_processing and draw_landmarks,
                    draw_roi=show_processing and draw_roi,
                )

                # _, index = hand_detector.choose_hand("top")
                hand_index = hand_detector.choose_hand("first")
                valide_hand =  hand_detector.hand_close_to(hand_center, 
                                                           max_distance=0.03,
                                                           frame=frame, draw=show_processing and draw_max_distance, hand_index=hand_index)
                # --------------------------------------------------
                # evaluate/change Hand status only if it is not moving
                if hand_stands_still or skip_hand_move_detection:
                    if valide_hand:
                        # hand detected in frame
                        frame_counter_hand += 1
                        
                        #
                        # aperture methode
                        #
                        hand_landmarks, frame = hand_detector.findHandPosition(
                        frame=frame, 
                        # hand_num=index, 
                        draw=False
                        )

                        width_factor = 0
                        frame, aperture = hand_detector.findHandAperture(
                                frame=frame, 
                                verbose=True, 
                                show_aperture=show_processing and draw_aperture,
                                use_len_if_larger_then_width = width_factor
                            )
                        hand_aperture_smoother.add(aperture)
                        aperture = hand_aperture_smoother.average
                        if aperture >= 70:
                            open_closed = 1 # open
                        elif aperture <= 60:
                            open_closed = 0 # closed
                        else:
                            open_closed = open_closed # stay like it is
                        hand_status_dict['aperture'] = open_closed
                        #
                        # aperture_width methode
                        #
                        width_factor = 1.2
                        frame, aperture = hand_detector.findHandAperture(
                                frame=frame, 
                                verbose=True, 
                                show_aperture=show_processing and draw_aperture,
                                use_len_if_larger_then_width = width_factor
                            )
                        hand_aperture_smoother.add(aperture)
                        aperture = hand_aperture_smoother.average
                        if aperture >= 70:
                            open_closed = 1 # open
                        elif aperture <= 60:
                            open_closed = 0 # closed
                        else:
                            open_closed = open_closed # stay like it is
                        hand_status_dict['aperture_width'] = open_closed
                        #
                        # len_width_thr_1.2 methode
                        #
                        opening_faktor = 1.2
                        open_closed = hand_detector.open_or_close_len_width_thr(frame, show_processing and draw_aperture, 
                                                                                    hand_opening_factor=opening_faktor)
                        hand_status_dict['len_width_thr_1.2'] = open_closed
                        #
                        # len_width_thr_1.4 methode
                        #
                        opening_faktor = 1.4
                        open_closed = hand_detector.open_or_close_len_width_thr(frame, show_processing and draw_aperture, 
                                                                                    hand_opening_factor=opening_faktor)
                        hand_status_dict['len_width_thr_1.4'] = open_closed
                        #
                        # distance_dif_0.3 methode
                        #
                        min_distance_difference = 0.3
                        open_closed = hand_detector.open_or_close_distance_dif(frame, show_processing and draw_aperture, 
                                                                                   min_distance_difference=min_distance_difference, frame_difference=S.hand_status_buffer_size)
                        hand_status_dict['distance_dif_0.3'] = open_closed
                        #
                        # distance_dif_0.4 methode
                        #
                        min_distance_difference = 0.4
                        open_closed = hand_detector.open_or_close_distance_dif(frame, show_processing and draw_aperture, 
                                                                                   min_distance_difference=min_distance_difference, frame_difference=S.hand_status_buffer_size)
                        hand_status_dict['distance_dif_0.4'] = open_closed

                    else:   
                        # if hand probably there but not found. closed hand are more likly to be not found
                        open_closed = hand_not_found_means
            
                    # --------------------------------------------------
                    # smoothing hand status
                    for methode in hand_status_dict.keys():
                        status = hand_status_dict[methode]
                        status = hand_status_buffer_dict[methode].add_and_get(status)
                        hand_status_detected[methode].append(status)
                    hand_status = status
                else:
                    # if hand is moving curently, do not change the hand status
                    hand_status = hand_status
                    hand_detector.buffer_clear()

                    for methode in hand_status_dict.keys():
                        status = hand_status_buffer_dict[methode].most_frequently
                        hand_status_detected[methode].append(status)

            else:
                hand_status = None # no hand in frame
                for methode in hand_status_dict.keys():
                        hand_status_detected[methode].append(None)
            
        # --------------------------------------------------
        # draw hand status
        # --------------------------------------------------
        if not paused and process:
                
            no_hand_status = {'text':"no hand", 'color':white}
            open_status = {'text':"open", 'color':blue}
            close_status = {'text':"closed", 'color':red}
            
            if hand_status == None: # no hand in screen
                text, color = no_hand_status['text'], no_hand_status['color']
            elif hand_status == 1: # open
                text, color = open_status['text'], open_status['color']
            elif hand_status == 0: # closed 
                text, color = close_status['text'], close_status['color']
            if not hand_stands_still: # hand is moving
                text += ' moving'

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
        # if not paused:
        #     if capture_status:
        #         hand_status_detected.append(open_closed)
                # open_close_status_capturer.add_comparison_status(open_closed)
        
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

                screenshot(frame=frame, name=source, ask_name=False,
                           info=[
                                    frame_x, frame_y,
                                    _roi_size, 
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


    
    hand_rate = round(frame_counter_hand / frame_counter_processed *100, 1)
    pose_rate = round(frame_counter_pose / frame_counter_processed *100, 1)
    fps_mean = round(fps_sum / frame_counter_processed, 1)

    if roi_size is None:
        _roi_size = size_sum//frame_counter_processed

    # --------------------------------------------------
    # print analyse stats
    print(f"pose detektet in {frame_counter_pose} of {frame_counter_processed} frames ({pose_rate} %)")
    print(f"hand detektet in {frame_counter_hand} of {frame_counter_processed} frames ({hand_rate} %)")
    print(f"used ROI size {_roi_size} in frame with {frame_x} x {frame_y} pixel")
    print(f'performance {fps_mean} fps mean')

    # --------------------------------------------------
    # save analyse stats

    # save_list_to_file(f'{source}_hand_pixel_moves.txt',hand_moves)

    if capture_status:
        for methode in hand_status_dict.keys():
            status = hand_status_buffer_dict[methode].most_frequently
            data = hand_status_detected[methode]
            save_list_to_file(source+f'-hand_detected_{methode}_no_hand_{hand_not_found_means}_no_movedetect_{skip_hand_move_detection}.txt',data)

    CSVWriter.write('HAND_detektionmethod_TEST.csv',
        name=source,
        frame_x=frame_x, frame_y=frame_y,
        roi_size=_roi_size, 
        frame_counter_processed=frame_counter_processed,
        frame_counter_pose=frame_counter_pose, pose_rate=pose_rate,
        frame_counter_hand=frame_counter_hand, hand_rate=hand_rate,
        hand_not_found_means=hand_not_found_means,
        skip_hand_move_detection=skip_hand_move_detection,
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
    videos = find_files(S.video_folder, ending=('.mp4', '.avi', '.mov'),names_only=True)
    
    # v1-11
    v1 = videos[0]
    v2 = videos[1]
    v3 = videos[2]
    v4 = videos[3]
    v5 = videos[4]
    v6 = videos[5]
    v7 = videos[6]
    v8 = videos[7]
    v9 = videos[8]
    v10 = videos[9]
    v11 = videos[10]
    
    rs = 'realsens'
    # Video file input
    for v in (v6,v6,v7,v8):
        for hand_not_found_means in [0,None,]:
            for skip_hand_move_detection in [False, True]:
                r = main(
                    fps_cap=30,
                    show_fps=True,
                    source=S.video_folder+v,
                    pause_frames=501,
                    show_processing=True,
                    capture_status_manually=False,
                    capture_status = False,
                    roi_size = None,
                    start_frame=100,
                    end_frame = None,
                    foto_name='arm winkel perspektieve',
                    foto_frames=None,
                    hand_not_found_means=hand_not_found_means,
                    skip_hand_move_detection=skip_hand_move_detection,
                    show_globe=False
                )
                if r == False:break
            if r == False:break
        if r == False:break
    
