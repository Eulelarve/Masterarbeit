import ctypes

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

    def save_to_file(self, filename):
        if not self.saved:
            print("No status to save.")
            return
        with open(filename, 'w') as f:
            for item in self.saved:
                f.write(f"{item}\n")
            print(f"Saved {len(self.saved)} status to {filename}.")
    
    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            self.saved = [line.strip() for line in f]
    
    def get(self, index):
        if index < len(self.saved):
            return self.saved[index]
        else:
            return None

class SaveFrameStatus(CaptureStatus):
    
    def add(self, start_frame, key, print_out=True):
        if key in self.keys:
            i = self.keys.index(key)
            add = [start_frame, self.status[i]]
            self.saved.append(add)
            if print_out:
                print('Frame', start_frame, '-', self.status[i])



def fit_frameregion_landmoars_to_frame(landmarks, pixel_frame_size, pixel_region_x_y_w_h):
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

def get_upper_hand_center(pose_landmarks):
    """
    gives the center of the hand that is higher in the image, based on the average y value of the pose landmarks.
    returns the right hand center if both hands are at the same height.
    Args:
        pose_landmarks: list of pose landmarks
    Returns:
        hand_center: the hand center as a tuple (x, y)
    """
    y_left_hand_center = (
        # pose_landmarks[15][2] +
        pose_landmarks[17][2] +
        pose_landmarks[19][2] 
        # + pose_landmarks[21][2]
        )

    y_right_hand_center = (
        # pose_landmarks[16][2] +
        pose_landmarks[18][2] +
        pose_landmarks[20][2] 
        # + pose_landmarks[22][2]
    )
    
    # smaller y value means higher position in the image
    if y_left_hand_center < y_right_hand_center: 
        # hand_points = [15, 17, 19, 21] # left hand landmarks from mediapipe pose
        hand_points = [ 17, 19] # landmarks ID of pinky start and index finger start
    else:
        # hand_points = [16, 18, 20, 22] # right hand landmarks from mediapipe pose
        hand_points = [18, 20] # landmarks ID of pinky start and index finger start

    return get_center_of_landmarks(pose_landmarks, hand_points)

def get_hand_center(pose_landmarks, left_right_top='top', mirrored=False):
    """ choose between left, right or top hand based on the pose landmarks
    Args:
        pose_landmarks: list of pose landmarks
        left_right_top: 'left', 'right' or 'top'
        mirrored: if the image is mirrored, left and right are switched
    Returns:
        hand_center: index of the chosen wrist landmark (15 for left, 16 for right)
    
    """
        
    # only the first leter is capital letter, so it is uniform for all spelling options
    left_right_top = left_right_top.capitalize() 
    hand_center = None
    left_hand_points = [15, 17, 19, 21] # left hand landmarks from mediapipe pose
    right_hand_points = [16, 18, 20, 22] # right hand landmarks from mediapipe pose

    if left_right_top == "Top":
        hand_center = get_upper_hand_center(pose_landmarks)

    elif left_right_top == "Left":
        hand_points = left_hand_points if not mirrored else right_hand_points
        hand_center = get_center_of_landmarks(pose_landmarks, hand_points)

    elif left_right_top == "Right":
        hand_points = right_hand_points if not mirrored else left_hand_points
        hand_center = get_center_of_landmarks(pose_landmarks, hand_points)
    else:
        print(f"Invalid hand selection mode: {left_right_top}. Please choose 'top', 'left' or 'right'.")
    
    return hand_center


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
    
    def atleast(self, min_nr_of_same_elements):
        if not self.values:
            return None

        for value in set(self.values):
            if self.values.count(value) >= min_nr_of_same_elements:
                return value
        
        # if no element nomber exceeds the min_nr_of_same_elements,
        return None

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

    def __init__(self, smoothing_len=5, buffer_size=10, lost_hand_counter=40, 
                 open_threshold = 70, 
                 close_threshold = 60 ):
        self.smoothed_aperture = ValueBuffer(smoothing_len)
        self.hand_status_buffer = ValueBuffer(buffer_size)
        self.lost_hand_by = lost_hand_counter
        self.open_threshold = open_threshold
        self.close_threshold = close_threshold

        self.open_status = {'text':"open", 'color':(0,0,255)}
        self.close_status = {'text':"closed", 'color':(255,0,0)}
        self.no_hand_status = {'text':"no hand", 'color':(255,255,0)}
        
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
