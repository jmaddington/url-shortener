import os
import sqlite3
import logging
from flask import Flask, request, redirect, render_template_string, send_file, abort
from werkzeug.utils import secure_filename

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Database initialization
def init_db():
    conn = sqlite3.connect('shortener.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS links
        (short_link TEXT PRIMARY KEY, 
         target_url TEXT,
         is_file INTEGER,
         filename TEXT)
    ''')
    conn.commit()
    conn.close()

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
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', sans-serif;
        }

        body {
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 2rem;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        h1 {
            color: #2d3748;
            font-size: 2.5rem;
            margin-bottom: 2rem;
            text-align: center;
        }

        h2 {
            color: #4a5568;
            font-size: 1.5rem;
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e2e8f0;
        }

        .card {
            background: white;
            border-radius: 10px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: #4a5568;
        }

        input[type="text"],
        input[type="url"],
        input[type="file"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }

        input[type="text"]:focus,
        input[type="url"]:focus {
            outline: none;
            border-color: #4299e1;
            box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.2);
        }

        button {
            background-color: #4299e1;
            color: white;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        button:hover {
            background-color: #3182ce;
        }

        button.delete {
            background-color: #e53e3e;
        }

        button.delete:hover {
            background-color: #c53030;
        }

        button.copy {
            background-color: #48bb78;
            padding: 0.5rem 1rem;
            margin-left: 0.5rem;
        }

        button.copy:hover {
            background-color: #38a169;
        }

        button.copy.copied {
            background-color: #68d391;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        th {
            background-color: #f7fafc;
            font-weight: 600;
            color: #4a5568;
        }

        tr:hover {
            background-color: #f7fafc;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.875rem;
            font-weight: 500;
        }

        .badge.url {
            background-color: #ebf4ff;
            color: #4299e1;
        }

        .badge.file {
            background-color: #f0fff4;
            color: #48bb78;
        }

        .tooltip {
            position: absolute;
            background-color: #1a202c;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            font-size: 0.875rem;
            opacity: 0;
            transition: opacity 0.2s;
            pointer-events: none;
            z-index: 1000;
        }

        .tooltip.show {
            opacity: 1;
        }

        .link-actions {
            display: flex;
            gap: 0.5rem;
            align-items: center;
        }

        @media (max-width: 768px) {
            body {
                padding: 1rem;
            }

            .card {
                padding: 1rem;
            }

            table {
                display: block;
                overflow-x: auto;
                white-space: nowrap;
            }

            th, td {
                padding: 0.75rem;
            }
        }

        .forms-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 2rem;
        }

        .alert {
            padding: 1rem;
            border-radius: 6px;
            margin-bottom: 1rem;
            border: 1px solid transparent;
        }

        .alert-success {
            background-color: #f0fff4;
            border-color: #c6f6d5;
            color: #2f855a;
        }

        .alert-error {
            background-color: #fff5f5;
            border-color: #fed7d7;
            color: #c53030;
        }

        .truncate {
            max-width: 200px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .copy-tooltip {
            position: fixed;
            background: #1a202c;
            color: white;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 14px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>URL Shortener Admin</h1>
        
        <div class="forms-container">
            <div class="card">
                <h2>Create URL Redirect</h2>
                <form method="POST" action="/admin/create">
                    <div class="form-group">
                        <label>Short Link:</label>
                        <input type="text" name="short_link" required placeholder="e.g., my-link">
                    </div>
                    <div class="form-group">
                        <label>Target URL:</label>
                        <input type="url" name="target_url" required placeholder="https://example.com">
                    </div>
                    <button type="submit">Create URL Link</button>
                </form>
            </div>

            <div class="card">
                <h2>Upload File</h2>
                <form method="POST" action="/admin/upload" enctype="multipart/form-data">
                    <div class="form-group">
                        <label>Short Link:</label>
                        <input type="text" name="short_link" required placeholder="e.g., my-file">
                    </div>
                    <div class="form-group">
                        <label>File:</label>
                        <input type="file" name="file" required>
                    </div>
                    <button type="submit">Upload File</button>
                </form>
            </div>
        </div>

        <div class="card">
            <h2>Existing Links</h2>
            <table>
                <tr>
                    <th>Short Link</th>
                    <th>Target</th>
                    <th>Type</th>
                    <th>Actions</th>
                </tr>
                {% for link in links %}
                <tr>
                    <td>
                        <div style="display: flex; align-items: center;">
                            <a href="/{{ link[0] }}" target="_blank">{{ link[0] }}</a>
                            <button class="copy" onclick="copyToClipboard(this, '{{ request.host_url }}{{ link[0] }}')" title="Copy link">
                                <i class="fas fa-copy"></i>
                            </button>
                        </div>
                    </td>
                    <td class="truncate">{{ link[1] if not link[2] else link[3] }}</td>
                    <td>
                        <span class="badge {{ 'file' if link[2] else 'url' }}">
                            {{ 'File' if link[2] else 'URL' }}
                        </span>
                    </td>
                    <td>
                        <form method="POST" action="/admin/delete" style="display: inline;">
                            <input type="hidden" name="short_link" value="{{ link[0] }}">
                            <button type="submit" class="delete">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </div>

    <div id="copyTooltip" class="copy-tooltip">Copied!</div>

    <script>
    function copyToClipboard(button, text) {
        // Copy the text
        navigator.clipboard.writeText(text).then(() => {
            // Add the copied class to the button
            button.classList.add('copied');
            
            // Show tooltip
            const tooltip = document.getElementById('copyTooltip');
            tooltip.style.opacity = '1';
            
            // Position tooltip near the button
            const rect = button.getBoundingClientRect();
            tooltip.style.top = (rect.top - 40) + 'px';
            tooltip.style.left = (rect.left + rect.width/2 - 30) + 'px';
            
            // Hide tooltip and remove copied class after 2 seconds
            setTimeout(() => {
                tooltip.style.opacity = '0';
                button.classList.remove('copied');
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    }
    </script>
</body>
</html>
'''

@app.route('/admin')
def admin():
    conn = sqlite3.connect('shortener.db')
    c = conn.cursor()
    c.execute('SELECT * FROM links')
    links = c.fetchall()
    conn.close()
    return render_template_string(ADMIN_TEMPLATE, links=links)

@app.route('/admin/create', methods=['POST'])
def create_link():
    short_link = request.form['short_link']
    target_url = request.form['target_url']
    
    if short_link == 'admin':
        return 'Cannot use reserved word "admin"', 400
    
    conn = sqlite3.connect('shortener.db')
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO links (short_link, target_url, is_file) VALUES (?, ?, 0)',
              (short_link, target_url))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/admin/upload', methods=['POST'])
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
        # Save file with short_link as name to maintain uniqueness
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], short_link + '_' + filename)
        file.save(file_path)
        
        conn = sqlite3.connect('shortener.db')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO links (short_link, target_url, is_file, filename) VALUES (?, ?, 1, ?)',
                  (short_link, file_path, filename))
        conn.commit()
        conn.close()
        
    return redirect('/admin')

