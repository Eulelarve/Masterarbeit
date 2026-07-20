import cv2
import time
import math

import pyrealsense2 as rs
import numpy as np
from datetime import datetime


from own_functions import angle_between_points, draw_angle_between_points, insert

from HandDetectorModule_changed import HandDetector as hdm
from PoseDetectorModule_changed import poseDetector as pdm
from analyse import SaveFrameStatus, save_list_to_file, find_files

import settings as S

def find_pointing_angle(angle_3d_points,i_hand,i_shulder, frame=None ,drawing_2d_points=None, draw=False, left_is_minus=True):

    p1_3d = angle_3d_points[i_hand][1:3] # take just x and y dimension, not z (hight)
    p2_3d = angle_3d_points[i_shulder][1:3] # take just x and y dimension, not z (hight)
    p3_3d = p2_3d.copy()
    # referenz line to the front (z - ref)
    p3_3d[1] += -1 # ajust deepth of the referenz axis/point

    arm_azimuth = angle_between_points(p1_3d[0:2], p2_3d[0:2], p3_3d[0:2]) # take just x and y dimension, not z (hight)
    # to different angle directions
    if p1_3d[0] < p2_3d[0]: # hand nach links side
        arm_azimuth *= 1 -2*left_is_minus  
    else:
        arm_azimuth *= -1 +2*left_is_minus 
        
    if draw:
        p1_2d = drawing_2d_points[i_hand][1:3]
        p2_2d = drawing_2d_points[i_shulder][1:3]
        p3_2d = p2_2d.copy()
        p3_2d[1] += 100 # draw in y direction
        text = str(round(arm_azimuth))
        draw_angle_between_points(frame,text,p1_2d,p2_2d,p3_2d,(-10,-10), S.green)
    
    return arm_azimuth
    # # p1_3d = angle_3d_points[i_hand][1:]
    # p3_3d = p2_3d.copy()
    # p3_3d[1] = -1 # ajust deepth
    # # p3_3d[1] = +1*ref_point_cam_angle_comp  # ajust y
    
    # arm_azimuth = angle_between_points(p1_3d[0:2], p2_3d[0:2], p3_3d[0:2]) # take just x and y dimension, not z (hight)
    # if draw_angles:
    #     p3_2d = p2_2d.copy()
    #     p3_2d[1] = frame.shape[0] # y = frame size
    #     text = str(round(arm_azimuth))+'z'
    #     draw_angle_between_points(frame,text,hand_center,p2_2d,p3_2d,(-10,-50),color)



