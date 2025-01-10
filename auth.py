from functools import wraps
from flask import session, redirect, url_for, current_app, request, g
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
import json
import os
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def init_saml_auth(req):
    saml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'saml')
    with open(os.path.join(saml_path, 'settings.json'), 'r') as f:
        settings = json.load(f)
        logger.debug(f"SAML Settings loaded: {json.dumps(settings, indent=2)}")
    auth = OneLogin_Saml2_Auth(req, settings)
    return auth

def prepare_flask_request(request):
    url_data = urlparse(request.url)
    logger.debug(f"Preparing Flask request: URL={request.url}, Host={request.host}")
    
    # Get the actual URL scheme (http or https)
    scheme = request.headers.get('X-Forwarded-Proto', request.scheme)
    
    return {
        'https': 'on' if scheme == 'https' else 'off',
        'http_host': request.host,
        'server_port': url_data.port or (443 if scheme == 'https' else 80),
        'script_name': request.path,
        'get_data': request.args.copy(),
        'post_data': request.form.copy(),
        'query_string': request.query_string
    }

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_app.config['ENABLE_SSO']:
            if 'user' not in session:
                session['user'] = {
                    'preferred_username': 'local_user',
                    'name': 'Local User'
                }
            return f(*args, **kwargs)
            
        if not session.get('user'):
            session['next_url'] = request.url
            logger.debug(f"No user in session, redirecting to SSO login. Next URL: {request.url}")
            return redirect(url_for('sso_login'))
            
        return f(*args, **kwargs)
    return decorated