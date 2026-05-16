from decimal import Decimal

from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, DecimalField, SubmitField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, AnyOf, Optional

from ..auth.forms import currency_choices


GOAL_TYPES = [
    ("cap", "Spending Cap — rewarded for staying below the amount"),
    ("target", "Spending Target — rewarded for reaching the amount"),
]


class _ThresholdFormBase(FlaskForm):
    label = StringField("Label", validators=[DataRequired(), Length(max=120)])
    condition_type = SelectField("Condition", choices=[("total", "Total spend"), ("category", "Specific category")],
                                 validators=[AnyOf(["total", "category"])])
    category_id = IntegerField("Category", validators=[Optional()])
    threshold = DecimalField("Threshold", places=2, validators=[DataRequired(),
                              NumberRange(min=Decimal("0.01"), max=Decimal("100000000"))])
    threshold_currency = SelectField("Currency", choices=currency_choices)
    start_date = DateField("Start date", validators=[DataRequired()])
    end_date = DateField("End date", validators=[DataRequired()])


class GoalForm(_ThresholdFormBase):
    goal_type = SelectField("Goal type", choices=GOAL_TYPES,
                            validators=[AnyOf([k for k, _ in GOAL_TYPES])], default="cap")
    submit = SubmitField("Submit goal")


class TripWireForm(_ThresholdFormBase):
    submit = SubmitField("Set trip wire")