class Instrument:
    def __init__(self, name, image=None):
        self.name = name
        self.image = image

        self.rect:list = None
        self.bar_pos:int = None
        self.bar_rect:list = None
        # self.group:list = None

        self.selected = False

        self.elevation:float = None
        self.azimuth:float = None
    
    def set_center(self, pos:tuple[int,int]):
        x,y = pos
        _, _, w, h = self.rect
        self.rect[0] = x - w//2
        self.rect[1] = y - h//2

    def collide(self, pos:tuple[int,int]):
        if self.rect is None:
            return None

        px, py = pos
        x, y, w, h = self.rect

        if x <= px <= x + w and y <= py <= y + h:
            return True
        return False
    
    @property
    def center(self):
        if self.rect is None:
            return None

        x, y, w, h = self.rect
        return (x + w // 2, y + h // 2)
    
    def remove(self):
        self.group.remove(self)

class GuiOverlay:

    def __init__(self, frame=None):
        self.frame = frame
        self.tile_bar:list[Instrument] =[]
        self.room:list[Instrument] = []
        self.selected:Instrument = None
        self.grasped = False
        self.sel_size = 10
        self.room_size = -30

    def _create_placeholder(self, text, size=100):
        img = np.full((size, size, 3), 180, np.uint8)

        cv2.putText(
            img,
            text[:2].upper(),
            (10, int(size * 0.65)),
            cv2.FONT_HERSHEY_SIMPLEX,
            size / 80,
            (0, 0, 0),
            2,
            cv2.LINE_AA,
        )

        return img

    def add_instrument(self, name, image_path=None, position=-1):

        if image_path is not None:
            image = cv2.imread(image_path)
            if image is None:
                image = self._create_placeholder(name)
        else:
            image = self._create_placeholder(name)

        instrument = Instrument(name, image)
        self._add_to_bar(instrument, position)
        
    
    def _add_to_bar(self, instrument:Instrument, position:int=None):
        if instrument in self.tile_bar:
            instrument.rect = instrument.bar_rect.copy() # get the old position beck
            return False
        
        if instrument in self.room:
            self.room.remove(instrument)

        if position is None:
            position = instrument.bar_pos
        insert(self.tile_bar, position, instrument)

        self.define_tile_pos_and_size()

    def _add_to_room(self, instrument:Instrument):
        if instrument in self.room:
            return False
        if instrument in self.tile_bar:
            self.tile_bar.remove(instrument)
        
        self.selected_size_change(self.room_size)
        self.room.append(instrument)


    def define_tile_pos_and_size(self):

        if not self.tile_bar:
            return False
        if self.frame is None:
            return False

        margin = 10
        n = len(self.tile_bar)

        tile_size = min(
            120,
            (self.frame.shape[1] - margin * (n - 1)) // n,
        )
        w = n * (tile_size + margin) - margin 
        edge = (self.frame.shape[1] - w) // 2

        for i, inst in enumerate(self.tile_bar):
            x = edge + i * (tile_size + margin)
            inst.rect = [x, self.hight, tile_size, tile_size]
            inst.bar_rect = [x, self.hight, tile_size, tile_size]
            inst.bar_pos = i
        
        return True
    
    def _set_frame(self, frame):
        if self.frame is None:
            self._set_frame_and_dependencies(frame)
        else:
            if frame.shape != self.frame.shape:
                self._set_frame_and_dependencies(frame)
            else:
                self.frame = frame
    
    def _set_frame_and_dependencies(self, frame):
        self.frame = frame
        self.hight = int(self.frame.shape[0] * (1 - S.gui_hight))
        self.room_top = int(self.frame.shape[0] * S.arm_decection_border_top)
        self.room_bot = int(self.frame.shape[0] * S.arm_decection_border_bot)
        self.define_tile_pos_and_size()

    def draw(self, frame):
        if self.frame is not frame:
            self._set_frame(frame)

        tile_edge = 4
        for inst in [*self.tile_bar, *self.room]:

            if inst.rect is None:
                continue

            x, y, w, h = inst.rect

            color = (0, 255, 255) if inst.selected else (255, 255, 255)

            cv2.rectangle(self.frame, (x, y), (x + w, y + h), color, 2)

            icon = cv2.resize(inst.image, (w - tile_edge*2, h - tile_edge*2))
            self.frame[y + tile_edge:y + h - tile_edge, x + tile_edge:x + w - tile_edge] = icon
        
    def choose_instrument(self, pointer_pos:tuple[int,int]):
        if self.grasped:
            return self.selected
        
        self.selected = None

        for inst in  [*self.tile_bar, *self.room]:

            inst.selected = False

            if inst.collide(pointer_pos):
                inst.selected = True
                self.selected = inst
                return inst
        return None
    
    def grap(self):
        if self.selected is None:
            return False
        if self.grasped == False:
            self.grasped = True
            if self.selected in self.tile_bar:
                self.selected_size_change(-self.sel_size)
            elif self.selected in self.room:
                self.selected_size_change(self.sel_size)
        return True
    
    def selected_size_change(self, size_change:int):
        self.selected.rect[2] += size_change
        self.selected.rect[3] += size_change
        return self.selected.rect[2:4]
        
    def release(self, azimuth:float=None, elevation:float=None,)->bool:
        if self.selected is None or self.grasped == False:
            return False
        
        if valide_angle_area(self.selected.center, self.frame.shape):
            self.selected_size_change(-self.sel_size)
            self._add_to_room(self.selected)
            self.selected_set_angle(azimuth=azimuth, elevation=elevation)
        else:
            self._add_to_bar(self.selected)
            self.selected_set_angle(azimuth=None, elevation=None)

        self.grasped = False
        return True

    def move(self, pos:tuple[int,int])-> bool:
        if not self.grasped:
            return False
        
        self.selected.set_center(pos)
        return True

    def selected_set_angle(self, azimuth:float, elevation:float):
        self.selected.azimuth = azimuth
        self.selected.elevation = elevation


def valide_angle_area(pos:list[int,int], frame_shape):
    return S.arm_decection_border_top <= pos[1]/frame_shape[0] <= S.arm_decection_border_bot


   