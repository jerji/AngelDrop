import os
import json
import sys
import time
import click
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, \
    send_from_directory  # Added jsonify
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db, close_db, get_user, add_user, get_all_users, delete_user, update_user_password
from database import get_link_by_path, create_link, delete_db_link, is_link_expired, check_link_password
from database import add_uploaded_file, get_files_for_link, get_link_by_id, get_link_by_token, get_all_links

app = Flask(__name__)
app.teardown_appcontext(close_db)  # Ensure DB is closed on teardown

# Load configuration from file
# check if config file exists
if os.path.exists('config.json'):
    with open('config.json', 'r') as f:
        config = json.load(f)
else:
    print('config.json not found', file=sys.stderr)
    exit(1)
app.config['SECRET_KEY'] = config['SECRET_KEY']

# Configure base path
if 'BASE_PATH' not in config or not config['BASE_PATH']:
    print('BASE_PATH not set in config.json', file=sys.stderr)
    exit(1)
# Ensure the base path exists and is a directory
if not os.path.isdir(config['BASE_PATH']):
    print(f"BASE_PATH '{config['BASE_PATH']}' does not exist or is not a directory.", file=sys.stderr)
    exit(1)
# Normalize and store the absolute base path
app.config['BASE_PATH'] = os.path.abspath(config['BASE_PATH'])

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
        # Ensure path exists before checking, especially useful if checking upload subdirs
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)  # Create if it doesn't exist
        statvfs = os.statvfs(path)
        return statvfs.f_frsize * statvfs.f_bavail
    except OSError as e:
        app.logger.error(f"Error checking disk space for {path}: {e}")
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
    user = get_user(get_db(), username=username)  # Use keyword arg for clarity
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
    # Use absolute paths for reliable comparison
    try:
        abs_base_path = os.path.abspath(base_path)
        abs_folder_path = os.path.abspath(folder_path)
    except Exception as e:
        app.logger.error(f"Error resolving paths for safety check: {e}")
        return False

    # Check if the common path is the base path itself
    return os.path.commonpath([abs_base_path, abs_folder_path]) == abs_base_path


def handle_file_upload(file, link):
    """
    Handle file upload with proper error handling and security checks.
    Logs the uploaded file to the database.

    Args:
        file: File object from request
        link: The database link object (contains folder_path, id, etc.)

    Returns:
        tuple: (success, message, filename) where success is a boolean,
               message is a string, and filename is the secured filename or None.
    """
    upload_path = link['folder_path']
    link_id = link['id']

    if file.filename == '':
        return False, "No selected file", None

    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_path, filename)

    try:
        # Ensure the specific upload directory exists
        if not os.path.exists(upload_path):
            # Check safety again before creating
            if not is_path_safe(upload_path, app.config['BASE_PATH']):
                app.logger.error(f"Attempt to create unsafe directory: {upload_path}")
                return False, f"Error saving {filename}: Invalid directory path.", filename
            try:
                os.makedirs(upload_path, exist_ok=True)
                app.logger.info(f"Created directory: {upload_path}")
            except OSError as e:
                app.logger.error(f"Could not create directory {upload_path}: {e}")
                return False, f"Error saving {filename}: Could not create target directory.", filename

        # Check if file already exists
        if os.path.exists(filepath):
            return False, f"File '{filename}' already exists in the target folder.", filename

        # Check available disk space (check space in the target directory)
        available_space = get_available_space(upload_path)
        content_length = request.content_length  # Note: This might not be reliable for chunked uploads or behind some proxies

        # Try getting size from the stream if content_length is missing (less efficient)
        if content_length is None:
            # This is tricky with streams; try seeking, but might fail
            try:
                pos = file.stream.tell()
                file.stream.seek(0, os.SEEK_END)
                content_length = file.stream.tell()
                file.stream.seek(pos)  # Reset stream position
            except (AttributeError, OSError):
                app.logger.warning("Could not determine file size from stream.")
                # Proceed cautiously or return error - let's proceed but warn
                pass  # Or return False, "Could not determine file size", filename

        if content_length is not None and content_length > available_space:
            return False, f"Not enough disk space for '{filename}' ({content_length} bytes required, {available_space} available).", filename

        # Stream the file content directly to disk
        with open(filepath, 'wb') as f:
            chunk_size = 4096  # 4KB chunks
            while True:
                chunk = file.stream.read(chunk_size)
                if not chunk:
                    break
                f.write(chunk)

        # Add entry to uploaded_files table
        add_uploaded_file(get_db(), link_id, filename)

        return True, f"File '{filename}' uploaded successfully.", filename
    except Exception as e:
        app.logger.error(f"Error handling file upload for {filename} to {upload_path}: {e}")
        # Attempt to clean up partially written file if error occurred
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                app.logger.info(f"Cleaned up partially written file: {filepath}")
            except OSError as remove_err:
                app.logger.error(f"Could not clean up partial file {filepath}: {remove_err}")
        return False, f"Error saving '{filename}': {str(e)}", filename


