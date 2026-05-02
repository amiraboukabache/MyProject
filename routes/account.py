from flask import Blueprint, request, jsonify
import requests
import uuid
from datetime import datetime, timezone
from config import SUPABASE_URL, SUPABASE_KEY, db_headers

account_bp = Blueprint("account", __name__)


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
# ➕ CRÉER un compte
# ─────────────────────────────────────────
@account_bp.route("/account", methods=["POST"])
def create_account():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    owner_id = user.get("id")

    # Vérifier si un compte existe déjà
    existing = requests.get(
        f"{SUPABASE_URL}/rest/v1/account?owner_id=eq.{owner_id}&select=*",
        headers=db_headers
    )
    if existing.json():
        return jsonify({"error": "Un compte existe déjà pour cet utilisateur"}), 400

    account_id = str(uuid.uuid4())

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/account",
        json={
            "account_id": account_id,
            "creation_date": datetime.now(timezone.utc).isoformat(),
            "status": "active",
            "owner_id": owner_id
        },
        headers=db_headers
    )

    if res.status_code not in (200, 201):
        return jsonify({
            "error": "Échec de la création du compte",
            "details": res.json()
        }), 400

    return jsonify({
        "message": "Compte créé avec succès",
        "data": res.json()
    }), 201


# ─────────────────────────────────────────
# 👤 VOIR son compte
# ─────────────────────────────────────────
@account_bp.route("/account", methods=["GET"])
def get_account():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    owner_id = user.get("id")

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/account?owner_id=eq.{owner_id}&select=*",
        headers=db_headers
    )

    accounts = res.json()
    if not accounts:
        return jsonify({"error": "Aucun compte trouvé"}), 404

    return jsonify(accounts[0]), 200


# ─────────────────────────────────────────
# ✏️ MODIFIER son compte
# ─────────────────────────────────────────
@account_bp.route("/account", methods=["PATCH"])
def update_account():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    owner_id = user.get("id")
    data = request.json

    if not data:
        return jsonify({"error": "Aucune donnée envoyée"}), 400

    allowed_fields = ["status"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}

    if not update_data:
        return jsonify({"error": "Aucun champ valide à modifier"}), 400

    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/account?owner_id=eq.{owner_id}",
        json=update_data,
        headers=db_headers
    )

    if res.status_code not in (200, 204):
        return jsonify({"error": "Échec de la modification", "details": res.json()}), 400

    return jsonify({
        "message": "Compte modifié avec succès",
        "updated": update_data
    }), 200


# ─────────────────────────────────────────
# 🗑️ SUPPRIMER son compte
# ─────────────────────────────────────────
@account_bp.route("/account", methods=["DELETE"])
def delete_account():
    token = get_token_from_request()
    if not token:

        return jsonify({"error": "Token manquant"}), 401

    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401

    owner_id = user.get("id")

    res = requests.delete(
        f"{SUPABASE_URL}/rest/v1/account?owner_id=eq.{owner_id}",
        headers=db_headers
    )

    if res.status_code not in (200, 204):
        return jsonify({"error": "Échec de la suppression"}), 400

    return jsonify({"message": "Compte supprimé avec succès"}), 200