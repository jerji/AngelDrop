import sqlite3
import secrets
import time
import os  # Added for init_db check
from flask import g, current_app, cli  # Added cli for init-db command
from werkzeug.security import generate_password_hash, check_password_hash
import click  # Added for CLI commands


def get_db():
    """
    Get a database connection from the Flask application context.
    Creates a new connection if one doesn't exist.

    Returns:
        sqlite3.Connection: Database connection with row factory set to sqlite3.Row
    """
    db = getattr(g, '_database', None)
    if db is None:
        db_path = current_app.config['DATABASE']
        # Ensure the directory exists before connecting
        db_dir = os.path.dirname(db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            current_app.logger.info(f"Created database directory: {db_dir}")
        db = g._database = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row
        # Enable Foreign Key support for cascades
        db.execute("PRAGMA foreign_keys = ON")
        current_app.logger.debug(f"Database connection opened: {db_path}")
    return db


def close_db(exception=None):  # Modified to accept exception argument for teardown
    """
    Close the database connection if it exists in the Flask application context.
    """
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        current_app.logger.debug("Database connection closed.")
        # Remove from context to ensure fresh connection next time
        g._database = None


def init_db(app):
    """
    Initialize the database using schema.sql if tables don't exist.
    Does NOT drop existing tables. Call from CLI `flask init-db` to clear.
    """
    with app.app_context():
        db = get_db()
        cursor = db.cursor()

        # Check if a key table (e.g., links) exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='links'")
        table_exists = cursor.fetchone()

        if not table_exists:
            app.logger.info("Database tables not found. Initializing...")
            try:
                with app.open_resource('schema.sql', mode='r') as f:
                    script = f.read()
                    db.executescript(script)  # Use executescript for multi-statement SQL
                db.commit()
                app.logger.info("Database initialized successfully from schema.sql.")
            except Exception as e:
                app.logger.error(f"Failed to initialize database from schema.sql: {e}")
                # Consider raising the exception or exiting if init fails critically
                raise e  # Re-raise to signal failure
        else:
            app.logger.info("Database tables already exist. Skipping initialization.")


# --- CLI command to truly initialize/reset the DB ---
@click.command('init-db')
@cli.with_appcontext
def init_db_command():
    """Clears existing data and creates new tables from schema.sql."""
    db = get_db()
    current_app.logger.warning("Re-initializing the database. ALL EXISTING DATA WILL BE LOST.")
    try:
        with current_app.open_resource('schema.sql', mode='r') as f:
            script = f.read()
            db.executescript(script)
        db.commit()
        click.echo('Initialized the database.')
        current_app.logger.info("Database re-initialized successfully.")
    except Exception as e:
        click.echo(f'Error initializing database: {e}')
        current_app.logger.error(f"Error during forced database initialization: {e}")


# Register the command with the Flask app
def register_commands(app):
    app.cli.add_command(init_db_command)


def create_link(db, folder_path, password=None, expiry_timestamp=None):
    """
    Create a new upload link in the database. Stores absolute, normalized path.

    Args:
        db: Database connection
        folder_path (str): Absolute path to the folder for uploads
        password (str, optional): Password to protect the link
        expiry_timestamp (int, optional): Unix timestamp for link expiration

    Returns:
        str: Generated token for the link
    """
    # Ensure path is absolute and normalized before storing
    normalized_path = os.path.abspath(folder_path)
    token = secrets.token_urlsafe(16)  # Generate a secure random token

    # Hash the password if provided
    password_hash = generate_password_hash(password) if password and password.strip() else None

    cursor = db.cursor()
    try:
        cursor.execute('''
            INSERT INTO links (token, folder_path, password_hash, expiry_timestamp)
            VALUES (?, ?, ?, ?)
        ''', (token, normalized_path, password_hash, expiry_timestamp))
        db.commit()
        current_app.logger.info(f"Created link with token {token} for path {normalized_path}")
        return token
    except sqlite3.IntegrityError as e:
        # Handle potential token collision (highly unlikely) or other constraints
        db.rollback()
        current_app.logger.error(f"Failed to create link for path {normalized_path}: {e}")
        raise  # Re-raise the exception


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


# --- New function: get_link_by_id ---
def get_link_by_id(db, link_id):
    """
    Get a link by its ID.

    Args:
        db: Database connection
        link_id (int): Link ID

    Returns:
        sqlite3.Row or None: Link record if found, None otherwise
    """
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links WHERE id = ?', (link_id,))
    return cursor.fetchone()


# --- End new function ---

def get_all_links(db):
    """
    Get all links from the database, ordered by creation time descending.

    Args:
        db: Database connection

    Returns:
        list: List of all link records (sqlite3.Row objects)
    """
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links ORDER BY created_timestamp DESC')
    return cursor.fetchall()


def get_link_by_path(db, folder_path):
    """
    Get a link by its folder path (checks absolute, normalized path).

    Args:
        db: Database connection
        folder_path (str): Folder path to search for

    Returns:
        sqlite3.Row or None: Link record if found, None otherwise
    """
    # Always compare against absolute, normalized path
    normalized_path = os.path.abspath(folder_path)
    cursor = db.cursor()
    cursor.execute('SELECT * FROM links WHERE folder_path = ?', (normalized_path,))
    return cursor.fetchone()


def check_link_password(link, provided_password):
    """
    Check if the provided password matches the link's password hash.

    Args:
        link: Link record (sqlite3.Row or dict) from database
        provided_password (str): Password to check

    Returns:
        bool: True if password matches or no password required, False otherwise
    """
    if not link['password_hash']:
        return True  # No password set, always valid
    if not provided_password:
        return False  # Password required but not given
    return check_password_hash(link['password_hash'], provided_password)


def is_link_expired(link):
    """
    Check if a link has expired based on its expiry timestamp.

    Args:
        link: Link record (sqlite3.Row or dict) from database

    Returns:
        bool: True if the link has expired, False otherwise
    """
    if link['expiry_timestamp'] is None:
        return False  # No expiry set, never expires
    return link['expiry_timestamp'] < int(time.time())


def delete_db_link(db, link_id):
    """
    Delete a link from the database by its ID.
    Relies on foreign key cascade to delete related uploaded_files.

    Args:
        db: Database connection
        link_id (int): ID of the link to delete
    """
    cursor = db.cursor()
    try:
        # Get token before deleting for logging
        link = get_link_by_id(db, link_id)
        token = link['token'] if link else 'Unknown ID'
        cursor.execute('DELETE FROM links WHERE id = ?', (link_id,))
        # Check if deletion happened
        if cursor.rowcount > 0:
            db.commit()
            current_app.logger.info(f"Deleted link ID {link_id} (Token: {token}) and associated files via cascade.")
        else:
            current_app.logger.warning(f"Attempted to delete link ID {link_id}, but it was not found.")
    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Error deleting link ID {link_id}: {e}")
        raise


# --- User Functions ---

def get_user(db, username=None, id=None):
    """
    Get a user by username or ID.

    Args:
        db: Database connection
        username (str, optional): Username to look up
        id (int, optional): User ID to look up

    Returns:
        sqlite3.Row or None: User record if found, None otherwise
    """
    cursor = db.cursor()
    if username:
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    elif id:
        cursor.execute('SELECT * FROM users WHERE id = ?', (id,))
    else:
        return None  # Need either username or id
    return cursor.fetchone()


def add_user(db, username, password):
    """
    Add a new user to the database if they don't already exist.

    Args:
        db: Database connection
        username (str): Username for the new user
        password (str): Password for the new user
    """
    if not username or not password:
        raise ValueError("Username and password cannot be empty.")

    # Check if user already exists
    if get_user(db, username=username):
        current_app.logger.warning(f"Attempted to add existing user: {username}")
        return  # Or raise an error depending on desired behavior

    # Hash password and create user
    password_hash = generate_password_hash(password)
    cursor = db.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                       (username, password_hash))
        db.commit()
        current_app.logger.info(f"Added user: {username}")
    except sqlite3.IntegrityError as e:
        db.rollback()
        current_app.logger.error(f"Failed to add user {username}: {e}")
        raise


