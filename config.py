import os
from datetime import timedelta


def _database_uri():
    if os.environ.get('DATABASE_URL'):
        return os.environ['DATABASE_URL']
    # Vercel's filesystem is read-only except /tmp, which resets on cold start.
    if os.environ.get('VERCEL'):
        return 'sqlite:////tmp/parkit.db'
    return 'sqlite:///database.db'  # created in instance/


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-only-change-me')
    SQLALCHEMY_DATABASE_URI = _database_uri()
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@parkit.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin@123')
    DEMO_EMAIL = 'demo@parkit.com'
    DEMO_PASSWORD = 'demo1234'
