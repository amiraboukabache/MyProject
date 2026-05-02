from flask import Blueprint, request, jsonify
import requests
from config import SUPABASE_URL, SUPABASE_KEY, db_headers

profile_bp = Blueprint("profile", __name__)


def get_current_user(token):
    """Récupère l'utilisateur depuis le token JWT"""
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
# 👤 GET PROFILE
# ─────────────────────────────────────────
@profile_bp.route("/profile", methods=["GET"])
def get_profile():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token manquant"}), 401

    token = auth_header.split(" ")[1]

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    user_id = user.get("id")

    profile_res = requests.get(
        f"{SUPABASE_URL}/rest/v1/users?user_id=eq.{user_id}&select=*",
        headers=db_headers
    )

    profiles = profile_res.json()
    if not profiles:
        return jsonify({"error": "Profil introuvable"}), 404

    return jsonify(profiles[0]), 200


# ─────────────────────────────────────────
# 👥 GET USERS (filtrer par rôle)
# ─────────────────────────────────────────
@profile_bp.route("/users", methods=["GET"])
def get_users():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Token manquant"}), 401

    token = auth_header.split(" ")[1]

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    # Filtrer par rôle si spécifié
    role = request.args.get("role")

    if role:
        url = f"{SUPABASE_URL}/rest/v1/users?role=eq.{role}&select=user_id,name,lastname,role"
    else:
        url = f"{SUPABASE_URL}/rest/v1/users?select=user_id,name,lastname,role"

    res = requests.get(url, headers=db_headers)

    # Exclure l'utilisateur connecté de la liste
    current_user_id = user.get("id")
    users = [u for u in res.json() if u.get("user_id") != current_user_id]

    return jsonify(users), 200