-- clicks definition

CREATE TABLE clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_link TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    referer TEXT,
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (short_link) REFERENCES links(short_link) ON DELETE CASCADE
);

CREATE INDEX idx_clicks_short_link ON clicks(short_link);
CREATE INDEX idx_clicks_ip_address ON clicks(ip_address);
CREATE INDEX clicks_short_link_IDX ON clicks (short_link);

-- links definition

CREATE TABLE links (
    short_link TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    is_file INTEGER NOT NULL DEFAULT 0,
    filename TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
, description TEXT, expires_at TEXT, guid_required TEXT, basic_auth_user TEXT, basic_auth_pass TEXT);

CREATE INDEX links_short_link_IDX ON links (short_link);