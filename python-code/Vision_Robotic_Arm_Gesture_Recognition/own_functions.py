from datetime import datetime
import cv2
import math
from statistics import median
import numpy as np
from collections import deque
import time

try:
    import settings as S
except:
    import Vision_Robotic_Arm_Gesture_Recognition.settings as S
    
            
def get_globe_timeline_curv(r=200,deg=-90,cx=0,cy=0, steps=50):

    rad = math.radians(deg)
    flatening = math.sin(rad)
    ys = np.linspace(-r, r, steps)
    pts = []

    for y in ys:
        x = flatening * math.sqrt(r**2-y**2)
        pts.append([x + cx, y + cy])

    return np.array(pts, dtype=np.int32).reshape((-1, 1, 2))

def get_globe_timeline_curvs(r, cx=0, cy=0, deg_steps=15, line_steps=50, frame=None, draw = False):
    """
        Compute multiple globe time-zone curves at regular angular intervals.

        The function generates several meridian lines for a front-view globe model.
        Optionally, the curves can be drawn directly into an image frame.

        Parameters
        ----------
        r : int or float
            Radius of the globe in pixels.
        cx : int or float, default=0
            X-coordinate of the globe center.
        cy : int or float, default=0
            Y-coordinate of the globe center.
        deg_steps : int, default=15
            Angular spacing in degrees between adjacent time-zone lines.
        line_steps : int, default=50
            Number of sample points used for each individual curve.
        frame : numpy.ndarray or None, default=None
            Image frame used for drawing, if `draw=True`.
        draw : bool, default=False
            If `True`, the curves are drawn directly onto `frame` using OpenCV.

        Returns
        -------
        list
            List of NumPy arrays, one array per generated curve.
    """
    timelines = []
    for deg in range(-90, deg_steps+90, deg_steps):
        pts = get_globe_timeline_curv(r,deg,cx,cy,line_steps)
        timelines.append(pts)

        if draw:
            color = (0, 255, 0)
            width = 2
            cv2.polylines(frame, [pts], False, color, width)

    if draw:
        color = (0, 0, 255)
        cv2.circle(frame,[cx,cy],width+2,color,-1)
    return timelines


class MoveDetector:
    def __init__(self,min_speed:int=S.moving_min_speed, buffer_time:int=S.moving_check_time):
        self.pos = None
        self.pos_buffer = ValueBufferTime(buffering_time=buffer_time)
        self.min_speed = min_speed
    
    def is_moving(self, new_pos:list=None)->int:
        pix_per_sec = self.get_speed(new_pos)
        if pix_per_sec >= self.min_speed:
            return pix_per_sec
        return 0
    
    def stands_still(self, new_pos:list)->bool:
        return not self.is_moving(new_pos)

    def get_speed(self, new_pos:tuple=None)->float:
        """ retruns the speed in pixel per second"""
        self.pos_buffer.add(new_pos)
        dist = self.pos_buffer.distance()
        pix_per_sec = dist / self.pos_buffer.buffering_time
        return pix_per_sec

    def get_smoothed_speed(self, new_pos:tuple=None)->float:
            if new_pos is not None:
                self.set_new_pos(new_pos)
            return self.smoothed_speed

    def set_new_pos(self, new_pos:tuple):
        if new_pos is not None:
            if self.pos is None:
                self.pos = new_pos
            self.speed = math.dist(new_pos, self.pos)
            self.smoothed_speed = self.speed_buffer.add_and_get_average(self.speed)
            self.pos = new_pos

    # def is_jumping(self, new_pos):
    #     if self.valide_move(new_pos):
    #         _, speed_change = self.get_changes(new_pos)

    #         if speed_change > self.max_speed_change:
    #             return True
    #         return False
        
    #     return None

def fit_roi_landmarks_to_frame(landmarks, pixel_frame_size, pixel_region_x_y_w_h):
    """ change the landmark coordinates to fit the region in the frame, if the region is not the whole frame.
        so you can draw in the origiunal frame in on the right position.
        for this, it applies a linear funktion offset to landmarks

        will change the inputed object!
    Args:
        landmarks: list of landmarks to change
        pixel_frame_size: tuple (width, height) of the original frame
        pixel_region_x_y_w_h: tuple (x, y, width, height) of the region in the frame
        """
    W, H = pixel_frame_size
    x,y,w,h = pixel_region_x_y_w_h
  
    factor_x = w / W
    factor_y = h / H
    offset_x = x / W
    offset_y = y / H

    for lm in landmarks:
        lm.x = lm.x * factor_x + offset_x
        lm.y = lm.y * factor_y + offset_y


