import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Event, Photo
from app.utils.audit import write_audit
from app.utils.decorators import role_required
from app.utils.security import sanitize_text


events_bp = Blueprint("events", __name__, url_prefix="/api/events")


def _refresh_status(event: Event):
    now = datetime.utcnow()
    if event.end_date < now:
        event.status = "termine"
    elif event.start_date <= now <= event.end_date:
        event.status = "en_cours"
    else:
        event.status = "a_venir"


def _to_dict(event: Event):
    _refresh_status(event)
    return {
        "id": event.id,
        "title": event.title,
        "type": event.event_type,
        "start_date": event.start_date.isoformat(),
        "end_date": event.end_date.isoformat(),
        "location": event.location,
        "description": event.description,
        "program_text": event.program_text,
        "program_pdf_path": event.program_pdf_path,
        "status": event.status,
        "photos": [
            {"id": p.id, "url": p.url, "caption": p.caption, "display_order": p.display_order}
            for p in sorted(event.photos, key=lambda x: x.display_order)
        ],
    }


@events_bp.get("")
def list_events():
    status = request.args.get("status")
    query = Event.query
    if status:
        query = query.filter(Event.status == status)

    items = query.order_by(Event.start_date.asc()).all()
    for item in items:
        _refresh_status(item)
    db.session.commit()

    return jsonify([_to_dict(item) for item in items])


@events_bp.post("")
@jwt_required()
@role_required("admin")
def create_event():
    payload = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})

    event = Event(
        title=sanitize_text(payload.get("title", "")),
        event_type=sanitize_text(payload.get("type", "seminaire")),
        start_date=datetime.fromisoformat(payload.get("start_date")),
        end_date=datetime.fromisoformat(payload.get("end_date")),
        location=sanitize_text(payload.get("location", "")),
        description=payload.get("description", ""),
        program_text=payload.get("program_text", ""),
    )

    program_pdf = request.files.get("program_pdf")
    if program_pdf:
        safe_name = secure_filename(program_pdf.filename)
        filename = f"program_{int(datetime.utcnow().timestamp())}_{safe_name}"
        target_dir = os.path.join(current_app.config["UPLOAD_DIR"], "pdfs")
        os.makedirs(target_dir, exist_ok=True)
        destination = os.path.join(target_dir, filename)
        program_pdf.save(destination)
        event.program_pdf_path = destination

    db.session.add(event)
    db.session.commit()
    write_audit("create", "event", event.id)
    return jsonify(_to_dict(event)), 201


@events_bp.post("/<int:event_id>/photos")
@jwt_required()
@role_required("admin")
def add_event_photos(event_id: int):
    event = Event.query.get_or_404(event_id)
    files = request.files.getlist("photos")
    if not files:
        return jsonify({"error": "Aucune photo fournie"}), 400

    target_dir = os.path.join(current_app.config["UPLOAD_DIR"], "photos")
    os.makedirs(target_dir, exist_ok=True)

    created = []
    for index, file in enumerate(files):
        safe_name = secure_filename(file.filename)
        filename = f"event_{event_id}_{int(datetime.utcnow().timestamp())}_{index}_{safe_name}"
        destination = os.path.join(target_dir, filename)
        file.save(destination)

        photo = Photo(
            event=event,
            url=destination,
            caption=request.form.get(f"caption_{index}", ""),
            display_order=index,
        )
        db.session.add(photo)
        created.append(photo)

    db.session.commit()
    write_audit("upload", "event_photos", event.id, f"{len(created)} photos")
    return jsonify({"created": len(created)})


@events_bp.patch("/<int:event_id>")
@jwt_required()
@role_required("admin")
def update_event(event_id: int):
    event = Event.query.get_or_404(event_id)
    payload = request.get_json(silent=True) or {}

    field_map = {
        "title": "title",
        "type": "event_type",
        "location": "location",
        "description": "description",
        "program_text": "program_text",
    }

    for request_field, model_field in field_map.items():
        if request_field in payload:
            value = payload.get(request_field)
            if request_field in {"title", "type", "location"}:
                value = sanitize_text(value)
            setattr(event, model_field, value)

    if "start_date" in payload:
        event.start_date = datetime.fromisoformat(payload.get("start_date"))
    if "end_date" in payload:
        event.end_date = datetime.fromisoformat(payload.get("end_date"))

    _refresh_status(event)
    db.session.commit()
    write_audit("update", "event", event.id)
    return jsonify(_to_dict(event))


@events_bp.delete("/<int:event_id>")
@jwt_required()
@role_required("admin")
def delete_event(event_id: int):
    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()
    write_audit("delete", "event", event_id)
    return jsonify({"message": "Événement supprimé"})
