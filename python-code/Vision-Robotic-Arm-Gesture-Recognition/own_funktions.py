# from copy import deepcopy

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
