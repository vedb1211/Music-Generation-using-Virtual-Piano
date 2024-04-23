import cv2
import mediapipe as mp
import pygame
import math
import sys
import os

# Disable oneDNN custom operations
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

# Function to get the correct path for resources
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# Initialize Pygame for sound and load sound files
pygame.mixer.init()

# Dictionary to map piano keys to their corresponding sound files
sound_files = {
    key: resource_path(f'piano_sounds/{key}.wav') for key in 
    ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C#', 'D#', 'F#', 'G#', 'A#', 'C2', 'D2', 'E2', 'F2', 'G2', 'A2', 'B2', 'C#2', 'D#2', 'F#2', 'G#2', 'A#2']
}
sounds = {}
for key, file in sound_files.items():
    if key != '':
        sound = pygame.mixer.Sound(file)
        sound.set_volume(0.1)
        sounds[key] = sound

# MediaPipe hands setup
mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils
hands = mp_hands.Hands(min_detection_confidence=0.8, min_tracking_confidence=0.8)

# OpenCV setup for webcam capture
cap = cv2.VideoCapture(0)
_, test_image = cap.read()
image_height, image_width, _ = test_image.shape

# Piano visualizer settings
white_keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C2', 'D2', 'E2', 'F2', 'G2', 'A2', 'B2']
white_key_width = image_width // len(white_keys)
white_key_height = 180  

# Piano visualizer settings - black keys
black_keys = ['C#', 'D#', '', 'F#', 'G#', 'A#', '', 'C#2', 'D#2', '', 'F#2', 'G#2', 'A#2', '']
black_key_width = int(white_key_width * 0.6)  
black_key_height = int(white_key_height * 0.6)

# Calculate the total width of the piano to center it
total_piano_width = len(white_keys) * white_key_width
piano_start_x = (image_width - total_piano_width) // 2  
piano_y = 5

# List to store the position of black keys in relation to each white key
# R = Black key on right, L = Black key on left, D = Black keys on both sides
black_to_white_key_relation = ['R', 'D', 'L', 'R', 'D', 'D', 'L', 'R', 'D', 'L', 'R', 'D', 'D', 'L']

# Initialize a dictionary to track key states and press timestamps
key_states = {
    key: {"pressed": False} for key in (white_keys + black_keys if '' not in black_keys else white_keys + [k for k in black_keys if k])
}

# Initialize a dictionary to track which finger is pressing which key
key_pressed = {"Right":{
                    "Thumb":[], 
                    "Index":[], 
                    "Middle":[], 
                    "Ring":[], 
                    "Pinky":[]
                },

                "Left":{
                    "Thumb":[], 
                    "Index":[], 
                    "Middle":[], 
                    "Ring":[], 
                    "Pinky":[]
                }
}

# Function to calculate angle between three points
def calculate_angle(landmark1, landmark2, landmark3):
    numerator = (landmark2.y - landmark1.y) * (landmark2.y - landmark3.y) + (landmark2.x - landmark1.x) * (landmark2.x - landmark3.x)
    denominator = math.sqrt((landmark2.y - landmark1.y)**2 + (landmark2.x - landmark1.x)**2) * math.sqrt((landmark2.y - landmark3.y)**2 + (landmark2.x - landmark3.x)**2)
    angle = math.acos(numerator / denominator)
    angle = abs(math.degrees(angle))
    if angle > 180:
        angle = 360 - angle
    return angle


# Function to determine if a finger is bent
def is_finger_bent(landmarks, finger_name):
    # Define finger joints
    finger_joints = {
        "Thumb": [mp_hands.HandLandmark.THUMB_CMC, mp_hands.HandLandmark.THUMB_MCP, mp_hands.HandLandmark.THUMB_TIP],
        "Index": [mp_hands.HandLandmark.INDEX_FINGER_MCP, mp_hands.HandLandmark.INDEX_FINGER_PIP, mp_hands.HandLandmark.INDEX_FINGER_DIP],
        "Middle": [mp_hands.HandLandmark.MIDDLE_FINGER_MCP, mp_hands.HandLandmark.MIDDLE_FINGER_PIP, mp_hands.HandLandmark.MIDDLE_FINGER_DIP],
        "Ring": [mp_hands.HandLandmark.RING_FINGER_MCP, mp_hands.HandLandmark.RING_FINGER_PIP, mp_hands.HandLandmark.RING_FINGER_DIP],
        "Pinky": [mp_hands.HandLandmark.PINKY_MCP, mp_hands.HandLandmark.PINKY_PIP, mp_hands.HandLandmark.PINKY_DIP]
    }

    angle = calculate_angle(landmarks[finger_joints[finger_name][0]],
                            landmarks[finger_joints[finger_name][1]],
                            landmarks[finger_joints[finger_name][2]])

    # Different threshold angles for bending in different fingers
    threshold = {
        "Thumb": 169,
        "Index": 160,
        "Middle": 160,
        "Ring": 155,
        "Pinky": 160
    }

    return ((angle < threshold[finger_name]) and (angle>90))

