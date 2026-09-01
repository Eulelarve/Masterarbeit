# colors
red = (0, 0, 255)
blue = (255, 0, 0)
green =(0, 255, 0)
white = (250,250,250)
black = (0,0,0)
yellow = (0, 255, 255)

# other
fps = 30
live_stream_resulutuin = (1280,720) # (1280,720) or (640,480)
window_size = (1920, 1080)#
hand_width_factor = 1.2
hand_opening_factor = 1.3
skip_frames = 100
hand_status_buffer_size = 6
hand_status_buffer_atleast = 5
default_buffer_mode = 'median'
no_hand_frame_count = 30 # by 30 FPS are 30 frames = one secund not hand, to get the no_hand status
video_folder = r'..\test_videos (gitignore)/'
moving_speed = 150 # pixel per sec, min needed to be detected as moving hand, choose between 2-20
moving_buffer_time = 0.3 # secunds, the pixel moves are checked
position_average_buffer_size = 0 # min 2 frames to be used, all positions are averaged over
position_median_buffer_size = 0 # min 3 frames to be used, all positions are averaged over
angle_buffer_size = 5 # frames, pointing angle averaged over
gui_hight = 1/4 # of the frame hight
arm_decection_border_top = 0/4 # x of the frame hight, boarder were the instruments cant be plased (no arm angle calcumation zone)
arm_decection_border_bot = 3/4 # x of the frame hight, boarder were the instruments cant be plased (no arm angle calcumation zone)
cam_angle_hight = {0:1.70, 32.5:2.60} # if the cam has the angle x° it is mounted in the hight y m
cam_angle = 0
volume_decimal_place = 2 # 2 means 0.12 ,1 means 0.1
port = 5005
IPv4_audiosystem = "127.0.0.1"
type_instrument = 'instrument'
instrument_start_volume = 0.5 # sound volume is between 0 and 1
rs_save_type = '.bag'
zero_degree_distance = 0.10 # in meters
real_depth_angle_resulutuin = 15
room_size = (3.4, 2.7, 3.4)   # xyz <- width, hight, depth in meters (outer boarders 4m,3m,4m und 30 cm thick frame beams)
room_center = (1.7, 1.5, 1.7) # xyz <- width, hight, depth in meters, (0,0,0) is bottom, left, front corner
ray_tracing_step_size = 0.1 # ray_tracing_step_size_to_find_room_angle, in meters
align_depth = True
dist_cam_to_room_center = 1.8 # in meter
visibility_threshold = 0.92
cam_intrinsics = 'xxx'
left_hand_landmark_ids = [ 15,17,19, 21 ] # left hand landmarks from mediapipe pose
right_hand_landmark_ids = [ 16,18,20, 22 ] # right hand landmarks from mediapipe pose
gui_info_image_path = r"..\icons\into_image.png"
overlay_visibilety_modes = {0:'show gui and processing', 1:'show gui', 2:'show buttons',3:'show buttons and processing' }

# d455 intrinsiks color frame:              [ 1280x720  p[638.568 367.388]  f[640.329 638.932]  Inverse Brown Conrady [-0.055931 0.0683116 -0.000836038 0.000658576 -0.0223113] ]
# d455 intrinsiks depth frame (unaligned):  [ 1280x720  p[643.714 366.77]  f[653.798 653.798]  Brown Conrady [0 0 0 0 0] ]

r""" 

Traceback (most recent call last):
  File "c:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code\Vision_Robotic_Arm_Gesture_Recognition\main_changed.py", line 1163, in <module>
    r = main(
        ^^^^^
  File "c:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code\Vision_Robotic_Arm_Gesture_Recognition\main_changed.py", line 615, in main
    angle_detector.find_room_angle_with_depth_frame(depth_frame,hand_center, shulder, frame_overlay, draw)
  File "c:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code\Vision_Robotic_Arm_Gesture_Recognition\angle_handler.py", line 243, in find_room_angle_with_depth_frame
    self.find_3d_hand_shoulder_with_depth_frame(depth_frame)
  File "c:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code\Vision_Robotic_Arm_Gesture_Recognition\angle_handler.py", line 279, in find_3d_hand_shoulder_with_depth_frame
    self.shoulder_3d =  rs_pixel_to_3d(self.shoulder_pixel_xy, *args)
                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code\Vision_Robotic_Arm_Gesture_Recognition\coordinates_handler.py", line 127, in rs_pixel_to_3d
    x,y,z = rs_pixel_to_meter(cam_intrinsics, pixel_xy, depth)
            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "c:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code\Vision_Robotic_Arm_Gesture_Recognition\coordinates_handler.py", line 112, in rs_pixel_to_meter
    return rs.rs2_deproject_pixel_to_point(intrinsics, pixel_xy, depth)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: rs2_deproject_pixel_to_point(): incompatible function arguments. The following argument types are supported:
    1. (intrin: pyrealsense2.pyrealsense2.intrinsics, pixel: List[float[2]], depth: float) -> List[float[3]]

Invoked with: [ 1280x720  p[638.568 367.388]  f[640.156 638.759]  Inverse Brown Conrady [-0.055931 0.0683116 -0.000836038 0.000658576 -0.0223113] ], [1426, 444], None
(venv) PS C:\Users\Videosystem\Desktop\Videosystem_Masterarbeit_Wegener\Masterarbeit\python-code> 
"""