def get_all_users(db):
    """
    Get all users from the database.

    Args:
        db: Database connection

    Returns:
        list: List of all user records (sqlite3.Row objects)
    """
    cursor = db.cursor()
    cursor.execute('SELECT id, username FROM users ORDER BY username')  # Exclude password hash
    return cursor.fetchall()


def delete_user(db, user_id):
    """
    Delete a user from the database by their ID.

    Args:
        db: Database connection
        user_id (int): ID of the user to delete
    """
    cursor = db.cursor()
    # Get username before deleting for logging
    user = get_user(db, id=user_id)
    username = user['username'] if user else 'Unknown ID'
    try:
        cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
        if cursor.rowcount > 0:
            db.commit()
            current_app.logger.info(f"Deleted user ID {user_id} (Username: {username})")
        else:
            current_app.logger.warning(f"Attempted to delete user ID {user_id}, but it was not found.")
    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Error deleting user ID {user_id}: {e}")
        raise


def update_user_password(db, user_id, new_password):
    """
    Update a user's password in the database.

    Args:
        db: Database connection
        user_id (int): ID of the user to update
        new_password (str): The new password
    """
    if not new_password:
        raise ValueError("New password cannot be empty.")

    password_hash = generate_password_hash(new_password)
    cursor = db.cursor()
    try:
        cursor.execute('''
            UPDATE users
            SET password_hash = ?
            WHERE id = ?
        ''', (password_hash, user_id))
        if cursor.rowcount > 0:
            db.commit()
            # Get username for logging AFTER commit might be safer if needed
            user = get_user(db, id=user_id)
            username = user['username'] if user else 'Unknown ID'
            current_app.logger.info(f"Updated password for user ID {user_id} (Username: {username})")
        else:
            current_app.logger.warning(f"Attempted to update password for user ID {user_id}, but user was not found.")
    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Error updating password for user ID {user_id}: {e}")
        raise


# --- New functions for uploaded_files ---

def add_uploaded_file(db, link_id, filename):
    """
    Record an uploaded file in the database.

    Args:
        db: Database connection
        link_id (int): The ID of the link used for upload
        filename (str): The name of the file that was uploaded
    """
    cursor = db.cursor()
    try:
        cursor.execute('''
            INSERT INTO uploaded_files (link_id, filename)
            VALUES (?, ?)
        ''', (link_id, filename))
        db.commit()
        current_app.logger.info(f"Recorded uploaded file '{filename}' for link ID {link_id}")
    except sqlite3.Error as e:
        db.rollback()
        current_app.logger.error(f"Failed to record uploaded file '{filename}' for link ID {link_id}: {e}")
        # Decide if this error should propagate or just be logged


def get_files_for_link(db, link_id):
    """
    Get a list of files uploaded using a specific link.

    Args:
        db: Database connection
        link_id (int): The ID of the link

    Returns:
        list: List of file records (sqlite3.Row objects) ordered by upload time desc
    """
    cursor = db.cursor()
    cursor.execute('''
        SELECT id, filename, upload_timestamp
        FROM uploaded_files
        WHERE link_id = ?
        ORDER BY upload_timestamp DESC
    ''', (link_id,))
    return cursor.fetchall()
