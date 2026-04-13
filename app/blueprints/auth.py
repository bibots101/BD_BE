from datetime import timedelta

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required
from itsdangerous import URLSafeTimedSerializer

from app.extensions import bcrypt, db
from app.models import User
from app.utils.audit import write_audit
from app.utils.security import is_valid_email, sanitize_text


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    first_name = sanitize_text(payload.get("first_name", ""))
    last_name = sanitize_text(payload.get("last_name", ""))
    email = sanitize_text(payload.get("email", "")).lower()
    password = payload.get("password", "")

    if not first_name or not last_name or not is_valid_email(email) or len(password) < 8:
        return jsonify({"error": "Données invalides"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email déjà utilisé"}), 409

    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role="researcher",
    )
    db.session.add(user)
    db.session.commit()
    write_audit("create", "user", user.id, "Inscription")

    return jsonify({"message": "Compte créé", "user_id": user.id}), 201


@auth_bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = sanitize_text(payload.get("email", "")).lower()
    password = payload.get("password", "")

    user = User.query.filter_by(email=email).first()
    if not user or not user.active or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Identifiants invalides"}), 401

    access = create_access_token(identity=str(user.id), additional_claims={"role": user.role}, expires_delta=timedelta(hours=2))
    refresh = create_refresh_token(identity=str(user.id))

    write_audit("login", "user", user.id, "Connexion réussie")
    return jsonify(
        {
            "access_token": access,
            "refresh_token": refresh,
            "user": {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.role,
            },
        }
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    from flask_jwt_extended import get_jwt_identity

    identity = get_jwt_identity()
    user = User.query.get(int(identity))
    if not user or not user.active:
        return jsonify({"error": "Utilisateur invalide"}), 403

    access = create_access_token(identity=str(user.id), additional_claims={"role": user.role}, expires_delta=timedelta(hours=2))
    return jsonify({"access_token": access})


@auth_bp.post("/forgot-password")
def forgot_password():
    payload = request.get_json(silent=True) or {}
    email = sanitize_text(payload.get("email", "")).lower()
    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"message": "Si l'email existe, un lien est généré"})

    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    token = serializer.dumps(user.email, salt="password-reset")
    write_audit("request_reset", "user", user.id, "Demande de reset")

    # In production, send this token by email through SMTP.
    return jsonify({"message": "Lien de réinitialisation généré", "reset_token": token})


@auth_bp.post("/reset-password")
def reset_password():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token", "")
    new_password = payload.get("new_password", "")

    if len(new_password) < 8:
        return jsonify({"error": "Mot de passe trop court"}), 400

    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt="password-reset", max_age=3600)
    except Exception:
        return jsonify({"error": "Token invalide ou expiré"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    user.password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()
    write_audit("reset_password", "user", user.id, "Réinitialisation")

    return jsonify({"message": "Mot de passe mis à jour"})
