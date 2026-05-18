"""Spend entry form. `validate_date` rejects future dates so a fresh entry
can immediately drive `evaluate_for_user` without needing to model 'pending'
future spend."""
from datetime import date
from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from ..auth.forms import currency_choices


class SpendForm(FlaskForm):
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=Decimal("0.01"), max=Decimal("100000000"))])
    currency = SelectField("Currency", choices=currency_choices)
    date = DateField("Date", validators=[DataRequired()])
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Add spend")

    def validate_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Date cannot be in the future.")
