from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import numpy as np
import mediapipe as mp
import cv2
import base64

app = Flask(__name__)
CORS(app)

with open('gesture_model.pkl', 'rb') as f:
    model = pickle.load(f)

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=True, max_num_hands=1)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    img_b64 = data['image']
    if ',' in img_b64:
        img_b64 = img_b64.split(',')[1]

    img_bytes = base64.b64decode(img_b64)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)

    if not result.multi_hand_landmarks:
        return jsonify({"prediction": None, "confidence": 0, "message": "No hand detected"})

    row = []
    for lm in result.multi_hand_landmarks[0].landmark:
        row.extend([lm.x, lm.y, lm.z])

    proba = model.predict_proba([row])[0]
    confidence = float(max(proba))
    prediction = model.classes_[proba.argmax()]

    if confidence < 0.60:
        return jsonify({"prediction": None, "confidence": round(confidence, 2), "message": "Low confidence"})

    return jsonify({"prediction": prediction, "confidence": round(confidence, 2)})

if __name__ == '__main__':
    app.run(port=5000)