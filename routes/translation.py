from flask import Blueprint, request, jsonify
import requests
import uuid
from datetime import datetime, timezone
from config import SUPABASE_URL, SUPABASE_KEY, firestore_db

translation_bp = Blueprint("translation", __name__)

# ─────────────────────────────────────────
# 🔧 HELPERS
# ─────────────────────────────────────────
def get_token_from_request():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]


def get_current_user(token):
    res = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {token}"
        }
    )
    if res.status_code != 200:
        return None
    return res.json()


# ─────────────────────────────────────────
# ➕ SAUVEGARDER une traduction
# ─────────────────────────────────────────
@translation_bp.route("/translation", methods=["POST"])
def save_translation():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    data = request.json

    required_fields = ["input_content", "output_content", "mode", "source_lang", "target_lang"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    allowed_modes = ["text-to-sign", "sign-to-text"]
    if data["mode"] not in allowed_modes:
        return jsonify({"error": f"Mode invalide. Choisir parmi : {allowed_modes}"}), 400

    translation_id = str(uuid.uuid4())
    user_id = user.get("id")

    translation_data = {
        "translation_id": translation_id,
        "user_id": user_id,
        "input_content": data["input_content"],
        "output_content": data["output_content"],
        "mode": data["mode"],
        "source_lang": data["source_lang"],
        "target_lang": data["target_lang"],
        "is_successful": data.get("is_successful", True),
        "message_id": data.get("message_id", None),
        "mappingData_id": data.get("mappingData_id", None),
        "date": datetime.now(timezone.utc).isoformat()
    }

    firestore_db.collection("Translation").document(translation_id).set(translation_data)

    return jsonify({
        "message": "Traduction sauvegardée avec succès",
        "data": translation_data
    }), 201


# ─────────────────────────────────────────
# 📋 VOIR toutes ses traductions
# ─────────────────────────────────────────
@translation_bp.route("/translation", methods=["GET"])
def get_translations():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    user_id = user.get("id")

    docs = firestore_db.collection("Translation")\
        .where("user_id", "==", user_id)\
        .stream()

    translations = [doc.to_dict() for doc in docs]
    translations.sort(key=lambda x: x.get("date", ""))

    if not translations:
        return jsonify({"message": "Aucune traduction trouvée"}), 200

    return jsonify(translations), 200


# ─────────────────────────────────────────
# 🗑️ SUPPRIMER une traduction
# ─────────────────────────────────────────
@translation_bp.route("/translation/<translation_id>", methods=["DELETE"])
def delete_translation(translation_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    user_id = user.get("id")

    doc = firestore_db.collection("Translation").document(translation_id).get()

    if not doc.exists:
        return jsonify({"error": "Traduction introuvable"}), 404

    if doc.to_dict().get("user_id") != user_id:
        return jsonify({"error": "Vous ne pouvez pas supprimer cette traduction"}), 403

    firestore_db.collection("Translation").document(translation_id).delete()

    return jsonify({"message": "Traduction supprimée avec succès"}), 200


# ─────────────────────────────────────────
# 🤖 PREDICT — Sign language recognition
# ─────────────────────────────────────────
@translation_bp.route("/predict", methods=["POST"])
def predict_sign():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    try:
        import pickle
        import numpy as np
        import os
    except ImportError as e:
        return jsonify({"error": f"Library not available: {str(e)}"}), 500

    data = request.get_json()
    if not data or 'landmarks' not in data:
        return jsonify({"error": "No landmarks provided"}), 400

    try:
        MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gesture_model.pkl')
        with open(MODEL_PATH, 'rb') as f:
            gesture_model = pickle.load(f)

        row = data['landmarks']

        if len(row) != 63:
            return jsonify({"error": f"Expected 63 landmarks, got {len(row)}"}), 400

        row = np.array(row).reshape(1, -1)
        proba = gesture_model.predict_proba(row)[0]
        confidence = float(max(proba))
        prediction = gesture_model.classes_[proba.argmax()]

        if confidence < 0.60:
            return jsonify({
                "prediction": None,
                "confidence": round(confidence, 2),
                "message": "Low confidence"
            })

        return jsonify({
            "prediction": prediction,
            "confidence": round(confidence, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"error": "No image provided"}), 400

    try:
        MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'gesture_model.pkl')
        with open(MODEL_PATH, 'rb') as f:
            gesture_model = pickle.load(f)

        mp_hands = mp.solutions.hands
        hands_detector = mp_hands.Hands(static_image_mode=True, max_num_hands=1)

        img_b64 = data['image']
        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]

        img_bytes = base64.b64decode(img_b64)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            return jsonify({"error": "Image invalide"}), 400

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands_detector.process(frame_rgb)

        if not result.multi_hand_landmarks:
            return jsonify({
                "prediction": None,
                "confidence": 0,
                "message": "No hand detected"
            })

        row = []
        for lm in result.multi_hand_landmarks[0].landmark:
            row.extend([lm.x, lm.y, lm.z])

        proba = gesture_model.predict_proba([row])[0]
        confidence = float(max(proba))
        prediction = gesture_model.classes_[proba.argmax()]

        if confidence < 0.60:
            return jsonify({
                "prediction": None,
                "confidence": round(confidence, 2),
                "message": "Low confidence"
            })

        return jsonify({
            "prediction": prediction,
            "confidence": round(confidence, 2)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500