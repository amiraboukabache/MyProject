import cv2
import mediapipe as mp
import csv
import os

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1)

dataset_path = "Data"
output_csv = "landmarks.csv"

with open(output_csv, "w", newline="") as f:
    writer = csv.writer(f)
    # 21 landmarks x 3 values (x, y, z) = 63 columns + label
    header = [f"{axis}{i}" for i in range(21) for axis in ["x", "y", "z"]] + ["label"]
    writer.writerow(header)

    for gesture in os.listdir(dataset_path):
        gesture_path = os.path.join(dataset_path, gesture)
        if not os.path.isdir(gesture_path):
            continue

        for video_file in os.listdir(gesture_path):
            cap = cv2.VideoCapture(os.path.join(gesture_path, video_file))

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(frame_rgb)

                if result.multi_hand_landmarks:
                    for hand_landmarks in result.multi_hand_landmarks:
                        row = []
                        for lm in hand_landmarks.landmark:
                            row.extend([lm.x, lm.y, lm.z])
                        row.append(gesture)
                        writer.writerow(row)

            cap.release()

print("Done! landmarks.csv created.")