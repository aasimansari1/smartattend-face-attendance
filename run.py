import os
from app import create_app, db
from app.models import User

app = create_app()


@app.cli.command('init-db')
def init_db():
    """Create all database tables."""
    db.create_all()
    print('Database tables created.')


@app.cli.command('seed-admin')
def seed_admin():
    """Create default admin user."""
    email = os.getenv('ADMIN_EMAIL', 'admin@college.edu')
    password = os.getenv('ADMIN_PASSWORD', 'admin123')

    if User.query.filter_by(email=email).first():
        print(f'Admin user {email} already exists.')
        return

    admin = User(email=email, role='admin')
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f'Admin user created: {email}')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
