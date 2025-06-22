from flask import Flask
from flask_cors import CORS
from .models import db
from flask_migrate import Migrate
from dotenv import load_dotenv
import os

load_dotenv()

def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)  # Inisialisasi SQLAlchemy
    migrate = Migrate(app, db)

    from .routes import main
    app.register_blueprint(main)
    CORS(app)

    with app.app_context():
        db.create_all()

    return app