# --- Custom Template Filters and Context Processors ---

@app.template_filter('datetimeformat')
def datetimeformat(value, d_format='%Y-%m-%d %H:%M:%S'):
    # ... (implementation) ...
    if value is None:
        return "N/A"
    try:
        # Assume value is a Unix timestamp
        ts = time.gmtime(int(value))  # Use gmtime for UTC consistency
        return time.strftime(d_format, ts) + " UTC"  # Indicate timezone
    except (ValueError, TypeError):
        app.logger.warning(f"Could not format timestamp value: {value}")
        return str(value)  # Return original value if conversion fails


@app.context_processor
def inject_is_link_expired():
    """Make is_link_expired function available in templates."""
    return dict(is_link_expired=is_link_expired)


@app.context_processor
def inject_os_path():
    """Make os.path module available in templates for path checks."""
    # Ensure os is imported at the top of the file
    import os
    return dict(os_path=os.path)  # Pass the specific module


# --- END IMPORTANT CONTEXT PROCESSOR ---


@app.context_processor
def inject_base_path():
    """Inject BASE_PATH into templates"""
    # Ensure it ends with a single slash
    base_path_with_slash = app.config['BASE_PATH'].rstrip(os.sep) + os.sep
    return dict(basepath=base_path_with_slash)


# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if session.get('logged_in'):
        return redirect(url_for('admin'))  # Redirect if already logged in

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if check_credentials(username, password):
            session['logged_in'] = True
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Handle user logout."""
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    """Admin dashboard to manage upload links."""
    # Check if user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Expect path relative to BASE_PATH from the form
        relative_folder_path = request.form['folder_path'].strip('/')
        folder_path = os.path.join(app.config['BASE_PATH'], relative_folder_path)
        folder_path = os.path.abspath(folder_path)


        # Security check: ensure folder is within base path
        if not is_path_safe(folder_path, app.config['BASE_PATH']):
            flash(f'Folder must be inside the base path! ({app.config["BASE_PATH"]})', 'error')
            return redirect(url_for('admin'))

        # Check if the *target* folder exists, create if doesn't BUT only if safe
        if not os.path.isdir(folder_path):
            # Double check safety before creating
            if is_path_safe(folder_path, app.config['BASE_PATH']):
                try:
                    os.makedirs(folder_path, exist_ok=True)
                    flash(f'Directory did not exist and was created: {folder_path}', 'info')
                except OSError as e:
                    flash(f'Error creating directory {folder_path}: {e}', 'error')
                    return redirect(url_for('admin'))
            else:
                # This should ideally be caught by the earlier is_path_safe check
                flash(f'Cannot create directory outside base path: {folder_path}', 'error')
                return redirect(url_for('admin'))

        # Check if link already exists for this *normalized absolute* folder path
        existing_link = get_link_by_path(get_db(), folder_path)
        if existing_link:
            flash(
                f'A link for this folder ({folder_path}) already exists: {request.url_root}upload/{existing_link["token"]}',
                'warning')
            return redirect(url_for('admin'))

        # Get optional password and expiry
        password = request.form.get('password')
        expiry = request.form.get('expiry')

        # Parse expiry timestamp if provided
        expiry_timestamp = None
        if expiry:
            try:
                # Frontend sends ISO format (YYYY-MM-DDTHH:MM), convert to Unix timestamp
                expiry_timestamp = int(time.mktime(time.strptime(expiry, '%Y-%m-%dT%H:%M')))
            except ValueError:
                flash('Invalid expiry format. Use the date picker or YYYY-MM-DDTHH:MM format.', 'error')
                return redirect(url_for('admin'))

        # Create the upload link using the absolute path
        token = create_link(get_db(), folder_path, password, expiry_timestamp)
        link_url = url_for('upload', token=token, _external=True)  # Generate full URL
        flash(f'Link created: {link_url}', 'success')
        return redirect(url_for('admin'))

    # Get all links for display
    links = get_all_links(get_db())
    # Pass the basepath for the form label - already handled by context processor
    return render_template('admin.html', links=links)  # Removed basepath= arg


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
        is_expired = is_link_expired(link)
        path_exists = os.path.isdir(link['folder_path'])  # Check if it's a directory specifically
        if is_expired or not path_exists:
            link_dict = dict(link)  # Convert Row object to dict to add custom keys
            link_dict['reason_expired'] = is_expired
            link_dict['reason_path_missing'] = not path_exists
            links_to_delete.append(link_dict)

    if request.method == 'POST':
        # Delete links if confirmed
        deleted_count = 0
        for link_data in links_to_delete:
            delete_db_link(db, link_data['id'])
            deleted_count += 1
        flash(f'{deleted_count} links cleaned up.', 'success')
        return redirect(url_for('admin'))

    # Show preview of links to be deleted
    # Fetch all links again for the main table display
    all_links = get_all_links(db)
    return render_template('admin.html', links=all_links, links_to_delete=links_to_delete,
                           show_cleanup_preview=True)  # Removed os=os (use context processor)


@app.route('/admin/link_details/<int:link_id>')
def link_details(link_id):
    """Display details and uploaded files for a specific link."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    link = get_link_by_id(db, link_id)

    if not link:
        flash('Link not found.', 'error')
        return redirect(url_for('admin'))

    uploaded_files = get_files_for_link(db, link_id)

    # Check if the directory still exists
    directory_exists = os.path.isdir(link['folder_path'])

    return render_template('link_details.html',
                           link=link,
                           uploaded_files=uploaded_files,
                           directory_exists=directory_exists)