class ReturnModes:
    """ mode declarations vor the get methodes of the ValueBuffer and ListBuffer classes"""
    mode_AVERAGE = 'average'
    mode_MEDIAN = 'median'
    mode_MOST = 'most'
    mode_MAJOR = 'major'
    mode_DIFF = 'diff'
    mode_MAX = 'max'
    mode_MIN = 'min'
    mode_DIFF_I = 'diff_i'
    mode_MAX_I = 'max_i'
    mode_MIN_I = 'min_i'

class ValueBuffer(ReturnModes):
    """_summary_ 
        A class to buffer of elements and calculate states like average, median, majority, max and most frequent of the elements in the buffer.
    """

    def __init__(self, buffer_size:int, default_get_mode:str=S.default_buffer_mode):
        self.buffer = deque(maxlen=buffer_size)
        self.last_majority = None # saves the last value that was the majority in the buffer, so that it can be returned if there is no majority in the current buffer
        self.majority_border = int(buffer_size / 2) +1
        self.default_mode = default_get_mode

    def add(self, value:any, ignore_none=False):
        if ignore_none and value is None:
            return False
        self.buffer.append(value)
        return True

    def get(self, mode:str|None=None)->any:
        if not mode:
            mode = self.default_mode
        mode = mode.lower()
        match mode:
            case self.mode_AVERAGE:
                return self.average
            case self.mode_MEDIAN:
                return self.median
            case self.mode_MOST:
                return self.most_frequently
            case self.mode_MAJOR:
                return self.majority
            case self.mode_DIFF:
                return self.difference
            case self.mode_MAX:
                return self.max
            case self.mode_MIN:
                return self.min
            case self.mode_DIFF_I:
                return self.i_difference
            case self.mode_MAX_I:
                return self.i_max
            case self.mode_MIN_I:
                return self.i_min
            case _:
                raise f'"{mode}" is not a valide mode'
            
    def add_and_get(self, value:any, mode:str|None=None, ignore_none=False)->any:
        self.add(value, ignore_none)
        return self.get(mode)
    
    def set_majority_boarder(self, new_border:int):
        if new_border > self.buffer.maxlen:
            raise f"new manorety border ({new_border} higher the buffer lenght ({self.buffer.maxlen}))"
        if new_border < 0:
            raise "majorety border must be positiv"
        self.majority_border = new_border
    
    def flood(self, value):
        for _ in range(self.buffer.maxlen-1):
            self.buffer.append(value)
        self.add(value, update_majority=True)

    def add_and_get_average(self, value, ignore_none=False):
        self.add(value, ignore_none=ignore_none)
        return self.average
    
    def add_and_get_mojority(self, value, ignore_none=False):
        self.add(value, ignore_none)
        return self.majority

    def add_and_get_most_frequently(self, value, ignore_none=False):
        self.add(value, ignore_none)
        return self.most_frequently

    def add_and_get_median(self, value, ignore_none=False):
        self.add(value, ignore_none)
        return self.median

    def atleast(self, nr_of_same_elements)->any:
        """ returns the most frequently element reaching the given number of same elements in the buffer list 
        """
        if not self.buffer:
            return None

        most = self.most_frequently
        if self.count(most) >= nr_of_same_elements:
                return most
        # if no element nomber reaches the min_nr_of_same_elements,
        return None

    def count(self, value:any)->int:
        return self.buffer.count(value)

    def index(self, value)->int:
        return self.buffer.index(value)
    
    def clear(self):
        self.buffer.clear()
    
    def __getitem__(self, index):
        return self.buffer[index]

    def __len__(self):
        return len(self.buffer)
    
    @property
    def average(self)->float|None:
        """ calculate the average of the element in the buffer
            only for boffered numerical values, otherwise it will crash
        """
        if not self.buffer:
            return None
        return sum(self.buffer) / len(self.buffer)
    
    @property
    def most_frequently(self)->any:
        """ returns the element that appears most frequently in the buffer list """
        if not self.buffer:
            return None
        return max(set(self.buffer), key=self.count)
        
    @property
    def majority(self)->any:
        """ returns the first value reaching the majorety number of same elements in the buffer list 
            also if no element nomber exceeds the half of the buffer size, return the last majority element, if there is one
        """
        if not self.buffer:
            return None

        for value in self.buffer:
            if self.count(value) >= self.majority_border:
                self.last_majority = value
                break
        return self.last_majority
    
    @property
    def median(self)->float|None:
        if not self.buffer:
            return None
        return median(self.buffer)
    
    @property
    def difference(self)->float|None:
        if not self.buffer:
            return None
        return self.max -self.min

    @property
    def max(self)->float|None:
        if not self.buffer:
            return None
        return max(self.buffer)
    
    @property
    def min(self)->float|None:
        if not self.buffer:
            return None
        return min(self.buffer)
    
    @property
    def i_max(self)->int:
        return self.index(self.max)
    
    @property
    def i_min(self)->int:
        return self.index(self.min)

    @property
    def i_difference(self)->int:
        return self.i_max - self.i_min
    
    @property
    def all_the_same(self)->any:
        if not self.buffer:
            return None
        value = set(self.buffer)
        if len(value) == 1:
            return value[0]
        return None


