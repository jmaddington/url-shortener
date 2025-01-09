import os
import tempfile
import subprocess
from flask import Flask, request, redirect, render_template_string, send_file, abort, session, url_for, make_response
from werkzeug.utils import secure_filename
from flask_session import Session
from urllib.parse import urlparse
import logging
import shutil

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

# Admin panel HTML template
ADMIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>URL Shortener Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* Previous styles remain the same */
        
        .download-btn {
            background-color: #6B7280;
            font-size: 0.875rem;
            padding: 0.5rem 1rem;
            margin-left: 0.5rem;
            text-decoration: none;
            color: white;
            border-radius: 6px;
            display: inline-block;
        }

        .download-btn:hover {
            background-color: #4B5563;
        }

        .download-btn i {
            margin-right: 0.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="user-info">
            {% if user %}
                Logged in as <span class="user-name">{{ user.name }}</span>
                <a href="/download-repo" class="download-btn">
                    <i class="fas fa-download"></i> Download Repository
                </a>
                <a href="/sso/logout" class="button logout-btn">Logout</a>
            {% endif %}
        </div>

        <!-- Rest of the template remains the same -->
        [... previous template content ...]
    </div>
</body>
</html>
'''

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

[... rest of the previous routes and code ...]