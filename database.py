import sqlite3
import secrets
import time
from flask import g, current_app
from werkzeug.security import generate_password_hash, check_password_hash


def get_db():
    """
    Get a database connection from the Flask application context.
    Creates a new connection if one doesn't exist.

    Returns:
        sqlite3.Connection: Database connection with row factory set to sqlite3.Row
    """
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(current_app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db


def close_db():
    """
    Close the database connection if it exists.
    Should be called when the application context ends.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db(app):
    """
    Initialize the database with required tables if they don't exist.

    Args:
        app: Flask application instance
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Check if tables already exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links'")
        table_exists = cursor.fetchone()

        if not table_exists:
            # Create tables using schema.sql
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            app.logger.info("Database initialized.")
        else:
            app.logger.info("Database tables already exist.")


def create_link(db, folder_path, password=None, expiry_timestamp=None):
    """
    Create a new upload link in the database.

    Args:
        db: Database connection
        folder_path (str): Path to the folder for uploads
        password (str, optional): Password to protect the link
        expiry_timestamp (int, optional): Unix timestamp for link expiration

    Returns:
        str: Generated token for the link
    """
    folder_path = folder_path.rstrip('/')
    token = secrets.token_urlsafe(16)  # Generate a secure random token

    # Hash the password if provided
    password_hash = generate_password_hash(password) if password else None

    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO links (token, folder_path, password_hash, expiry_timestamp)
        VALUES (?, ?, ?, ?)
    ''', (token, folder_path, password_hash, expiry_timestamp))
    db.commit()

    return token


def get_link_by_token(db, token):
    """
    Get a link by its token.

    Args:
        db: Database connection
        token (str): Link token

    Returns:
        sqlite3.Row or None: Link record if found, None otherwise
    """
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links WHERE token = ?', (token,))
    return cursor.fetchone()


def get_all_links(db):
    """
    Get all links from the database.

    Args:
        db: Database connection

    Returns:
        list: List of all link records
    """
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links')
    return cursor.fetchall()


def get_link_by_path(db, folder_path):
    """
    Get a link by its folder path.

    Args:
        db: Database connection
        folder_path (str): Folder path to search for

    Returns:
        sqlite3.Row or None: Link record if found, None otherwise
    """
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links WHERE folder_path = ?', (folder_path,))
    return cursor.fetchone()


def check_link_password(link, provided_password):
    """
    Check if the provided password matches the link's password hash.

    Args:
        link: Link record from database
        provided_password (str): Password to check

    Returns:
        bool: True if password matches or no password required, False otherwise
    """
    if link['password_hash'] is None:
        return True  # No password set, always valid
    return check_password_hash(link['password_hash'], provided_password)


def is_link_expired(link):
    """
    Check if a link has expired based on its expiry timestamp.

    Args:
        link: Link record from database

    Returns:
        bool: True if the link has expired, False otherwise
    """
    if link['expiry_timestamp'] is None:
        return False  # No expiry set, never expires
    return link['expiry_timestamp'] < int(time.time())


def delete_db_link(db, link_id):
    """
    Delete a link from the database by its ID.

    Args:
        db: Database connection
        link_id (int): ID of the link to delete
    """
    cursor = db.cursor()
    cursor.execute('DELETE FROM links WHERE id = ?', (link_id,))
    db.commit()


def get_user(db, username):
    """
    Get a user by username.

    Args:
        db: Database connection
        username (str): Username to look up

    Returns:
        sqlite3.Row or None: User record if found, None otherwise
    """
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone()


def add_user(db, username, password):
    """
    Add a new user to the database if they don't already exist.

    Args:
        db: Database connection
        username (str): Username for the new user
        password (str): Password for the new user
    """
    # Check if user already exists
    cursor = db.cursor()
    existing_user = get_user(db, username)
    if existing_user:
        return

    # Hash password and create user
    password_hash = generate_password_hash(password)
    cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                   (username, password_hash))
    db.commit()