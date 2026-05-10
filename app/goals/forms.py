from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, DecimalField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, AnyOf, Optional

from ..auth.forms import SUPPORTED


class GoalForm(FlaskForm):
    label = StringField("Label", validators=[DataRequired(), Length(max=120)])
    condition_type = SelectField("Condition", choices=[("total", "Total spend"), ("category", "Specific category")],
                                 validators=[AnyOf(["total", "category"])])
    category_id = IntegerField("Category", validators=[Optional()])
    threshold = DecimalField("Threshold", places=2, validators=[DataRequired(),
                              NumberRange(min=Decimal("0.01"), max=Decimal("100000000"))])
    threshold_currency = SelectField("Currency", choices=[(c, c) for c in SUPPORTED], validators=[AnyOf(SUPPORTED)])
    start_date = DateField("Start date", validators=[DataRequired()])
    end_date = DateField("End date", validators=[DataRequired()])
    submit = SubmitField("Submit goal")


class TripWireForm(GoalForm):
    submit = SubmitField("Set trip wire")
