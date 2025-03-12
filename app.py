import os
import secrets
import json
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from database import get_db, init_db, create_link, get_link_by_token, get_all_links, get_user, add_user, get_link_by_path, check_link_password, is_link_expired
import models
import shutil
import time  # Import the time module

app = Flask(__name__)

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)
app.config['SECRET_KEY'] = config['SECRET_KEY']

# --- Database Configuration (Absolute Path) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, 'db')
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)
DATABASE = os.path.join(DB_DIR, 'uploader.db')
app.config['DATABASE'] = DATABASE

# --- Helper Functions ---

def get_available_space(path):
    statvfs = os.statvfs(path)
    return statvfs.f_frsize * statvfs.f_bavail

def check_credentials(username, password):
    user = get_user(get_db(), username)
    if user and check_password_hash(user['password_hash'], password):
        return True
    return False

# --- Custom Template Filter ---
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    ts = time.gmtime(value)
    return time.strftime(format, ts)

# --- Make is_link_expired available in templates ---
@app.context_processor
def inject_is_link_expired():
    return dict(is_link_expired=is_link_expired)

# --- Routes ---
# ... (your routes: /login, /logout, /admin, /admin/delete,) ...
@app.route('/login', methods=['GET', 'POST'])
def login():
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
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        folder_path = request.form['folder_path']
        folder_path = folder_path.rstrip('/')
        password = request.form.get('password')  # Use .get() for optional fields
        expiry = request.form.get('expiry')

        if not os.path.isdir(folder_path):
            flash('Invalid folder path', 'error')
            return redirect(url_for('admin'))

        existing_link = get_link_by_path(get_db(), folder_path)
        if existing_link:
            flash(f'A link for this folder already exists: {request.url_root}upload/{existing_link["token"]}', 'warning')
            return redirect(url_for('admin', _anchor='links'))

        expiry_timestamp = None
        if expiry:
            try:
                expiry_timestamp = int(time.mktime(time.strptime(expiry, '%Y-%m-%dT%H:%M')))
            except ValueError:
                flash('Invalid expiry format. Use YYYY-MM-DDTHH:MM', 'error')
                return redirect(url_for('admin'))

        token = create_link(get_db(), folder_path, password, expiry_timestamp)
        flash(f'Link created: {request.url_root}upload/{token}', 'success')
        return redirect(url_for('admin', _anchor='links'))

    links = get_all_links(get_db())
    return render_template('admin.html', links=links)

@app.route('/admin/delete/<int:link_id>', methods=['POST'])
def delete_link(link_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM links WHERE id = ?', (link_id,))
    db.commit()
    flash('Link deleted successfully', 'success')
    return redirect(url_for('admin', _anchor='links'))


@app.route('/upload/<token>', methods=['GET', 'POST'])
def upload(token):
    link = get_link_by_token(get_db(), token)
    if not link:
        flash('Invalid upload link', 'error')
        return "Invalid upload link", 404

    if is_link_expired(link):
        flash('This upload link has expired.', 'error')
        return "This upload link has expired.", 403

    if request.method == 'POST':
        if link['password_hash']:
            provided_password = request.form.get('link_password')
            if not provided_password or not check_link_password(link, provided_password):
                flash('Incorrect password for this link.', 'error')
                return render_template('upload.html', token=token, requires_password=True)

        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)

        # --- Handle Multiple Files ---
        files = request.files.getlist('file')  # Get a list of files
        for file in files:
            if file.filename == '':
                # Skip empty filenames (can happen with multiple file inputs)
                continue

            filename = secure_filename(file.filename)
            upload_path = link['folder_path']
            filepath = os.path.join(upload_path, filename)

            # Disk space check (check for EACH file)
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            available_space = get_available_space(upload_path)
            if file_size > available_space:
                flash(f'Not enough disk space for {filename}', 'error')
                return redirect(request.url) # Stop on first error

            try:
                file.save(filepath)
            except Exception as e:
                flash(f'Error saving {filename}: {e}', 'error')
                return redirect(request.url) # Stop on first error
        flash('All files uploaded successfully', 'success') # Only flash if all files were saved.
        return redirect(request.url)

    requires_password = link['password_hash'] is not None
    return render_template('upload.html', token=token, requires_password=requires_password)

# --- Initialization ---
with app.app_context():
     init_db(app)
     db = get_db()
     for username, password in config["users"].items():
        add_user(db, username, password)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)