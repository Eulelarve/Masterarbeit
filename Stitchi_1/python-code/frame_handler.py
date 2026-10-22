""" Stitchi 1.0

Video and depth-frame source management.

FrameSoarce selects and initializes the configured source: a standard webcam,
a video file, an Intel RealSense live camera, or a RealSense .bag recording.
It reads frames, optionally aligns depth to the colour image, manages playback
and frame navigation, displays the processed image, and shuts down the source.
The class is instantiated by main.py.
"""

import cv2
import pyrealsense2 as rs
import settings as S
from own_functions import cv2_mouse_callback
import numpy as np

class FrameSource:
  def __init__(self) -> None:
    self.name = S.name+' - '+S.version
    self.source = S.video_source
    self.w, self.h = S.live_stream_resulutuin
    self.align_depth = S.align_depth
    self.show_depth_frame = S.show_depth_frame
    self.mirrow = S.mirrow_view
    self.show_size = S.window_size
    self.end_frame = S.end_frame
    self.show_flash = None

    self.check_sourse()
    self.init_source()
    self.init_show_window()

  def init_show_window(self):
    cv2.namedWindow(self.name)
    cv2.setMouseCallback(self.name, cv2_mouse_callback)
     
  def check_sourse(self):
    self.playback = False
    self.video = False
    self.use_rs = False
    self.use_depth_cam = False
    if type(self.source) is int:
        print('use livestream cam nr.:', self.source)
    elif 'depth' in self.source.lower():
        self.use_rs = True
        self.use_depth_cam = True
        print(self.source,': means using realsens depth cam', )
    else:
        self.playback = True
        if self.source[-4:] == S.rs_save_type:
            self.use_rs = True
            self.use_depth_cam = True
            print('playback realsens file:', self.source)
        else:
            self.video = True
            print('playback video:', self.source)
          
  def init_realsense(self):
    self.pipeline = rs.pipeline()
    self.config = rs.config()
    if self.playback:
        self.config.enable_device_from_file(self.source, repeat_playback=False)
    else:
        self.config.enable_stream(rs.stream.color, 
                                  *S.live_stream_resulutuin, 
                                  rs.format.bgr8, 
                                  S.fps)
        if self.use_rs:
            self.config.enable_stream(rs.stream.depth,                   
                                      *S.live_stream_resulutuin,
                                      rs.format.z16,
                                      S.fps)
    self.profile = self.pipeline.start(self.config)
    if self.use_rs and self.align_depth:
        self.aligner = rs.align(rs.stream.color)
    if self.playback:
        device = self.profile.get_device()
        self.rs_playback = device.as_playback()
        self.rs_playback.set_real_time(False)
    
    # try:
    #     self.pipeline.stop()
    #     print('pyrealsense2 was not firmly clossed')
    # except:
    #     pass

  def init_cv_source(self):
    self.video_capture = cv2.VideoCapture(self.source)
    if not self.video:
        self.video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, S.live_stream_resulutuin[0])
        self.video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, S.live_stream_resulutuin[1])
    if not self.video_capture.isOpened():
        print(f"cv2: Error: Cannot open source: {self.source}")
        self.finish = True

  def set_start_and_end_video_frame(self):
    # set to start frame / reset to frame 0
    if self.playback:
      if self.use_rs:
          # aprox last frame number of the bag file
          play_time = self.rs_playback.get_duration().total_seconds()
          fps_db3 = self.profile.get_stream(rs.stream.color).as_video_stream_profile().fps()
          last_frame = int(fps_db3*play_time)
      else:
          last_frame = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
          if S.start_frame > 1:
              self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, S.start_frame -1)
      if last_frame < self.end_frame or not self.end_frame:
          self.end_frame = last_frame

  def init_source(self):
    self.finish = False
    self.counter = 0
    if self.use_rs:
       self.init_realsense()
    else: # other webcams or video input
       self.init_cv_source()
    self.set_start_and_end_video_frame()  

  def get_next_frame(self)->int:
    if self.use_rs: # real sense read frame
        try:
            frames = self.pipeline.wait_for_frames(timeout_ms=1000)
        except RuntimeError:
            print(f"realSense: {S.rs_save_type.upper()}-Datei beendet")
            self.finish
            return self.counter

        if self.use_depth_cam and self.align_depth:
            frames = self.aligner.process(frames) # das alighnment geht noch nicht
        self.color_frame = frames.get_color_frame()
        if not self.color_frame:
            return self.counter
        self.cam_intrinsics = self.color_frame.profile.as_video_stream_profile().intrinsics
        self.BRG_frame = np.asanyarray(self.color_frame.get_data())
        if self.use_depth_cam:
            self.depth_frame = frames.get_depth_frame()
            if self.depth_frame and self.show_depth_frame:
                depth_image = np.asanyarray(self.depth_frame.get_data())
                self.depth_colormap = cv2.applyColorMap(cv2.convertScaleAbs(depth_image,alpha=0.03), cv2.COLORMAP_JET)
                if self.mirrow:
                  self.depth_colormap = cv2.flip(self.depth_colormap, 1)
                    
    else: # cv2 read frame
        success, self.BRG_frame = self.video_capture.read()
        if not success:
            print("cv2: End of video stream reached.")
            self.finish = True
    if self.BRG_frame is None:
        return self.counter
    self.h, self.w = self.BRG_frame.shape[:2]
    if self.mirrow:
      self.BRG_frame = cv2.flip(self.BRG_frame, 1)
    self.RGB_frame = cv2.cvtColor(self.BRG_frame, cv2.COLOR_BGR2RGB)
    # --------------------------------------------------
    # coute frames
    # --------------------------------------------------
    if self.playback:
        if self.use_rs:
          self.counter = frames.get_frame_number()
        else:
          self.counter = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
    else: # live stream not paused
        self.counter += 1
    return self.counter

  def set_video_frame(self, frame_nr:int):
      self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_nr)

  def show_frame(self):
      is_size = self.w, self.h
      if is_size != self.show_size:
          show_frame = cv2.resize(self.BRG_frame, self.show_size)
      else:
          show_frame = self.BRG_frame.copy()
      if self.show_flash is not None:
          show_frame[:] = self.show_flash
          self.show_flash = None
      if self.check_window_alive():
        cv2.imshow(self.name, show_frame) # show the frame
        if self.use_depth_cam and self.show_depth_frame:
            cv2.imshow(self.name + " Depth Frame", self.depth_colormap) # show depth frame

  def check_window_alive(self)->bool:
    open_windows = cv2.getWindowProperty(self.name, cv2.WND_PROP_VISIBLE)
    forst_frame = S.start_frame +1 if self.video else 1
    if self.counter >  forst_frame: # wate for forst frame, to open up the window
      if open_windows < 1: # if no wiendow is open
        print('window closed by user')
        self.finish = True
        return False
    return True

  def check_end_frame_reached(self):
      if self.end_frame:
        if self.counter >= self.end_frame:
          self.finish = True
          print(f'currend frame {self.counter} reached end frame {self.end_frame} -> end this loop')


  def end(self):
    self.finish = True
    cv2.destroyAllWindows() # close show window
    # closing cv2 or realsens 
    if self.use_rs:
        self.pipeline.stop()
        print('pyrealsense2 colsed')
    else:
        self.video_capture.release()
        print('cv2 colsed')