# Function to highlight keys when pressed
def highlight_key(image, key, key_x, key_width, key_height, is_black_key=False, black_key_right=False, black_key_left=False):
    """Highlights a key and plays its sound."""
    highlight_color = (80, 200, 120) if not is_black_key else (255, 0, 0)
    border_color = (0, 0, 0) 

    # Highlight white keys
    if not is_black_key:
        # Bottom part of key
        cv2.rectangle(image, (int(key_x), int(piano_y + black_key_height)), (int(key_x + key_width), int(piano_y + key_height)), highlight_color, cv2.FILLED)

        if black_key_left:
            white_key_top_highlight_start = int(key_x + (black_key_width/2))
            left_border_start = int(piano_y + black_key_height)
        else:
            white_key_top_highlight_start = int(key_x)
            left_border_start = int(piano_y)
        
        if black_key_right:
            white_key_top_highlight_end = int(key_x + key_width - (black_key_width/2))
            right_border_start = int(piano_y + black_key_height)
        else:
            white_key_top_highlight_end = int(key_x + key_width)
            right_border_start = int(piano_y)

        # Top part of key
        cv2.rectangle(image, (white_key_top_highlight_start, int(piano_y)), (white_key_top_highlight_end, int(piano_y + black_key_height)), highlight_color, cv2.FILLED)

        # Top Border
        cv2.line(image, (white_key_top_highlight_start, int(piano_y)), (white_key_top_highlight_end, int(piano_y)), border_color, 4)
        
        # Bottom Border
        cv2.line(image, (int(key_x), int(piano_y + key_height)), (int(key_x + key_width), int(piano_y + key_height)), border_color, 4)
        
        # Left Border
        cv2.line(image, (int(key_x), left_border_start), (int(key_x), int(piano_y + key_height)), border_color, 4)

        # Right Border
        cv2.line(image, (int(key_x + key_width), right_border_start), (int(key_x + key_width), int(piano_y + key_height)), border_color, 4)

    # Highlight black keys
    else:
        cv2.rectangle(image, (int(key_x), int(piano_y)), (int(key_x + key_width), int(piano_y + key_height)), highlight_color, cv2.FILLED)
        cv2.rectangle(image, (int(key_x), int(piano_y)), (int(key_x + key_width), int(piano_y + key_height)), border_color, 4)

    if key in sounds:
        if not key_states[key]["pressed"]:
            print(f"Playing {key}")
            sounds[key].play()
            key_states[key] = {"pressed": True}


while cap.isOpened():
    success, image = cap.read()
    if not success:
        # print("Ignoring empty camera frame.")
        continue

    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
    results = hands.process(image)

    # Draw piano keys
    for i in range(len(white_keys)):
        key_x = piano_start_x + i * white_key_width
        cv2.rectangle(image, (key_x, piano_y), (key_x + white_key_width, piano_y + white_key_height), (255, 255, 255), -1)
        cv2.rectangle(image, (key_x, piano_y), (key_x + white_key_width, piano_y + white_key_height), (0, 0, 0), 1)

    for i, key in enumerate(black_keys):
        if key:
            key_x = piano_start_x + (i * white_key_width) + int(white_key_width - (black_key_width / 2))
            cv2.rectangle(image, (int(key_x), piano_y), (int(key_x + black_key_width), piano_y + black_key_height), (0, 0, 0), -1)

    # Highlight keys and play sound on finger press
    if results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Determine if the hand is left or right
            hand_label = "Right" if handedness.classification[0].label == "Right" else "Left"

            # Convert landmarks to a list for easier access
            landmarks = [landmark for landmark in hand_landmarks.landmark]

            # Finger tips index for "Thumb", "Index", "Middle", "Ring", "Pinky"
            finger_tips_indices = [4, 8, 12, 16, 20]

            # Check for bent fingers and process each bent finger individually
            for finger_index, finger_name in enumerate(["Thumb", "Index", "Middle", "Ring", "Pinky"]):
                if is_finger_bent(landmarks, finger_name):
                    tip_index = finger_tips_indices[finger_index]
                    tip = hand_landmarks.landmark[tip_index]
                    finger_tip_x, finger_tip_y = int(tip.x * image_width), int(tip.y * image_height)

                    black_key_pressed = False
                    # Check for black key presses
                    for i, key in enumerate(black_keys):
                        if key:  # Skip empty placeholder for black keys
                            black_key_x_start = piano_start_x + i * white_key_width + (white_key_width - (black_key_width / 2))
                            black_key_x_end = black_key_x_start + black_key_width
                                
                            if black_key_x_start < finger_tip_x < black_key_x_end and piano_y < finger_tip_y < (piano_y + black_key_height):
                                highlight_key(image, key, int(black_key_x_start), black_key_width, black_key_height, is_black_key=True)
                                key_pressed[hand_label][finger_name].append(key)
                                black_key_pressed = True
                                break  # Break if a black key press is detected to avoid white key overlap

                    # Check for white key presses if no black key was pressed
                    if not black_key_pressed:
                        for i, key in enumerate(white_keys):
                            white_key_x_start = piano_start_x + i * white_key_width
                            white_key_x_end = white_key_x_start + white_key_width

                            if black_to_white_key_relation[i] == 'R':
                                black_key_right = True
                                black_key_left = False

                            elif black_to_white_key_relation[i] == 'L':
                                black_key_right = False
                                black_key_left = True

                            else:
                                black_key_right = True
                                black_key_left = True
                                
                            if white_key_x_start < finger_tip_x < white_key_x_end and piano_y < finger_tip_y < (piano_y + white_key_height):
                                highlight_key(image, key, white_key_x_start, white_key_width, white_key_height, is_black_key=False, black_key_right=black_key_right, black_key_left=black_key_left)
                                key_pressed[hand_label][finger_name].append(key)
                                break

                else:
                    # Check if finger has recently pressed any keys
                    key_list = key_pressed[hand_label][finger_name]
                    if key_list:
                        for key in key_list:
                            # Reset state of keys
                            key_states[key] = {"pressed": False}
                                        
                        # Reset pressed key list for finger
                        key_list.clear()

            # Landmark tracking for hands
            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
    
    # Name of application and exit mechanism
    cv2.imshow('Air Piano UI', cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

hands.close()
cap.release()
cv2.destroyAllWindows()