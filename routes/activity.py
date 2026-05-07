from flask import Blueprint, request, jsonify
import requests
import uuid
from datetime import datetime, timezone
from config import SUPABASE_URL, SUPABASE_KEY, firestore_db

activity_bp = Blueprint("activity", __name__)


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
# ✅ HELPER INTERNE — appelé depuis d'autres routes
# ─────────────────────────────────────────
def log_activity_internal(user_id, action):
    try:
        activity_id = str(uuid.uuid4())
        firestore_db.collection("UserActivity").document(activity_id).set({
            "activity_id": activity_id,
            "user_id": user_id,
            "action": action,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        })
    except Exception as e:
        print(f"❌ log_activity_internal ERREUR: {e}")


# ─────────────────────────────────────────
# ➕ ENREGISTRER une activité
# ─────────────────────────────────────────
@activity_bp.route("/activity", methods=["POST"])
def save_activity():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    data = request.json

    if not data.get("action"):
        return jsonify({"error": "Champ manquant : action"}), 400

    user_id = user.get("id")
    log_activity_internal(user_id, data["action"])

    return jsonify({
        "message": "Activité enregistrée avec succès"
    }), 201


# ─────────────────────────────────────────
# 📋 VOIR toutes ses activités
# ─────────────────────────────────────────
@activity_bp.route("/activity", methods=["GET"])
def get_activities():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    user_id = user.get("id")

    docs = firestore_db.collection("UserActivity")\
        .where("user_id", "==", user_id)\
        .stream()

    activities = []
    for doc in docs:
        d = doc.to_dict()
        date_val = d.get("date")
        if hasattr(date_val, "ToDatetime"):
            d["date"] = date_val.ToDatetime(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif hasattr(date_val, "strftime"):
            if date_val.tzinfo is None:
                date_val = date_val.replace(tzinfo=timezone.utc)
            d["date"] = date_val.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif isinstance(date_val, str):
            d["date"] = date_val
        else:
            d["date"] = ""
        activities.append(d)

    activities.sort(key=lambda x: x.get("date") or "", reverse=True)

    if not activities:
        return jsonify({"message": "Aucune activité trouvée"}), 200

    return jsonify(activities), 200


# ─────────────────────────────────────────
# 👑 ADMIN — Voir toutes les activités
# ─────────────────────────────────────────
@activity_bp.route("/admin/activity", methods=["GET"])
def get_all_activities():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    from config import db_headers
    user_id = user.get("id")
    profile_res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=role",
        headers=db_headers
    )
    profiles = profile_res.json()
    if not profiles or profiles[0].get("role") != "admin":
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    docs = firestore_db.collection("UserActivity").stream()
    activities = []
    for doc in docs:
        d = doc.to_dict()
        date_val = d.get("date")
        if hasattr(date_val, "ToDatetime"):
            d["date"] = date_val.ToDatetime(tzinfo=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif hasattr(date_val, "strftime"):
            if date_val.tzinfo is None:
                date_val = date_val.replace(tzinfo=timezone.utc)
            d["date"] = date_val.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        elif isinstance(date_val, str):
            d["date"] = date_val
        else:
            d["date"] = ""
        activities.append(d)

    activities.sort(key=lambda x: x.get("date") or "", reverse=True)

    return jsonify(activities), 200