@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    """Manage user accounts."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    current_user_id = get_user(db, username=session.get('username'))['id'] if session.get('username') else None

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            username = request.form['new_username']
            password = request.form['new_password']
            if not username or not password:
                flash('Username and password are required to add a user.', 'error')
            elif get_user(db, username=username):
                flash(f'Username "{username}" already exists.', 'error')
            else:
                add_user(db, username, password)
                flash(f'User "{username}" added successfully.', 'success')

        elif action == 'reset_password':
            user_id_to_reset = request.form.get('user_id')
            new_password = request.form.get('reset_password')
            if not user_id_to_reset or not new_password:
                flash('User ID and new password are required for password reset.', 'error')
            else:
                try:
                    user_id_to_reset = int(user_id_to_reset)
                    user_to_reset = get_user(db, id=user_id_to_reset)
                    if user_to_reset:
                        update_user_password(db, user_id_to_reset, new_password)
                        flash(f'Password for user "{user_to_reset["username"]}" reset successfully.', 'success')
                    else:
                        flash('User not found for password reset.', 'error')
                except ValueError:
                    flash('Invalid user ID format.', 'error')

        return redirect(url_for('manage_users'))

    users = get_all_users(db)
    return render_template('users.html', users=users, current_user_id=current_user_id)


@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
def delete_user_route(user_id):
    """Delete a specific user by ID."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    current_user = get_user(db, username=session.get('username'))

    if current_user and user_id == current_user['id']:
        flash('You cannot delete your own account using this method.', 'error')
    else:
        user_to_delete = get_user(db, id=user_id)
        if user_to_delete:
            delete_user(db, user_id)
            flash(f'User "{user_to_delete["username"]}" deleted successfully.', 'success')
        else:
            flash('User not found.', 'error')
    return redirect(url_for('manage_users'))


