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
window_size = (1280,720)#(1920, 1080)#
hand_width_factor = 1.2
hand_opening_factor = 1.3
skip_frames = 100
hand_status_buffer_size = 10
default_buffer_mode = 'median'
no_hand_frame_count = 30 # by 30 FPS are 30 frames = one secund not hand, to get the no_hand status
video_folder = r'..\test_videos (gitignore)/'
moving_speed = 10 # pixel per frame, min needed to be detected as moving hand, choose between 2-20
moving_buffer_size = 5 # frames, the pixel moves are averaged over
position_buffer_size = 5 # frames, all positions are averaged over
angle_buffer_size = 5 # frames, pointing angle averaged over
gui_hight = 1/5 # of the frame hight
arm_decection_border_top = 1/4 # of the frame hight
arm_decection_border_bot = 3/4 # of the frame hight
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
gui_info_image_path = r"..\icons\into_imate.png"
overlay_visibilety_modes = {0:'show buttons',1:'show gui', 2:'show gui and processing', 3:'show buttons and processing'}

# d455 intrinsiks color frame:              [ 1280x720  p[638.568 367.388]  f[640.329 638.932]  Inverse Brown Conrady [-0.055931 0.0683116 -0.000836038 0.000658576 -0.0223113] ]
# d455 intrinsiks depth frame (unaligned):  [ 1280x720  p[643.714 366.77]  f[653.798 653.798]  Brown Conrady [0 0 0 0 0] ]
