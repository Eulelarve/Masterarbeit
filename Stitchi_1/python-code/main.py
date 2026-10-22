""" Stitchi 1.0

Stitchi 1 — Main application entry point.

Coordinates the complete gesture-control pipeline: initializes the video/depth
source, MediaPipe pose and hand detectors, gesture detector, room-angle
calculation, GUI overlay, and UDP communication. Each frame is acquired by
FrameSource, processed for body/hand landmarks, converted into pointing angles,
and passed to GuiOverlay. GUI state changes are sent as JSON/UDP messages to
the configured audio-system endpoint. Also handles keyboard controls, display
modes, screenshots, test statistics, and orderly source shutdown.

Run this file to start the application. Most runtime configuration is in
settings.py.
"""


import cv2
import time

import numpy as np
from datetime import datetime
from collections import defaultdict

from communication import SendOnChange, SaveUdpToDict
from GUI import GuiOverlay
from own_functions import ValueBuffer, CSVWriter, tolist, screenshot, MoveDetector, get_globe_timeline_curvs , MOUSE, cv2_center_text, cv2_putText_outlined
from angle_handler import RoomAngleDetector

from MediaPipe_handler import PoseDetector, HandDetector 
from analyse import SaveFrameStatus, save_list_to_file, find_files
from gesture_handler import GestureDetector
from frame_handler import FrameSource

import settings as S

