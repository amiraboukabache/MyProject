from flask import Blueprint, request, jsonify
import requests
import uuid
from config import SUPABASE_URL, SUPABASE_KEY, db_headers

mappingdata_bp = Blueprint("mappingdata", __name__)


def get_token_from_request():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    return auth_header.split(" ")[1]


def get_current_user(token):
    res = requests.get(
        f"{SUPABASE_URL}/auth/v1/user",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {token}"}
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


# ─────────────────────────────────────────
# 📋 VOIR tous les mappings
# ─────────────────────────────────────────
@mappingdata_bp.route("/mappingdata", methods=["GET"])
def get_mappingdata():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    user = get_current_user(token)
    if not user:
        return jsonify({"error": "Token invalide"}), 401
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/mappingdata?select=*",
        headers=db_headers
    )
    return jsonify(res.json()), 200


# ─────────────────────────────────────────
# 🔍 RECHERCHER un mapping par texte
# ─────────────────────────────────────────
@mappingdata_bp.route("/mappingdata/search", methods=["GET"])
def search_mappingdata():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401

    text = request.args.get("text", "").strip().lower()
    if not text:
        return jsonify({"error": "Texte manquant"}), 400

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/mappingdata?text_content=ilike.*{text}*&select=*&limit=1",
        headers=db_headers
    )
    data = res.json()

    if not data:
        return jsonify({"content_url": None, "message": "Aucun signe trouvé"}), 200

    return jsonify({
        "content_url": data[0]["content_url"],
        "text_content": data[0]["text_content"]
    }), 200


# ─────────────────────────────────────────
# ➕ AJOUTER un mapping (admin seulement)
# ─────────────────────────────────────────
@mappingdata_bp.route("/mappingdata", methods=["POST"])
def add_mappingdata():
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    data = request.json
    required_fields = ["text_content", "content_url"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    user = get_current_user(token)
    admin_id = user.get("id")
    mappingdata_id = str(uuid.uuid4())

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/mappingdata",
        json={
            "mappingdata_id": mappingdata_id,
            "text_content": data["text_content"],
            "content_url": data["content_url"],
            "admin_id": admin_id
        },
        headers=db_headers
    )
    if res.status_code not in (200, 201):
        return jsonify({"error": "Échec de l'ajout", "details": res.json()}), 400

    return jsonify({"message": "Mapping ajouté avec succès", "data": res.json()}), 201


# ─────────────────────────────────────────
# ✏️ MODIFIER un mapping (admin seulement)
# ─────────────────────────────────────────
@mappingdata_bp.route("/mappingdata/<mappingdata_id>", methods=["PATCH"])
def update_mappingdata(mappingdata_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    data = request.json
    if not data:
        return jsonify({"error": "Aucune donnée envoyée"}), 400

    allowed_fields = ["text_content", "content_url"]
    update_data = {k: v for k, v in data.items() if k in allowed_fields}
    if not update_data:
        return jsonify({"error": "Aucun champ valide à modifier"}), 400

    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/mappingdata?mappingdata_id=eq.{mappingdata_id}",
        json=update_data,
        headers=db_headers
    )
    if res.status_code not in (200, 204):
        return jsonify({"error": "Échec de la modification", "details": res.json()}), 400

    return jsonify({"message": f"Mapping {mappingdata_id} modifié", "updated": update_data}), 200


# ─────────────────────────────────────────
# 🗑️ SUPPRIMER un mapping (admin seulement)
# ─────────────────────────────────────────
@mappingdata_bp.route("/mappingdata/<mappingdata_id>", methods=["DELETE"])
def delete_mappingdata(mappingdata_id):
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Token manquant"}), 401
    if not is_admin(token):
        return jsonify({"error": "Accès refusé — admin seulement"}), 403

    res = requests.delete(
        f"{SUPABASE_URL}/rest/v1/mappingdata?mappingdata_id=eq.{mappingdata_id}",
        headers=db_headers
    )
    if res.status_code not in (200, 204):
        return jsonify({"error": "Échec de la suppression"}), 400

    return jsonify({"message": f"Mapping {mappingdata_id} supprimé"}), 200