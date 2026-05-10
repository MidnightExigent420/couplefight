from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, render_template, jsonify, request, url_for
from flask_login import login_required, current_user

from ..models import Goal, TripWire, SpendEntry
from ..fx.service import convert
from ..services.evaluation import expire_stale

bp = Blueprint("dashboard", __name__, template_folder="../templates")


@bp.route("/dashboard")
@login_required
def home():
    try:
        expire_stale()
    except Exception:
        pass
    partner = None
    invite_url = None
    if current_user.couple_group:
        partner = current_user.couple_group.partner_of(current_user)
        invite_url = url_for("auth.join_couple", token=current_user.couple_group.invite_token, _external=True)

    active_goals = []
    active_tripwires_against = []
    if current_user.couple_group_id:
        active_goals = Goal.query.filter(
            Goal.owner_id == current_user.id, Goal.status.in_(("active",))
        ).order_by(Goal.end_date.asc()).all()
        active_tripwires_against = TripWire.query.filter(
            TripWire.target_user_id == current_user.id, TripWire.status == "active"
        ).order_by(TripWire.end_date.asc()).all()

    return render_template(
        "dashboard/home.html",
        partner=partner,
        invite_url=invite_url,
        active_goals=active_goals,
        active_tripwires_against=active_tripwires_against,
    )


def _cumulative(user_id, start: date, end: date, dst_currency: str, category_id: int | None,
                up_to: date | None = None) -> tuple[list[str], list[float]]:
    q = SpendEntry.query.filter(
        SpendEntry.user_id == user_id,
        SpendEntry.date >= start,
        SpendEntry.date <= end,
    )
    if category_id is not None:
        q = q.filter(SpendEntry.category_id == category_id)
    entries = q.all()

    daily = {}
    for e in entries:
        amt = convert(e.amount, e.original_currency, dst_currency, e.date)
        daily[e.date] = daily.get(e.date, Decimal("0")) + amt

    labels = []
    values = []
    running = Decimal("0")
    cap = up_to or end
    days = (end - start).days
    for i in range(days + 1):
        d = start + timedelta(days=i)
        if d <= cap:
            running += daily.get(d, Decimal("0"))
        labels.append(d.isoformat())
        values.append(float(running))
    return labels, values


@bp.route("/api/chart")
@login_required
def chart_data():
    """Chart data for a goal or tripwire — values in viewer's preferred currency.

    Query params:
      kind: "goal" | "tripwire"
      id:   numeric id
      up_to: optional ISO date for replay (cumulative up to this day; later days flat)
    """
    kind = request.args.get("kind")
    target_id = request.args.get("id", type=int)
    up_to_str = request.args.get("up_to")
    if kind not in ("goal", "tripwire") or not target_id:
        return jsonify({"error": "bad params"}), 400

    dst = current_user.preferred_currency

    if kind == "goal":
        g = Goal.query.get_or_404(target_id)
        # Auth: must own this goal.
        if g.owner_id != current_user.id:
            return jsonify({"error": "forbidden"}), 403
        start, end = g.start_date, g.end_date
        cat_id = g.category_id if g.condition_type == "category" else None
        goal_threshold = float(convert(g.threshold, g.threshold_currency, dst))
        # Find any tripwires targeting current user overlapping this window with same category scope.
        tw_q = TripWire.query.filter(
            TripWire.target_user_id == current_user.id,
            TripWire.start_date <= end,
            TripWire.end_date >= start,
        )
        if cat_id is not None:
            tw_q = tw_q.filter((TripWire.category_id == cat_id) | (TripWire.condition_type == "total"))
        overlapping_tw = [float(convert(tw.threshold, tw.threshold_currency, dst)) for tw in tw_q.all()]
        label_ctx = g.label
        user_id = g.owner_id
    else:
        tw = TripWire.query.get_or_404(target_id)
        # Setter or target may view (both see chart of target's spend).
        if tw.setter_id != current_user.id and tw.target_user_id != current_user.id:
            return jsonify({"error": "forbidden"}), 403
        start, end = tw.start_date, tw.end_date
        cat_id = tw.category_id if tw.condition_type == "category" else None
        goal_threshold = None
        overlapping_tw = [float(convert(tw.threshold, tw.threshold_currency, dst))]
        label_ctx = tw.label
        user_id = tw.target_user_id

    up_to = None
    if up_to_str:
        try:
            up_to = date.fromisoformat(up_to_str)
        except ValueError:
            return jsonify({"error": "bad up_to"}), 400

    labels, values = _cumulative(user_id, start, end, dst, cat_id, up_to=up_to)
    return jsonify({
        "label": label_ctx,
        "currency": dst,
        "labels": labels,
        "values": values,
        "goal_threshold": goal_threshold,
        "tripwire_thresholds": overlapping_tw,
        "start": start.isoformat(),
        "end": end.isoformat(),
    })
