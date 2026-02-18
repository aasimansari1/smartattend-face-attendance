from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from app import db
from app.models import Student, Enrollment, Course, AttendanceSession, Attendance, Notification
from app.utils import role_required

student_bp = Blueprint('student', __name__)


@student_bp.route('/dashboard')
@login_required
@role_required('student')
def dashboard():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()
    enrollments = Enrollment.query.filter_by(student_id=student.id).all()
    courses = [Course.query.get(e.course_id) for e in enrollments]

    course_stats = []
    for course in courses:
        sessions = AttendanceSession.query.filter_by(course_id=course.id).all()
        total = len(sessions)
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_([s.id for s in sessions]),
            Attendance.status == 'present'
        ).count()
        percentage = round((present / total * 100), 1) if total > 0 else 0
        course_stats.append({
            'course': course,
            'present': present,
            'total': total,
            'percentage': percentage,
        })

    threshold = current_app.config['LOW_ATTENDANCE_THRESHOLD']
    notifications = (Notification.query
                     .filter_by(user_id=current_user.id)
                     .order_by(Notification.created_at.desc())
                     .limit(10).all())

    return render_template('student/dashboard.html',
                           student=student, course_stats=course_stats,
                           threshold=threshold, notifications=notifications)


@student_bp.route('/attendance')
@login_required
@role_required('student')
def attendance():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()
    enrollments = Enrollment.query.filter_by(student_id=student.id).all()
    courses = [Course.query.get(e.course_id) for e in enrollments]

    attendance_data = {}
    for course in courses:
        sessions = (AttendanceSession.query
                    .filter_by(course_id=course.id)
                    .order_by(AttendanceSession.date.desc())
                    .all())
        records = []
        for session in sessions:
            record = Attendance.query.filter_by(
                session_id=session.id, student_id=student.id
            ).first()
            records.append({
                'date': session.date,
                'start_time': session.start_time,
                'status': record.status if record else 'N/A',
                'marked_by': record.marked_by if record else '',
            })
        attendance_data[course] = records

    return render_template('student/attendance.html',
                           student=student, attendance_data=attendance_data)


@student_bp.route('/analytics')
@login_required
@role_required('student')
def analytics():
    student = Student.query.filter_by(user_id=current_user.id).first_or_404()
    enrollments = Enrollment.query.filter_by(student_id=student.id).all()
    courses = [Course.query.get(e.course_id) for e in enrollments]

    chart_data = {'labels': [], 'present': [], 'absent': [], 'percentages': []}
    for course in courses:
        sessions = AttendanceSession.query.filter_by(course_id=course.id).all()
        total = len(sessions)
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_([s.id for s in sessions]),
            Attendance.status == 'present'
        ).count()
        absent = total - present
        percentage = round((present / total * 100), 1) if total > 0 else 0

        chart_data['labels'].append(course.code)
        chart_data['present'].append(present)
        chart_data['absent'].append(absent)
        chart_data['percentages'].append(percentage)

    threshold = current_app.config['LOW_ATTENDANCE_THRESHOLD']
    return render_template('student/analytics.html',
                           student=student, chart_data=chart_data, threshold=threshold)
