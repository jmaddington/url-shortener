import os
from flask import Flask, request, redirect, render_template_string, send_file, abort, session, url_for, make_response
from werkzeug.utils import secure_filename
from flask_session import Session
from urllib.parse import urlparse
import logging

from auth import requires_auth, init_saml_auth, prepare_flask_request
from database import init_db, get_db, close_db, record_click, get_link_stats
from config import Config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
Session(app)

# Initialize database
with app.app_context():
    init_db()

# [Previous HTML template content]
ADMIN_TEMPLATE = '''
[Your previous HTML template content]
'''

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
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT l.*, 
               COUNT(DISTINCT c.ip_address) as unique_visitors,
               COUNT(c.id) as total_clicks
        FROM links l
        LEFT JOIN clicks c ON l.short_link = c.short_link
        GROUP BY l.short_link
    ''')
    links = c.fetchall()
    return render_template_string(ADMIN_TEMPLATE, 
                                links=links,
                                user=session.get('user'))

@app.route('/admin/create', methods=['POST'])
@requires_auth
def create_link():
    short_link = request.form['short_link']
    target_url = request.form['target_url']
    
    if short_link == 'admin':
        return 'Cannot use reserved word "admin"', 400
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO links 
        (short_link, target_url, is_file, created_by) 
        VALUES (?, ?, 0, ?)
    ''', (short_link, target_url, session['user'].get('preferred_username')))
    conn.commit()
    return redirect('/admin')

@app.route('/admin/upload', methods=['POST'])
@requires_auth
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    short_link = request.form['short_link']
    
    if short_link == 'admin':
        return 'Cannot use reserved word "admin"', 400
    
    if file.filename == '':
        return 'No selected file', 400
        
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], 
                                short_link + '_' + filename)
        file.save(file_path)
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT OR REPLACE INTO links 
            (short_link, target_url, is_file, filename, created_by) 
            VALUES (?, ?, 1, ?, ?)
        ''', (short_link, file_path, filename, 
              session['user'].get('preferred_username')))
        conn.commit()
        
    return redirect('/admin')

@app.route('/admin/stats/<short_link>')
@requires_auth
def link_stats(short_link):
    stats = get_link_stats(short_link)
    return render_template_string('''
        <h1>Statistics for {{ short_link }}</h1>
        <p>Total Clicks: {{ stats.total_clicks }}</p>
        <p>Unique Visitors: {{ stats.unique_visitors }}</p>
        <h2>Recent Clicks</h2>
        <table>
            <tr>
                <th>IP Address</th>
                <th>User Agent</th>
                <th>Referer</th>
                <th>Time</th>
            </tr>
            {% for click in stats.recent_clicks %}
            <tr>
                <td>{{ click.ip_address }}</td>
                <td>{{ click.user_agent }}</td>
                <td>{{ click.referer }}</td>
                <td>{{ click.clicked_at }}</td>
            </tr>
            {% endfor %}
        </table>
    ''', short_link=short_link, stats=stats)

@app.route('/<short_link>')
def redirect_link(short_link):
    if short_link == 'admin':
        return redirect('/admin')
        
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT target_url, is_file, filename 
        FROM links 
        WHERE short_link = ?
    ''', (short_link,))
    result = c.fetchone()
    
    if result is None:
        abort(404)
    
    # Record the click
    record_click(
        short_link=short_link,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string,
        referer=request.referrer
    )
        
    if result['is_file']:  # If it's a file
        return send_file(result['target_url'], 
                        download_name=result['filename'])
    else:  # If it's a URL
        return redirect(result['target_url'])

@app.teardown_appcontext
def cleanup(exc):
    close_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)