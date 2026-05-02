import cv2
import mediapipe as mp
import numpy as np
import os

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1)
pose = mp_pose.Pose(static_image_mode=False)

dataset_path = "Data"
output_path = "sequences"
SEQUENCE_LENGTH = 30

os.makedirs(output_path, exist_ok=True)

for gesture in os.listdir(dataset_path):
    gesture_path = os.path.join(dataset_path, gesture)
    if not os.path.isdir(gesture_path):
        continue

    gesture_out = os.path.join(output_path, gesture)
    os.makedirs(gesture_out, exist_ok=True)

    video_count = 0
    for video_file in os.listdir(gesture_path):
        cap = cv2.VideoCapture(os.path.join(gesture_path, video_file))
        frames = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            hand_result = hands.process(frame_rgb)
            pose_result = pose.process(frame_rgb)

            # Hand landmarks (63 values)
            if hand_result.multi_hand_landmarks:
                hand_row = []
                for lm in hand_result.multi_hand_landmarks[0].landmark:
                    hand_row.extend([lm.x, lm.y, lm.z])
            else:
                hand_row = [0.0] * 63

            # Pose landmarks (132 values = 33 points x 4)
            if pose_result.pose_landmarks:
                pose_row = []
                for lm in pose_result.pose_landmarks.landmark:
                    pose_row.extend([lm.x, lm.y, lm.z, lm.visibility])
            else:
                pose_row = [0.0] * 132

            frames.append(hand_row + pose_row)

        cap.release()

        if len(frames) >= SEQUENCE_LENGTH:
            indices = np.linspace(0, len(frames) - 1, SEQUENCE_LENGTH, dtype=int)
            sequence = np.array([frames[i] for i in indices])
            np.save(os.path.join(gesture_out, f"{video_count}.npy"), sequence)
            video_count += 1

    print(f"{gesture}: {video_count} sequences saved")

print("Done! Sequences extracted.")