import glob
import zipfile
from flask import Flask, g, request, redirect, render_template, send_file, abort, session, url_for, make_response
from werkzeug.utils import secure_filename
from flask_session import Session
from urllib.parse import urlparse
import logging
import shutil
import os
import tempfile
import subprocess
import uuid
import base64
from datetime import datetime

from auth import requires_auth, init_saml_auth, prepare_flask_request
from database import init_db, get_db, close_db, record_click, get_link_stats
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
Session(app)

# Make sure this directory exists or is configured properly
# e.g. app.config['UPLOAD_FOLDER'] = '/path/to/uploads'
if not hasattr(app.config, 'UPLOAD_FOLDER'):
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
with app.app_context():
    init_db()

def _http_auth_required():
    """Helper function to return a 401 with WWW-Authenticate header."""
    response = make_response("Authentication required", 401)
    response.headers["WWW-Authenticate"] = 'Basic realm="URLShortener"'
    return response

def is_valid_url(url):
    """Minimal check to ensure URL is http or https, and has a netloc."""
    parsed = urlparse(url)
    return parsed.scheme in ['http', 'https'] and parsed.netloc

def normalize_url(url):
    """If the URL doesn’t start with http:// or https://, prepend https://."""
    if url and not (url.startswith('http://') or url.startswith('https://')):
        return 'https://' + url
    return url

@app.route('/download-repo')
@requires_auth
def download_repo():
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create archive of the current directory, excluding certain paths
        repo_dir = os.getcwd()
        archive_path = os.path.join(temp_dir, 'urlshortener.zip')
        
        try:
            # Use git archive to create a zip of the repo
            subprocess.run([
                'git', 'archive', 
                '--format=zip',
                '--output', archive_path,
                'HEAD'
            ], check=True)
            
            return send_file(
                archive_path,
                as_attachment=True,
                download_name='urlshortener.zip',
                mimetype='application/zip'
            )
        except Exception as e:
            logger.error(f"Error creating repository archive: {str(e)}")
            return "Error creating repository archive", 500

@app.route('/sso/login')
def sso_login():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    return redirect(auth.login())

@app.route('/sso/metadata')
def metadata():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)

    if len(errors) == 0:
        resp = make_response(metadata, 200)
        resp.headers['Content-Type'] = 'text/xml'
    else:
        resp = make_response(', '.join(errors), 500)
    return resp

@app.route('/sso/acs', methods=['POST'])
def acs():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    logger.info("Processing SAML response")
    auth.process_response()
    errors = auth.get_errors()
    
    if errors:
        logger.error(f"SAML Authentication errors: {errors}")
        logger.error(f"Last error reason: {auth.get_last_error_reason()}")
        return f'Authentication failed: {", ".join(errors)}', 401
    
    if not auth.is_authenticated():
        logger.error("SAML Authentication failed: User not authenticated")
        return 'Authentication failed: Not authenticated', 401

    # Get user attributes
    attributes = auth.get_attributes()
    name_id = auth.get_nameid()
    logger.info(f"User authenticated. NameID: {name_id}")
    logger.info(f"User attributes: {attributes}")

    # Store user information in session
    session['samlUserdata'] = attributes
    session['samlNameId'] = name_id
    session['user'] = {
        'preferred_username': name_id,
        'name': attributes.get('displayName', [name_id])[0] if attributes else name_id
    }

    # Redirect to the next URL or admin page
    if 'next_url' in session:
        next_url = session.pop('next_url')
        logger.info(f"Redirecting to: {next_url}")
        return redirect(next_url)
    return redirect(url_for('admin'))

@app.route('/sso/sls')
def sls():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    url = auth.process_slo(delete_session_cb=lambda: session.clear())
    errors = auth.get_errors()
    if len(errors) == 0:
        if url is not None:
            return redirect(url)
        return redirect(url_for('admin'))
    return 'Logout failed', 500

@app.route('/sso/logout')
def logout():
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    name_id = session.get('samlNameId')
    session_index = session.get('samlSessionIndex')
    if name_id is None and session_index is None:
        session.clear()
        return redirect(url_for('admin'))
    else:
        return redirect(auth.logout())

