"""Take screenshots of all pages in the attendance system using Playwright."""
import os
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:5000"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def login(page, email, password):
    """Login to the app."""
    page.goto(f"{BASE_URL}/login", wait_until="networkidle")
    page.fill('input[name="email"]', email)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


def shot(page, url, filename, wait_for_charts=False):
    """Navigate to a URL and take a full-page screenshot."""
    page.goto(url, wait_until="networkidle")
    if wait_for_charts:
        page.wait_for_timeout(2000)
    else:
        page.wait_for_timeout(500)
    filepath = os.path.join(OUT_DIR, filename)
    page.screenshot(path=filepath, full_page=True)
    print(f"  Saved: {filename}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ==================== LOGIN PAGE ====================
        print("=== Login Page ===")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(f"{BASE_URL}/login", wait_until="networkidle")
        page.wait_for_timeout(500)
        page.screenshot(path=os.path.join(OUT_DIR, "01_login.png"), full_page=True)
        print("  Saved: 01_login.png")
        ctx.close()

        # ==================== ADMIN PAGES ====================
        print("\n=== Admin Pages ===")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        login(page, "admin@college.edu", "admin123")

        shot(page, f"{BASE_URL}/admin/dashboard", "02_admin_dashboard.png")
        shot(page, f"{BASE_URL}/admin/students", "03_admin_students.png")
        shot(page, f"{BASE_URL}/admin/students/add", "04_admin_add_student.png")
        shot(page, f"{BASE_URL}/admin/faculty", "05_admin_faculty.png")
        shot(page, f"{BASE_URL}/admin/faculty/add", "06_admin_add_faculty.png")
        shot(page, f"{BASE_URL}/admin/courses", "07_admin_courses.png")
        shot(page, f"{BASE_URL}/admin/courses/add", "08_admin_add_course.png")
        shot(page, f"{BASE_URL}/admin/analytics", "09_admin_analytics.png", wait_for_charts=True)

        # Click department details on analytics
        page.goto(f"{BASE_URL}/admin/analytics", wait_until="networkidle")
        page.wait_for_timeout(1500)
        btns = page.query_selector_all("button.btn-outline-primary")
        if btns:
            btns[0].click()
            page.wait_for_timeout(1500)
            page.screenshot(path=os.path.join(OUT_DIR, "10_admin_analytics_detail.png"), full_page=True)
            print("  Saved: 10_admin_analytics_detail.png")

        shot(page, f"{BASE_URL}/change-password", "11_change_password.png")
        ctx.close()

        # ==================== FACULTY PAGES ====================
        print("\n=== Faculty Pages (Dr. Sarah Connor) ===")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        login(page, "sarah@college.edu", "faculty123")

        shot(page, f"{BASE_URL}/faculty/dashboard", "12_faculty_dashboard.png")
        shot(page, f"{BASE_URL}/faculty/courses", "13_faculty_courses.png")
        shot(page, f"{BASE_URL}/faculty/attendance/start", "14_faculty_start_attendance.png")
        shot(page, f"{BASE_URL}/faculty/reports", "15_faculty_reports.png")
        shot(page, f"{BASE_URL}/faculty/reports/course/1", "16_faculty_course_report_cs301.png", wait_for_charts=True)
        shot(page, f"{BASE_URL}/faculty/reports/course/2", "17_faculty_course_report_cs302.png", wait_for_charts=True)
        shot(page, f"{BASE_URL}/faculty/attendance/1/report", "18_faculty_session_report.png")
        shot(page, f"{BASE_URL}/faculty/attendance/33", "19_faculty_mark_attendance.png")
        ctx.close()

        # ==================== STUDENT PAGES (Alice - high attendance) ====================
        print("\n=== Student Pages (Alice - high attendance) ===")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        login(page, "alice@college.edu", "student123")

        shot(page, f"{BASE_URL}/student/dashboard", "20_student_dashboard_alice.png")
        shot(page, f"{BASE_URL}/student/attendance", "21_student_attendance_alice.png")
        shot(page, f"{BASE_URL}/student/analytics", "22_student_analytics_alice.png", wait_for_charts=True)
        ctx.close()

        # ==================== STUDENT PAGES (Charlie - low attendance) ====================
        print("\n=== Student Pages (Charlie - low attendance) ===")
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        login(page, "charlie@college.edu", "student123")

        shot(page, f"{BASE_URL}/student/dashboard", "23_student_dashboard_charlie.png")
        shot(page, f"{BASE_URL}/student/attendance", "24_student_attendance_charlie.png")
        shot(page, f"{BASE_URL}/student/analytics", "25_student_analytics_charlie.png", wait_for_charts=True)
        ctx.close()

        browser.close()

    pngs = sorted(f for f in os.listdir(OUT_DIR) if f.endswith('.png'))
    print(f"\nDone! {len(pngs)} screenshots saved to {OUT_DIR}/")
    for f in pngs:
        print(f"  {f}")


if __name__ == "__main__":
    main()
