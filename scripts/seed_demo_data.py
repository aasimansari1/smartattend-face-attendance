"""Seed the database with comprehensive demo data for testing."""
import sys
import os
import random
from datetime import datetime, date, time, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import (User, Student, Faculty, Course, Enrollment,
                        AttendanceSession, Attendance, Notification)

app = create_app()

DEMO_STUDENTS = [
    ('Alice Johnson', 'CS2024001', 'Computer Science', 3, 'A', 'alice@college.edu', '9876543001', 'parent_alice@email.com'),
    ('Bob Smith', 'CS2024002', 'Computer Science', 3, 'A', 'bob@college.edu', '9876543002', 'parent_bob@email.com'),
    ('Charlie Brown', 'CS2024003', 'Computer Science', 3, 'A', 'charlie@college.edu', '9876543003', 'parent_charlie@email.com'),
    ('Diana Ross', 'CS2024004', 'Computer Science', 3, 'A', 'diana@college.edu', '9876543004', 'parent_diana@email.com'),
    ('Eve Wilson', 'EC2024001', 'Electronics', 3, 'A', 'eve@college.edu', '9876543005', 'parent_eve@email.com'),
    ('Frank Miller', 'EC2024002', 'Electronics', 3, 'A', 'frank@college.edu', '9876543006', 'parent_frank@email.com'),
]

DEMO_FACULTY = [
    ('Dr. Sarah Connor', 'FAC001', 'Computer Science', 'sarah@college.edu', '9876500001'),
    ('Prof. John Matrix', 'FAC002', 'Electronics', 'john@college.edu', '9876500002'),
]

DEMO_COURSES = [
    ('CS301', 'Data Structures & Algorithms', 'Computer Science', 3, 'A', 'FAC001', 'Mon 09:00-10:00, Wed 09:00-10:00, Fri 09:00-10:00'),
    ('CS302', 'Database Management Systems', 'Computer Science', 3, 'A', 'FAC001', 'Tue 10:00-11:00, Thu 10:00-11:00'),
    ('EC301', 'Digital Signal Processing', 'Electronics', 3, 'A', 'FAC002', 'Mon 11:00-12:00, Wed 11:00-12:00, Fri 11:00-12:00'),
]

# Attendance patterns: student_email -> course_code -> probability of being present
# This creates realistic varying attendance rates
ATTENDANCE_PATTERNS = {
    'alice@college.edu':   {'CS301': 0.95, 'CS302': 0.90},  # Excellent
    'bob@college.edu':     {'CS301': 0.80, 'CS302': 0.75},  # Good
    'charlie@college.edu': {'CS301': 0.60, 'CS302': 0.55},  # Low (below 75%)
    'diana@college.edu':   {'CS301': 0.85, 'CS302': 0.90},  # Good
    'eve@college.edu':     {'EC301': 0.50},                   # Very low
    'frank@college.edu':   {'EC301': 0.88},                   # Good
}