@app.route('/admin')
@requires_auth
def admin():
    page = request.args.get("page", 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    conn = get_db()
    c = conn.cursor()
    
    # Get total count
    c.execute("SELECT COUNT(*) as count FROM links")
    total_links = c.fetchone()["count"]
    total_pages = (total_links + per_page - 1) // per_page
    
    # Get paginated links (including basic info like unique visitors, etc.)
    c.execute("""
        SELECT l.*, 
               COUNT(DISTINCT c.ip_address) as unique_visitors,
               COUNT(c.id) as total_clicks
        FROM links l
        LEFT JOIN clicks c ON l.short_link = c.short_link
        GROUP BY l.short_link
        ORDER BY l.created_at DESC
        LIMIT ? OFFSET ?
    """, (per_page, offset))
    
    links = c.fetchall()
    return render_template("admin.html", 
                           links=links,
                           user=session.get("user"),
                           page=page,
                           total_pages=total_pages,
                           total_links=total_links)

@app.route('/admin/search')
@requires_auth
def search_links():
    search_term = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page
    
    logger.info(f"Searching for: {search_term} (page {page})")
    
    conn = get_db()
    c = conn.cursor()
    
    if search_term:
        search_pattern = f"%{search_term}%"
        # Get total count for search
        c.execute("""
            SELECT COUNT(*) as count 
            FROM links 
            WHERE short_link LIKE ? 
               OR target_url LIKE ? 
               OR filename LIKE ?
               OR description LIKE ?
        """, (search_pattern, search_pattern, search_pattern, search_pattern))
        total_links = c.fetchone()["count"]
        
        # Get paginated search results
        c.execute("""
            SELECT l.*, 
                   COUNT(DISTINCT c.ip_address) as unique_visitors,
                   COUNT(c.id) as total_clicks
            FROM links l
            LEFT JOIN clicks c ON l.short_link = c.short_link
            WHERE l.short_link LIKE ? 
               OR l.target_url LIKE ? 
               OR l.filename LIKE ?
               OR l.description LIKE ?
            GROUP BY l.short_link
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
        """, (search_pattern, search_pattern, search_pattern, search_pattern, per_page, offset))
    else:
        # Get total count
        c.execute("SELECT COUNT(*) as count FROM links")
        total_links = c.fetchone()["count"]
        
        # Get paginated results
        c.execute("""
            SELECT l.*, 
                   COUNT(DISTINCT c.ip_address) as unique_visitors,
                   COUNT(c.id) as total_clicks
            FROM links l
            LEFT JOIN clicks c ON l.short_link = c.short_link
            GROUP BY l.short_link
            ORDER BY l.created_at DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))
    
    total_pages = (total_links + per_page - 1) // per_page
    links = c.fetchall()
    logger.info(f"Found {total_links} results, showing page {page} of {total_pages}")
    return render_template("_links_table.html",
                           links=links,
                           page=page,
                           total_pages=total_pages,
                           total_links=total_links)

@app.route('/admin/create', methods=['POST'])
@requires_auth
def create_link():
    """
    Creates a new link that redirects to a URL (non-file).
    If the user actually wants to upload a file, 
    they should call the /admin/upload endpoint instead.
    """
    short_link = request.form['short_link'].strip()
    target_url = request.form['target_url'].strip()
    description = request.form.get('description', '').strip()
    
    # Optional fields
    expires_at = request.form.get('expires_at', '').strip()
    require_guid = request.form.get('require_guid')  # checkbox
    basic_auth_user = request.form.get('basic_auth_user', '').strip()
    basic_auth_pass = request.form.get('basic_auth_pass', '').strip()
    
    # Validate short_link
    if short_link == 'admin':
        return 'Cannot use reserved word "admin"', 400
    
    # Normalize URL first (prepend https:// if needed)
    if target_url:
        target_url = normalize_url(target_url)
        # Now validate
        if not is_valid_url(target_url):
            return "Invalid URL", 400
    
    # If user checked the "require_guid" box, generate a GUID
    guid_required = None
    if require_guid == 'on':
        guid_required = str(uuid.uuid4())
    
    # If expires_at is empty, store NULL
    if not expires_at:
        expires_at = None
    
    # If basic_auth_user or pass is empty, store NULL
    if not basic_auth_user:
        basic_auth_user = None
    if not basic_auth_pass:
        basic_auth_pass = None
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO links 
        (short_link, target_url, is_file, created_by, description, expires_at, guid_required, basic_auth_user, basic_auth_pass) 
        VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?)
    ''', (
        short_link,
        target_url,
        session['user'].get('preferred_username'),
        description,
        expires_at,
        guid_required,
        basic_auth_user,
        basic_auth_pass
    ))
    conn.commit()
    return redirect('/admin')

@app.route('/admin/upload', methods=['POST'])
@requires_auth
def upload_file():
    """
    Creates a new link that points to a file stored locally.
    """
    if 'file' not in request.files:
        return 'No file part', 400
    
    file = request.files['file']
    short_link = request.form['short_link'].strip()
    description = request.form.get('description', '').strip()
    
    # Optional fields for new features
    expires_at = request.form.get('expires_at', '').strip()
    require_guid = request.form.get('require_guid')  # checkbox
    basic_auth_user = request.form.get('basic_auth_user', '').strip()
    basic_auth_pass = request.form.get('basic_auth_pass', '').strip()
    
    # Validate short_link
    if short_link == 'admin':
        return 'Cannot use reserved word "admin"', 400
    
    if file.filename == '':
        return 'No selected file', 400
    
    # Secure and save the uploaded file
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], short_link + '_' + filename)
    file.save(file_path)
    
    # If user checked "require_guid", generate a GUID
    guid_required = None
    if require_guid == 'on':
        guid_required = str(uuid.uuid4())
    
    # If expires_at is empty, store NULL
    if not expires_at:
        expires_at = None
    
    # If either basic_auth_user or pass is empty, store NULL
    if not basic_auth_user:
        basic_auth_user = None
    if not basic_auth_pass:
        basic_auth_pass = None
    
    # Insert (or replace) link record into DB
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO links
        (short_link, target_url, is_file, filename, created_by, description,
         expires_at, guid_required, basic_auth_user, basic_auth_pass)
        VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        short_link,
        file_path,  # <-- This becomes target_url in the DB
        filename,
        session['user'].get('preferred_username'),
        description,
        expires_at,
        guid_required,
        basic_auth_user,
        basic_auth_pass
    ))
    conn.commit()
    
    return redirect('/admin')


@app.route('/admin/edit/<short_link>', methods=['GET', 'POST'])
@requires_auth
def edit_link(short_link):
    """
    Allows editing of an existing short_link (either a file-based link or a URL).
    """
    conn = get_db()
    c = conn.cursor()
    
    if request.method == 'GET':
        c.execute("SELECT * FROM links WHERE short_link = ?", (short_link,))
        link = c.fetchone()
        
        if link is None:
            abort(404)
            
        return render_template("edit.html", link=link)
    
    else:
        # Fetch the original row
        c.execute("SELECT * FROM links WHERE short_link = ?", (short_link,))
        current_link = c.fetchone()
        
        if current_link is None:
            abort(404)
        
        new_short_link = request.form["short_link"].strip()
        description = request.form.get("description", "").strip()
        expires_at = request.form.get('expires_at', '').strip()
        require_guid = request.form.get('require_guid')  # checkbox
        basic_auth_user = request.form.get('basic_auth_user', '').strip()
        basic_auth_pass = request.form.get('basic_auth_pass', '').strip()
        
        # Validate
        if new_short_link == "admin":
            return "Cannot use reserved word \"admin\"", 400
        
        # If user wants a GUID
        guid_required = None
        if require_guid == 'on':
            guid_required = str(uuid.uuid4())
        
        # If expires_at is empty, store NULL
        if not expires_at:
            expires_at = None
        
        # If either basic_auth_user or pass is empty, store NULL
        if not basic_auth_user:
            basic_auth_user = None
        if not basic_auth_pass:
            basic_auth_pass = None
        
        # If it's a file-based link
        if current_link["is_file"]:
            file = request.files.get("file")
            if file and file.filename:
                # (A) User uploaded a new file
                try:
                    # Delete the old file if it exists
                    os.remove(current_link["target_url"])
                except OSError:
                    pass
                
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], new_short_link + "_" + filename)
                file.save(file_path)
                
                if short_link == new_short_link:
                    # Update same row
                    c.execute("""
                        UPDATE links
                        SET target_url = ?,
                            filename = ?,
                            description = ?,
                            expires_at = ?,
                            guid_required = ?,
                            basic_auth_user = ?,
                            basic_auth_pass = ?
                        WHERE short_link = ?
                    """, (
                        file_path,
                        filename,
                        description,
                        expires_at,
                        guid_required,
                        basic_auth_user,
                        basic_auth_pass,
                        short_link
                    ))
                else:
                    # If short_link changed, create new row and delete old
                    c.execute("""
                        INSERT OR REPLACE INTO links
                        (short_link, target_url, is_file, filename, created_by, description,
                         expires_at, guid_required, basic_auth_user, basic_auth_pass)
                        VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        new_short_link,
                        file_path,
                        filename,
                        session["user"].get("preferred_username"),
                        description,
                        expires_at,
                        guid_required,
                        basic_auth_user,
                        basic_auth_pass
                    ))
                    c.execute("DELETE FROM links WHERE short_link = ?", (short_link,))
            
            else:
                # (B) No new file uploaded; keep current file path & filename
                if short_link == new_short_link:
                    # Just update metadata
                    c.execute("""
                        UPDATE links
                        SET description = ?,
                            expires_at = ?,
                            guid_required = ?,
                            basic_auth_user = ?,
                            basic_auth_pass = ?
                        WHERE short_link = ?
                    """, (
                        description,
                        expires_at,
                        guid_required,
                        basic_auth_user,
                        basic_auth_pass,
                        short_link
                    ))
                else:
                    # Short link changed, so re‐insert with same file, remove old
                    c.execute("""
                        INSERT OR REPLACE INTO links
                        (short_link, target_url, is_file, filename, created_by, description,
                         expires_at, guid_required, basic_auth_user, basic_auth_pass)
                        VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        new_short_link,
                        current_link["target_url"],
                        current_link["filename"],
                        session["user"].get("preferred_username"),
                        description,
                        expires_at,
                        guid_required,
                        basic_auth_user,
                        basic_auth_pass
                    ))
                    c.execute("DELETE FROM links WHERE short_link = ?", (short_link,))
        
        else:
            # It's not a file link; it's a URL link
            target_url = request.form["target_url"].strip()
            if target_url:
                target_url = normalize_url(target_url)
                if not is_valid_url(target_url):
                    return "Invalid URL", 400
            
            if short_link == new_short_link:
                # Update same row
                c.execute("""
                    UPDATE links
                    SET target_url = ?,
                        description = ?,
                        expires_at = ?,
                        guid_required = ?,
                        basic_auth_user = ?,
                        basic_auth_pass = ?
                    WHERE short_link = ?
                """, (
                    target_url,
                    description,
                    expires_at,
                    guid_required,
                    basic_auth_user,
                    basic_auth_pass,
                    short_link
                ))
            else:
                # Short link changed -> insert new, remove old
                c.execute("""
                    INSERT OR REPLACE INTO links
                    (short_link, target_url, is_file, created_by, description,
                     expires_at, guid_required, basic_auth_user, basic_auth_pass)
                    VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?)
                """, (
                    new_short_link,
                    target_url,
                    session["user"].get("preferred_username"),
                    description,
                    expires_at,
                    guid_required,
                    basic_auth_user,
                    basic_auth_pass
                ))
                c.execute("DELETE FROM links WHERE short_link = ?", (short_link,))
        
        conn.commit()
        return redirect("/admin")

@app.route('/admin/stats/<short_link>')
@requires_auth
def link_stats(short_link):
    stats = get_link_stats(short_link)
    return render_template('stats.html', short_link=short_link, stats=stats)

@app.route('/<short_link>')
def redirect_link(short_link):
    if short_link == 'admin':
        return redirect('/admin')
        
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT target_url, is_file, filename,
               expires_at, guid_required, basic_auth_user, basic_auth_pass
        FROM links
        WHERE short_link = ?
    ''', (short_link,))
    result = c.fetchone()
    
    if result is None:
        abort(404)
    
    # 1) Check if expired
    expires_at = result['expires_at']
    if expires_at:
        try:
            expires_dt = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            if datetime.utcnow() > expires_dt:
                abort(404)  # Link expired
        except ValueError:
            # If parsing fails, ignore or log an error
            pass
    
    # 2) Check Basic Auth
    if result['basic_auth_user'] is not None:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Basic '):
            return _http_auth_required()
        
        # Decode base64
        encoded_credentials = auth_header.split(' ', 1)[1].strip()
        try:
            decoded_bytes = base64.b64decode(encoded_credentials)
            decoded_str = decoded_bytes.decode('utf-8')
            incoming_user, incoming_pass = decoded_str.split(':', 1)
        except Exception:
            return _http_auth_required()
        
        # Compare with stored credentials
        if (incoming_user != result['basic_auth_user'] or
                incoming_pass != result['basic_auth_pass']):
            return _http_auth_required()
    
    # 3) Check GUID
    if result['guid_required']:
        passed_guid = request.args.get('s')
        if passed_guid != result['guid_required']:
            abort(403)  # Wrong or missing GUID
    
    # If we pass all checks, record the click
    record_click(
        short_link=short_link,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referer=request.referrer
    )
    
    # Finally, serve the file or redirect
    if result['is_file']:  # If it's a file
        return send_file(result['target_url'], download_name=result['filename'])
    else:  # If it's a URL
        return redirect(result['target_url'])

@app.route('/admin/delete', methods=['POST'])
@requires_auth
def delete_link():
    short_link = request.form['short_link']
    
    conn = get_db()
    c = conn.cursor()
    
    # Get file info before deletion
    c.execute('SELECT is_file, target_url FROM links WHERE short_link = ?', (short_link,))
    result = c.fetchone()
    
    if result and result['is_file']:
        # Delete the file if it exists
        try:
            os.remove(result['target_url'])
        except OSError:
            pass
    
    # Delete from database
    c.execute('DELETE FROM links WHERE short_link = ?', (short_link,))
    conn.commit()
    
    return redirect('/admin')

@app.teardown_appcontext
def cleanup(exc):
    if hasattr(g, "db"):
        g.db.close()

if __name__ == '__main__':
    # Adjust as needed, but normally we'd use WSGI (Gunicorn, etc.)
    app.run(host='0.0.0.0', port=8080)
