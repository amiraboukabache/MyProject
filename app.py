from flask import Flask
from flask_cors import CORS
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.admin import admin_bp
from routes.messages import messages_bp
from routes.mappingdata import mappingdata_bp
from routes.account import account_bp
from routes.translation import translation_bp
from routes.activity import activity_bp
import os

app = Flask(__name__)
CORS(app)

# Enregistrer les routes
app.register_blueprint(auth_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(mappingdata_bp)
app.register_blueprint(account_bp)
app.register_blueprint(translation_bp)
app.register_blueprint(activity_bp)

@app.route("/")
def home():
    return "Backend is alive"

if __name__ == "__main__":
    debug_mode = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug_mode, host="0.0.0.0", port=8000)