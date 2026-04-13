from datetime import datetime

from flask import Blueprint, jsonify, request

from app.models import Event, MasterStudent, PhDStudent, Publication, ResearchAxis, Researcher


public_bp = Blueprint("public", __name__, url_prefix="/api/public")


def _researcher_to_dict(item: Researcher):
    full_name = ""
    if item.user:
        full_name = f"{item.user.first_name} {item.user.last_name}".strip()

    return {
        "id": item.id,
        "full_name": full_name,
        "grade": item.grade,
        "specialty": item.specialty,
        "email": item.institution_email,
        "is_retired": item.is_retired,
        "axes": [axis.title for axis in item.axes.all()],
    }


@public_bp.get("/home")
def home_data():
    now = datetime.utcnow()

    latest_publications = (
        Publication.query.filter_by(status="published")
        .order_by(Publication.year.desc(), Publication.created_at.desc())
        .limit(5)
        .all()
    )
    upcoming_events = (
        Event.query.filter(Event.start_date >= now)
        .order_by(Event.start_date.asc())
        .limit(5)
        .all()
    )

    stats = {
        "researchers": Researcher.query.count(),
        "publications": Publication.query.filter_by(status="published").count(),
        "doctorants": PhDStudent.query.count(),
        "projects": ResearchAxis.query.count(),
        "masteriens": MasterStudent.query.count(),
    }

    return jsonify(
        {
            "summary": "LIMTIC - Laboratoire d'Informatique, Modélisation et Traitement de l'Information.",
            "quick_links": ["chercheurs", "publications", "evenements", "axes"],
            "latest_publications": [
                {"id": p.id, "title": p.title, "year": p.year, "ranking": p.ranking}
                for p in latest_publications
            ],
            "upcoming_events": [
                {"id": e.id, "title": e.title, "start_date": e.start_date.isoformat(), "location": e.location}
                for e in upcoming_events
            ],
            "stats": stats,
        }
    )


@public_bp.get("/researchers")
def list_researchers():
    axis_id = request.args.get("axis_id", type=int)
    grade = request.args.get("grade")
    status = request.args.get("status")

    query = Researcher.query
    if grade:
        query = query.filter(Researcher.grade == grade)
    if status == "actif":
        query = query.filter(Researcher.is_retired.is_(False))
    elif status == "retire":
        query = query.filter(Researcher.is_retired.is_(True))
    if axis_id:
        query = query.join(Researcher.axes).filter(ResearchAxis.id == axis_id)

    items = query.order_by(Researcher.id.desc()).all()
    return jsonify([_researcher_to_dict(item) for item in items])


@public_bp.get("/researchers/<int:researcher_id>")
def researcher_profile(researcher_id: int):
    item = Researcher.query.get_or_404(researcher_id)

    publications = [
        {
            "id": pub.id,
            "title": pub.title,
            "type": pub.publication_type,
            "year": pub.year,
            "doi": pub.doi,
            "venue": pub.venue_name,
            "ranking": pub.ranking,
            "citations": pub.citations,
        }
        for pub in item.publications.order_by(Publication.year.desc()).all()
    ]

    return jsonify({**_researcher_to_dict(item), "bio": item.bio, "publications": publications})


@public_bp.get("/axes")
def list_axes():
    axes = ResearchAxis.query.order_by(ResearchAxis.title.asc()).all()
    return jsonify(
        [
            {
                "id": axis.id,
                "title": axis.title,
                "description": axis.description,
                "members_count": axis.members.count(),
            }
            for axis in axes
        ]
    )
