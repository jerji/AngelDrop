-- Database Schema

-- Links table
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    folder_path TEXT NOT NULL,
    password_hash TEXT,
    creation_timestamp INTEGER DEFAULT (strftime('%s', 'now')),
    expiry_timestamp INTEGER
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_links_token ON links(token);
CREATE INDEX IF NOT EXISTS idx_links_folder_path ON links(folder_path);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);