from flask import Blueprint, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import Category

bp = Blueprint("categories", __name__)


def _require_group():
    if not current_user.couple_group_id:
        abort(403)
    return current_user.couple_group_id


@bp.route("/", methods=["POST"])
@login_required
def create():
    group_id = _require_group()
    name = (request.form.get("name") or request.json and request.json.get("name") or "").strip()
    if not name or len(name) > 60:
        if request.is_json:
            return jsonify({"error": "invalid name"}), 400
        flash("Category name is required (≤ 60 chars).", "error")
        return redirect(request.referrer or url_for("dashboard.home"))

    cat = Category(name=name, couple_group_id=group_id)
    db.session.add(cat)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = Category.query.filter_by(couple_group_id=group_id, name=name).first()
        if request.is_json:
            return jsonify({"id": existing.id, "name": existing.name})
        flash("Category already exists.", "error")
        return redirect(request.referrer or url_for("dashboard.home"))

    if request.is_json:
        return jsonify({"id": cat.id, "name": cat.name})
    flash("Category added.", "success")
    return redirect(request.referrer or url_for("dashboard.home"))
