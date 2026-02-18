from datetime import datetime, date, time
from flask import (Blueprint, render_template, redirect, url_for, flash,
                   request, current_app, jsonify)
from flask_login import login_required, current_user
from app import db
from app.models import (Faculty, Course, Enrollment, Student,
                        AttendanceSession, Attendance, Notification)
from app.forms import AttendanceSessionForm
from app.utils import role_required
from app.face_recognition_module import face_system

faculty_bp = Blueprint('faculty', __name__)


@faculty_bp.route('/dashboard')
@login_required
@role_required('faculty')
def dashboard():
    faculty = Faculty.query.filter_by(user_id=current_user.id).first_or_404()
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    active_sessions = AttendanceSession.query.filter(
        AttendanceSession.course_id.in_([c.id for c in courses]),
        AttendanceSession.status == 'active'
    ).all()
    today_sessions = AttendanceSession.query.filter(
        AttendanceSession.course_id.in_([c.id for c in courses]),
        AttendanceSession.date == date.today()
    ).all()

    return render_template('faculty/dashboard.html',
                           faculty=faculty, courses=courses,
                           active_sessions=active_sessions,
                           today_sessions=today_sessions)


@faculty_bp.route('/courses')
@login_required
@role_required('faculty')
def courses():
    faculty = Faculty.query.filter_by(user_id=current_user.id).first_or_404()
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    return render_template('faculty/courses.html', courses=courses)


@faculty_bp.route('/attendance/start', methods=['GET', 'POST'])
@login_required
@role_required('faculty')
def start_attendance():
    faculty = Faculty.query.filter_by(user_id=current_user.id).first_or_404()
    form = AttendanceSessionForm()
    form.course_id.choices = [
        (c.id, f'{c.code} - {c.name}')
        for c in Course.query.filter_by(faculty_id=faculty.id).all()
    ]

    if form.validate_on_submit():
        session = AttendanceSession(
            course_id=form.course_id.data,
            date=form.date.data,
            start_time=form.start_time.data,
            status='active',
            created_by=current_user.id,
        )
        db.session.add(session)
        db.session.flush()

        # Pre-fill absent records for all enrolled students
        enrolled = Enrollment.query.filter_by(course_id=form.course_id.data).all()
        for e in enrolled:
            record = Attendance(
                session_id=session.id,
                student_id=e.student_id,
                status='absent',
                marked_by='manual',
            )
            db.session.add(record)

        db.session.commit()
        flash('Attendance session started.', 'success')
        return redirect(url_for('faculty.mark_attendance', session_id=session.id))

    form.date.data = date.today()
    form.start_time.data = datetime.now().time().replace(second=0, microsecond=0)
    return render_template('faculty/start_attendance.html', form=form)


@faculty_bp.route('/attendance/<int:session_id>')
@login_required
@role_required('faculty')
def mark_attendance(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    course = Course.query.get(session.course_id)
    records = (Attendance.query
               .filter_by(session_id=session_id)
               .join(Student)
               .order_by(Student.roll_number)
               .all())

    students_map = {}
    for r in records:
        students_map[r.student_id] = {
            'record': r,
            'student': r.student,
        }

    return render_template('faculty/mark_attendance.html',
                           session=session, course=course,
                           students_map=students_map)


@faculty_bp.route('/attendance/<int:session_id>/manual', methods=['POST'])
@login_required
@role_required('faculty')
def manual_attendance(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    present_ids = request.form.getlist('present')

    records = Attendance.query.filter_by(session_id=session_id).all()
    for record in records:
        record.status = 'present' if str(record.student_id) in present_ids else 'absent'
        record.marked_by = 'manual'
        record.marked_at = datetime.utcnow()

    db.session.commit()
    flash('Attendance updated manually.', 'success')
    return redirect(url_for('faculty.mark_attendance', session_id=session_id))


@faculty_bp.route('/attendance/<int:session_id>/face', methods=['POST'])
@login_required
@role_required('faculty')
def face_attendance(session_id):
    """Process uploaded image for face recognition attendance."""
    session = AttendanceSession.query.get_or_404(session_id)

    if 'image' not in request.files:
        flash('No image uploaded.', 'danger')
        return redirect(url_for('faculty.mark_attendance', session_id=session_id))

    image_file = request.files['image']
    image_data = image_file.read()

    # Load enrolled students' face encodings
    enrolled_ids = [e.student_id for e in Enrollment.query.filter_by(course_id=session.course_id).all()]
    students = Student.query.filter(Student.id.in_(enrolled_ids)).all()
    face_system.load_known_faces(students)

    # Recognize faces
    results = face_system.recognize_from_image(image_data)
    recognized_count = 0

    for student_id, confidence in results:
        record = Attendance.query.filter_by(
            session_id=session_id, student_id=student_id
        ).first()
        if record:
            record.status = 'present'
            record.marked_by = 'face_recognition'
            record.confidence = confidence
            record.marked_at = datetime.utcnow()
            recognized_count += 1

    db.session.commit()
    flash(f'Face recognition complete. {recognized_count} student(s) recognized.', 'success')
    return redirect(url_for('faculty.mark_attendance', session_id=session_id))


@faculty_bp.route('/attendance/<int:session_id>/close', methods=['POST'])
@login_required
@role_required('faculty')
def close_session(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    session.status = 'closed'
    session.end_time = datetime.now().time()
    db.session.commit()
    flash('Session closed.', 'success')
    return redirect(url_for('faculty.session_report', session_id=session_id))


@faculty_bp.route('/attendance/<int:session_id>/report')
@login_required
@role_required('faculty')
def session_report(session_id):
    session = AttendanceSession.query.get_or_404(session_id)
    course = Course.query.get(session.course_id)
    records = (Attendance.query
               .filter_by(session_id=session_id)
               .join(Student)
               .order_by(Student.roll_number)
               .all())

    present = sum(1 for r in records if r.status == 'present')
    total = len(records)

    return render_template('faculty/session_report.html',
                           session=session, course=course, records=records,
                           present=present, total=total)


@faculty_bp.route('/reports')
@login_required
@role_required('faculty')
def reports():
    faculty = Faculty.query.filter_by(user_id=current_user.id).first_or_404()
    courses = Course.query.filter_by(faculty_id=faculty.id).all()
    return render_template('faculty/reports.html', courses=courses)


@faculty_bp.route('/reports/course/<int:course_id>')
@login_required
@role_required('faculty')
def course_report(course_id):
    course = Course.query.get_or_404(course_id)
    enrolled = Enrollment.query.filter_by(course_id=course_id).all()
    sessions = AttendanceSession.query.filter_by(course_id=course_id).order_by(AttendanceSession.date).all()
    total_sessions = len(sessions)

    student_stats = []
    for e in enrolled:
        student = Student.query.get(e.student_id)
        present_count = Attendance.query.filter(
            Attendance.student_id == e.student_id,
            Attendance.session_id.in_([s.id for s in sessions]),
            Attendance.status == 'present'
        ).count()
        percentage = round((present_count / total_sessions * 100), 1) if total_sessions > 0 else 0
        student_stats.append({
            'student': student,
            'present': present_count,
            'total': total_sessions,
            'percentage': percentage,
        })

    student_stats.sort(key=lambda x: x['student'].roll_number)
    threshold = current_app.config['LOW_ATTENDANCE_THRESHOLD']

    return render_template('faculty/course_report.html',
                           course=course, student_stats=student_stats,
                           total_sessions=total_sessions, threshold=threshold)
