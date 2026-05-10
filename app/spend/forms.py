from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, AnyOf, Optional

from ..auth.forms import SUPPORTED


class SpendForm(FlaskForm):
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=Decimal("0.01"), max=Decimal("100000000"))])
    currency = SelectField("Currency", choices=[(c, c) for c in SUPPORTED], validators=[AnyOf(SUPPORTED)])
    date = DateField("Date", validators=[DataRequired()])
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Add spend")
