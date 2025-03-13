# AngelDrop - Simple File Dropper.

## BIG, BOLD, SHAMEFUL WARNING!

**THIS CODE WAS LARGELY GENERATED WITH THE ASSISTANCE OF AN AI (Gemini 2.0 Pro). I, THE "AUTHOR," FEEL A DEEP SENSE OF
SHAME AND REGRET FOR NOT HAVING CRAFTED EVERY LINE OF THIS SCRIPT BY HAND, WITH THE SWEAT OF MY BROW AND THE GRIT OF
PURE, UNADULTERATED CODING PROWESS. I APOLOGIZE FOR ANY INCONVENIENCE, OFFENSE, OR EXISTENTIAL DREAD THIS MAY CAUSE.
PLEASE USE WITH CAUTION, AND KNOW THAT A HUMAN (ME) *DID* REVIEW AND MODIFY THE AI-GENERATED OUTPUT, BUT THE ORIGINAL
SIN OF AI ASSISTANCE REMAINS.**  Consider contributing improvements or rewriting sections entirely if you feel so moved!
The goal was to provide a functional tool, and hopefully, the end result is helpful despite its origins. My apologies.

---
AngelDrop is a self-hosted file-sharing tool built with Python (Flask) that allows you to easily create upload links for
specific folders on your server. It prioritizes security and ease of use, providing features like:

* **Secure Uploads:**  Uses strong password hashing, random token generation, and prevents directory traversal.
* **Per-Folder Links:**  Generate unique, opaque links for different folders. Users cannot change the destination
  folder.
* **Password Protection (Optional):**  Add password protection to individual upload links.
* **Expiry Times (Optional):** Set expiration times for upload links.
* **Admin Interface:** A simple web interface to manage links (create, delete, copy to clipboard), with
  password-protected login.
* **Drag-and-Drop Upload:**  Drag and drop files anywhere on the upload page, or use a traditional file picker.
* **Multiple File Uploads:**  Supports uploading multiple files at once.
* **Disk Space Checks:**  Verifies sufficient disk space before accepting uploads.
* **SQLite Database:** Uses SQLite for easy setup and deployment (suitable for small to medium-scale use).
* **Responsive Design:** Works well on both desktop and mobile devices.

## Requirements

* Python 3.7+
* pip
* A system where you can run python code

## Installation and Setup

1. **Create a Virtual Environment (Recommended):**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    .venv\Scripts\activate    # On Windows
    ```

2. **Install Dependencies:**

        ```bash
        pip install flask werkzeug
        ```

3. **Configure `config.json`:**

    * Create a file named `config.json` in the `file_uploader` directory.
    * Copy the file from lib/config.example.json to config.json and replace the placeholder values.

    - - **`users`:**  Add your desired admin username(s) and password(s) here.  *Change the default password immediately!*
      This is crucial for security.
   - - **`BASE_PATH`:** The base path that this app will use as it's root. using `/` will be the entire system.
   - - **`SECRET_KEY`:** Generate a strong, random secret key. You can use a command like this in your terminal:

      ```bash
      python -c 'import secrets; print(secrets.token_hex(32))'
      ```

      Copy the output and paste it as the value for `SECRET_KEY`. This key is essential for securing your application (
      session management, etc.).

4. **Run the Application:**

    ```bash
    python app.py
    ```

5. **Access the Application:**

    * **Admin Panel:** Open your web browser and go to `http://127.0.0.1:5000/admin`. Log in with the credentials you
      set in `config.json`.
    * **Upload Links:** Create upload links in the admin panel. These links will be of the form
      `http://127.0.0.1:5000/upload/<unique_token>`.

## Usage

1. **Admin Panel:**
    * Log in to the admin panel (`/admin`).
    * **Create Links:** Enter the *full, absolute path* to the folder you want to create an upload link for. Optionally,
      set a password and/or an expiry time (in `YYYY-MM-DDTHH:MM` format). Click "Create Link".
    * **Manage Links:**  View existing links, copy them to your clipboard, or delete them. Expired links are highlighted
      in red.
    * **Clean up Links:** Provides an eazy way do clean up expired links and links where the folder was deleted.
2. **Uploading Files:**
    * Visit an upload link.
    * If the link is password-protected, enter the password.
    * Drag and drop files onto the page, or click "Select files" to use the file picker.
    * Multiple files can be uploaded simultaneously.

## Deployment (Important!)

**Do *not* use the built-in Flask development server (`python app.py`) for production deployments.** It's not designed
for security or performance in a real-world setting.

For production, you should use a proper WSGI server like **Gunicorn** or **uWSGI**, along with a reverse proxy like *
*Nginx** or **Apache**. Here's a basic example using Gunicorn:

1. **Install Gunicorn:**

   ```bash
   pip install gunicorn
   ```

2. **Run with Gunicorn:**

   ```bash
   gunicorn --workers 3 --bind 0.0.0.0:5000 app:app
   ```

    * `--workers 3`:  Specifies the number of worker processes (adjust based on your server's resources).
    * `--bind 0.0.0.0:8000`:  Binds to all interfaces on port 8000 (you can change the port).
    * `app:app`:  Tells Gunicorn where to find your Flask application (`app` is the filename, and the second `app` is
      the variable name of your Flask instance).

3. **Configure Nginx/Apache (Recommended):**

   Set up Nginx or Apache as a reverse proxy in front of Gunicorn. This provides several benefits:

    * **SSL/TLS Termination:** Handle HTTPS encryption (essential for security).
    * **Static File Serving:** Serve static files (CSS, JavaScript) directly, which is more efficient.
    * **Load Balancing:**  Distribute traffic across multiple Gunicorn workers.
    * **Security:**  Protect your application from common web attacks.

I had to add these to the http block of the nginx config. Mileage may vary.
```yaml
    http{
    
        client_max_body_size 100M;  # Adjust this as needed (e.g., 100MB, 1G)
        client_body_timeout 600s;   # Time to receive the entire request body
        send_timeout 600s;         # Time to send data to the client
        proxy_read_timeout 600s;   # Time to wait for a response from the upstream server (Gunicorn)
        proxy_send_timeout 600s;   # Time to send a request to the upstream server
        keepalive_timeout 75s;     # Keep-alive connections timeout

        # If using HTTPS
        ssl_session_timeout 10m;
    }
```

I have provided an example systemd service file and nginx config file in `/lib`

## Security Considerations

* **Change Default Credentials:**  Immediately change the default admin password in `config.json`.
* **Use a Strong Secret Key:** Generate a long, random `SECRET_KEY`.
* **HTTPS:**  Use HTTPS (SSL/TLS) in a production environment. This is *essential* for protecting passwords and uploaded
  data.
* **Rate Limiting:**  Consider implementing rate limiting (e.g., using Flask-Limiter) to prevent abuse of the upload
  endpoint.
* **File Type Validation:**  If you only want to allow specific file types, add validation logic to the `/upload` route.
* **Regular Updates:**  Keep Flask, Werkzeug, and other dependencies updated to patch security vulnerabilities.
* **Secure file storage:** Ensure the folder you are uploading to has correct permissions and is well protected.

## Contributing

Contributions are welcome! Please submit pull requests or open issues on the repository.

## License

This project is licensed under the MIT License - see the LICENSE file for details
