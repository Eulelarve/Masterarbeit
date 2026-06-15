def _get_topmost_wrist(pose_landmarks):
    """
    Gibt die Hand zurück, deren Mittelpunkt
    am weitesten oben im Bild liegt.
    """
    left_wrist_y = pose_landmarks[15][2]
    right_wrist_y = pose_landmarks[16][2]
    
    # smaller y value means higher position in the image
    if left_wrist_y < right_wrist_y: 
        choosen_wrist = 15
    else:
        choosen_wrist = 16

    return choosen_wrist

def choose_wrist(pose_landmarks, left_right_top='top', mirrored=False):
    """ choose between left, right or top wrist based on the pose landmarks
    Args:
        pose_landmarks: list of pose landmarks
        left_right_top: 'left', 'right' or 'top'
        mirrored: if the image is mirrored, left and right are switched
    Returns:
        choosen_wrist: index of the chosen wrist landmark (15 for left, 16 for right)
    
    """
        
    # only the first leter is capital letter, so it is uniform for all spelling options
    left_right_top = left_right_top.capitalize() 
    choosen_wrist = None

    if left_right_top == "Top":
        choosen_wrist = _get_topmost_wrist(pose_landmarks)

    elif left_right_top == "Left":
        choosen_wrist = 15 if not mirrored else 16

    elif left_right_top == "Right":
        choosen_wrist = 16 if not mirrored else 15
    else:
        print(f"Invalid hand selection mode: {left_right_top}. Please choose 'top', 'left' or 'right'.")
    
    return choosen_wrist

