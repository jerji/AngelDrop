-- schema.sql
DROP TABLE IF EXISTS links;
DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS uploaded_files; -- Add this drop

CREATE TABLE links
(
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    token             TEXT UNIQUE NOT NULL,
    folder_path       TEXT        NOT NULL,
    password_hash     TEXT,                                   -- Can be NULL if no password
    expiry_timestamp  INTEGER,                                -- Unix timestamp, Can be NULL if no expiry
    created_timestamp INTEGER DEFAULT (strftime('%s', 'now')) -- Added creation timestamp
);

CREATE TABLE users
(
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL,
    password_hash TEXT        NOT NULL
);

-- New table for uploaded files
CREATE TABLE uploaded_files
(
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id          INTEGER NOT NULL,
    filename         TEXT    NOT NULL,
    upload_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (link_id) REFERENCES links (id) ON DELETE CASCADE -- Delete records if link is deleted
);

-- Optional: Indexes for faster lookups
CREATE INDEX idx_links_token ON links (token);
CREATE INDEX idx_links_folder_path ON links (folder_path);
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_uploaded_files_link_id ON uploaded_files (link_id);
CREATE INDEX idx_uploaded_files_timestamp ON uploaded_files (upload_timestamp);