class ValueBufferTime(ValueBuffer):
    def __init__(self, buffering_time:float, default_get_mode:str = S.default_buffer_mode):
        """ buffering_time: time in secunds the buffer keeps values befor drop/ replace them """
        self.buffer:list = []
        self.times:list = []
        self.buffering_time = buffering_time
        self.last_majority = None # saves the last value that was the majority in the buffer, so that it can be returned if there is no majority in the current buffer
        self.default_mode = default_get_mode

    def add(self, value, ignore_none=False):
        if ignore_none and value is None:
            return False
        self.buffer.append(value)
        self.times.append(time.time())
        while self.times[-1] - self.times[0] > self.buffering_time:
            self.buffer.pop(0)
            self.times.pop(0)
    
    @property
    def majority_border(self):
        return len(self.buffer)//2+1

    def clear(self):
        self.times.clear()
        return super().clear()

    def distance(self)->float:
        return math.dist(self.buffer[0], self.buffer[-1])

class ListBuffer(ReturnModes):
    def __init__(self, buffer_size:int=5, default_get_mode:str=S.default_buffer_mode):
        self.buffer_list:list[ValueBuffer] = []
        self.buffer_size = buffer_size
        self.default_mode = default_get_mode

    def add(self, values:tuple, ignore_none=False):
        for i, value in enumerate(values):
            if value is None and ignore_none:
                continue

            if i >= len(self.buffer_list):
                self.buffer_list.append(ValueBuffer(self.buffer_size))

            self.buffer_list[i].add(value)

    def get(self, mode:str|None=None, round_to:int|None = None)->list:
        if not mode:
            mode = self.default_mode
        r = []
        for buffer in self.buffer_list:
            value = buffer.get(mode=mode)
            value = round0(value, round_to)
            r.append(value)
        return r

    def add_and_get(self, list:tuple, mode:str|None=None, round_to:int|None = None, ignore_none=False)->list:
        self.add(list,ignore_none)
        return self.get(mode, round_to)


def round0(value:float, decimal:int|None)->int|float:
    """ if decimal is 0 return an int value
        if decimal is None returns the original value
    """
    if decimal is None:
        return value
    if decimal:
        return round(value, decimal)
    return round(value) 


class HandOpenClosedBuffer(ValueBuffer):
    """_summary_
        A class to store a buffer of hand status (open, closed, no hand) and calculate the majority of the hand status in the buffer.
    """

    def __init__(self, buffer_size, non_means_closed_after_frame=5, none_after_frame=99999):
        super().__init__(buffer_size)
        self.none_frame = none_after_frame
        self.closed_frame = non_means_closed_after_frame
        self.none_counter = 0
        self.closed_status = 0
        self.open_status = 1
    
    def add(self, hand_status, update_majority=True):
        if hand_status == None:
            self.none_counter += 1
            if self.none_counter >= self.none_frame:
                self.values.clear() # clear the buffer if no hand is detected for a long time, so that the majority is not influenced by old values
            elif self.none_counter >= self.closed_frame:
                super().add(self.closed_status, update_majority=update_majority) # None is interpreted as closed hand, because it is more likely that closed hand is not detected
        else:
            self.none_counter = 0
            super().add(hand_status, update_majority=update_majority)
        
    def add_and_get(self, hand_status):
        return self.add_and_get_most_frequently(hand_status)

  




