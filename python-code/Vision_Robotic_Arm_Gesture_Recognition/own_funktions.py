import ctypes
import ast
from datetime import datetime
import cv2

def save_list_to_file(filename, data:tuple=None):
    if not data:
        print("No status data to save.")
        return
    with open(filename, 'w') as f:
        for item in data:
            f.write(f"{item}\n")
        print(f"Saved {len(data)} status to {filename}.")

def load_list_from_file(filename, data:list=None):
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            data.append(ast.literal_eval(line)) # alternative to json file

def key_pressed(vk_code):
    return ctypes.windll.user32.GetAsyncKeyState(vk_code) & 0x8000 != 0

class CaptureStatus:
    def __init__(self, keys:list, status:list=None):
        if status is None:
            status = keys
        self.keys = keys
        self.status = status
        self.saved = []
    
    def add(self, key, if_no_key_match_add_none=True):
        if key in self.keys:
            index = self.keys.index(key)
            self.saved.append(self.status[index])
            return self.status[index]
        elif if_no_key_match_add_none:
            self.saved.append(None)
        else:
            return None
    
    def add_from_pressed_key(self, if_no_key_match_add_none=True, add_only_first=False):
        add = []
        
        for i, key in enumerate(self.keys):
            if key_pressed(key):
                add.append(self.status[i])
        
        if not add and if_no_key_match_add_none:
            add.append(None)
        
        if add_only_first:
            add = add[0]

        self.saved.append(add)

        return add if add else None

    def shift_all_by(self, i:int, fill = None):
        if type(self.saved[0]) is list and type(fill) is not list:
            fill = [fill]

        fill = [fill]*abs(i)
        lost = None
        if i >= 1:
            lost = self.saved[:i]
            self.saved = fill + self.saved[i:]
        elif i <= -1:
            lost = self.saved[i:]
            self.saved = self.saved[:i] + fill
        return lost, fill

    def save_to_file(self, filename, data:tuple=None):
        if not data:
            data = self.saved
        save_list_to_file(filename=filename,data=data)
    
    def load_from_file(self, filename, data:list=None):
        if not data:
            data = self.saved
        load_list_from_file(filename=filename, data=data)
    
    def get(self, index):
        if index < len(self.saved):
            return self.saved[index]
        else:
            return None
        
    def pop(self, i:int=-1):
        if self.saved:
            return self.saved.pop(i)


class SaveFrameStatus(CaptureStatus):
    def __init__(self, keys, status = None):
        super().__init__(keys, status)
        self.pop_key = ord('x')
        self.status_for_each_frame = []
        self.status_for_each_frame_comp = []

    def add(self, start_frame, key, print_out=True):
        if key in self.keys:
            i = self.keys.index(key)
            add = [start_frame, self.status[i]]
            self.saved.append(add)
            if print_out:
                print('Frame', start_frame, '-', self.status[i])
        elif key == self.pop_key:
            wrong = self.pop()
            if wrong:
                if print_out:
                    print('pop: Frame', wrong[0], '-', wrong[1])
                return wrong[0]
            else:
                if print_out:
                    print('empty - nothing to pop')

    def get_status_for_each_frame(self,):
        if not self.status_for_each_frame:
            self.create_status_for_each_frame()
        return self.status_for_each_frame

    def create_status_for_each_frame(self):
        if not self.saved:
            raise Exception('no self.saved data to transform')
        
        self.status_for_each_frame.clear() # just in case
        status = None # start startus
        f_nr = 0 # start frame nr

        # for each saved startus change in saved
        for start_frame, next_status in self.saved:
            # add the same status until the start frame of the next status is reached
            while f_nr < start_frame:   
                self.status_for_each_frame.append(status)
                f_nr += 1 
            status = next_status
        
        # add last status only ons for all remaining frames 
        self.status_for_each_frame.append(status)

    def check_frame_order(self):
        frame_nr_before = -1
        for save in self.saved:
            f_nr = save[0]
            if f_nr > frame_nr_before:
                frame_nr_before = f_nr
            else:
                raise Exception(f'Frame order Error: {f_nr} folows {frame_nr_before}')
    
    def add_comparison_status(self, status, if_no_match_add_none=True):
        if status in self.status:
            self.status_for_each_frame_comp.append(status)
        elif if_no_match_add_none:
            self.status_for_each_frame_comp.append(None)

    def load_from_file(self, filename):
        r = super().load_from_file(filename)
        # self.change_str_to_int()
        self.check_frame_order()
        return r
    
    def save_comp_to_file(self, filename:str):
        if not self.status_for_each_frame_comp:
            print('no compare data to save')
        if not self.status_for_each_frame:
            try:
                self.create_status_for_each_frame()
            except:
                print('no saved data there, just save saved_comp data')
                data = self.status_for_each_frame_comp
                
        if self.status_for_each_frame:
            print('saving zip[saveed, saved_comp] data for each frame')
            data = zip(self.status_for_each_frame, self.status_for_each_frame_comp)

        return super().save_to_file(filename, data)

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
        center: the center as a tuple (x, y)
    """
    x_sum = 0
    y_sum = 0
    for index in landmark_indices:
        x_sum += pose_landmarks[index][1]
        y_sum += pose_landmarks[index][2]
    
    center_x = x_sum / len(landmark_indices)
    center_y = y_sum / len(landmark_indices)

    if round_to_int:
        center_x = int(center_x)
        center_y = int(center_y)

    return (center_x, center_y)



from collections import deque

class ValueBuffer:
    """_summary_ 
        A class to store a buffer of elements and calculate the average, most frequently, majority and atleast x of the values in the buffer.
    """

    def __init__(self, buffer_size):
        self.values = deque(maxlen=buffer_size)
        self.last_majority = None # saves the last value that was the majority in the buffer, so that it can be returned if there is no majority in the current buffer

    def add(self, value, update_majority=True):
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
            if self.values.count(value) > len(self.values) / 2:
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

    def atleast(self, min_nr_of_same_elements):
        if not self.values:
            return None

        for value in set(self.values):
            if self.values.count(value) >= min_nr_of_same_elements:
                return value
        
        # if no element nomber exceeds the min_nr_of_same_elements,
        return None
    
    def clear(self):
        self.values.clear()

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


def tolist(list_or_not, keep_none=True):
    if list_or_not is None:
        return None if keep_none else []
    if isinstance(list_or_not, list):
        return list_or_not
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