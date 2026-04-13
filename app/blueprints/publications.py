import os
from datetime import datetime

from flask import Blueprint, Response, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from sqlalchemy import or_
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import ExternalAuthor, Publication, ResearchAxis, Researcher, User
from app.utils.audit import write_audit
from app.utils.decorators import role_required
from app.utils.exporters import publications_to_bibtex, publications_to_csv
from app.utils.security import sanitize_text


publications_bp = Blueprint("publications", __name__, url_prefix="/api/publications")


def _publication_dict(item: Publication):
    return {
        "id": item.id,
        "title": item.title,
        "type": item.publication_type,
        "year": item.year,
        "abstract": item.abstract,
        "doi": item.doi,
        "external_url": item.external_url,
        "pdf_path": item.pdf_path,
        "venue_name": item.venue_name,
        "ranking": item.ranking,
        "ranking_source": item.ranking_source,
        "keywords": item.keywords,
        "citations": item.citations,
        "status": item.status,
        "axes": [x.title for x in item.axes.all()],
        "internal_authors": [a.id for a in item.internal_authors.all()],
        "external_authors": [a.full_name for a in item.external_authors],
    }


@publications_bp.get("")
def list_publications():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    publication_type = request.args.get("type")
    year = request.args.get("year", type=int)
    axis_id = request.args.get("axis_id", type=int)
    search = request.args.get("search", "")

    query = Publication.query
    if publication_type:
        query = query.filter(Publication.publication_type == publication_type)
    if year:
        query = query.filter(Publication.year == year)
    if axis_id:
        query = query.join(Publication.axes).filter(ResearchAxis.id == axis_id)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Publication.title.ilike(like),
                Publication.keywords.ilike(like),
                Publication.venue_name.ilike(like),
            )
        )

    pagination = query.order_by(Publication.year.desc(), Publication.id.desc()).paginate(page=page, per_page=min(per_page, 50))

    return jsonify(
        {
            "items": [_publication_dict(item) for item in pagination.items],
            "page": pagination.page,
            "pages": pagination.pages,
            "total": pagination.total,
        }
    )


@publications_bp.post("")
@jwt_required()
def create_publication():
    payload = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})

    identity = int(get_jwt_identity())
    user = User.query.get(identity)
    if not user:
        return jsonify({"error": "Utilisateur introuvable"}), 404

    if user.role not in {"researcher", "admin", "super_admin"}:
        return jsonify({"error": "Permissions insuffisantes"}), 403

    owner = user.researcher
    if not owner and user.role == "researcher":
        return jsonify({"error": "Profil chercheur requis"}), 400

    pub = Publication(
        title=sanitize_text(payload.get("title", "")),
        publication_type=sanitize_text(payload.get("type", "journal")),
        year=int(payload.get("year", datetime.utcnow().year)),
        abstract=payload.get("abstract", ""),
        doi=sanitize_text(payload.get("doi", "")),
        external_url=sanitize_text(payload.get("external_url", "")),
        venue_name=sanitize_text(payload.get("venue_name", "")),
        ranking=sanitize_text(payload.get("ranking", "")),
        ranking_source=sanitize_text(payload.get("ranking_source", "")),
        keywords=sanitize_text(payload.get("keywords", "")),
        citations=int(payload.get("citations", 0) or 0),
        status=sanitize_text(payload.get("status", "draft")),
        owner_id=owner.id if owner else None,
    )

    pdf_file = request.files.get("pdf")
    if pdf_file:
        safe_name = secure_filename(pdf_file.filename)
        filename = f"{int(datetime.utcnow().timestamp())}_{safe_name}"
        target_dir = os.path.join(current_app.config["UPLOAD_DIR"], "pdfs")
        os.makedirs(target_dir, exist_ok=True)
        destination = os.path.join(target_dir, filename)
        pdf_file.save(destination)
        pub.pdf_path = destination

    axis_ids = payload.get("axis_ids", "")
    if axis_ids:
        ids = [int(x) for x in axis_ids.split(",") if x.strip().isdigit()]
        for axis in ResearchAxis.query.filter(ResearchAxis.id.in_(ids)).all():
            pub.axes.append(axis)

    internal_author_ids = payload.get("internal_author_ids", "")
    if internal_author_ids:
        ids = [int(x) for x in internal_author_ids.split(",") if x.strip().isdigit()]
        for author in Researcher.query.filter(Researcher.id.in_(ids)).all():
            pub.internal_authors.append(author)

    external_authors = payload.get("external_authors", "")
    if external_authors:
        for name in [x.strip() for x in external_authors.split(",") if x.strip()]:
            pub.external_authors.append(ExternalAuthor(full_name=sanitize_text(name)))

    db.session.add(pub)
    db.session.commit()
    write_audit("create", "publication", pub.id)

    return jsonify(_publication_dict(pub)), 201


@publications_bp.patch("/<int:publication_id>")
@jwt_required()
def update_publication(publication_id: int):
    pub = Publication.query.get_or_404(publication_id)
    payload = request.get_json(silent=True) or {}

    identity = int(get_jwt_identity())
    user = User.query.get(identity)
    is_owner = user and user.researcher and pub.owner_id == user.researcher.id
    if not user or (user.role not in {"admin", "super_admin"} and not is_owner):
        return jsonify({"error": "Permissions insuffisantes"}), 403

    updatable = [
        "title",
        "publication_type",
        "year",
        "abstract",
        "doi",
        "external_url",
        "venue_name",
        "ranking",
        "ranking_source",
        "keywords",
        "citations",
        "status",
    ]

    for field in updatable:
        if field in payload:
            value = payload.get(field)
            if field in {"title", "publication_type", "doi", "external_url", "venue_name", "ranking", "ranking_source", "keywords", "status"}:
                value = sanitize_text(str(value))
            setattr(pub, field, value)

    db.session.commit()
    write_audit("update", "publication", pub.id)
    return jsonify(_publication_dict(pub))


@publications_bp.delete("/<int:publication_id>")
@jwt_required()
@role_required("admin")
def delete_publication(publication_id: int):
    pub = Publication.query.get_or_404(publication_id)
    db.session.delete(pub)
    db.session.commit()
    write_audit("delete", "publication", publication_id)
    return jsonify({"message": "Publication supprimée"})


@publications_bp.get("/export/csv")
def export_csv():
    publications = Publication.query.order_by(Publication.year.desc()).all()
    content = publications_to_csv(publications)
    return Response(content, mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=publications.csv"})


@publications_bp.get("/export/bibtex")
def export_bibtex():
    publications = Publication.query.order_by(Publication.year.desc()).all()
    content = publications_to_bibtex(publications)
    return Response(
        content,
        mimetype="text/plain",
        headers={"Content-Disposition": "attachment; filename=publications.bib"},
    )