class ProcessHandAperture():
    """_summary_
        A class to process the hand status based on the aperture values and a buffer of the hand status. 
        It can be used to smooth the hand status and to detect if the hand is lost.
    """

    def __init__(self, smoothing_len=5, buffer_size=5, lost_hand_counter=40, 
                 open_threshold = 70, 
                 close_threshold = 60 ):
        self.smoothed_aperture = ValueBuffer(smoothing_len)
        self.hand_status_buffer = ValueBuffer(buffer_size)
        self.lost_hand_by = lost_hand_counter
        self.open_threshold = open_threshold
        self.close_threshold = close_threshold

        self.open_status = 1
        self.close_status = 0
        self.no_hand_status = None
        
        self.lost_hand_counter = 0
        self.status_now = self.no_hand_status

    def add(self, aperture):
        if aperture is not None:
            self.lost_hand_counter = 0
            self.smoothed_aperture.add(aperture)
            self._status_decision()
        else:
            self.lost_hand_counter += 1

    def _status_decision(self):
        if self.smoothed_aperture.average >= self.open_threshold:
                self.status_now = self.open_status
        elif self.smoothed_aperture.average <= self.close_threshold:
            self.status_now = self.close_status

        # buffer to get majority   
        if self.status_now is not None: 
            self.hand_status_buffer.add(self.status_now)

    def get_major(self):
        if self.lost_hand_counter >= self.lost_hand_by:
            return self.no_hand_status
        else:
            major = self.hand_status_buffer.majority
            if major is None:
                return self.status_now
            else:
                return major


# chat gpt jasn class
import json
import os
from datetime import datetime

