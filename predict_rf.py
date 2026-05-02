import cv2
import mediapipe as mp
import pickle
from collections import deque, Counter

with open('gesture_model.pkl', 'rb') as f:
    model = pickle.load(f)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands()

cap = cv2.VideoCapture(0)

prediction_history = deque(maxlen=10)
stable_prediction = ''
confidence_val = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)

    if result.multi_hand_landmarks:
        for hand_landmarks in result.multi_hand_landmarks:
            mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        row = []
        for lm in result.multi_hand_landmarks[0].landmark:
            row.extend([lm.x, lm.y, lm.z])

        proba = model.predict_proba([row])[0]
        confidence_val = max(proba)
        current_prediction = model.classes_[proba.argmax()]

        prediction_history.append(current_prediction)
        most_common, count = Counter(prediction_history).most_common(1)[0]
        if count >= 5:
            stable_prediction = most_common

    if stable_prediction:
        cv2.putText(frame, f'{stable_prediction} ({int(confidence_val*100)}%)',
                    (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)

    cv2.imshow('Gesture Recognition', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()