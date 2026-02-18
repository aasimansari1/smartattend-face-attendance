from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, PasswordField, SelectField, IntegerField,
                     SubmitField, HiddenField, TimeField, DateField)
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class StudentRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Optional(), Length(min=6)])
    roll_number = StringField('Roll Number', validators=[DataRequired(), Length(max=20)])
    department = SelectField('Department', validators=[DataRequired()], choices=[
        ('Computer Science', 'Computer Science'),
        ('Electronics', 'Electronics'),
        ('Mechanical', 'Mechanical'),
        ('Civil', 'Civil'),
        ('Electrical', 'Electrical'),
        ('Information Technology', 'Information Technology'),
    ])
    semester = IntegerField('Semester', validators=[DataRequired(), NumberRange(min=1, max=8)])
    section = StringField('Section', validators=[DataRequired(), Length(max=10)])
    phone = StringField('Phone', validators=[Optional(), Length(max=15)])
    parent_email = StringField('Parent Email', validators=[Optional(), Email()])
    photo = FileField('Photo', validators=[FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')])
    submit = SubmitField('Register Student')


class FacultyRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    faculty_id = StringField('Faculty ID', validators=[DataRequired(), Length(max=20)])
    department = SelectField('Department', validators=[DataRequired()], choices=[
        ('Computer Science', 'Computer Science'),
        ('Electronics', 'Electronics'),
        ('Mechanical', 'Mechanical'),
        ('Civil', 'Civil'),
        ('Electrical', 'Electrical'),
        ('Information Technology', 'Information Technology'),
    ])
    phone = StringField('Phone', validators=[Optional(), Length(max=15)])
    submit = SubmitField('Register Faculty')


class CourseForm(FlaskForm):
    code = StringField('Course Code', validators=[DataRequired(), Length(max=20)])
    name = StringField('Course Name', validators=[DataRequired(), Length(max=150)])
    department = SelectField('Department', validators=[DataRequired()], choices=[
        ('Computer Science', 'Computer Science'),
        ('Electronics', 'Electronics'),
        ('Mechanical', 'Mechanical'),
        ('Civil', 'Civil'),
        ('Electrical', 'Electrical'),
        ('Information Technology', 'Information Technology'),
    ])
    semester = IntegerField('Semester', validators=[DataRequired(), NumberRange(min=1, max=8)])
    section = StringField('Section', validators=[DataRequired(), Length(max=10)])
    faculty_id = SelectField('Assign Faculty', coerce=int, validators=[Optional()])
    schedule = StringField('Schedule', validators=[Optional(), Length(max=255)])
    submit = SubmitField('Save Course')


class AttendanceSessionForm(FlaskForm):
    course_id = SelectField('Course', coerce=int, validators=[DataRequired()])
    date = DateField('Date', validators=[DataRequired()])
    start_time = TimeField('Start Time', validators=[DataRequired()])
    submit = SubmitField('Start Session')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')
