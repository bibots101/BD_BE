from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import AuditLog, Event, MasterStudent, PhDStudent, Publication, Researcher, Setting, User
from app.utils.audit import write_audit
from app.utils.decorators import role_required
from app.utils.security import sanitize_text


admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@admin_bp.get("/dashboard")
@jwt_required()
@role_required("admin")
def dashboard():
    publications_by_type = {}
    for pub_type, count in db.session.query(Publication.publication_type, db.func.count(Publication.id)).group_by(Publication.publication_type):
        publications_by_type[pub_type] = count

    upcoming_events = Event.query.filter(Event.status == "a_venir").count()

    return jsonify(
        {
            "stats": {
                "researchers": Researcher.query.count(),
                "doctorants": PhDStudent.query.count(),
                "masteriens": MasterStudent.query.count(),
                "events": Event.query.count(),
                "publications_by_type": publications_by_type,
            },
            "alerts": {
                "pending_publications": Publication.query.filter(Publication.status.in_(["draft", "submitted"])).count(),
                "upcoming_events": upcoming_events,
            },
            "latest_changes": [
                {
                    "action": item.action,
                    "entity": item.entity,
                    "entity_id": item.entity_id,
                    "created_at": item.created_at.isoformat(),
                }
                for item in AuditLog.query.order_by(AuditLog.created_at.desc()).limit(10).all()
            ],
        }
    )


@admin_bp.get("/users")
@jwt_required()
@role_required("super_admin")
def list_users():
    users = User.query.order_by(User.id.desc()).all()
    return jsonify(
        [
            {
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "role": u.role,
                "active": u.active,
            }
            for u in users
        ]
    )


@admin_bp.patch("/users/<int:user_id>")
@jwt_required()
@role_required("super_admin")
def update_user(user_id: int):
    user = User.query.get_or_404(user_id)
    payload = request.get_json(silent=True) or {}

    if "role" in payload:
        user.role = sanitize_text(payload.get("role"))
    if "active" in payload:
        user.active = bool(payload.get("active"))

    db.session.commit()
    write_audit("update", "user", user.id, "role or active changed")
    return jsonify({"message": "Utilisateur mis à jour"})


@admin_bp.get("/settings")
@jwt_required()
@role_required("admin")
def get_settings():
    settings = Setting.query.order_by(Setting.key.asc()).all()
    return jsonify({item.key: item.value for item in settings})


@admin_bp.put("/settings")
@jwt_required()
@role_required("admin")
def upsert_settings():
    payload = request.get_json(silent=True) or {}
    for key, value in payload.items():
        clean_key = sanitize_text(key)
        setting = Setting.query.filter_by(key=clean_key).first()
        if setting:
            setting.value = str(value)
        else:
            setting = Setting(key=clean_key, value=str(value))
            db.session.add(setting)

    db.session.commit()
    write_audit("upsert", "settings", "global")
    return jsonify({"message": "Paramètres sauvegardés"})


@admin_bp.get("/audit-logs")
@jwt_required()
@role_required("admin")
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(200).all()
    return jsonify(
        [
            {
                "id": log.id,
                "actor_user_id": log.actor_user_id,
                "action": log.action,
                "entity": log.entity,
                "entity_id": log.entity_id,
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ]
    )
