"""Category creation endpoint.

Single POST `/categories/` that accepts either form-encoded or JSON. The JSON
path is for the inline 'Add new category' button on the spend form
(`category_inline.js`); the form path is for ordinary submits. On duplicate
name within the same couple group it returns the existing category instead
of erroring — clients can treat 'create' as idempotent.
"""
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
    payload = request.get_json(silent=True) or {}
    name = (request.form.get("name") or payload.get("name") or "").strip()
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
        # UniqueConstraint(couple_group_id, name) hit: treat as idempotent —
        # return the existing row so the spend form can just select it.
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
