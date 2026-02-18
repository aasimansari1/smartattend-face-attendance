import os
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (User, Student, Faculty, Course, Enrollment,
                        Attendance, AttendanceSession, Notification)
from app.forms import StudentRegistrationForm, FacultyRegistrationForm, CourseForm
from app.utils import role_required, save_upload, allowed_file
from app.face_recognition_module import face_system

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    stats = {
        'total_students': Student.query.count(),
        'total_faculty': Faculty.query.count(),
        'total_courses': Course.query.count(),
        'active_sessions': AttendanceSession.query.filter_by(status='active').count(),
        'today_sessions': AttendanceSession.query.filter(
            AttendanceSession.date == datetime.today().date()
        ).count(),
    }
    recent_sessions = (AttendanceSession.query
                       .order_by(AttendanceSession.created_at.desc())
                       .limit(10).all())
    return render_template('admin/dashboard.html', stats=stats, recent_sessions=recent_sessions)


@admin_bp.route('/students')
@login_required
@role_required('admin')
def students():
    page = request.args.get('page', 1, type=int)
    dept = request.args.get('department', '')
    query = Student.query
    if dept:
        query = query.filter_by(department=dept)
    students = query.order_by(Student.roll_number).paginate(page=page, per_page=20)
    return render_template('admin/students.html', students=students, department=dept)


@admin_bp.route('/students/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_student():
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        if not form.password.data:
            flash('Password is required for new students.', 'danger')
            return render_template('admin/add_student.html', form=form)
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/add_student.html', form=form)
        if Student.query.filter_by(roll_number=form.roll_number.data).first():
            flash('Roll number already exists.', 'danger')
            return render_template('admin/add_student.html', form=form)

        user = User(email=form.email.data, role='student')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        student = Student(
            user_id=user.id,
            roll_number=form.roll_number.data,
            name=form.name.data,
            department=form.department.data,
            semester=form.semester.data,
            section=form.section.data,
            phone=form.phone.data,
            parent_email=form.parent_email.data,
        )

        if form.photo.data:
            filename = f"{form.roll_number.data}.jpg"
            filepath = save_upload(form.photo.data, current_app.config['UPLOAD_FOLDER'], filename)
            student.photo_path = filepath

            encoding = face_system.encode_face(filepath)
            if encoding:
                student.face_encoding = encoding
            else:
                flash('No face detected in photo. Please upload a clear face photo.', 'warning')

        db.session.add(student)
        db.session.commit()
        flash(f'Student {student.name} registered successfully.', 'success')
        return redirect(url_for('admin.students'))

    return render_template('admin/add_student.html', form=form)


@admin_bp.route('/students/<int:student_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_student(student_id):
    student = Student.query.get_or_404(student_id)
    form = StudentRegistrationForm(obj=student)

    if form.validate_on_submit():
        student.name = form.name.data
        student.department = form.department.data
        student.semester = form.semester.data
        student.section = form.section.data
        student.phone = form.phone.data
        student.parent_email = form.parent_email.data
        student.user.email = form.email.data

        if form.password.data:
            student.user.set_password(form.password.data)

        if form.photo.data:
            filename = f"{student.roll_number}.jpg"
            filepath = save_upload(form.photo.data, current_app.config['UPLOAD_FOLDER'], filename)
            student.photo_path = filepath
            encoding = face_system.encode_face(filepath)
            if encoding:
                student.face_encoding = encoding

        db.session.commit()
        flash('Student updated successfully.', 'success')
        return redirect(url_for('admin.students'))

    form.email.data = student.user.email
    form.password.data = ''
    return render_template('admin/add_student.html', form=form, editing=True, student=student)


@admin_bp.route('/students/<int:student_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_student(student_id):
    student = Student.query.get_or_404(student_id)
    user = student.user
    db.session.delete(user)
    db.session.commit()
    flash('Student deleted.', 'success')
    return redirect(url_for('admin.students'))


@admin_bp.route('/faculty')
@login_required
@role_required('admin')
def faculty_list():
    faculty = Faculty.query.order_by(Faculty.name).all()
    return render_template('admin/faculty.html', faculty=faculty)


@admin_bp.route('/faculty/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_faculty():
    form = FacultyRegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data).first():
            flash('Email already registered.', 'danger')
            return render_template('admin/add_faculty.html', form=form)

        user = User(email=form.email.data, role='faculty')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        faculty = Faculty(
            user_id=user.id,
            faculty_id=form.faculty_id.data,
            name=form.name.data,
            department=form.department.data,
            phone=form.phone.data,
        )
        db.session.add(faculty)
        db.session.commit()
        flash(f'Faculty {faculty.name} registered successfully.', 'success')
        return redirect(url_for('admin.faculty_list'))

    return render_template('admin/add_faculty.html', form=form)


@admin_bp.route('/courses')
@login_required
@role_required('admin')
def courses():
    courses = Course.query.order_by(Course.code).all()
    return render_template('admin/courses.html', courses=courses)


@admin_bp.route('/courses/add', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def add_course():
    form = CourseForm()
    form.faculty_id.choices = [(0, 'Not Assigned')] + [
        (f.id, f'{f.name} ({f.faculty_id})') for f in Faculty.query.order_by(Faculty.name).all()
    ]

    if form.validate_on_submit():
        course = Course(
            code=form.code.data,
            name=form.name.data,
            department=form.department.data,
            semester=form.semester.data,
            section=form.section.data,
            faculty_id=form.faculty_id.data if form.faculty_id.data != 0 else None,
            schedule=form.schedule.data,
        )
        db.session.add(course)
        db.session.commit()

        # Auto-enroll students matching department/semester/section
        matching_students = Student.query.filter_by(
            department=course.department,
            semester=course.semester,
            section=course.section
        ).all()
        for s in matching_students:
            enrollment = Enrollment(student_id=s.id, course_id=course.id)
            db.session.add(enrollment)
        db.session.commit()

        flash(f'Course {course.code} created. {len(matching_students)} students auto-enrolled.', 'success')
        return redirect(url_for('admin.courses'))

    return render_template('admin/add_course.html', form=form)


@admin_bp.route('/analytics')
@login_required
@role_required('admin')
def analytics():
    departments = db.session.query(Student.department).distinct().all()
    dept_stats = []
    for (dept,) in departments:
        total = Student.query.filter_by(department=dept).count()
        dept_stats.append({'department': dept, 'total_students': total})

    return render_template('admin/analytics.html', dept_stats=dept_stats)
