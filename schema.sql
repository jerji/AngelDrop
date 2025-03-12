DROP TABLE IF EXISTS links;
DROP TABLE IF EXISTS users;

CREATE TABLE links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    folder_path TEXT NOT NULL,
    password_hash TEXT,  -- Store password hash (can be NULL)
    expiry_timestamp INTEGER  -- Store expiry timestamp as Unix time (can be NULL)
);

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);