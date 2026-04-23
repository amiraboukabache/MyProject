from flask import Blueprint, request, jsonify
import requests
from config import SUPABASE_URL, SUPABASE_KEY, db_headers, auth_headers

auth_bp = Blueprint("auth", __name__)


# ─────────────────────────────────────────
# 🔐 REGISTER
# ─────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.json

    required_fields = ["email", "password", "name", "lastname", "role"]
    missing = [f for f in required_fields if not data.get(f)]
    if missing:
        return jsonify({"error": f"Champs manquants : {', '.join(missing)}"}), 400

    email    = data["email"]
    password = data["password"]
    name     = data["name"]
    lastname = data["lastname"]
    role     = data["role"]

    # ÉTAPE 1 : Créer dans Supabase Auth
    auth_res = requests.post(
        f"{SUPABASE_URL}/auth/v1/signup",
        json={"email": email, "password": password},
        headers=auth_headers
    )
    auth_data = auth_res.json()

    if auth_res.status_code not in (200, 201):
        return jsonify({
            "error": "Échec de la création du compte",
            "details": auth_data
        }), 400

    user_id = auth_data.get("user", auth_data).get("id")

    if not user_id:
        return jsonify({
            "error": "Impossible de récupérer l'ID utilisateur",
            "details": auth_data
        }), 400

    # ÉTAPE 2 : Insérer dans la table users
    db_res = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        json={
            "user_id": user_id,
            "name": name,
            "lastname": lastname,
            "email": email,
            "role": role
        },
        headers=db_headers
    )

    if db_res.status_code not in (200, 201):
        return jsonify({
            "error": "Compte créé mais échec de l'insertion du profil",
            "details": db_res.json()
        }), 400

    return jsonify({
        "message": "Utilisateur créé avec succès",
        "user_id": user_id,
        "profile": db_res.json()
    }), 201


# ─────────────────────────────────────────
# 🔵 LOGIN
# ─────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json

    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Email et mot de passe requis"}), 400

    res = requests.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        json={"email": data["email"], "password": data["password"]},
        headers=auth_headers
    )
    login_data = res.json()

    if "access_token" not in login_data:
        return jsonify({
            "error": "Email ou mot de passe incorrect",
            "details": login_data
        }), 401

    return jsonify({
        "message": "Connexion réussie",
        "access_token": login_data["access_token"],
        "refresh_token": login_data.get("refresh_token"),
        "user": login_data.get("user")
    }), 200