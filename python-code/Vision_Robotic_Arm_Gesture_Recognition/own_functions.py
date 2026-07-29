from datetime import datetime
import cv2
import math
import numpy as np
try:
    import settings as S
except:
    import Vision_Robotic_Arm_Gesture_Recognition.settings as S
    
def angle_between_points(p1:tuple, p2:tuple, p3:tuple)->float:
    """ 
        calcumates the angle between 2 vectors given by 3 points (2D or 3D)
        p2 is the mittel point / angle point / shared point of the voctors
    """
    v1 = np.array(p1) - np.array(p2)
    v2 = np.array(p3) - np.array(p2)

    angle = np.arccos(
        np.dot(v1, v2) /
        (np.linalg.norm(v1) * np.linalg.norm(v2))
    )

    return np.degrees(angle)

def draw_angle_between_points(frame, text:str, p1:list[int,int] ,p2:list[int,int] ,p3:list[int,int] , text_pos=(-50,+50), color=(255, 255, 255)):
        """ 
            draw lines between points and are angle number next to p2
        """
        cx1, cy1 = p1
        cx2, cy2 = p2
        cx3, cy3 = p3
        
        cv2.circle(frame, (cx1, cy1), 5, (255, 0, 255), -1)
        cv2.circle(frame, (cx2, cy2), 5, (255, 0, 255), -1)
        cv2.circle(frame, (cx2, cy2), 10, (255, 0, 255), 1)
        cv2.circle(frame, (cx3, cy3), 5, (255, 0, 255), -1)
        
        cv2.line(frame, (cx2, cy2), (cx3, cy3), color, 2)
        cv2.line(frame, (cx2, cy2), (cx1, cy1), color, 2)
        
        cv2.putText(frame, text, (cx2 + text_pos[0], cy2 + text_pos[1]),
                    cv2.FONT_HERSHEY_PLAIN, 1, color, 2, cv2.LINE_AA)
            
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
    def __init__(self,min_speed=10, buffer_size=5):
        self.pos = None
        self.speed = None
        self.status_buffer = ValueBuffer(buffer_size=buffer_size)
        self.min_speed = min_speed

    def _is_moving_no_buffer(self, new_pos:list):
        if self.is_jumping(new_pos) == False:
            if self.pos_change >= self.min_speed:
                return True
            return False
        return None

    
    def is_moving(self, new_pos:list)->bool|None:
        speed = self.get_speed(new_pos)
        if speed >= self.min_speed:
            return True
        return False

    def is_moving_status_buffered(self, new_pos:list)->bool:
        self.status_buffer.add(self.is_moving(new_pos))
        return self.status_buffer.most_frequently
    
    def stands_still(self, new_pos:list)->bool:
        return not self.is_moving(new_pos)

    def get_speed(self, new_pos):
        if self.pos is None:
            self.pos = new_pos
        pos_change = math.dist(new_pos, self.pos)
        self.pos = new_pos
        return pos_change

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


def offset_landmarks(landmarks, dx=0, dy=0, dz=0):
    """
    Verschiebt MediaPipe-Landmarks.
    will change the inputed objece!

    input can be:
        results.pose_landmarks.landmark
        results.multi_hand_landmarks[i].landmark
    not just:
        results.pose_landmarks
        results.multi_hand_landmarks[i]


    """
    # landmarks_copy = deepcopy(pose_or_hand_landmarks)

    # # Überprüfen, ob es das übergeordnete Landmark-Objekt ist oder bereits die Liste der Landmark-Objekte
    # if hasattr(pose_or_hand_landmarks, 'landmark'):
    #     landmarks = pose_or_hand_landmarks.landmark
    # else:
    #     landmarks = pose_or_hand_landmarks
    
    for lm in landmarks:

        if dx:
            lm.x += dx
        if dy:
            lm.y += dy
        if dz:
            lm.z += dz


def get_center_of_landmarks(pose_landmarks, landmark_indices, round_to_int=True):
    """ calculate the center of the given landmarks
    Args:
        pose_landmarks: list of pose landmarks
        landmark_indices: list of indices of the landmarks to calculate the center from
        round_to_int: whether to round the center coordinates to integers
    Returns:
        center: the center as a tuple (x, y) or (x,y,z)
    """
    x_sum = sum([pose_landmarks[i][1] for i in landmark_indices])
    y_sum = sum([pose_landmarks[i][2] for i in landmark_indices])
    center_x = x_sum / len(landmark_indices)
    center_y = y_sum / len(landmark_indices)

    if round_to_int:
        center_x = round(center_x)
        center_y = round(center_y)

    try:
        z_sum = sum([pose_landmarks[i][3] for i in landmark_indices])
        center_z = z_sum / len(landmark_indices)
        if round_to_int:
            center_z = round(center_z)

        return [center_x, center_y, center_z]
    except:
        return [center_x, center_y]



