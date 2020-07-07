CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    uri TEXT NOT NULL,
    created TEXT NOT NULL,
    FOREIGN KEY (user_id)
        REFERENCES users (id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
);

CREATE TABLE user_sessions (
    user_id INTEGER PRIMARY KEY,
    session_id TEXT NOT NULL UNIQUE,
    expiration TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS.SSS
    FOREIGN KEY (user_id)
        REFERENCES users (id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
);

CREATE TABLE user_email_state (
    user_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL UNIQUE,
    expiration TEXT NOT NULL, -- YYYY-MM-DD HH:MM:SS.SSS
    FOREIGN KEY (user_id)
        REFERENCES users (id)
            ON DELETE CASCADE
            ON UPDATE NO ACTION
);