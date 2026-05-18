"""Auth forms (register, login, profile) plus the shared `currency_choices`
callable used by every form that needs a currency dropdown."""
from flask import current_app
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo


def currency_choices():
    # Resolved per request so the canonical list in app.config stays the single source of truth.
    return [(c, c) for c in current_app.config["SUPPORTED_CURRENCIES"]]


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Confirm", validators=[DataRequired(), EqualTo("password")])
    preferred_currency = SelectField("Preferred currency", choices=currency_choices, default="USD")
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=1, max=128)])
    submit = SubmitField("Log in")


class ProfileForm(FlaskForm):
    preferred_currency = SelectField("Preferred currency", choices=currency_choices)
    submit = SubmitField("Save")
