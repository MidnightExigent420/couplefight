import logging

from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user

from ..extensions import db, csrf
from ..models import Notification
from ..services.evaluation import expire_stale

bp = Blueprint("notifications", __name__)
log = logging.getLogger(__name__)


@bp.route("/notifications", methods=["GET"])
@login_required
def list_notifications():
    # Lightweight expire check on poll. Cheap because filtered queries hit indexes.
    # Best-effort: log and roll back on failure so a broken expire pass doesn't 500 the bell poll.
    try:
        expire_stale()
    except Exception:
        log.exception("expire_stale failed during notifications poll")
        db.session.rollback()

    notes = (Notification.query.filter_by(recipient_id=current_user.id)
             .order_by(Notification.created_at.desc()).limit(50).all())
    unread = sum(1 for n in notes if not n.read)
    return jsonify({
        "unread": unread,
        "points": current_user.points or 0,
        "items": [
            {
                "id": n.id,
                "type": n.type,
                "message": n.message,
                "payload": n.payload,
                "read": n.read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notes
        ],
    })


@bp.route("/notifications/<int:note_id>/read", methods=["POST"])
@login_required
def mark_read(note_id):
    n = Notification.query.get_or_404(note_id)
    if n.recipient_id != current_user.id:
        abort(403)
    n.read = True
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(recipient_id=current_user.id, read=False).update({"read": True})
    db.session.commit()
    return jsonify({"ok": True})
