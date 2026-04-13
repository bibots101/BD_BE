import csv
import io
from datetime import datetime

from flask import Blueprint, Response, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from app.extensions import bcrypt
from app.extensions import db
from app.models import MasterStudent, PhDStudent, Researcher, User
from app.utils.audit import write_audit
from app.utils.decorators import role_required
from app.utils.security import is_valid_email, sanitize_text


members_bp = Blueprint("members", __name__, url_prefix="/api/members")


def _researcher_dict(r: Researcher):
    user = r.user
    return {
        "id": r.id,
        "user_id": r.user_id,
        "full_name": f"{user.first_name} {user.last_name}" if user else "",
        "grade": r.grade,
        "specialty": r.specialty,
        "office": r.office,
        "phone": r.phone,
        "institution_email": r.institution_email,
        "is_retired": r.is_retired,
    }


@members_bp.post("/researchers")
@jwt_required()
@role_required("admin")
def create_researcher():
    payload = request.get_json(silent=True) or {}

    email = sanitize_text(payload.get("email", "")).lower()
    password = payload.get("password", "")
    if not is_valid_email(email):
        return jsonify({"error": "Email invalide"}), 400
    if len(password) < 8:
        return jsonify({"error": "Mot de passe minimum 8 caractères"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email déjà utilisé"}), 409

    user = User(
        first_name=sanitize_text(payload.get("first_name", "")),
        last_name=sanitize_text(payload.get("last_name", "")),
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=payload.get("role", "researcher"),
        active=True,
    )

    researcher = Researcher(
        user=user,
        grade=sanitize_text(payload.get("grade", "")),
        specialty=sanitize_text(payload.get("specialty", "")),
        office=sanitize_text(payload.get("office", "")),
        phone=sanitize_text(payload.get("phone", "")),
        bio=payload.get("bio", ""),
        is_retired=bool(payload.get("is_retired", False)),
        institution_email=sanitize_text(payload.get("institution_email", email)).lower(),
        orcid=sanitize_text(payload.get("orcid", "")),
        google_scholar_url=sanitize_text(payload.get("google_scholar_url", "")),
        researchgate_url=sanitize_text(payload.get("researchgate_url", "")),
        linkedin_url=sanitize_text(payload.get("linkedin_url", "")),
    )
    db.session.add(researcher)
    db.session.commit()
    write_audit("create", "researcher", researcher.id)

    return jsonify(_researcher_dict(researcher)), 201


@members_bp.get("/researchers")
@jwt_required(optional=True)
def list_researchers():
    items = Researcher.query.order_by(Researcher.id.desc()).all()
    return jsonify([_researcher_dict(x) for x in items])


@members_bp.patch("/researchers/<int:researcher_id>")
@jwt_required()
def update_researcher(researcher_id: int):
    researcher = Researcher.query.get_or_404(researcher_id)
    payload = request.get_json(silent=True) or {}

    identity = int(get_jwt_identity())
    user = User.query.get(identity)
    is_owner = researcher.user_id == identity
    if not user or (user.role not in {"admin", "super_admin"} and not is_owner):
        return jsonify({"error": "Permissions insuffisantes"}), 403

    for field in ["grade", "specialty", "office", "phone", "bio", "orcid", "google_scholar_url", "researchgate_url", "linkedin_url"]:
        if field in payload:
            setattr(researcher, field, sanitize_text(payload.get(field)) if field != "bio" else payload.get(field))

    if "is_retired" in payload and user.role in {"admin", "super_admin"}:
        researcher.is_retired = bool(payload.get("is_retired"))

    db.session.commit()
    write_audit("update", "researcher", researcher.id)
    return jsonify(_researcher_dict(researcher))


@members_bp.delete("/researchers/<int:researcher_id>")
@jwt_required()
@role_required("admin")
def delete_researcher(researcher_id: int):
    researcher = Researcher.query.get_or_404(researcher_id)
    db.session.delete(researcher)
    db.session.commit()
    write_audit("delete", "researcher", researcher_id)
    return jsonify({"message": "Supprimé"})


@members_bp.get("/export/csv")
@jwt_required()
@role_required("admin")
def export_members_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["type", "id", "first_name", "last_name", "topic_or_specialty", "status"])

    for r in Researcher.query.all():
        first_name = r.user.first_name if r.user else ""
        last_name = r.user.last_name if r.user else ""
        writer.writerow(["researcher", r.id, first_name, last_name, r.specialty, "actif" if not r.is_retired else "retire"])

    for d in PhDStudent.query.all():
        writer.writerow(["phd", d.id, d.first_name, d.last_name, d.thesis_topic, d.status])

    for m in MasterStudent.query.all():
        writer.writerow(["master", m.id, m.first_name, m.last_name, m.topic, m.status])

    csv_content = output.getvalue()
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=members.csv"},
    )


@members_bp.post("/import/csv")
@jwt_required()
@role_required("admin")
def import_members_csv():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "Fichier CSV requis"}), 400

    content = file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))
    created = 0

    for row in reader:
        member_type = (row.get("type") or "").strip().lower()
        if member_type == "phd":
            phd = PhDStudent(
                first_name=row.get("first_name", "").strip(),
                last_name=row.get("last_name", "").strip(),
                thesis_topic=row.get("topic_or_specialty", "").strip(),
                start_date=datetime.utcnow().date(),
                progress_state="import",
                status=row.get("status", "en_cours").strip() or "en_cours",
            )
            db.session.add(phd)
            created += 1
        elif member_type == "master":
            master = MasterStudent(
                first_name=row.get("first_name", "").strip(),
                last_name=row.get("last_name", "").strip(),
                topic=row.get("topic_or_specialty", "").strip(),
                promotion=str(datetime.utcnow().year),
                status=row.get("status", "en_cours").strip() or "en_cours",
            )
            db.session.add(master)
            created += 1

    db.session.commit()
    write_audit("import", "members_csv", "bulk", f"{created} records")
    return jsonify({"message": "Import terminé", "created": created})
