import io
import csv
from datetime import datetime, date
from flask import Blueprint, jsonify, request, send_file, current_app
from flask_login import login_required, current_user
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from app import db
from app.models import (Student, Faculty, Course, Enrollment,
                        AttendanceSession, Attendance)
from app.utils import role_required

api_bp = Blueprint('api', __name__)


@api_bp.route('/attendance/stats/<int:course_id>')
@login_required
@role_required('faculty', 'admin')
def attendance_stats(course_id):
    """Get attendance statistics for a course (JSON for charts)."""
    sessions = (AttendanceSession.query
                .filter_by(course_id=course_id)
                .order_by(AttendanceSession.date)
                .all())

    data = {'dates': [], 'present': [], 'absent': [], 'total': []}
    for session in sessions:
        records = Attendance.query.filter_by(session_id=session.id).all()
        present = sum(1 for r in records if r.status == 'present')
        total = len(records)
        data['dates'].append(session.date.strftime('%Y-%m-%d'))
        data['present'].append(present)
        data['absent'].append(total - present)
        data['total'].append(total)

    return jsonify(data)


@api_bp.route('/analytics/department/<department>')
@login_required
@role_required('admin')
def department_analytics(department):
    """Get department-wide analytics."""
    students = Student.query.filter_by(department=department).all()
    courses = Course.query.filter_by(department=department).all()

    course_data = []
    for course in courses:
        sessions = AttendanceSession.query.filter_by(course_id=course.id).all()
        total_sessions = len(sessions)
        if total_sessions == 0:
            continue

        total_present = 0
        total_records = 0
        for s in sessions:
            records = Attendance.query.filter_by(session_id=s.id).all()
            total_present += sum(1 for r in records if r.status == 'present')
            total_records += len(records)

        avg = round((total_present / total_records * 100), 1) if total_records > 0 else 0
        course_data.append({
            'code': course.code,
            'name': course.name,
            'sessions': total_sessions,
            'avg_attendance': avg,
        })

    return jsonify({
        'department': department,
        'total_students': len(students),
        'total_courses': len(courses),
        'courses': course_data,
    })


@api_bp.route('/report/csv/<int:course_id>')
@login_required
@role_required('faculty', 'admin')
def export_csv(course_id):
    """Export course attendance as CSV."""
    course = Course.query.get_or_404(course_id)
    sessions = (AttendanceSession.query
                .filter_by(course_id=course_id)
                .order_by(AttendanceSession.date)
                .all())
    enrolled = Enrollment.query.filter_by(course_id=course_id).all()

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    header = ['Roll Number', 'Name']
    for s in sessions:
        header.append(s.date.strftime('%Y-%m-%d'))
    header.extend(['Present', 'Total', 'Percentage'])
    writer.writerow(header)

    for e in enrolled:
        student = Student.query.get(e.student_id)
        row = [student.roll_number, student.name]
        present_count = 0
        for s in sessions:
            record = Attendance.query.filter_by(
                session_id=s.id, student_id=student.id
            ).first()
            status = record.status[0].upper() if record else 'A'
            row.append(status)
            if record and record.status == 'present':
                present_count += 1
        total = len(sessions)
        pct = round((present_count / total * 100), 1) if total > 0 else 0
        row.extend([present_count, total, f'{pct}%'])
        writer.writerow(row)

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'attendance_{course.code}_{date.today()}.csv'
    )


@api_bp.route('/report/pdf/<int:course_id>')
@login_required
@role_required('faculty', 'admin')
def export_pdf(course_id):
    """Export course attendance as PDF."""
    course = Course.query.get_or_404(course_id)
    sessions = (AttendanceSession.query
                .filter_by(course_id=course_id)
                .order_by(AttendanceSession.date)
                .all())
    enrolled = Enrollment.query.filter_by(course_id=course_id).all()
    threshold = current_app.config['LOW_ATTENDANCE_THRESHOLD']

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=30, bottomMargin=30)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(f'Attendance Report: {course.code} - {course.name}', styles['Title']))
    elements.append(Paragraph(f'Department: {course.department} | Semester: {course.semester} | Section: {course.section}', styles['Normal']))
    elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', styles['Normal']))
    elements.append(Spacer(1, 20))

    # Summary table
    data = [['Roll Number', 'Name', 'Present', 'Total', 'Percentage', 'Status']]
    for e in enrolled:
        student = Student.query.get(e.student_id)
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_([s.id for s in sessions]),
            Attendance.status == 'present'
        ).count()
        total = len(sessions)
        pct = round((present / total * 100), 1) if total > 0 else 0
        status = 'OK' if pct >= threshold else 'LOW'
        data.append([student.roll_number, student.name, str(present), str(total), f'{pct}%', status])

    if len(data) > 1:
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#ecf0f1')]),
        ]))
        elements.append(table)
    else:
        elements.append(Paragraph('No enrollment data available.', styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'attendance_{course.code}_{date.today()}.pdf'
    )


@api_bp.route('/students/low-attendance/<int:course_id>')
@login_required
@role_required('faculty', 'admin')
def low_attendance_students(course_id):
    """Get students below attendance threshold."""
    course = Course.query.get_or_404(course_id)
    sessions = AttendanceSession.query.filter_by(course_id=course_id).all()
    enrolled = Enrollment.query.filter_by(course_id=course_id).all()
    threshold = current_app.config['LOW_ATTENDANCE_THRESHOLD']
    total_sessions = len(sessions)

    low_students = []
    for e in enrolled:
        student = Student.query.get(e.student_id)
        present = Attendance.query.filter(
            Attendance.student_id == student.id,
            Attendance.session_id.in_([s.id for s in sessions]),
            Attendance.status == 'present'
        ).count()
        pct = round((present / total_sessions * 100), 1) if total_sessions > 0 else 0
        if pct < threshold:
            low_students.append({
                'roll_number': student.roll_number,
                'name': student.name,
                'present': present,
                'total': total_sessions,
                'percentage': pct,
                'email': student.user.email,
                'parent_email': student.parent_email,
            })

    return jsonify({'threshold': threshold, 'students': low_students})
