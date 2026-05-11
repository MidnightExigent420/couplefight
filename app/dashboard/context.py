"""Context processor: data for the persistent activity side panel.

Returns the user's goals + tripwires (all statuses), each enriched with a
``completion_date`` derived from the most recent state-change notification.
"""
from __future__ import annotations

from flask_login import current_user

from ..extensions import db
from ..models import Goal, TripWire, Notification


_GOAL_STATE_NOTIF_TYPES = ("goal_met", "goal_busted", "goal_expired")
_TW_STATE_NOTIF_TYPES = ("tripwire_tripped", "tripwire_expired")


def _state_change_dates(user_id: int, payload_prefix: str, types: tuple[str, ...]) -> dict[int, object]:
    """Return {entity_id: latest_notification_created_at} for the given prefix/types.

    Looks at notifications addressed to ``user_id`` with payload like ``"goal:42"``
    or ``"tripwire:7"``. Used as a zero-migration proxy for state-change time.
    """
    rows = (
        Notification.query
        .filter(Notification.recipient_id == user_id,
                Notification.type.in_(types),
                Notification.payload.like(f"{payload_prefix}:%"))
        .order_by(Notification.created_at.desc())
        .all()
    )
    out: dict[int, object] = {}
    for n in rows:
        try:
            eid = int(n.payload.split(":", 1)[1])
        except (ValueError, IndexError):
            continue
        if eid not in out:  # already sorted desc → first hit is latest
            out[eid] = n.created_at
    return out


def activity_panel_context():
    if not current_user.is_authenticated:
        return {}

    goals = (Goal.query.filter_by(owner_id=current_user.id)
             .order_by(Goal.created_at.desc()).all())
    tripwires = (TripWire.query.filter_by(target_user_id=current_user.id)
                 .order_by(TripWire.created_at.desc()).all())

    goal_completion = _state_change_dates(current_user.id, "goal", _GOAL_STATE_NOTIF_TYPES)
    tw_completion = _state_change_dates(current_user.id, "tripwire", _TW_STATE_NOTIF_TYPES)

    completed_goal_statuses = {"met", "expired", "rejected"}
    completed_tw_statuses = {"tripped", "expired"}

    goal_rows = []
    for g in goals:
        completed_at = goal_completion.get(g.id) if g.status in completed_goal_statuses else None
        goal_rows.append({
            "id": g.id,
            "kind": "goal",
            "label": g.label,
            "goal_type": g.goal_type,
            "status": g.status,
            "bucket": _goal_bucket(g.status),
            "threshold": g.threshold,
            "currency": g.threshold_currency,
            "created_at": g.created_at,
            "end_date": g.end_date,
            "completion_date": completed_at.date() if completed_at else None,
        })

    tw_rows = []
    for t in tripwires:
        completed_at = tw_completion.get(t.id) if t.status in completed_tw_statuses else None
        tw_rows.append({
            "id": t.id,
            "kind": "tripwire",
            "label": t.label,
            "goal_type": None,
            "status": t.status,
            "bucket": _tripwire_bucket(t.status),
            "threshold": t.threshold,
            "currency": t.threshold_currency,
            "created_at": t.created_at,
            "end_date": t.end_date,
            "completion_date": completed_at.date() if completed_at else None,
        })

    return {
        "activity_panel_items": goal_rows + tw_rows,
    }


def _goal_bucket(status: str) -> str:
    # Pending is in BOTH Pending and Inactive buckets, expressed as space-separated tokens.
    if status == "active":
        return "active"
    if status == "met":
        return "completed"
    if status == "pending":
        return "pending inactive"
    # 'expired' or 'rejected'
    return "inactive"


def _tripwire_bucket(status: str) -> str:
    if status == "active":
        return "active"
    if status == "tripped":
        return "completed"
    return "inactive"
