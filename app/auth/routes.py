"""Auth routes: register, login, logout, profile, couple group create/join/leave.

Couple group default categories are seeded here (not in the model) so the
seed list stays close to the route that creates the group.
"""
import logging

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db, limiter
from ..models import User, CoupleGroup, Category
from .forms import RegisterForm, LoginForm, ProfileForm

bp = Blueprint("auth", __name__, template_folder="../templates")
log = logging.getLogger(__name__)

DEFAULT_CATEGORIES = [
    "Food", "Medical", "Transport", "Shopping",
    "Entertainment", "Utilities", "Travel", "Other",
]


def _seed_categories(group: CoupleGroup):
    for name in DEFAULT_CATEGORIES:
        db.session.add(Category(name=name, couple_group_id=group.id))


@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10/hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(email=form.email.data, preferred_currency=form.preferred_currency.data)
        try:
            user.set_password(form.password.data)
        except ValueError as e:
            flash(str(e), "error")
            return render_template("auth/register.html", form=form)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with that email already exists.", "error")
            return render_template("auth/register.html", form=form)
        login_user(user)
        log.info("User registered: id=%s", user.id)
        return redirect(url_for("dashboard.home"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("20/hour")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            db.session.commit()
            log.info("Login success: id=%s", user.id)
            next_url = request.args.get("next")
            # Open redirect protection: only allow relative paths.
            if next_url and next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("dashboard.home"))
        log.info("Login failure for email=%r", form.email.data)
        flash("Invalid email or password.", "error")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(preferred_currency=current_user.preferred_currency)
    if form.validate_on_submit():
        current_user.preferred_currency = form.preferred_currency.data
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)


@bp.route("/couple/create", methods=["POST"])
@login_required
def create_couple():
    if current_user.couple_group_id:
        flash("You are already in a couple group.", "error")
        return redirect(url_for("dashboard.home"))
    group = CoupleGroup()
    db.session.add(group)
    db.session.flush()
    current_user.couple_group_id = group.id
    _seed_categories(group)
    db.session.commit()
    flash("Couple group created. Share the invite link with your partner.", "success")
    return redirect(url_for("dashboard.home"))


@bp.route("/couple/join/<token>", methods=["GET", "POST"])
@login_required
def join_couple(token):
    group = CoupleGroup.query.filter_by(invite_token=token).first()
    if not group:
        abort(404)
    if current_user.couple_group_id == group.id:
        return redirect(url_for("dashboard.home"))
    if current_user.couple_group_id:
        flash("You are already in a couple group. Leave first to join another.", "error")
        return redirect(url_for("dashboard.home"))
    if group.is_full():
        flash("This couple group is already full.", "error")
        return redirect(url_for("dashboard.home"))

    if request.method == "POST":
        current_user.couple_group_id = group.id
        db.session.commit()
        flash("Joined couple group.", "success")
        return redirect(url_for("dashboard.home"))
    return render_template("auth/join_couple.html", token=token)


@bp.route("/couple/leave", methods=["POST"])
@login_required
def leave_couple():
    current_user.couple_group_id = None
    db.session.commit()
    flash("Left couple group.", "success")
    return redirect(url_for("dashboard.home"))