def seed():
    with app.app_context():
        print('Seeding demo data...')

        # Admin
        if not User.query.filter_by(email='admin@college.edu').first():
            admin = User(email='admin@college.edu', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            print('  Created admin user')

        # Faculty
        faculty_map = {}
        for name, fid, dept, email, phone in DEMO_FACULTY:
            if not User.query.filter_by(email=email).first():
                user = User(email=email, role='faculty')
                user.set_password('faculty123')
                db.session.add(user)
                db.session.flush()
                faculty = Faculty(user_id=user.id, faculty_id=fid, name=name,
                                  department=dept, phone=phone)
                db.session.add(faculty)
                faculty_map[fid] = faculty
                print(f'  Created faculty: {name}')
            else:
                faculty_map[fid] = Faculty.query.filter_by(faculty_id=fid).first()

        db.session.commit()

        # Students
        student_map = {}
        for name, roll, dept, sem, sec, email, phone, parent_email in DEMO_STUDENTS:
            if not User.query.filter_by(email=email).first():
                user = User(email=email, role='student')
                user.set_password('student123')
                db.session.add(user)
                db.session.flush()
                student = Student(
                    user_id=user.id, roll_number=roll, name=name,
                    department=dept, semester=sem, section=sec,
                    phone=phone, parent_email=parent_email
                )
                db.session.add(student)
                student_map[email] = student
                print(f'  Created student: {name}')
            else:
                user = User.query.filter_by(email=email).first()
                student_map[email] = Student.query.filter_by(user_id=user.id).first()

        db.session.commit()

        # Courses
        course_map = {}
        for code, name, dept, sem, sec, fid, schedule in DEMO_COURSES:
            if not Course.query.filter_by(code=code).first():
                faculty = faculty_map.get(fid) or Faculty.query.filter_by(faculty_id=fid).first()
                course = Course(
                    code=code, name=name, department=dept,
                    semester=sem, section=sec,
                    faculty_id=faculty.id if faculty else None,
                    schedule=schedule
                )
                db.session.add(course)
                db.session.flush()
                course_map[code] = course

                # Auto-enroll matching students
                students = Student.query.filter_by(
                    department=dept, semester=sem, section=sec
                ).all()
                for s in students:
                    if not Enrollment.query.filter_by(student_id=s.id, course_id=course.id).first():
                        db.session.add(Enrollment(student_id=s.id, course_id=course.id))
                print(f'  Created course: {code} ({len(students)} students enrolled)')
            else:
                course_map[code] = Course.query.filter_by(code=code).first()

        db.session.commit()

        # Generate attendance sessions across the last 30 days
        today = date.today()
        session_dates = {}
        for code, _, _, _, _, _, schedule_str in DEMO_COURSES:
            course = course_map.get(code)
            if not course:
                continue

            # Parse schedule to get days
            day_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4}
            schedule_days = []
            for part in schedule_str.split(','):
                part = part.strip()
                for day_name, day_num in day_map.items():
                    if part.startswith(day_name):
                        time_part = part.split(' ')[1].split('-')[0]
                        h, m = time_part.split(':')
                        schedule_days.append((day_num, int(h), int(m)))

            # Generate sessions for the last ~4 weeks (skip weekends)
            dates_for_course = []
            for days_ago in range(28, 0, -1):
                session_date = today - timedelta(days=days_ago)
                weekday = session_date.weekday()
                for day_num, hour, minute in schedule_days:
                    if weekday == day_num:
                        dates_for_course.append((session_date, time(hour, minute)))

            session_dates[code] = dates_for_course

        # Create the sessions and attendance records
        random.seed(42)  # Reproducible randomness

        admin_user = User.query.filter_by(email='admin@college.edu').first()
        if not admin_user:
            admin_user = User.query.filter_by(role='admin').first()

        # Get faculty user for created_by
        faculty_users = {}
        for fid_key, fac in faculty_map.items():
            if fac:
                faculty_users[fid_key] = User.query.get(fac.user_id)

        total_sessions_created = 0
        total_records_created = 0

        for code, dates in session_dates.items():
            course = course_map.get(code)
            if not course:
                continue

            # Find the faculty user who created sessions
            creator = None
            if course.faculty:
                creator = User.query.get(course.faculty.user_id)
            if not creator:
                creator = admin_user

            enrolled = Enrollment.query.filter_by(course_id=course.id).all()
            enrolled_students = [Student.query.get(e.student_id) for e in enrolled]

            for session_date, start_t in dates:
                # Check if session already exists
                existing = AttendanceSession.query.filter_by(
                    course_id=course.id, date=session_date, start_time=start_t
                ).first()
                if existing:
                    continue

                end_t = time(start_t.hour + 1, start_t.minute)
                session = AttendanceSession(
                    course_id=course.id,
                    date=session_date,
                    start_time=start_t,
                    end_time=end_t,
                    status='closed',
                    created_by=creator.id,
                    created_at=datetime.combine(session_date, start_t)
                )
                db.session.add(session)
                db.session.flush()
                total_sessions_created += 1

                # Create attendance records based on patterns
                for student in enrolled_students:
                    email = student.user.email
                    prob = ATTENDANCE_PATTERNS.get(email, {}).get(code, 0.75)
                    is_present = random.random() < prob

                    record = Attendance(
                        session_id=session.id,
                        student_id=student.id,
                        status='present' if is_present else 'absent',
                        marked_by='manual',
                        marked_at=datetime.combine(session_date, start_t) + timedelta(minutes=random.randint(1, 15))
                    )
                    db.session.add(record)
                    total_records_created += 1

        db.session.commit()
        print(f'  Created {total_sessions_created} attendance sessions')
        print(f'  Created {total_records_created} attendance records')

        # Create one active session for today (so faculty dashboard shows it)
        cs301 = course_map.get('CS301')
        if cs301:
            sarah = Faculty.query.filter_by(faculty_id='FAC001').first()
            sarah_user = User.query.get(sarah.user_id) if sarah else admin_user
            existing_today = AttendanceSession.query.filter_by(
                course_id=cs301.id, date=today
            ).first()
            if not existing_today:
                active_session = AttendanceSession(
                    course_id=cs301.id,
                    date=today,
                    start_time=time(9, 0),
                    status='active',
                    created_by=sarah_user.id,
                )
                db.session.add(active_session)
                db.session.flush()

                # Pre-fill attendance as absent
                enrolled = Enrollment.query.filter_by(course_id=cs301.id).all()
                for e in enrolled:
                    db.session.add(Attendance(
                        session_id=active_session.id,
                        student_id=e.student_id,
                        status='absent',
                        marked_by='manual',
                    ))
                db.session.commit()
                print(f'  Created active session for today (CS301)')

        # Create notifications for low-attendance students
        threshold = 75
        for email, patterns in ATTENDANCE_PATTERNS.items():
            student = student_map.get(email)
            if not student:
                continue
            for course_code, prob in patterns.items():
                if prob < 0.70:  # Likely below threshold
                    course = course_map.get(course_code)
                    if not course:
                        continue
                    sessions = AttendanceSession.query.filter_by(course_id=course.id).all()
                    total = len(sessions)
                    if total == 0:
                        continue
                    present = Attendance.query.filter(
                        Attendance.student_id == student.id,
                        Attendance.session_id.in_([s.id for s in sessions]),
                        Attendance.status == 'present'
                    ).count()
                    pct = round((present / total * 100), 1)
                    if pct < threshold:
                        existing_notif = Notification.query.filter_by(
                            user_id=student.user_id,
                            title=f'Low Attendance: {course_code}'
                        ).first()
                        if not existing_notif:
                            db.session.add(Notification(
                                user_id=student.user_id,
                                title=f'Low Attendance: {course_code}',
                                message=f'Your attendance in {course_code} is {pct}%, below the required {threshold}%.',
                                type='warning',
                                created_at=datetime.now() - timedelta(days=2)
                            ))
                            print(f'  Created low attendance notification for {student.name} in {course_code} ({pct}%)')

        db.session.commit()

        print('\nDemo data seeded successfully!')
        print('\nLogin credentials:')
        print('  Admin:   admin@college.edu / admin123')
        print('  Faculty: sarah@college.edu / faculty123')
        print('  Faculty: john@college.edu  / faculty123')
        print('  Student: alice@college.edu / student123  (high attendance)')
        print('  Student: charlie@college.edu / student123  (low attendance)')
        print('  Student: eve@college.edu / student123  (very low attendance)')

        # Print summary
        print(f'\nSummary:')
        print(f'  Users: {User.query.count()}')
        print(f'  Students: {Student.query.count()}')
        print(f'  Faculty: {Faculty.query.count()}')
        print(f'  Courses: {Course.query.count()}')
        print(f'  Enrollments: {Enrollment.query.count()}')
        print(f'  Sessions: {AttendanceSession.query.count()}')
        print(f'  Attendance Records: {Attendance.query.count()}')
        print(f'  Notifications: {Notification.query.count()}')


if __name__ == '__main__':
    seed()
