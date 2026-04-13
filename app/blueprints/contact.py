from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import ContactMessage
from app.utils.audit import write_audit
from app.utils.decorators import role_required
from app.utils.security import is_valid_email, sanitize_text


contact_bp = Blueprint("contact", __name__, url_prefix="/api/contact")


@contact_bp.post("")
def submit_contact_message():
    payload = request.get_json(silent=True) or {}

    name = sanitize_text(payload.get("name", ""))
    email = sanitize_text(payload.get("email", "")).lower()
    subject = sanitize_text(payload.get("subject", ""))
    message = payload.get("message", "")

    captcha_token = payload.get("captcha", "")
    if not captcha_token:
        return jsonify({"error": "Captcha requis"}), 400

    if not name or not is_valid_email(email) or not subject or not message.strip():
        return jsonify({"error": "Champs invalides"}), 400

    contact_message = ContactMessage(name=name, email=email, subject=subject, message=message)
    db.session.add(contact_message)
    db.session.commit()
    write_audit("create", "contact_message", contact_message.id)

    return jsonify({"message": "Message envoyé"}), 201


@contact_bp.get("")
@jwt_required()
@role_required("admin")
def list_contact_messages():
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return jsonify(
        [
            {
                "id": item.id,
                "name": item.name,
                "email": item.email,
                "subject": item.subject,
                "message": item.message,
                "is_read": item.is_read,
                "created_at": item.created_at.isoformat(),
            }
            for item in messages
        ]
    )


@contact_bp.patch("/<int:message_id>/read")
@jwt_required()
@role_required("admin")
def mark_read(message_id: int):
    item = ContactMessage.query.get_or_404(message_id)
    item.is_read = True
    db.session.commit()
    write_audit("update", "contact_message", item.id, "marked as read")
    return jsonify({"message": "Message marqué comme lu"})
