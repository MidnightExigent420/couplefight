from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from ..extensions import db
from ..models import TripWire, Category
from ..goals.forms import TripWireForm

bp = Blueprint("tripwires", __name__, template_folder="../templates")


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    if not current_user.couple_group_id:
        flash("Join a couple group first.", "error")
        return redirect(url_for("dashboard.home"))
    partner = current_user.couple_group.partner_of(current_user) if current_user.couple_group else None

    form = TripWireForm()
    cats = Category.query.filter_by(couple_group_id=current_user.couple_group_id).order_by(Category.name).all()

    if form.validate_on_submit():
        if not partner:
            flash("You need a partner before setting trip wires.", "error")
            return redirect(url_for("tripwires.index"))
        if form.end_date.data < form.start_date.data:
            flash("End date must be on or after start date.", "error")
            return redirect(url_for("tripwires.index"))
        cat = None
        if form.condition_type.data == "category":
            if not form.category_id.data:
                flash("Pick a category.", "error")
                return redirect(url_for("tripwires.index"))
            cat = Category.query.filter_by(id=form.category_id.data,
                                           couple_group_id=current_user.couple_group_id).first()
            if not cat:
                abort(403)

        tw = TripWire(
            setter_id=current_user.id,
            target_user_id=partner.id,
            label=form.label.data.strip(),
            condition_type=form.condition_type.data,
            category_id=cat.id if cat else None,
            threshold=form.threshold.data,
            threshold_currency=form.threshold_currency.data,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            status="active",
        )
        db.session.add(tw)
        db.session.commit()
        flash("Trip wire set.", "success")
        return redirect(url_for("tripwires.index"))

    my_set = TripWire.query.filter_by(setter_id=current_user.id).order_by(TripWire.created_at.desc()).all()
    against_me = TripWire.query.filter_by(target_user_id=current_user.id).order_by(TripWire.created_at.desc()).all()
    return render_template("tripwires/index.html", form=form, my_set=my_set,
                           against_me=against_me, categories=cats)
