# app/__init__.py

from flask import Flask
from dotenv import load_dotenv
from flask_cors import CORS

def create_app():
    load_dotenv()  # Load environment variables from .env file

    app = Flask(__name__)
    CORS(app)
    from .routes import main
    app.register_blueprint(main)

    return app
