CREATE TABLE IF NOT EXISTS links (
    short_link TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    is_file INTEGER NOT NULL DEFAULT 0,
    filename TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_link TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    referer TEXT,
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (short_link) REFERENCES links (short_link) ON DELETE CASCADE
);