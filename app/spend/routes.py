from datetime import date

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import SpendEntry, Category
from ..services.evaluation import evaluate_for_user
from .forms import SpendForm

bp = Blueprint("spend", __name__, template_folder="../templates")


def _categories():
    return Category.query.filter_by(couple_group_id=current_user.couple_group_id).order_by(Category.name).all()


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if not current_user.couple_group_id:
        flash("Create or join a couple group first.", "error")
        return redirect(url_for("dashboard.home"))

    form = SpendForm()
    cats = _categories()
    form.category_id.choices = [(c.id, c.name) for c in cats]
    if request.method == "GET":
        form.currency.data = current_user.preferred_currency
        form.date.data = date.today()

    if form.validate_on_submit():
        # Authorization: category must belong to my couple group.
        cat = Category.query.filter_by(id=form.category_id.data,
                                       couple_group_id=current_user.couple_group_id).first()
        if not cat:
            abort(403)
        entry = SpendEntry(
            user_id=current_user.id,
            amount=form.amount.data,
            original_currency=form.currency.data,
            date=form.date.data,
            description=(form.description.data or "").strip() or None,
            category_id=cat.id,
        )
        db.session.add(entry)
        db.session.commit()
        evaluate_for_user(current_user, on_date=entry.date)
        flash("Spend logged.", "success")
        return redirect(url_for("spend.index"))

    entries = (SpendEntry.query.filter_by(user_id=current_user.id)
               .order_by(SpendEntry.date.desc(), SpendEntry.id.desc()).limit(50).all())
    return render_template("spend/index.html", form=form, entries=entries, categories=cats)


@bp.route("/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete(entry_id):
    entry = SpendEntry.query.get_or_404(entry_id)
    if entry.user_id != current_user.id:
        abort(403)
    db.session.delete(entry)
    db.session.commit()
    flash("Spend deleted.", "success")
    return redirect(url_for("spend.index"))
