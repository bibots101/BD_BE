from flask_jwt_extended import get_jwt_identity

from app.extensions import db
from app.models import AuditLog


def write_audit(action: str, entity: str, entity_id: str, details: str = "") -> None:
    actor_user_id = None
    try:
        actor_user_id = get_jwt_identity()
    except Exception:
        actor_user_id = None

    log = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        details=details,
    )
    db.session.add(log)
    db.session.commit()
