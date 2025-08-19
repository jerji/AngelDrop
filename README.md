# AngelDrop - Simple File Dropper


## Overview

AngelDrop is a self-hosted file-sharing tool built with Python (Flask) that allows you to easily create upload links for
specific folders on your server. It prioritizes security and ease of use.

### Key Features

* **Secure Uploads:** Uses strong password hashing, random token generation, and prevents directory traversal
* **Per-Folder Links:** Generate unique, opaque links for different folders
* **Password Protection:** Add optional password protection to individual upload links
* **Expiry Times:** Set optional expiration times for upload links
* **Admin Interface:** Web interface to manage links with password-protected login
* **Drag-and-Drop Upload:** Simple interface for uploading files
* **Multiple File Uploads:** Support for uploading multiple files at once
* **Disk Space Checks:** Verification of sufficient disk space before accepting uploads
* **SQLite Database:** Simple database for easy setup and deployment
* **Responsive Design:** Works well on both desktop and mobile devices

## System Requirements

* Python 3.7+
* pip
* Linux, macOS, or Windows operating system

## File Structure

```
angelDrop/
├── app.py                    # Main application file
├── database.py               # Database operations
├── models.py                 # Placeholder
├── config.json               # Configuration file (create from example)
├── schema.sql                # Database Schema
├── README.md                 # This file :P
├── LICENCE                   # Copy of the MIT licence
│
├── lib/                      # Auxiliary files
│   ├── config.example.json   # Example configuration
│   ├── angeldrop.nginx.conf  # Example Nginx configuration
│   └── angeldrop.service     # Example systemd service file
│
├── static/                   # Static assets (CSS, JavaScript)
│   ├── script.js             # Main Javascript File
│   └── style.css             # Main CSS file
│
├── templates/                # HTML templates
│   ├── admin.html            # Template for admin page
│   ├── base.html             # Base template
│   ├── login.html            # Template for login page
│   └── upload.html           # Templade for public upload page
│
└── db/                       # Database directory (created automatically)
    └── uploader.db           # SQLite database (created automatically)
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/jerji/AngelDrop.git
cd AngelDrop
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Linux/macOS
# OR
.venv\Scripts\activate     # On Windows
```

### 3. Install Dependencies

```bash
pip install flask werkzeug
```

### 4. Configure the Application

Create a configuration file by copying the example:

```bash
cp lib/config.example.json config.json
```

Edit `config.json` with your settings:

```json
{
  "users": {
    "admin": "password123"
  },
  "BASE_PATH": "/tmp",
  "SECRET_KEY": "SUPER-SECRET-KEY-REPLACEME"
}

```

Key configuration items:

* **`SECRET_KEY`**: Generate a strong random key using:
  ```bash
  python -c 'import secrets; print(secrets.token_hex(32))'
  ```

* **`BASE_PATH`**: Root directory for file operations. Using `/` grants access to the entire system (not recommended for
  production).

* **`users`**: Admin username(s) and password(s). **Change the default password immediately!**

### 5. Run the Application (Development Only)

```bash
python app.py
```

## Usage

### Admin Panel

1. Access the admin panel at `http://your-server:5000/admin`
2. Log in with credentials from your `config.json`
3. Create upload links:
    - Enter the absolute path to your target folder
    - Optionally set a password
    - Optionally set an expiry time (format: `YYYY-MM-DDTHH:MM`)
4. Manage existing links:
    - Copy links to clipboard
    - Delete links
    - Clean up expired or invalid links

### Uploading Files

1. Visit a generated upload link (`http://your-server:5000/upload/<token>`)
2. Enter the password if required
3. Upload files by:
    - Dragging and dropping onto the page
    - Clicking "Select files" to use the file picker
4. Multiple files can be uploaded simultaneously

## Production Deployment

### Important: Do NOT use the built-in Flask server in production!

For production environments, use a proper WSGI server with a reverse proxy:

### 1. Install Gunicorn

```bash
pip install gunicorn
```

### 2. Run with Gunicorn

```bash
gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
```

### 3. Configure Nginx as a Reverse Proxy

Create an Nginx configuration (example in `lib/angeldrop.nginx.conf`):

```nginx
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name upload.example.com;

    access_log /var/log/nginx/angeldrop.access.log combined;
    error_log /var/log/nginx/angeldrop.error.log warn;

    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;

    proxy_buffer_size   128k;
    proxy_buffers   4 256k;
    proxy_busy_buffers_size   256k;
    client_max_body_size 20000M;


    location /login {
        proxy_pass http://localhost:5000/login;
        allow 192.168.0.0/16;
        deny all;
    }

    location /admin {
        proxy_pass http://localhost:5000/admin;
        allow 192.168.0.0/16;
        deny all;
    }

    location = /logout {
        proxy_pass http://localhost:5000/logout;
        allow 192.168.0.0/16;
        deny all;

    }

    location /upload {
        proxy_pass http://localhost:5000/upload;
   }


   location /static {
        proxy_pass http://localhost:5000/static;
   }

}
```

This config is separated to assure only people on the local network can access admin pages.

### 4. Nginx Performance Settings

Add to the `http` block in your Nginx configuration:

```nginx
http {
    client_max_body_size 100M;  # Adjust as needed
    client_body_timeout 600s;   # Time to receive request body
    send_timeout 600s;          # Time to send data to client
    proxy_read_timeout 600s;    # Time to wait for upstream response
    proxy_send_timeout 600s;    # Time to send request upstream
    keepalive_timeout 75s;      # Keep-alive timeout
    
    # If using HTTPS
    ssl_session_timeout 10m;
}
```

### 5. Set Up as a Systemd Service

Create a systemd service file (example in `lib/angeldrop.service`):

```ini
[Unit]
Description = Angel Drop File Dropper
After = network.target

[Service]
User = your_user
Group = your_user
WorkingDirectory = /opt/AngelDrop
ExecStart = /opt/AngelDrop/venv/bin/gunicorn -b 0.0.0.0:5000 -w 4 --timeout 600 app:app
Restart = always

[Install]
WantedBy = multi-user.target

```

Enable and start the service:

```bash
sudo cp lib/angeldrop.service /etc/systemd/system/angeldrop.service
sudo systemctl daemon-reload
sudo systemctl enable angeldrop
sudo systemctl start angeldrop
```

## Security Best Practices

* **Change Default Credentials:** Update the admin password immediately
* **Use HTTPS:** Always use SSL/TLS in production
* **Restrict BASE_PATH:** Never use `/` as BASE_PATH in production
* **Regular Updates:** Keep all dependencies updated
* **File Permissions:** Ensure upload directories have appropriate permissions
* **Firewall Configuration:** Restrict access to the application server
* **Rate Limiting:** Consider implementing rate limiting to prevent abuse
* **Backup Strategy:** Regularly backup your database and configuration
* **Audit Logs:** Monitor access and upload activity

## Troubleshooting

### Common Issues

1. **Database Errors**
    - Check that the `db` directory exists and is writable
    - Verify database permissions

2. **Upload Failures**
    - Check available disk space
    - Verify folder permissions
    - Check file size limits in both the application and Nginx

3. **Link Expiration Issues**
    - Verify server time is correct
    - Check for time zone discrepancies

## Contributing

Contributions are welcome! Please submit pull requests or open issues on the repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details.
