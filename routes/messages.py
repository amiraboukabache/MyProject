from flask import Blueprint, request, jsonify
from firebase_admin import firestore
import requests
import uuid 
import time
from datetime import datetime, timezone
from config import SUPABASE_URL, SUPABASE_KEY, firestore_db
from routes.activity import log_activity_internal

messages_bp = Blueprint("messages", __name__)


def get_user_from_token(token):
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

def get_token_from_request():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]


@messages_bp.route("/messages", methods=["POST"])
def send_message():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_user_from_token(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    data = request.json

    required_fields = ["receiver_id", "content", "type"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    allowed_types = ["text", "voice", "sign"]
    if data["type"] not in allowed_types:
        return jsonify({"error": f"Type invalide. Choisir parmi : {allowed_types}"}), 400

    message_id = str(uuid.uuid4())
    sender_id = user.get("id")

    message_data = {
        "message_id": message_id,
        "sender_id": sender_id,
        "receiver_id": data["receiver_id"],
        "content": data["content"],
        "type": data["type"],
        "media_url": data.get("media_url", None),
        "status": "sent",
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    }

    try:
        firestore_db.collection("Messages").document(message_id).set(message_data)
        log_activity_internal(sender_id, "send_message")
    except Exception as e:
        return jsonify({"error": "Erreur lors de l'envoi du message", "details": str(e)}), 503

    return jsonify({
        "message": "Message envoyé avec succès",
        "data": message_data
    }), 201


conversation_cache = {}

@messages_bp.route("/messages/<other_user_id>", methods=["GET"])
def get_messages(other_user_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_user_from_token(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    sender_id = user.get("id")

    cache_key = f"{sender_id}_{other_user_id}"
    now = time.time()
    if cache_key in conversation_cache:
        cached_data, cached_time = conversation_cache[cache_key]
        if now - cached_time < 15:
            return jsonify(cached_data), 200

    try:
        sent = firestore_db.collection("Messages")\
            .where("sender_id", "==", sender_id)\
            .where("receiver_id", "==", other_user_id)\
            .stream()

        received = firestore_db.collection("Messages")\
            .where("sender_id", "==", other_user_id)\
            .where("receiver_id", "==", sender_id)\
            .stream()

        messages = []
        for msg in sent:
            messages.append(msg.to_dict())
        for msg in received:
            messages.append(msg.to_dict())

        messages.sort(key=lambda x: x.get("date", ""))
        conversation_cache[cache_key] = (messages, now)

        return jsonify(messages), 200

    except Exception as e:
        if cache_key in conversation_cache:
            cached_data, _ = conversation_cache[cache_key]
            return jsonify(cached_data), 200
        return jsonify({"error": "Service temporairement indisponible. Réessayez dans quelques instants."}), 503


history_cache = {}

@messages_bp.route("/messages/<message_id>", methods=["DELETE"])
def delete_message(message_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_user_from_token(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    sender_id = user.get("id")

    try:
        doc = firestore_db.collection("Messages").document(message_id).get()

        if not doc.exists:
            return jsonify({"error": "Message introuvable"}), 404

        msg_data = doc.to_dict()
        if msg_data.get("sender_id") != sender_id:
            return jsonify({"error": "Vous ne pouvez pas supprimer ce message"}), 403

        firestore_db.collection("Messages").document(message_id).delete()

        keys_to_delete = [k for k in conversation_cache if sender_id in k]
        for k in keys_to_delete:
            del conversation_cache[k]

        keys_to_delete = [k for k in history_cache if k == sender_id]
        for k in keys_to_delete:
            del history_cache[k]

    except Exception as e:
        return jsonify({"error": "Erreur lors de la suppression", "details": str(e)}), 503

    return jsonify({"message": "Message supprimé avec succès"}), 200


@messages_bp.route("/messages/history", methods=["GET"])
def get_history():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_user_from_token(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    user_id = user.get("id")

    cache_key = user_id
    now = time.time()
    if cache_key in history_cache:
        cached_data, cached_time = history_cache[cache_key]
        if now - cached_time < 30:
            return jsonify(cached_data), 200

    try:
        sent = firestore_db.collection("Messages")\
            .where("sender_id", "==", user_id)\
            .stream()

        received = firestore_db.collection("Messages")\
            .where("receiver_id", "==", user_id)\
            .stream()

        messages = []
        for msg in sent:
            messages.append(msg.to_dict())
        for msg in received:
            messages.append(msg.to_dict())

        messages.sort(key=lambda x: x.get("date", ""))
        history_cache[cache_key] = (messages, now)

        if not messages:
            return jsonify({"message": "Aucun historique disponible"}), 200

        return jsonify(messages), 200

    except Exception as e:
        if cache_key in history_cache:
            cached_data, _ = history_cache[cache_key]
            return jsonify(cached_data), 200
        return jsonify({"error": "Service temporairement indisponible. Réessayez dans quelques instants."}), 503