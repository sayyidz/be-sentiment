from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Daftarkan blueprint dari routes.py
    from .routes import main
    app.register_blueprint(main)

    # Aktifkan CORS untuk semua route
    CORS(app)

    return app
