import sqlite3
from flask import current_app, g
import os

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE_PATH'])
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    
    # Read schema
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    
    # Create uploads directory if it doesn't exist
    os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

def record_click(short_link, ip_address, user_agent=None, referer=None):
    db = get_db()
    db.execute('''
        INSERT INTO clicks (short_link, ip_address, user_agent, referer)
        VALUES (?, ?, ?, ?)
    ''', (short_link, ip_address, user_agent, referer))
    db.commit()

def get_link_stats(short_link):
    db = get_db()
    # Get total clicks
    total_clicks = db.execute('''
        SELECT COUNT(*) as count FROM clicks WHERE short_link = ?
    ''', (short_link,)).fetchone()['count']
    
    # Get unique IPs
    unique_ips = db.execute('''
        SELECT COUNT(DISTINCT ip_address) as count FROM clicks WHERE short_link = ?
    ''', (short_link,)).fetchone()['count']
    
    # Get recent clicks
    recent_clicks = db.execute('''
        SELECT ip_address, user_agent, referer, clicked_at
        FROM clicks
        WHERE short_link = ?
        ORDER BY clicked_at DESC
        LIMIT 10
    ''', (short_link,)).fetchall()
    
    return {
        'total_clicks': total_clicks,
        'unique_visitors': unique_ips,
        'recent_clicks': recent_clicks
    }