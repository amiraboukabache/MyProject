from flask import Blueprint, request, jsonify
import requests
from datetime import datetime
from config import SUPABASE_URL, SUPABASE_KEY, db_headers, auth_headers, firestore_db

admin_bp = Blueprint("admin", __name__)


# ─────────────────────────────────────────
#  HELPERS
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

def is_admin(token):
    user = get_current_user(token)
    if not user:
        return False
    user_id = user.get("id")
    profile_res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=role",
        headers=db_headers
    )
    profiles = profile_res.json()
    if not profiles:
        return False
    return profiles[0].get("role") == "admin"

def log_activity(user_id, action):
    firestore_db.collection("UserActivity").add({
        "user_id": user_id,
        "action": action,
        "date": datetime.utcnow().isoformat() + "+00:00"
    })


# ─────────────────────────────────────────
#  ADMIN — Voir tous les utilisateurs
# ─────────────────────────────────────────
@admin_bp.route("/admin/users", methods=["GET"])
def admin_get_users():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?select=*",
        headers=db_headers
    )
    return jsonify(res.json()), 200


# ─────────────────────────────────────────
#  ADMIN — Voir un utilisateur
# ─────────────────────────────────────────
@admin_bp.route("/admin/users/<user_id>", methods=["GET"])
def admin_get_user(user_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=*",
        headers=db_headers
    )
    users = res.json()
    if not users:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    return jsonify(users[0]), 200


# ─────────────────────────────────────────
#  ADMIN — Ajouter un utilisateur
# ─────────────────────────────────────────
@admin_bp.route("/admin/users", methods=["POST"])
def admin_add_user():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    data = request.json
    required_fields = ["email", "password", "name", "lastname", "role"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    auth_res = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={"email": data["email"], "password": data["password"]},
        headers=auth_headers
    )
    auth_data = auth_res.json()

    if auth_res.status_code not in (200, 201):
        return jsonify({"error": "Échec création compte", "details": auth_data}), 400

    user_id = auth_data.get("user", auth_data).get("id")
    if not user_id:
        return jsonify({"error": "Impossible de récupérer l'ID", "details": auth_data}), 400

    db_res = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        json={
            "user_id": user_id,
            "name": data["name"],
            "lastname": data["lastname"],
            "email": data["email"],
            "role": data["role"]
        },
        headers=db_headers
    )

    if db_res.status_code not in (200, 201):
        return jsonify({"error": "Compte créé mais échec insertion", "details": db_res.json()}), 400

    # ✅ Log activity
    log_activity(user_id, "create_account")

    return jsonify({
        "message": "Utilisateur ajouté avec succès",
        "user_id": user_id,
        "profile": db_res.json()
    }), 201


# ─────────────────────────────────────────
#  ADMIN — Supprimer un utilisateur
# ─────────────────────────────────────────
@admin_bp.route("/admin/users/<user_id>", methods=["DELETE"])
def admin_delete_user(user_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    db_res = requests.delete(
        f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}",
        headers=db_headers
    )
    if db_res.status_code not in (200, 204):
        return jsonify({"error": "Échec suppression profil"}), 400

    requests.delete(
        f"{SUPABASE_URL}/auth/v1/admin/users/{user_id}",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    )

    # ✅ Log activity
    log_activity(user_id, "delete_user")

    return jsonify({"message": f"Utilisateur {user_id} supprimé avec succès"}), 200


# ─────────────────────────────────────────
#  ADMIN — Modifier un utilisateur
# ─────────────────────────────────────────
@admin_bp.route("/admin/users/<user_id>", methods=["PATCH"])
def admin_update_user(user_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    data = request.json
    if not data:
        return jsonify({"error": "Aucune donnée envoyée"}), 400

    allowed_fields = ["name", "lastname", "role"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "Aucun champ valide à modifier"}), 400

    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}",
        json=update_data,
        headers=db_headers
    )

    if res.status_code not in (200, 204):
        return jsonify({"error": "Échec modification", "details": res.json()}), 400

    # ✅ Log activity
    log_activity(user_id, "update_user")

    return jsonify({
        "message": f"Utilisateur {user_id} modifié avec succès",
        "updated": update_data
    }), 200


# ─────────────────────────────────────────
#  ADMIN — Activité utilisateurs
# ─────────────────────────────────────────
@admin_bp.route("/admin/activity", methods=["GET"])
def admin_get_activity():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    docs = firestore_db.collection("UserActivity").order_by(
        "date", direction="DESCENDING"
    ).limit(50).stream()

    activities = []
    for doc in docs:
        d = doc.to_dict()
        d["activity_id"] = doc.id
        activities.append(d)

    return jsonify(activities), 200