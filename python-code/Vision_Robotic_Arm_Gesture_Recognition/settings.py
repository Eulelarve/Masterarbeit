# colors
red = (0, 0, 255)
blue = (255, 0, 0)
green =(0, 255, 0)
white = (250,250,250)
black = (0,0,0)
yellow = (0, 255, 255)

# other
live_stream_resulutuin = (1280,720) # (1280,720) or (640,480)
hand_width_factor = 1.2
hand_opening_factor = 1.3
skip_frames = 100
hand_status_buffer_size = 10
no_hand_frame_count = 30 # by 30 FPS are 30 frames = one secund not hand, to get the no_hand status
video_folder = r'..\test_videos (gitignore)/'
moving_speed = 10 # pixel per frame, min needed to be detected as moving hand, choose between 2-20
max_speed_change = 300 # if the hand speed change quicker if is asoomt as a jumping between the hands. enter a big number (>100) to tirn this function off
moving_buffer_size = 5 # frames the pixel moves are buffert over
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