@app.route('/admin/delete', methods=['POST'])
def delete_link():
    short_link = request.form['short_link']
    logger.info(f"Attempting to delete link: {short_link}")
    
    conn = sqlite3.connect('shortener.db')
    c = conn.cursor()
    
    # Get link info before deletion
    c.execute('SELECT is_file, target_url FROM links WHERE short_link = ?', (short_link,))
    link_info = c.fetchone()
    
    if link_info and link_info[0]:  # If it's a file
        file_path = link_info[1]
        logger.info(f"Link is a file. Attempting to delete file at path: {file_path}")
        # Delete the file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Successfully deleted file: {file_path}")
            else:
                logger.warning(f"File not found at path: {file_path}")
        except OSError as e:
            logger.error(f"Error deleting file {file_path}: {str(e)}")
    
    # Delete from database
    c.execute('DELETE FROM links WHERE short_link = ?', (short_link,))
    conn.commit()
    conn.close()
    logger.info(f"Successfully deleted link from database: {short_link}")
    
    return redirect('/admin')

@app.route('/<short_link>')
def redirect_link(short_link):
    if short_link == 'admin':
        return redirect('/admin')
        
    conn = sqlite3.connect('shortener.db')
    c = conn.cursor()
    c.execute('SELECT target_url, is_file, filename FROM links WHERE short_link = ?', (short_link,))
    result = c.fetchone()
    conn.close()
    
    if result is None:
        abort(404)
        
    if result[1]:  # If it's a file
        return send_file(result[0], download_name=result[2])
    else:  # If it's a URL
        return redirect(result[0])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)