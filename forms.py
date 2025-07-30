from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo, Email

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

class ProfileForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('New Password', validators=[Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[EqualTo('password')])
    submit = SubmitField('Update Profile')

class ParkingLotForm(FlaskForm):
    prime_location_name = StringField('Location Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    pin_code = StringField('PIN Code', validators=[DataRequired(), Length(6, 6)])
    price = FloatField('Price per Hour (₹)', validators=[DataRequired(), NumberRange(min=1)])
    max_number_of_spots = IntegerField('Maximum Parking Spots', 
                                     validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Save')

class BookingForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    vehicle_number = StringField('Vehicle Number', validators=[DataRequired(), Length(min=3, max=20)])
    hours = IntegerField('Booking Time Period (Hours)', validators=[DataRequired(), NumberRange(min=1, max=24)], default=1)
    submit = SubmitField('Book Now')