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