import sqlite3
from flask import g, current_app
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
import time  # Import the time module


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db


def close_db():
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db(app):
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links'")
        table_exists = cursor.fetchone()

        if not table_exists:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            print("Database initialized.")
        else:
            print("Database tables already exist.")


def create_link(db, folder_path, password=None, expiry_timestamp=None):
    folder_path = folder_path.rstrip('/')
    token = secrets.token_urlsafe(16)
    password_hash = generate_password_hash(password) if password else None  # Hash if provided

    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO links (token, folder_path, password_hash, expiry_timestamp)
        VALUES (?, ?, ?, ?)
    ''', (token, folder_path, password_hash, expiry_timestamp))
    db.commit()
    return token


def get_link_by_token(db, token):
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links WHERE token = ?', (token,))
    return cursor.fetchone()


def get_all_links(db):
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links')
    return cursor.fetchall()


def get_link_by_path(db, folder_path):
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links WHERE folder_path = ?', (folder_path,))
    return cursor.fetchone()


def check_link_password(link, provided_password):
    if link['password_hash'] is None:
        return True  # No password set, always valid
    return check_password_hash(link['password_hash'], provided_password)


def is_link_expired(link):
    if link['expiry_timestamp'] is None:
        return False  # No expiry set, never expired
    return link['expiry_timestamp'] < int(time.time())


def get_user(db, username):
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()


def add_user(db, username, password):
    cursor = db.cursor()
    existing_user = get_user(db, username)
    if existing_user:
        return
    password_hash = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)', (username, password_hash))
    db.commit()
