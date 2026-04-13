from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import ResearchAxis, Researcher
from app.utils.audit import write_audit
from app.utils.decorators import role_required
from app.utils.security import sanitize_text


axes_bp = Blueprint("axes", __name__, url_prefix="/api/axes")


@axes_bp.get("")
def list_axes():
    axes = ResearchAxis.query.order_by(ResearchAxis.title.asc()).all()
    return jsonify(
        [
            {
                "id": axis.id,
                "title": axis.title,
                "description": axis.description,
                "lead_researcher_id": axis.lead_researcher_id,
                "member_ids": [member.id for member in axis.members.all()],
            }
            for axis in axes
        ]
    )


@axes_bp.post("")
@jwt_required()
@role_required("admin")
def create_axis():
    payload = request.get_json(silent=True) or {}
    axis = ResearchAxis(
        title=sanitize_text(payload.get("title", "")),
        description=payload.get("description", ""),
        lead_researcher_id=payload.get("lead_researcher_id"),
    )

    member_ids = payload.get("member_ids", [])
    if member_ids:
        for member in Researcher.query.filter(Researcher.id.in_(member_ids)).all():
            axis.members.append(member)

    db.session.add(axis)
    db.session.commit()
    write_audit("create", "research_axis", axis.id)
    return jsonify({"id": axis.id, "title": axis.title}), 201


@axes_bp.patch("/<int:axis_id>")
@jwt_required()
@role_required("admin")
def update_axis(axis_id: int):
    axis = ResearchAxis.query.get_or_404(axis_id)
    payload = request.get_json(silent=True) or {}

    if "title" in payload:
        axis.title = sanitize_text(payload.get("title", ""))
    if "description" in payload:
        axis.description = payload.get("description", "")
    if "lead_researcher_id" in payload:
        axis.lead_researcher_id = payload.get("lead_researcher_id")

    if "member_ids" in payload:
        axis.members = []
        member_ids = payload.get("member_ids") or []
        for member in Researcher.query.filter(Researcher.id.in_(member_ids)).all():
            axis.members.append(member)

    db.session.commit()
    write_audit("update", "research_axis", axis.id)
    return jsonify({"message": "Axe mis à jour"})


@axes_bp.delete("/<int:axis_id>")
@jwt_required()
@role_required("admin")
def delete_axis(axis_id: int):
    axis = ResearchAxis.query.get_or_404(axis_id)
    db.session.delete(axis)
    db.session.commit()
    write_audit("delete", "research_axis", axis_id)
    return jsonify({"message": "Axe supprimé"})
