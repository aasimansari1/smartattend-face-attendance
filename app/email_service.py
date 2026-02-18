from flask import current_app, render_template_string
from flask_mail import Message
from app import mail, db
from app.models import Student, Notification

LOW_ATTENDANCE_TEMPLATE = """
<h2>Low Attendance Alert</h2>
<p>Dear {{ recipient_name }},</p>
<p>This is to inform you that <strong>{{ student_name }}</strong> (Roll: {{ roll_number }})
has an attendance of <strong>{{ percentage }}%</strong> in <strong>{{ course_name }}</strong> ({{ course_code }}).</p>
<p>The minimum required attendance is <strong>{{ threshold }}%</strong>.</p>
<p>Current Stats: {{ present }}/{{ total }} sessions attended.</p>
<p>Please take necessary action.</p>
<br>
<p>Regards,<br>College Attendance Management System</p>
"""

ABSENT_ALERT_TEMPLATE = """
<h2>Absence Notification</h2>
<p>Dear {{ recipient_name }},</p>
<p><strong>{{ student_name }}</strong> (Roll: {{ roll_number }}) was marked
<strong>absent</strong> for <strong>{{ course_name }}</strong> on {{ date }}.</p>
<br>
<p>Regards,<br>College Attendance Management System</p>
"""


def send_low_attendance_alert(student, course, present, total, threshold):
    """Send low attendance email to student and parent."""
    percentage = round((present / total * 100), 1) if total > 0 else 0

    context = {
        'student_name': student.name,
        'roll_number': student.roll_number,
        'course_name': course.name,
        'course_code': course.code,
        'percentage': percentage,
        'threshold': threshold,
        'present': present,
        'total': total,
    }

    # Notify student
    try:
        context['recipient_name'] = student.name
        body = render_template_string(LOW_ATTENDANCE_TEMPLATE, **context)
        msg = Message(
            subject=f'Low Attendance Alert - {course.code}',
            recipients=[student.user.email],
            html=body,
        )
        mail.send(msg)
    except Exception as e:
        current_app.logger.error(f'Failed to send email to student: {e}')

    # Notify parent
    if student.parent_email:
        try:
            context['recipient_name'] = 'Parent/Guardian'
            body = render_template_string(LOW_ATTENDANCE_TEMPLATE, **context)
            msg = Message(
                subject=f'Low Attendance Alert for {student.name} - {course.code}',
                recipients=[student.parent_email],
                html=body,
            )
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f'Failed to send email to parent: {e}')

    # Create in-app notification
    notification = Notification(
        user_id=student.user_id,
        title=f'Low Attendance: {course.code}',
        message=f'Your attendance in {course.code} is {percentage}%, below the required {threshold}%.',
        type='warning',
    )
    db.session.add(notification)
    db.session.commit()


def send_absent_notification(student, course, session_date):
    """Send absence notification email."""
    context = {
        'student_name': student.name,
        'roll_number': student.roll_number,
        'course_name': course.name,
        'date': session_date.strftime('%Y-%m-%d'),
    }

    if student.parent_email:
        try:
            context['recipient_name'] = 'Parent/Guardian'
            body = render_template_string(ABSENT_ALERT_TEMPLATE, **context)
            msg = Message(
                subject=f'Absence Alert: {student.name} - {course.code} ({session_date})',
                recipients=[student.parent_email],
                html=body,
            )
            mail.send(msg)
        except Exception as e:
            current_app.logger.error(f'Failed to send absence alert: {e}')


def check_and_alert_low_attendance(course_id, threshold=None):
    """Check all enrolled students and send alerts for low attendance."""
    from app.models import Course, Enrollment, AttendanceSession, Attendance

    if threshold is None:
        threshold = current_app.config['LOW_ATTENDANCE_THRESHOLD']

    course = Course.query.get(course_id)
    if not course:
        return

    sessions = AttendanceSession.query.filter_by(course_id=course_id).all()
    total = len(sessions)
    if total == 0:
        return

    enrolled = Enrollment.query.filter_by(course_id=course_id).all()
    for e in enrolled:
        student = Student.query.get(e.student_id)
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_([s.id for s in sessions]),
            Attendance.status == 'present'
        ).count()
        percentage = round((present / total * 100), 1)
        if percentage < threshold:
            send_low_attendance_alert(student, course, present, total, threshold)
