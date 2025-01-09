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

# [Previous HTML template content remains the same]

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
    auth.process_response()
    errors = auth.get_errors()
    
    if not errors:
        if auth.is_authenticated():
            session['samlUserdata'] = auth.get_attributes()
            session['samlNameId'] = auth.get_nameid()
            session['user'] = {
                'preferred_username': auth.get_nameid(),
                'name': auth.get_attributes().get('displayName', [auth.get_nameid()])[0]
            }
            if 'next_url' in session:
                next_url = session['next_url']
                del session['next_url']
                return redirect(next_url)
            return redirect(url_for('admin'))
    return 'Authentication failed', 401

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

# [Rest of the previous routes remain the same]

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)