"""Evaluate goals and trip wires after spend changes.

Goals: condition is "spend in window stays at or below threshold". A goal is
"met" only AFTER the end_date has passed and total stays under threshold.
Trip wires: triggered as soon as target's spend in window exceeds threshold.

All comparisons happen in the threshold's currency, converted from the spend
entry's original currency at the spend entry's date (cached daily FX).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..extensions import db
from ..models import SpendEntry, Goal, TripWire, Notification, User
from ..fx.service import convert


def _spend_total_in_currency(user_id: int, dst_currency: str, start: date, end: date,
                             category_id: int | None) -> Decimal:
    q = SpendEntry.query.filter(
        SpendEntry.user_id == user_id,
        SpendEntry.date >= start,
        SpendEntry.date <= end,
    )
    if category_id is not None:
        q = q.filter(SpendEntry.category_id == category_id)
    total = Decimal("0")
    for entry in q.all():
        total += convert(entry.amount, entry.original_currency, dst_currency, entry.date)
    return total


def _notify(user_id: int, type_: str, message: str, payload: str | None = None):
    db.session.add(Notification(recipient_id=user_id, type=type_, message=message, payload=payload))


def expire_stale(today: date | None = None):
    today = today or date.today()
    expired_goals = Goal.query.filter(Goal.status.in_(("pending", "active")), Goal.end_date < today).all()
    for g in expired_goals:
        if g.status == "active":
            total = _spend_total_in_currency(g.owner_id, g.threshold_currency,
                                             g.start_date, g.end_date, g.category_id)
            # Cap: met if total stayed at or under threshold. Target: met if total reached threshold.
            if g.goal_type == "target":
                met = total >= Decimal(g.threshold)
            else:
                met = total <= Decimal(g.threshold)
            if met:
                g.status = "met"
                g.owner.points = (g.owner.points or 0) + 10
                _notify(g.owner_id, "goal_met", f"Goal met: {g.label}", payload=f"goal:{g.id}")
                partner = g.owner.couple_group.partner_of(g.owner) if g.owner.couple_group else None
                if partner:
                    _notify(partner.id, "goal_met", f"Partner met goal: {g.label}", payload=f"goal:{g.id}")
            else:
                g.status = "expired"
                _notify(g.owner_id, "goal_expired", f"Goal expired: {g.label}", payload=f"goal:{g.id}")
        else:
            g.status = "expired"
            _notify(g.owner_id, "goal_expired", f"Goal expired (never approved): {g.label}", payload=f"goal:{g.id}")

    expired_tw = TripWire.query.filter(TripWire.status == "active", TripWire.end_date < today).all()
    for tw in expired_tw:
        tw.status = "expired"
        _notify(tw.setter_id, "tripwire_expired", f"Trip wire expired untriggered: {tw.label}",
                payload=f"tripwire:{tw.id}")
        _notify(tw.target_user_id, "tripwire_expired", f"Trip wire expired: {tw.label}",
                payload=f"tripwire:{tw.id}")
    db.session.commit()


def evaluate_for_user(user: User, on_date: date | None = None):
    """After a spend entry by `user`, recheck their active goals and any
    trip wires targeting them. Award points and create notifications."""
    today = on_date or date.today()

    # Goals: a goal is "tripped" (i.e., busted) if spend exceeds threshold within the window.
    # We don't auto-mark "met" until end_date passes (handled by expire_stale).
    # But we DO want to alert the owner if they've already exceeded — flag via expired.
    active_goals = Goal.query.filter_by(owner_id=user.id, status="active").all()
    for g in active_goals:
        if today < g.start_date or today > g.end_date:
            continue
        spent = _spend_total_in_currency(user.id, g.threshold_currency,
                                         g.start_date, g.end_date, g.category_id)
        if g.goal_type == "target":
            # Target: hitting the threshold mid-window is an immediate win.
            if spent >= Decimal(g.threshold):
                g.status = "met"
                user.points = (user.points or 0) + 10
                _notify(user.id, "goal_met",
                        f"Goal met: {g.label} (+10 pts)", payload=f"goal:{g.id}")
                partner = user.couple_group.partner_of(user) if user.couple_group else None
                if partner:
                    _notify(partner.id, "goal_met",
                            f"Partner met goal: {g.label}", payload=f"goal:{g.id}")
        else:
            # Cap: blowing past the threshold mid-window busts the goal.
            if spent > Decimal(g.threshold):
                g.status = "expired"
                _notify(user.id, "goal_busted",
                        f"Goal busted (over threshold): {g.label}", payload=f"goal:{g.id}")
                partner = user.couple_group.partner_of(user) if user.couple_group else None
                if partner:
                    _notify(partner.id, "goal_busted",
                            f"Partner busted goal: {g.label}", payload=f"goal:{g.id}")

    # Trip wires targeting this user
    active_tw = TripWire.query.filter_by(target_user_id=user.id, status="active").all()
    for tw in active_tw:
        if today < tw.start_date or today > tw.end_date:
            continue
        spent = _spend_total_in_currency(user.id, tw.threshold_currency,
                                         tw.start_date, tw.end_date, tw.category_id)
        if spent > Decimal(tw.threshold):
            tw.status = "tripped"
            setter = User.query.get(tw.setter_id)
            if setter:
                setter.points = (setter.points or 0) + 10
            _notify(tw.setter_id, "tripwire_tripped",
                    f"Trip wire tripped: {tw.label} (+10 pts)", payload=f"tripwire:{tw.id}")
            _notify(tw.target_user_id, "tripwire_tripped",
                    f"Trip wire tripped against you: {tw.label}", payload=f"tripwire:{tw.id}")

    db.session.commit()
