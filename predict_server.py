from flask import Flask, request, jsonify
from flask_cors import CORS
import pickle
import numpy as np

app = Flask(__name__)
CORS(app)

with open('gesture_model.pkl', 'rb') as f:
    model = pickle.load(f)

@app.route('/predict', methods=['POST'])
def predict():
    data = request.get_json()
    landmarks = data.get('landmarks')
    
    if not landmarks:
        return jsonify({"prediction": None, "message": "No landmarks"})

    proba = model.predict_proba([landmarks])[0]
    confidence = float(max(proba))
    prediction = model.classes_[proba.argmax()]

    if confidence < 0.60:
        return jsonify({"prediction": None, "confidence": round(confidence, 2), "message": "Low confidence"})

    return jsonify({"prediction": prediction, "confidence": round(confidence, 2)})

if __name__ == '__main__':
    app.run(port=5000)