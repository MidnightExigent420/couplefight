"""Shared form validation for Goal and TripWire — both check the same
(date range, category-belongs-to-group) invariants."""
from __future__ import annotations

from ..models import Category


def validate_threshold_form(form, group_id: int) -> tuple[Category | None, str | None]:
    """Validate the shared date/category invariants on a goal or tripwire form.

    Returns (cat, error_message). ``error_message`` is None on success.
    ``cat`` is the resolved Category for category-scoped forms, else None.
    """
    if form.end_date.data < form.start_date.data:
        return None, "End date must be on or after start date."
    if form.condition_type.data != "category":
        return None, None
    if not form.category_id.data:
        return None, "Pick a category."
    cat = Category.query.filter_by(id=form.category_id.data, couple_group_id=group_id).first()
    if not cat:
        return None, "Invalid category."
    return cat, None
