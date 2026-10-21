"""
Central configuration for Stitchi 1.0.

Defines video/depth input, image/window dimensions, MediaPipe/hand detection
thresholds, gesture recognition modes, room geometry, angle smoothing, GUI
appearance, UDP endpoints, and diagnostic overlays. The processing modules
read these values at runtime through `import settings as S`. Change settings
here before starting main.py; some parameters require recalibration for a new
camera position, room, or input source.
"""

# window
name = "Gesture control"
version = "Stitchi 1.0"
window_size = (1920, 1080) # (1920, 1080)

# input source
video_source =  1#'depth'#'../test_videos (gitignore)/d01_0deg_1280x720p_15deg_steps_right.bag'# 1 # can be 0, 1, 2 ... or 'depth_cam' or 'filename.mp4_or_so' or 'filename.bag',  defould is 'depth' to use the real sense depthcam, 0 means une the forst found videostream
live_stream_resulutuin = (1280,720) # (1280,720) or (640,480)
fps = 30
cam_inclination_angle = 0 # Camera tilt angle, measured downwards (+90°) from the horizontal (0°)
start_frame = 1 # can be uset to start somewere in are video file not for realsens file.bag
end_frame = 0 # can be uset to end the programm at a specific frames: 0 mean it is inactive
align_depth = True # should be on True to aline GRB and depth frame

# pathes
icon_folder = '../Stitchi1.0/icons'
screenshots_folder = '../Stitchi1.0/screenshots'
gui_info_window_image_path = "../Stitchi1.0/info_window.png"
video_folder = r'..\Testmaterial/test_videos (gitignore)/' # for testing and analysis


# UDP communication
port = 5005
IPv4_audiosystem = "192.168.0.10"
IPv4_videosystem = "192.168.0.11" # this pc
bind_ip = "0.0.0.0"
printout_udp = True # print alls sended and received messages out im show pressessing mode 
add_inst_key = 'add_instruments'
start_instruments =  []#["trumpet", "trumpet", "Tröte", "piano", "violin","trommel","xylo","r2d2"]  # optional, later the audiosystem should give this infos per UDP




## hand detection
active_hand = 'both' # Available modules are: right, left, moving, top, both | 'moving' means take the fastest hand, 'top' means take the most top hand, 'right' means always right hand ...
no_hand_frame_count = 50 # by 30 FPS are 30 frames = one secund not hand, to get the no_hand status
moving_min_speed = 150 # in pixel per sec. min speed needed to be detected as moving 
moving_check_time = 0.3 # in secunds. the pixel moves are checked over x secunds
hand_change_min_speed = 200 # in pixel per sec. min speed needed to detected a hand in choose 'moving' hand mode 
use_roi = True # if true: use only a part around the hand of the cmera image to look for a hand skelett
roi_min_size = 50 # in pixel
hand_shoulder_intersect_dist = 0.10 # if using depth cam: in meters , if shoulder uand hand are very close in the image, it pionts to the cam and intersect
hand_shoulder_intersect_pixel = 20 # if using no depth cam: in meters , if shoulder uand hand are very close in the image, it pionts to the cam and intersect
hand_center_hands = (5, 17) # landmark numbers to calcumate the hand center in madiapipe hands
# hand from pose detection
left_hand_center_pose = (17,19) # landmark numbers to calcumate the hand center in madiapipe pose
right_hand_center_pose = (18,20) # landmark numbers to calcumate the hand center in madiapipe pose
# hand detection mode
grab_detection_methode = 'dynamic' # can be 'static' or 'dynamic'
# for dynamic grab mode
dynamic_grab_distance_difference = 1
dynamic_grab_time_difference = 1
# for static grab mode
hand_status_buffer_size = 3
hand_status_buffer_atleast = 3
hand_open_thrashold = 75
hand_close_thrashold = 65


# Roomdirektion / Pointingangle
real_depth_angle_resulutuin = 15
ray_tracing_step_size = 0.1 # ray_tracing_step_size_to_find_room_angle, in meters
room_size = (3.4, 2.7, 3.4)   # xyz <- width, hight, depth in meters (outer boarders 4m,3m,4m und 30 cm thick frame beams)
room_center = (1.7, 1.5, 1.7) # xyz <- width, hight, depth in meters, (0,0,0) is bottom, left, front corner
cam_pos_in_room = (1.7, 1.7, -0.1) # xyz <- width, hight, depth in meters, relative to the origin (0,0,0) is bottom, left, front corner
estimated_hip_hight = 0.95 # in meters only for compensating MediaPipe Wold lantmarks if used
angle_buffer_size = 5 # frames, pointing angle averaged over
volume_decimal_place = 2 # 2 means 0.12 ,1 means 0.1

# GUI
show_gui = True
gui_tile_max_size = 100
gui_hight = 1/4 # of the frame hight
controll_trigger_text_time = 1.0 # in secunds, how long the text feedbeck will be showen in the screen after triggering an controll grsture or key, 0.0 means no text feedback
instrument_start_volume = 0.5 # sound volume is between 0 and 1
no_mouse_control = False


# live infos 
# im show pressessing mode
mirrow_view = True # should be True, or things get confusing with your hand sides on the screen.
draw_aperture = True # if True, shows the hand opening as a blue conection line
draw_hand_skeleton = True
draw_body_skeleton = True
draw_roi = True
draw_hand_vlidation_dist = True
show_depth_frame = False # shows a extra window with the depth frame, if used
display_feedback_mode = ['show gui and processing','show gui']# 'show buttons','show buttons and processing' ] # you can ad modes hier

# other
visibility_threshold = 0.92  # shuolt be between 0.85 and 0.98 or so: mediapipe visibiliti throshold, below counts as covered landmark
default_buffer_mode = 'median' # bupper standart calculation methode, is not so importete
skip_frames = 100 # skip frames with 'a' and  'd' key in video mode, if a video is the source of the stream
type_instrument = 'instrument' # name key
rs_save_type = '.bag'   
save_stets_in_csv = False # saves some parameters in a line of a csv file after closing this programm

# colors
red = (0, 0, 255)
blue = (255, 0, 0)
green =(0, 255, 0)
white = (250,250,250)
black = (0,0,0)
yellow = (0, 255, 255)