@app.route('/admin/delete/<int:link_id>', methods=['POST'])
def delete_link(link_id):
    """Delete a specific link by ID."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    link = get_link_by_id(db, link_id)  # Get link to check if exists
    if link:
        delete_db_link(db, link_id)
        flash(f'Link (Token: {link["token"]}) deleted successfully', 'success')
    else:
        flash('Link not found.', 'error')
    return redirect(url_for('admin'))


# --- Upload Routes ---

@app.route('/upload/<token>', methods=['GET', 'POST'])
def upload(token):
    """Handle file uploads for a specific token."""
    db = get_db()
    link = get_link_by_token(db, token)

    if not link:
        flash('Invalid or expired upload link.', 'error')
        return render_template('message.html', message_title="Link Not Found",
                               message_body="The upload link you used is invalid or has expired."), 404

    # Check if link has expired
    if is_link_expired(link):
        flash('This upload link has expired.', 'error')
        return render_template('message.html', message_title="Link Expired",
                               message_body="This upload link has expired and can no longer be used."), 403

    # Check if target directory exists and is writable (basic check)
    target_dir = link['folder_path']
    if not os.path.isdir(target_dir) or not os.access(target_dir, os.W_OK):
        app.logger.error(
            f"Upload target directory issue for token {token}. Path: '{target_dir}'. Exists: {os.path.exists(target_dir)}. IsDir: {os.path.isdir(target_dir)}. Writable: {os.access(target_dir, os.W_OK)}")
        # Don't reveal path details to the user
        flash('Upload destination is currently unavailable. Please contact the administrator.', 'error')
        return render_template('message.html', message_title="Upload Error",
                               message_body="The destination for this upload link is currently unavailable."), 500

    requires_password = link['password_hash'] is not None

    if request.method == 'POST':
        if requires_password:
            provided_password = request.form.get('link_password')
            if not provided_password or not check_link_password(link, provided_password):
                flash('Incorrect password for this link.', 'error')
                # Return the form, indicating password is still required
                return render_template('upload.html', token=token, requires_password=True, link=link), 403

        # --- File Handling ---
        if 'file' not in request.files:
            flash('No file part in the request.', 'error')
            return redirect(request.url)  # Redirect back to the GET page

        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash('No files selected for upload.', 'error')
            return redirect(request.url)

        results = []
        any_errors = False
        for file in files:
            # Pass the whole link object now
            success, message, filename = handle_file_upload(file, link)
            if success:
                results.append({'filename': filename, 'success': True, 'message': message})
            else:
                results.append({'filename': filename, 'success': False, 'message': message})
                any_errors = True

        # --- Response Handling for AJAX ---
        # Check if the request prefers JSON (sent by our JS)
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            # Send back JSON containing flash messages
            flashed_messages = session.pop('_flashed_messages', [])
            return jsonify(success=not any_errors, messages=flashed_messages, results=results)
        else:
            # For non-JS fallback or direct form submission
            return redirect(request.url)
        # --- End File Handling ---

    # Render upload form for GET request
    return render_template('upload.html', token=token, requires_password=requires_password, link=link)


# --- Initialization ---
@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db(app)
    click.echo('Initialized the database.')


@app.cli.command('create-user')
@click.argument('username')
@click.argument('password')
def create_user_command(username, password):
    """Create a new admin user."""
    with app.app_context():
        db = get_db()
        if get_user(db, username=username):
            click.echo(f'User {username} already exists.')
        else:
            add_user(db, username, password)
            click.echo(f'User {username} created.')


with app.app_context():
    # Initialize database if needed (checks internally if tables exist)
    init_db(app)
    # Load initial admin user from config ONLY if no users exist at all
    db = get_db()
    if not get_all_users(db):
        app.logger.info("No users found in DB. Attempting to load from config.json...")
        initial_users = config.get("users", {})
        if not initial_users:
            app.logger.warning(
                "No users found in DB and no 'users' section in config.json. Application will have no initial login.")
        else:
            for username, password in initial_users.items():
                if not get_user(db, username=username):  # Check again just in case
                    add_user(db, username, password)
                    app.logger.info(f"Added initial user '{username}' from config.")
                else:
                    app.logger.info(f"Initial user '{username}' from config already exists in DB.")
    else:
        app.logger.info("Users found in database. Skipping initial user creation from config.")



@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/icons'), 'favicon.ico')


@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('admin'))
    else:
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)