from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity

from app.models import User


ROLE_PRIORITY = {
    "visitor": 0,
    "researcher": 1,
    "admin": 2,
    "super_admin": 3,
}


def role_required(min_role: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            identity = get_jwt_identity()
            if not identity:
                return jsonify({"error": "Authentification requise"}), 401

            user = User.query.get(int(identity))
            if not user or not user.active:
                return jsonify({"error": "Utilisateur invalide"}), 403

            if ROLE_PRIORITY.get(user.role, -1) < ROLE_PRIORITY.get(min_role, 999):
                return jsonify({"error": "Permissions insuffisantes"}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator
