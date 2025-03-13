import os
import json
import sys
import time
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db, get_user, add_user, get_link_by_token, get_all_links
from database import get_link_by_path, create_link, delete_db_link, is_link_expired, check_link_password

app = Flask(__name__)

# Load configuration from file
#check if config file exists
if os.path.exists('config.json'):
    with open('config.json', 'r') as f:
        config = json.load(f)
else:
    print('config.json not found', file=sys.stderr)
    exit(1)
app.config['SECRET_KEY'] = config['SECRET_KEY']

# Configure base path
if config['BASE_PATH'] == '/':
    app.config['BASE_PATH'] = '/'
else:
    app.config['BASE_PATH'] = config['BASE_PATH'].rstrip('/')

# Database Configuration with absolute path for reliability
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'db')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
DATABASE = os.path.join(DB_DIR, 'uploader.db')
app.config['DATABASE'] = DATABASE


# --- Helper Functions ---

def get_available_space(path):
    """
    Get available disk space in bytes for the given path.

    Args:
        path (str): Path to check for available space

    Returns:
        int: Available space in bytes
    """
    try:
        statvfs = os.statvfs(path)
        return statvfs.f_frsize * statvfs.f_bavail
    except OSError as e:
        app.logger.error(f"Error checking disk space: {e}")
        return 0


def check_credentials(username, password):
    """
    Verify user credentials against the database.

    Args:
        username (str): Username to check
        password (str): Password to verify

    Returns:
        bool: True if credentials are valid, False otherwise
    """
    user = get_user(get_db(), username)
    if user and check_password_hash(user['password_hash'], password):
        return True
    return False


def is_path_safe(folder_path, base_path):
    """
    Check if the folder path is within the base path to prevent directory traversal.

    Args:
        folder_path (str): Folder path to check
        base_path (str): Base path that should contain the folder path

    Returns:
        bool: True if path is safe, False otherwise
    """
    # Normalize paths for comparison
    base_path = os.path.join(os.path.realpath(base_path), '')
    real_path = os.path.join(os.path.realpath(folder_path), '')

    # Check if the real path is within the base path
    return os.path.commonprefix([base_path, real_path]) == base_path


def handle_file_upload(file, upload_path):
    """
    Handle file upload with proper error handling and security checks.

    Args:
        file: File object from request
        upload_path (str): Path to save the file

    Returns:
        tuple: (success, message) where success is a boolean and message is a string
    """
    if file.filename == '':
        return False, "No selected file"

    try:
        filename = secure_filename(file.filename)
        filepath = os.path.join(upload_path, filename)

        # Check if file already exists
        if os.path.exists(filepath):
            return False, f"File {filename} already exists"

        # Check available disk space
        available_space = get_available_space(upload_path)
        content_length = request.content_length

        if content_length is None:
            return False, "Could not determine file size"

        if content_length > available_space:
            return False, f"Not enough disk space for {filename}"

        # Stream the file content directly to disk
        with open(filepath, 'wb') as f:
            while True:
                chunk = file.stream.read(4096)  # Read in 4KB chunks
                if not chunk:
                    break
                f.write(chunk)

        return True, f"File {filename} uploaded successfully"
    except Exception as e:
        app.logger.error(f"Error handling file upload: {e}")
        return False, f"Error saving {filename}: {str(e)}"


# --- Custom Template Filters and Context Processors ---

@app.template_filter('datetimeformat')
def datetimeformat(value, d_format='%Y-%m-%d %H:%M'):
    """Format a timestamp into a readable date string."""
    ts = time.gmtime(value)
    return time.strftime(d_format, ts)


# --- Make is_link_expired available in templates ---
@app.context_processor
def inject_is_link_expired():
    """Make is_link_expired function available in templates."""
    return dict(is_link_expired=is_link_expired)


@app.context_processor
def inject_os():
    """Make os module available in templates."""
    return dict(os=os)


# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if check_credentials(username, password):
            session['logged_in'] = True
            session['username'] = username
            return redirect(url_for('admin'))
        else:
            flash('Invalid credentials', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))


# --- Admin Routes ---

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin dashboard to manage upload links."""
    # Check if user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get folder path from form and normalize it
        folder_path = os.path.join(app.config['BASE_PATH'], request.form['folder_path'])
        folder_path = folder_path.rstrip('/')

        # Security check: ensure folder is within base path
        if not is_path_safe(folder_path, app.config['BASE_PATH']):
            flash(f'Folder must be inside the base path! ({app.config["BASE_PATH"]})', 'error')
            return redirect(url_for('admin'))

        # Check if folder exists
        if not os.path.isdir(folder_path):
            flash('Invalid folder path', 'error')
            return redirect(url_for('admin'))

        # Check if link already exists for this folder
        existing_link = get_link_by_path(get_db(), folder_path)
        if existing_link:
            flash(f'A link for this folder already exists: {request.url_root}upload/{existing_link["token"]}',
                  'warning')
            return redirect(url_for('admin'))

        # Get optional password and expiry
        password = request.form.get('password')
        expiry = request.form.get('expiry')

        # Parse expiry timestamp if provided
        expiry_timestamp = None
        if expiry:
            try:
                expiry_timestamp = int(time.mktime(time.strptime(expiry, '%Y-%m-%dT%H:%M')))
            except ValueError:
                flash('Invalid expiry format. Use YYYY-MM-DDTHH:MM', 'error')
                return redirect(url_for('admin'))

        # Create the upload link
        token = create_link(get_db(), folder_path, password, expiry_timestamp)
        flash(f'Link created: {request.url_root}upload/{token}', 'success')
        return redirect(url_for('admin'))

    # Get all links for display
    links = get_all_links(get_db())
    return render_template('admin.html', links=links, basepath=app.config['BASE_PATH'].rstrip('/') + '/')


@app.route('/admin/cleanup', methods=['GET', 'POST'])
def cleanup_links():
    """Clean up expired or invalid links."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    links = get_all_links(db)
    links_to_delete = []

    # Find expired or invalid links
    for link in links:
        if is_link_expired(link) or not os.path.exists(link['folder_path']):
            links_to_delete.append(link)

    if request.method == 'POST':
        # Delete links if confirmed
        for link in links_to_delete:
            delete_db_link(db, link['id'])
        flash(f'{len(links_to_delete)} links cleaned up.', 'success')
        return redirect(url_for('admin'))

    # Show preview of links to be deleted
    return render_template('admin.html', links=links, links_to_delete=links_to_delete,
                           show_cleanup_preview=True, os=os)


@app.route('/admin/delete/<int:link_id>', methods=['POST'])
def delete_link(link_id):
    """Delete a specific link by ID."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    delete_db_link(db, link_id)
    flash('Link deleted successfully', 'success')
    return redirect(url_for('admin'))


# --- Upload Routes ---

@app.route('/upload/<token>', methods=['GET', 'POST'])
def upload(token):
    """Handle file uploads for a specific token."""
    # Validate token
    link = get_link_by_token(get_db(), token)
    if not link:
        flash('Invalid upload link', 'error')
        return "Invalid upload link", 404

    # Check if link has expired
    if is_link_expired(link):
        flash('This upload link has expired.', 'error')
        return "This upload link has expired.", 403

    if request.method == 'POST':
        # Check password if required
        if link['password_hash']:
            provided_password = request.form.get('link_password')
            if not provided_password or not check_link_password(link, provided_password):
                flash('Incorrect password for this link.', 'error')
                return render_template('upload.html', token=token, requires_password=True)

        # Handle file upload
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        files = request.files.getlist('file')
        for file in files:
            success, message = handle_file_upload(file, link['folder_path'])
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')

        return redirect(request.url)

    # Render upload form
    requires_password = link['password_hash'] is not None
    return render_template('upload.html', token=token, requires_password=requires_password)


# --- Initialization ---
with app.app_context():
    # Initialize database and create users from config
    init_db(app)
    database = get_db()
    for username, password in config["users"].items():
        add_user(database, username, password)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)