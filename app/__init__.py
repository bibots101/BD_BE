import os

from flask import Flask, jsonify
from flask_cors import CORS

from app.blueprints.admin import admin_bp
from app.blueprints.auth import auth_bp
from app.blueprints.axes import axes_bp
from app.blueprints.contact import contact_bp
from app.blueprints.events import events_bp
from app.blueprints.members import members_bp
from app.blueprints.public import public_bp
from app.blueprints.publications import publications_bp
from app.config import Config
from app.extensions import bcrypt, db, jwt, migrate


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    os.makedirs(os.path.join(app.config["UPLOAD_DIR"], "pdfs"), exist_ok=True)
    os.makedirs(os.path.join(app.config["UPLOAD_DIR"], "photos"), exist_ok=True)

    CORS(app)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(public_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(publications_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(axes_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(admin_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "LIMTIC Flask API"})

    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Ressource introuvable"}), 404

    @app.errorhandler(400)
    def bad_request(_):
        return jsonify({"error": "Requête invalide"}), 400

    @app.errorhandler(413)
    def file_too_large(_):
        return jsonify({"error": "Fichier trop volumineux"}), 413

    return app
