import cv2
import mediapipe as mp
import numpy as np
import pickle
from tensorflow.keras.models import load_model
from collections import deque, Counter

model = load_model("gesture_lstm.h5")
with open("lstm_labels.pkl", "rb") as f:
    le = pickle.load(f)

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.3,
    min_tracking_confidence=0.3
)
pose = mp_pose.Pose()

cap = cv2.VideoCapture(0)

SEQUENCE_LENGTH = 30
sequence = deque(maxlen=SEQUENCE_LENGTH)
prediction_history = deque(maxlen=10)
stable_prediction = ""
confidence_val = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    hand_result = hands.process(frame_rgb)
    pose_result = pose.process(frame_rgb)

    # Hand landmarks
    if hand_result.multi_hand_landmarks:
        for hand_landmarks in hand_result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        hand_row = []
        for lm in hand_result.multi_hand_landmarks[0].landmark:
            hand_row.extend([lm.x, lm.y, lm.z])
    else:
        hand_row = [0.0] * 63

    # Pose landmarks
    if pose_result.pose_landmarks:
        pose_row = []
        for lm in pose_result.pose_landmarks.landmark:
            pose_row.extend([lm.x, lm.y, lm.z, lm.visibility])
    else:
        pose_row = [0.0] * 132

    sequence.append(hand_row + pose_row)

    if len(sequence) == SEQUENCE_LENGTH:
        input_data = np.expand_dims(list(sequence), axis=0)
        proba = model.predict(input_data, verbose=0)[0]
        confidence_val = max(proba)
        current_prediction = le.classes_[np.argmax(proba)]

        prediction_history.append(current_prediction)

        most_common, count = Counter(prediction_history).most_common(1)[0]
        if count >= 7:
            stable_prediction = most_common

    if stable_prediction:
        cv2.putText(frame, f"{stable_prediction} ({int(confidence_val*100)}%)",
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

    cv2.imshow("Gesture Recognition - LSTM", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()