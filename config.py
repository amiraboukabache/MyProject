import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

# ─── Supabase ───
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

db_headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

auth_headers = {
    "apikey": SUPABASE_KEY,
    "Content-Type": "application/json"
}

# ─── Firebase / Firestore ───
cred = credentials.Certificate(os.getenv("FIREBASE_CREDENTIALS", "firebase_credentials.json"))
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()