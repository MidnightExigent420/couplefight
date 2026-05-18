"""Goal routes: create (pending, awaits partner approval), approve, reject.

Goals always start in `pending` and need the partner to approve before they
become `active`. Status transitions to `met`/`expired` are owned by
`app/services/evaluation.py`, not these routes.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Goal, Category, Notification
from ..services.validators import validate_threshold_form
from .forms import GoalForm

bp = Blueprint("goals", __name__, template_folder="../templates")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if not current_user.couple_group_id:
        flash("Join a couple group first.", "error")
        return redirect(url_for("dashboard.home"))
    partner = current_user.couple_group.partner_of(current_user) if current_user.couple_group else None

    form = GoalForm()
    cats = Category.query.filter_by(couple_group_id=current_user.couple_group_id).order_by(Category.name).all()

    if form.validate_on_submit():
        if not partner:
            flash("You need a partner before creating goals.", "error")
            return redirect(url_for("goals.index"))
        cat, err = validate_threshold_form(form, current_user.couple_group_id)
        if err:
            flash(err, "error")
            return redirect(url_for("goals.index"))
        goal = Goal(
            owner_id=current_user.id,
            label=form.label.data.strip(),
            goal_type=form.goal_type.data,
            condition_type=form.condition_type.data,
            category_id=cat.id if cat else None,
            threshold=form.threshold.data,
            threshold_currency=form.threshold_currency.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status="pending",
        )
        db.session.add(goal)
        db.session.flush()
        db.session.add(Notification(
            recipient_id=partner.id,
            type="goal_pending",
            message=f"Approval needed: {goal.label}",
            payload=f"goal:{goal.id}",
        ))
        db.session.commit()
        flash("Goal submitted for partner approval.", "success")
        return redirect(url_for("goals.index"))

    my_goals = Goal.query.filter_by(owner_id=current_user.id).order_by(Goal.created_at.desc()).all()
    pending_for_me = []
    if partner:
        pending_for_me = Goal.query.filter_by(owner_id=partner.id, status="pending").all()
    return render_template("goals/index.html", form=form, my_goals=my_goals,
                           pending_for_me=pending_for_me, categories=cats)


@bp.route("/<int:goal_id>/approve", methods=["POST"])
@login_required
def approve(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    partner = current_user.couple_group.partner_of(current_user) if current_user.couple_group else None
    if not partner or goal.owner_id != partner.id:
        abort(403)
    if goal.status != "pending":
        flash("Goal is no longer pending.", "error")
        return redirect(request.referrer or url_for("goals.index"))
    goal.status = "active"
    db.session.add(Notification(
        recipient_id=goal.owner_id,
        type="goal_approved",
        message=f"Partner approved goal: {goal.label}",
        payload=f"goal:{goal.id}",
    ))
    db.session.commit()
    flash("Goal approved.", "success")
    return redirect(request.referrer or url_for("goals.index"))


@bp.route("/<int:goal_id>/reject", methods=["POST"])
@login_required
def reject(goal_id):
    goal = Goal.query.get_or_404(goal_id)
    partner = current_user.couple_group.partner_of(current_user) if current_user.couple_group else None
    if not partner or goal.owner_id != partner.id:
        abort(403)
    if goal.status != "pending":
        flash("Goal is no longer pending.", "error")
        return redirect(request.referrer or url_for("goals.index"))
    goal.status = "rejected"
    db.session.add(Notification(
        recipient_id=goal.owner_id,
        type="goal_rejected",
        message=f"Partner rejected goal: {goal.label}",
        payload=f"goal:{goal.id}",
    ))
    db.session.commit()
    flash("Goal rejected.", "success")
    return redirect(request.referrer or url_for("goals.index"))