def main(fps_cap=S.fps, show_fps=True,source=0, 
         pause_frames:list=None, 
         capture_status_manually:bool=False, 
         capture_status:bool=False,
         start_frame:int = None,
         end_frame:int=None,
         foto_frames:list=None,
         show_globe = False,
         grab_detection_methode = S.grab_detection_methode,
         show_depth_frame = False,
         udp_reception_dict={}
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
    red = S.red
    blue = S.blue
    green = S.green
    white = S.white
    should_run = True

    cv2.setUseOptimized(True)
    gui = GuiOverlay()
    frame_source = FrameSource()


    frame_counter_processed = 0
    frame_counter_pose = 0
    frame_counter_hand = 0
    frame_now = start_frame - 1
    hand_status:list[int|None,int|None] = [None, None]
    video_name = ''
    visibilety_mode_loop_list = S.display_feedback_mode.copy()
    show_processing = 'process' in visibilety_mode_loop_list[0]
    trigger_text = {'text':'', 'color':green, 'time':0.0}


    hand_status_list_dict = {'static_7050':[], 'static_7065':[],  'static_7060':[], 'dynamic_0.6':[], 'dynamic_1.0':[],'dynamic_1.4':[]}
    hand_status_dict = {'static_7050':None, 'static_7065':None,  'static_7060':None, 'dynamic_0.6':None, 'dynamic_1.0':None,'dynamic_1.4':None}
 
    moves_dict = defaultdict(list)

    paused = False
    process = True
    frame = None
    process_ones = False
    upper_body_len_buffer = ValueBuffer(40)
    hand_moves = (MoveDetector(),MoveDetector())
    open_close_status_capturer = SaveFrameStatus(keys=(ord('1'), ord('2'), ord('3')), status=('hand open', 'hand closed', None))

    last_frame_time = time.perf_counter()

    fps_limit = fps_cap
    frame_interval = 1.0 / fps_limit
    fps_sum = 0
    cam_intrinsics = None

    hand_detectors = (HandDetector(), HandDetector())
    pose_detector = PoseDetector()
    angle_detector = RoomAngleDetector()
    gesture_detector = GestureDetector()
    communicator = SendOnChange((S.IPv4_audiosystem,S.port))
    info_receiver = SaveUdpToDict()
    info_receiver.start_receiving()

    time.sleep(0.5)



    frame_x=frame_source.w 
    frame_y=frame_source.h

    # -------------------------------------------------------
    # Main processing loop
    # -------------------------------------------------------
    while should_run:
        # --------------------------------------------------
        # set and reset 
        # --------------------------------------------------
        pose_found = False
        hand_found = [False, False]
        hand_stands_still = [None, None]
        change_display_mode = False
        clear_gui = False
        trigger_info_menu = False
        display_flash = None
        room_azimuth = [None,None]
        room_elevation = [None,None]
        hand_centers:list[list|None] = [None, None]
        pose_hands = []
        # object reset
        gesture_detector.clear_lm()
        
        # released_angle = None
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

        if key == 27: # esc
            should_run = False

        if key == ord('q'):
            print('terminate application with Q-key, it will may start again')
            break            

        elif key == ord(' '): # space -> Pause
            paused = not paused

        elif key == 13: # enter -> processing on/off
            process = not process

        elif key == ord('p'): # p -> screen shot
                display_flash = white

        elif key == ord('v'): # v -> change displayed informationes
            change_display_mode = True

        elif key == ord('r'): # r -> reset all instruments and trhe gui 
            clear_gui = True

        elif key == ord('i'): # i -> show info window with gesture controles
            trigger_info_menu = True

        # --------------------------------------------------
        # Video frame navigation
        # --------------------------------------------------

        if frame_source.playback and not frame_source.use_rs:
            if chr(key) in 'wasd':
                if paused:
                    process_ones = True
                
                # A = step back x frame
                if key == ord('a'):
                    frame_now = max(0, frame_now- S.skip_frames)

                # D = step forward x frame
                elif key == ord('d'):
                    frame_now += S.skip_frames

                # S = step back 1 frames
                elif key == ord('s'):
                    frame_now = max(0, frame_now - 1) 

                # W = step forward 1 frames
                elif key == ord('w'):
                    frame_now += 1 
                
                frame_now -= 1 # -1 because each loop adds one frame, by it self
                # set frame in video
                frame_source.set_video_frame(frame_now)
                
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
            frame_now = frame_source.get_next_frame()            
            if frame_source.finish:
                should_run = False
                continue
            RGB_frame = frame_source.RGB_frame
            frame_overlay = frame_source.BRG_frame

        # --------------------------------------------------
        # Pose detection
        # --------------------------------------------------
        if not paused and process:


            pose_detector.findPose(RGB_frame)
   
            pose_landmarks = pose_detector.create_pixel_landmark_list()
            gesture_detector.pose_lm = pose_landmarks
            
            pose_found = True if len(pose_landmarks) > 0 else False
            
            if pose_found:
                pose_detector.create_moving_list()
                pose_detector.create_visibility_list()
                frame_counter_pose += 1

                pose_world_landmarks = pose_detector.estimate_room_coordinates()
                
                if show_processing and S.draw_body_skeleton:
                    pose_detector.draw_skeleton(frame_overlay)

        # --------------------------------------------------
        # get hand center and coresponding shoulder and max arm length, relative arm length
        # --------------------------------------------------
        if not paused and process and pose_found:
            # hand and shoulder
            hand_bussy_in_gui = gui.grabbing[0] or gui.grabbing[1]
            pose_detector.find_specific_points(S.active_hand, hand_bussy_in_gui, True)
            pose_hands = pose_detector.hand_center.copy()
            shoulders = pose_detector.shoulder.copy()
            length = pose_detector.get_upper_body_length()
            upper_body_pixel_len = int(upper_body_len_buffer.add_and_get_average(length))
       
       # ==================================================
       # start of for-handside loop
        for _i in range(len(pose_hands)):
            # for if hand not found or not in screen. if a hand is found this will be owerriwen later
            gesture_detector.no_hand_count(_i, S.no_hand_frame_count)

            if pose_hands[_i] is None:
                continue

            i_hand , *hand_center = pose_hands[_i]
            i_shoulder, *shoulder = shoulders[_i]
            hand_side = pose_detector.hand_side[_i]
            hand_detector = hand_detectors[_i]
            hand_centers[_i] = hand_center




            # --------------------------------------------------
            # Hand detection
            # --------------------------------------------------
            if not paused and process and pose_found:

                hand_landmarks = hand_detector.find_valide_hand(
                    RGB_frame, hand_center, upper_body_pixel_len,
                    frame_overlay, show_processing
                )
                hand_found[_i] = hand_landmarks is not None

                # --------------------------------------------------
                # overwrite the Hand center of pose by hand detection and set lansmarks fpr gesture detection
                # --------------------------------------------------
                if hand_found[_i]:
                    hand_center = hand_detector.hand_center
                    hand_centers[_i] = hand_center 
                    gesture_detector.hands_lm[_i] = hand_landmarks
                else:
                    gesture_detector.hands_lm[_i] = None

            # --------------------------------------------------
            # hand is moving
            # --------------------------------------------------
            if not paused and process and pose_found:
                    hand_stands_still[_i] = hand_moves[_i].stands_still(hand_centers[_i])
            
            # --------------------------------------------------
            # Analyze arm angle / pointing direction
            # --------------------------------------------------
            if not paused and process and pose_found:
                draw_angles = True

                draw = draw_angles and show_processing
                if frame_source.use_depth_cam:
                    angle_detector.find_room_angle_with_depth_frame(frame_source.depth_frame, hand_center, shoulder, frame_overlay, draw)
                else:
                    hand_3d = pose_world_landmarks[i_hand][1:4]
                    shoulder_3d = pose_world_landmarks[i_shoulder][1:4]
                    if cam_intrinsics:
                        hand_world_depth = hand_3d[2] 
                        shoulder_world_depth = shoulder_3d[2]
                        angle_detector.find_room_angle_with_intrinsics(cam_intrinsics, hand_center , shoulder, hand_world_depth, shoulder_world_depth, frame_overlay, draw)
                    else:
                        angle_detector.find_room_angles_45_deg_aprox(hand_side, hand_3d, shoulder_3d, hand_center, shoulder, frame_overlay,draw)

                room_azimuth[_i] = angle_detector.azimuth
                room_elevation[_i] = angle_detector.elevation


            # --------------------------------------------------
            # evaluate/change Hand status only if it is not moving
            # --------------------------------------------------
            if not paused and process and pose_found:
                if hand_stands_still[_i]:
                    if hand_found[_i]:
                        # hand detected in frame

                        # ---------------------------------------
                        # choose a hand opening detection methode
                        if capture_status:
                            hand_status[_i] = gesture_detector.hand_open_close_static(_i, thr_open=70, thr_closed = 50, frame=frame_overlay, draw=show_processing, buffer_size=S.hand_status_buffer_size)
                            hand_status_dict['static_7050'] = hand_status[_i]
                            hand_status[_i] = gesture_detector.hand_open_close_static(_i, thr_open=70, thr_closed = 65, frame=frame_overlay, draw=show_processing, buffer_size=S.hand_status_buffer_size)
                            hand_status_dict['static_7065'] = hand_status[_i]
                            hand_status[_i] = gesture_detector.hand_open_close_static(_i, thr_open=70, thr_closed = 60, frame=frame_overlay, draw=show_processing, buffer_size=S.hand_status_buffer_size)
                            hand_status_dict['static_7060'] = hand_status[_i]
                            hand_status[_i] = gesture_detector.hand_open_close_dynamic(_i, frame_overlay, show_processing, min_distance_difference=0.8)
                            hand_status_dict['dynamic_0.6'] = hand_status[_i]
                            hand_status[_i] = gesture_detector.hand_open_close_dynamic(_i, frame_overlay, show_processing, min_distance_difference=1)
                            hand_status_dict['dynamic_1.0'] = hand_status[_i]
                            hand_status[_i] = gesture_detector.hand_open_close_dynamic(_i, frame_overlay, show_processing, min_distance_difference=1.2)
                            hand_status_dict['dynamic_1.4'] = hand_status[_i]

                        else:
                            try:
                                factor = float(grab_detection_methode[grab_detection_methode.find('__')+2:])
                            except:
                                factor = None
                                
                            if 'static' in grab_detection_methode:
                                hand_status[_i] = gesture_detector.hand_open_close_static(_i, frame=frame_overlay, draw=show_processing)
                            elif 'dynamic' in grab_detection_methode:
                                if not factor: factor = 1
                                hand_status[_i] = gesture_detector.hand_open_close_dynamic(_i, frame_overlay, show_processing)

                    else:   
                        pass
                else:
                    # if hand is moving curently, do not change the hand status
                    hand_status[_i] = hand_status[_i]


        # end of for-handside loop
        # ==================================================
        
        # --------------------------------------------------
        # count frames with detected hand skelet
        if not paused and process and pose_found:
            if True in hand_found:
                frame_counter_hand += 1

        # --------------------------------------------------
        # gesture detection
        if not paused and process and pose_found:   
            gesture_detector.find_grab()

        # --------------------------------------------------
        # control gestures - Info, terminate app, clear gui, change display mode
        # -------------------------------------------------- 
        if not paused and process and pose_found:
            gesture_detector.pose_visibilety = list(pose_detector.lm_visibility)
            gesture_detector.pose_movement = list(pose_detector.lm_movment_list)
            gesture_detector.upper_body_len = upper_body_len_buffer.get()
        
            if gesture_detector.find_termination_gesture():
                should_run = False
            if gesture_detector.find_info_trigger():
                trigger_info_menu = True
            if gesture_detector.find_clear_trigger():
                clear_gui = True
            if gesture_detector.find_visibilety_mode_trigger():
                change_display_mode = True

        # --------------------------------------------------
        # capture status manually
        # --------------------------------------------------
        if capture_status_manually:
            wrong_frame = open_close_status_capturer.add(frame_now, key)
            if type(wrong_frame) == int:
                if frame_source.video:
                    if paused:
                        process_ones = True
                    # set frame in video
                    frame_source.set_video_frame(wrong_frame-1)

        # --------------------------------------------------
        # frame is fully processed 
        # --------------------------------------------------
        if not paused and process:
            frame_counter_processed += 1

        # --------------------------------------------------
        # alppy controlles  
        # --------------------------------------------------
        if change_display_mode:
            first_mode = visibilety_mode_loop_list.pop(0)
            visibilety_mode_loop_list.append(first_mode) 
            gui.set_gui_visibility(visibilety_mode_loop_list[0])
            show_processing = 'process' in visibilety_mode_loop_list[0]
            trigger_text['text'] = 'change display mode'
            trigger_text['time'] = time.time()

        if trigger_info_menu:
            gui.show_info_menu = not gui.show_info_menu
            trigger_text['text'] = 'info on/off'
            trigger_text['time'] = time.time()

        if clear_gui:
            gui.reset_gui()
            while visibilety_mode_loop_list[0] != S.display_feedback_mode[0]:
                first_mode = visibilety_mode_loop_list.pop(0)
                visibilety_mode_loop_list.append(first_mode) 
            gui.set_gui_visibility(visibilety_mode_loop_list[0])
            show_processing = 'process' in visibilety_mode_loop_list[0]
            trigger_text['text'] = 'reset gui'
            trigger_text['time'] = time.time()



        # ##################################################
        # Status overlay - end of video processing
        # ##################################################

        # --------------------------------------------------
        # controll commant triggered - text  fedbeck
        # --------------------------------------------------

        if trigger_text['text']:
            if time.time() - trigger_text['time'] > S.controll_trigger_text_time:
                trigger_text = {'text':'', 'color':green, 'time':0.0}
            else:
                text = trigger_text['text']
                color = trigger_text['color']
                cv2_center_text(frame_overlay,text,color)

        # --------------------------------------------------
        # live info text, on the left screen side
        # --------------------------------------------------
        font_scale = 1
        color = white
        line_size = 1
        # --------------------------------------------------
        # FPS overlay
        x = 10
        y = 30
        margin = 40
        if not paused and show_processing:
            if show_fps:
                text = f"FPS: {round(fps, 1)}"
                cv2_putText_outlined(
                    frame_overlay,
                    f"FPS: {round(fps, 1)}",
                    (x, y),
                    font_scale,
                    color,
                    line_size,
                )
        # --------------------------------------------------
        #  video / Live status overlay
        y += margin
        if show_processing:
            status = "VIDEO" if frame_source.playback else "LIVE"

            cv2_putText_outlined(
                frame_overlay,
                status,
                (x, y),
                font_scale,
                color,
                line_size,
            )
        # --------------------------------------------------
        # pause status
        if paused:
            x = 120
            cv2_putText_outlined(
                frame_overlay,
                "PAUSED",
                (x, y),
                font_scale,
                color,
                line_size,
            )
        # --------------------------------------------------
        # frame counter overlay
        x = 10
        y += margin
        if show_processing:
            text = f"Frame: {frame_now}"
            if frame_source.playback:
                text += '/'
                text += str(frame_source.end_frame)

            cv2_putText_outlined(
                frame_overlay,
                text,
                (x, y),
                font_scale,
                color,
                line_size,
            )
        # --------------------------------------------------
        # draw hand status
        x = 10
        if not paused and process and show_processing:
                
            no_hand_status = {'text':"no hand ", 'color':white}
            open_status = {'text':"open ", 'color':blue}
            close_status = {'text':"closed ", 'color':red}
            i_hs = list(enumerate(hand_status))
            for i, hs in i_hs[::-1]:
                y +=  margin
                text, _color ,outline= '', white , S.black # default
                if hs == None: # no hand in screen
                    text, _color = no_hand_status['text'], no_hand_status['color']
                elif hs == 1: # open
                    text, _color ,outline = open_status['text'], open_status['color'], white
                elif hs == 0: # closed 
                    text, _color = close_status['text'], close_status['color']
                if hand_stands_still[i] == False: # hand is moving
                    text += 'moving '
                # show hand status
                cv2_putText_outlined(
                    frame_overlay,
                    text,
                    (x,y),
                    font_scale,
                    _color,
                    line_size,
                    2,
                    outline
                )

        # --------------------------------------------------
        # draw arm angle
        x = 10
        if not paused and process and show_processing:
            side_and_angle = list(zip(pose_detector.hand_side,room_azimuth, room_elevation))
            for hs,a,e in side_and_angle[::-1]:
                if hs == 'right':
                    text = 'L'
                elif hs == 'left':
                    text ='R'
                else:
                    continue
                text += f'[a/e]: {a}/{e}'
                y += margin
                cv2_putText_outlined(
                    frame_overlay,
                    text,
                    (x,y),
                    font_scale,
                    color,
                    line_size,
                )

        # --------------------------------------------------
        # controls overlay
        x = 10
        y =  frame_overlay.shape[0] - 10
        font_scale = 0.5
        if show_processing:
            text = "SPACE: Pause | ENTER: processing on/off | P: screenshot | ESC: exit"
            cv2_putText_outlined(
                frame_overlay,
                text,
                (x, y),
                font_scale,
                color,
                line_size,
                1,
            )

        # video file controls
        x = 10
        y = frame_overlay.shape[0] - 25
        if frame_source.video:
            text = "W/S=+/-1 frame | A/D=+/-200 frames"
            cv2_putText_outlined(
                frame_overlay,
                text,
                (x, y),
                font_scale,
                color,
                line_size,
                1,
            )
          
        # --------------------------------------------------
        # draw glode limelines
        # --------------------------------------------------
        if not paused and process and pose_found:
            if show_globe:
                r = 260
                get_globe_timeline_curvs(r,
                                        *shoulder,
                                        frame=frame_overlay,
                                        draw=show_globe
                                        )
        # --------------------------------------------------
        # draw GUI overlas
        # --------------------------------------------------
        # add instruments received from udp communication or start input
        # --------------------------------------------------
        if S.show_gui:
            if S.add_inst_key in udp_reception_dict:
                insts = tolist(udp_reception_dict[S.add_inst_key])
                for inst in insts:
                    gui.add_instrument(inst)
            udp_reception_dict = info_receiver.get_msg()
            # --------------------------------------------------

            # show and evaluate hands and Mauseposition 
            if not paused and process and pose_found:
                mouse_pos = np.int16(np.array(MOUSE.pos) * [frame_x, frame_y] / S.window_size)
                selector1 = {'pos':hand_centers[0], 'grab':gesture_detector.grab[0], 'release':gesture_detector.releas[0]}
                selector2 = {'pos':hand_centers[1], 'grab':gesture_detector.grab[1], 'release':gesture_detector.releas[1]}
                selector3 = {'pos':mouse_pos,       'grab':MOUSE.is_pressed(),       'release':MOUSE.is_release()}
                if S.no_mouse_control:
                    selector3 = {'pos':None, 'grab':None, 'release':None}

                gui.select(selector1['pos'], selector2['pos'], selector3['pos'])
                gui.grab(selector1['grab'], selector2['grab'], selector3['grab'])
                gui.move(azimuth=room_azimuth,elevation=room_elevation)
                gui.release(selector1['release'], selector2['release'], selector3['release'])
            gui.draw(frame_overlay, show_processing)
            gui_info = gui.get_info()
            # --------------------------------------------------
            # comunikation Audiosystem
            # --------------------------------------------------
            if gui_info:
                if gui_info['type'] == S.type_instrument:
                    communicator.send(show_processing, **gui_info) # some error after add elevation

        # --------------------------------------------------
        # foto at frame or bei pressing P
        # --------------------------------------------------
        foto_info = None
        foto_name ='shreenshot'
        if foto_frames:
            foto_frame = min(foto_frames)
            if frame_now == foto_frame:
                print(f"reached foto frame {foto_frame}")
                foto_frames.remove(foto_frame)

                hand_rate = round(frame_counter_hand / frame_counter_processed *100, 1)
                pose_rate = round(frame_counter_pose / frame_counter_processed *100, 1)
                fps_mean = round(fps_sum / frame_counter_processed, 1)
                foto_info=[
                        frame_x, frame_y,
                        frame_counter_processed,
                        frame_counter_pose, pose_rate,
                        frame_counter_hand, hand_rate,
                        fps_mean,
                    ]
                foto_name=source
                display_flash = white

        if display_flash:
            if not screenshot(frame=frame_overlay, name=foto_name, ask_name=False, info=foto_info):
                display_flash = None
            frame_source.show_flash = display_flash
            
        # --------------------------------------------------
        # pause at frame or later if skiped
        # --------------------------------------------------
        if pause_frames:
            pause_frame = min(pause_frames)
            if frame_now >= pause_frame:
                if not paused:
                    print(f"currend frame {frame_now} reached pause frame {pause_frame}")
                    paused = True
                    pause_frames.remove(pause_frame)

        # --------------------------------------------------
        # Display the processed frame - opens a window 
        # --------------------------------------------------
        frame_source.show_frame()
        
    # ==================================================
    # finaly and closing - loop ended
    # ==================================================
    info_receiver.stop_receiving()
    frame_source.end()

    # --------------------------------------------------
    # post-processing

    name = str(source)+f"_frame_and_open_close_manual_status"
    end = '.txt'
    if capture_status_manually:
        open_close_status_capturer.save_to_file(name+end)

    hand_rate = round(frame_counter_hand / frame_counter_processed *100, 1)
    pose_rate = round(frame_counter_pose / frame_counter_processed *100, 1)
    fps_mean = round(fps_sum / frame_counter_processed, 1)

    # --------------------------------------------------
    # print analyse stats
    print(f"pose detektet in {frame_counter_pose} of {frame_counter_processed} frames ({pose_rate} %)")
    print(f"hand detektet in {frame_counter_hand} of {frame_counter_processed} frames ({hand_rate} %)")
    print(f'performance {fps_mean} fps mean')

    # --------------------------------------------------
    # save analyse stats

    if capture_status:
        for key in hand_status_list_dict.keys():
            data = hand_status_list_dict[key]
            folder = r"C:\Users\Ampelman\Desktop\Masterarbeit\open close status data for videos\median3_pos_buffer_test/"
            save_list_to_file(folder+video_name+f'-hand_detected_{key}_len_{len(data)}.txt',data)
    
    if S.save_stets_in_csv:
        CSVWriter.write('HAND_detektionmethod_TEST.csv',
            name=source,
            frame_x=frame_x, frame_y=frame_y,
            frame_counter_processed=frame_counter_processed,
            frame_counter_pose=frame_counter_pose, pose_rate=pose_rate,
            frame_counter_hand=frame_counter_hand, hand_rate=hand_rate,
            fps_mean=fps_mean,
            time = time_stemp
        )

        frames_and_moves = moves_dict[grab_detection_methode]
        CSVWriter.write('Move_grab_detection_methode_test.csv',
            frames_and_moves= frames_and_moves,
            buffer_size=S.hand_status_buffer_size,
            methode= grab_detection_methode,
            video=video_name,
            time = time_stemp,
        )
    # --------------------------------------------------
    # end mesage
    print(f"Video Detection with source: {source}")
    print(f"Video Detection End")
    return should_run


if __name__ == "__main__":

    # videos = find_files(S.video_folder, ending=('.mp4', '.avi', '.mov'),names_only=True)
    # bags = find_files(S.video_folder, ending=S.rs_save_type ,names_only=True)

    r = True
    while r: 
        r = main(
            fps_cap=S.fps,
            show_fps=True,
            source=S.video_source, # kan be 0, 1, 2 ... or 'depth' or 'filename.mp4'
            pause_frames=None, #(300,500,700),
            capture_status_manually=False,
            capture_status = False,
            start_frame=1,
            end_frame = None,
            foto_frames=None,
            show_globe=False,
            # grab_detection_methode=grab_detection_methode,
            show_depth_frame = False,
            udp_reception_dict={S.add_inst_key:S.start_instruments},
        )
        if r == False:break
    