class SaveToJSON:
    def __init__(self, filename="save.json", timestemp=True):
        self.timestemp = timestemp
        self.filename = filename
        self.data = {}

        # Falls Datei schon existiert, laden wir sie direkt
        if os.path.exists(self.filename):
            self.load()

    def set(self, key, value):
        """Speichert eine einzelne Variable"""
        self.data[key] = value

    def set_many(self, **kwargs):
        """Speichert mehrere Variablen auf einmal"""
        for key, value in kwargs.items():
            self.data[key] = value

    def get(self, key, default=None):
        """Liest eine Variable"""
        return self.data.get(key, default)

    def remove(self, key):
        """Löscht eine Variable"""
        if key in self.data:
            del self.data[key]

    def save(self):
        """Speichert alles in die JSON-Datei"""
    
        end = '.json'
        if self.timestemp:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.filename += ' '+timestamp

        with open(self.filename+end, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def load(self):
        """Lädt Daten aus der JSON-Datei"""
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.data = {}

# fon chag gpt CSVWriter

import csv
import os

class CSVWriter:

    @staticmethod
    def create(filename:str, *headers):
        """
        Beispiel:
        filename = CSVWriter.create(
            "name",
            "alter",
            "punkte"
        )
        """
        # timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # filename += f"{timestamp}.csv"

        with open(filename, "w", newline="", encoding="utf-8") as file:
            i = 2
            if os.path.exists(filename):
                while os.path.exists(filename+f'({i})'):
                    i=+1
                filename+=f'({i})'

            writer = csv.writer(file)
            writer.writerow(headers)
            print(f'CSVWriter: create {filename}')
        return filename

    @staticmethod
    def write(filename:str, **kwargs):
        file_exists = os.path.exists(filename)

        with open(filename, "a", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=kwargs.keys()
            )

            if not file_exists:
                print(f'CSVWriter: create {filename}')

                writer.writeheader()

            writer.writerow(kwargs)
            print(f'CSVWriter: add row to {filename}')


def close_to(max_distance:float, *points:tuple[float,float])->bool:
    """ returns false if one of the given points is not close enough to the first given point """
    p_ref = points[0]
    for p in points:
        if math.dist(p_ref, p) > max_distance:
            return False
    return True

def tolist(list_or_not, keep_None=True):
    if list_or_not is None:
        return None if keep_None else []
    if isinstance(list_or_not, list):
        return list_or_not
    if isinstance(list_or_not, str):
        return [list_or_not]
    try:
        return list(list_or_not)
    except TypeError:
        return [list_or_not]


def screenshot(frame,
               name="screenshot",
               timestamp=True,
               printout=True,
               info=None,
               ask_name=False):

    if ask_name:
        user_name = input("Name the Screenshots (empty = default): ").strip()
        if user_name:
            name = user_name

    if info:
        for v in info:
            name += "_" + str(v)

    if timestamp:
        name += datetime.now().strftime("_%Y%m%d_%H%M%S")

    name += ".png"

    success = cv2.imwrite(name, frame)

    if printout:
        print(f"Screenshot: {name}")
        print("...Saved" if success else "...Failed!")

    return success


def map_threshold(value, thresholds, outputs):
    """
    Mappt einen Wert anhand von Schwellwerten auf einen Ausgabewert.

    Parameters
    ----------
    value : float | int
        Der Eingabewert.
    thresholds : list
        Aufsteigend sortierte Schwellwerte.
    outputs : list
        Ausgabewerte. Muss genau ein Element mehr enthalten als thresholds.

    Returns
    -------
    Der passende Eintrag aus outputs.
    """
    if len(outputs) != len(thresholds) + 1:
        raise ValueError("outputs muss genau ein Element mehr enthalten als thresholds.")

    for threshold, output in zip(thresholds, outputs):
        if value < threshold:
            return output

    return outputs[-1]

class Mouse:
    def __init__(self):
        self.pos = (0,0)
        self.pressed = False
        self.release = False

    def is_pressed(self):
        if self.pressed:
            self.pressed = False
            return True
        return False
    
    def is_release(self):
        if self.release:
            self.release = False
            return True
        return False
    
    def get_pos(self):
        return self.pos[:]

MOUSE = Mouse()        

def cv2_mouse_callback(event, x, y, flags, param):
    global MOUSE

    MOUSE.pos = (x, y)

    if event == cv2.EVENT_LBUTTONDOWN:
        MOUSE.pressed = True
        print("Linksklick:", MOUSE.get_pos())

    elif event == cv2.EVENT_LBUTTONUP:
        MOUSE.release = True



def insert(list:list, position:int, object)->int:
    """
        Inserts an object or just a number into a list at the specified position.

        Position behavior:
        - position >= 0:
            Inserts the object at the given index (same as list.insert()).
        - position == -1:
            Appends the object to the end of the list.
        - position < -1:
            Inserts the object relative to the end of the list.
            For example:
                position = -2  -> before the last element
                position = -3  -> before the second-to-last element

        Examples:
            [1, 2, 3, 4], position= 1 -> [1, x, 2, 3, 4]
            [1, 2, 3, 4], position= 0 -> [x, 1, 2, 3, 4]
            [1, 2, 3, 4], position=-1 -> [1, 2, 3, 4, x]
            [1, 2, 3, 4], position=-2 -> [1, 2, 3, x, 4]
            [1, 2, 3, 4], position=-3 -> [1, 2, x, 3, 4]
    """
    if position == -1:
        list.append(object)
        return len(list) -1
    else:
        if position < 0:
            position = position + len(list) +1

        list.insert(position, object)
        return position

def clamp(value, low, high):
    return max(low, min(value, high))

def keep_rect_inside(inner_rect, outer_rect):
    """
    Clamp an inner rectangle so that it stays fully inside an outer rectangle.

    Parameters
    ----------
    inner_rect : tuple
        (x, y, w, h) of the inner rectangle.
    outer_rect : tuple
        Either (width, height) for a screen starting at (0, 0),
        or (x, y, width, height) for a custom outer rectangle.

    Returns
    -------
    tuple
        Clamped inner rectangle as (x, y, w, h).
    """
    if len(outer_rect) == 2:
        ox, oy = 0, 0
        ow, oh = outer_rect
    elif len(outer_rect) == 4:
        ox, oy, ow, oh = outer_rect
    else:
        raise ValueError("outer_rect must be (w, h) or (x, y, w, h)")

    x, y, w, h = inner_rect

    if w > ow:
        w = ow
    if h > oh:
        h = oh

    x = clamp(x, ox, ox + ow - w)
    y = clamp(y, oy, oy + oh - h)

    return (x, y, w, h)



def valide_angle_zone(pos:list[int,int], frame_shape):
    return S.arm_decection_border_top <= pos[1]/frame_shape[0] <= S.arm_decection_border_bot