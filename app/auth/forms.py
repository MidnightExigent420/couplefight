from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, AnyOf


SUPPORTED = ["USD", "EUR", "GBP", "SGD", "JPY", "AUD", "CAD", "CHF", "CNY", "HKD", "INR", "NZD"]


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    confirm = PasswordField("Confirm", validators=[DataRequired(), EqualTo("password")])
    preferred_currency = SelectField("Preferred currency", choices=[(c, c) for c in SUPPORTED], default="USD",
                                     validators=[AnyOf(SUPPORTED)])
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=254)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=1, max=128)])
    submit = SubmitField("Log in")


class ProfileForm(FlaskForm):
    preferred_currency = SelectField("Preferred currency", choices=[(c, c) for c in SUPPORTED],
                                     validators=[AnyOf(SUPPORTED)])
    submit = SubmitField("Save")
