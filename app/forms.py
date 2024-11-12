from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, URLField, SubmitField
from wtforms.validators import DataRequired, URL, Length

class EnrollForm(FlaskForm):
    ASVZ_ID = StringField('ASVZ ID', validators=[DataRequired(), Length(max=100)])
    ASVZ_Password = PasswordField('ASVZ Password', validators=[DataRequired(), Length(min=6)])
    URL = URLField('URL', validators=[DataRequired(), URL()])
    submit = SubmitField('Submit')