from collections import deque

class ValueBuffer:
    """_summary_ 
        A class to store a buffer of elements and calculate the average, most frequently, majority and atleast x of the values in the buffer.
    """

    def __init__(self, buffer_size):
        self.values = deque(maxlen=buffer_size)
        self.last_majority = None # saves the last value that was the majority in the buffer, so that it can be returned if there is no majority in the current buffer

    def add(self, value, update_majority=False):
        self.values.append(value)
        if update_majority:
            self.majority
    
    def set_majority(self, value):
        self.values.clear()
        for _ in range(self.values.maxlen//2):
            self.values.append(value)
        self.add(value, update_majority=True)

    def flood(self, value):
        for _ in range(self.values.maxlen-1):
            self.values.append(value)
        self.add(value, update_majority=True)

    def add_and_get_average(self, value):
        self.add(value, update_majority=False)
        return self.average
    
    def add_and_get_mojority(self, value):
        self.add(value)
        return self.majority

    def add_and_get_most_frequently(self, value):
        self.add(value, update_majority=False)
        return self.most_frequently
    
    @property
    def average(self):
        """ calculate the average of the values in the buffer
            only for boffered numerical values, otherwise it will crash
        """
        if not self.values:
            return None

        return sum(self.values) / len(self.values)
    
    @property
    def most_frequently(self):
        if not self.values:
            return None
        
        return max(set(self.values), key=self.values.count)
        
    @property
    def majority(self):
        if not self.values:
            return None

        for value in self.values:
            if self.values.count(value) > self.values.maxlen / 2:
                self.last_majority = value
                return value
            
        # if no element nomber exceeds the half of the buffer size, return the last majority element, if there is one
        return None
    
    @property
    def difference(self):
        return max(self.values) - min(self.values)

    @property
    def max(self):
        return max(self.values)
    
    @property
    def min(self):
        return min(self.values)
    
    @property
    def i_max(self):
        return self.index(self.max)

    
    @property
    def i_min(self):
        return self.index(self.min)
    
    def atleast(self, min_nr_of_same_elements):
        if not self.values:
            return None

        for value in set(self.values):
            if self.values.count(value) >= min_nr_of_same_elements:
                return value
        
        # if no element nomber exceeds the min_nr_of_same_elements,
        return None
    
    @property
    def all_the_same(self):
        value = set(self.values)
        if len(value) == 1:
            return value[0]
        return None
    
    def clear(self):
        self.values.clear()
    
    def __getitem__(self, index):
        return self.values[index]

    def __len__(self):
        return len(self.values)
    
    def index(self, value):
        return self.values.index(value)

class ListAverager:
    def __init__(self, buffer_size=5, list_len=2):
        self.buffer_list = []
        for _ in range(list_len):
            self.buffer_list.append(ValueBuffer(buffer_size))

    def add(self, list:tuple):
        for i, value in enumerate(list):
            self.buffer_list[i].add(value)

    def get(self, rounded=False)->list:
        r = []
        for buffer in self.buffer_list:
            value = buffer.average
            if rounded:
                value = round(value)
            r.append(value)
        return r

    def add_and_gat(self, list:tuple, rounded = False)->list:
        self.add(list)
        return self.get(rounded)

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


def close_to(max_distance:float, *points:list)->bool:
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


def mediapipe_pose_world_to_global(pose_world_landmarks, cam_angle):

    pts = np.asarray(pose_world_landmarks, dtype=np.float64)
    if pts.ndim == 1:
        pts = pts.reshape(1, -1)

    if len(pts[0]) > 3: 
        pts = pts[:, 1:4]
    
    # change coordinates: +x = rechts, +z  = oben , +y = hinten
    for i,(xa,ya,za) in enumerate(pts):
        xn = xa
        yn = za
        zn = -ya 
        pts[i] = [xn,yn,zn]    

    theta = np.deg2rad(cam_angle)

    x = pts[:, 0]
    y = pts[:, 1]
    z = pts[:, 2]

    y0 = y*np.cos(theta) + z*np.sin(theta)
    z0 = -y*np.sin(theta) + z*np.cos(theta)

    y0 += 2 # so y = 0 is ruffly at the camera position if person stants in the room center
    z0 += 1 # so z = 0 ruffly on the flore hight

    pts = np.column_stack((x, y0, z0))
    return pts

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
        print("Linksklick:", MOUSE)

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