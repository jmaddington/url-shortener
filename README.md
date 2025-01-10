# URL Shortener with File Hosting

A simple URL shortener and file hosting service built with Flask, featuring SSO authentication and click tracking.

## Features

- Create custom short links for URLs
- Upload and host files with custom short links
- Copy short links to clipboard
- Admin interface for managing links
- File and URL deletion
- Click tracking with statistics
- Single Sign-On with Microsoft Entra ID
- Responsive design

## Setup

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env`:
```bash
# Create from .env.sample
cp .env.sample .env

# Edit .env with your settings
SECRET_KEY=your-secret-key
ENABLE_SSO=true  # or false for local auth
FLASK_DEBUG=false  # set to true for development
```

3. Run the application:
```bash
python app.py
```

4. Access the admin interface at:
```
http://localhost:8080/admin
```

## File Storage

- Uploaded files are stored in the `uploads/` directory
- Files are named as `{short_link}_{original_filename}`
- Database records in SQLite (`shortener.db`)
  - File metadata stored in `links` table
  - Click tracking in `clicks` table

## Database Schema

### Links Table
```sql
CREATE TABLE links (
    short_link TEXT PRIMARY KEY,
    target_url TEXT NOT NULL,
    is_file INTEGER NOT NULL DEFAULT 0,
    filename TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Clicks Table
```sql
CREATE TABLE clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    short_link TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    user_agent TEXT,
    referer TEXT,
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (short_link) REFERENCES links(short_link) ON DELETE CASCADE
);
```


## Docker Deployment

### Quick Start with Docker Compose

1. Run the setup script:
```bash
./setup.sh
```

2. Edit the `.env` file with your settings:
```bash
nano .env
```

3. Start the application:
```bash
docker-compose up -d
```

4. Access the admin interface at:
```
http://localhost:8080/admin
```

### Directory Structure

The setup creates the following directory structure:
```
.
├── data/           # SQLite database storage
├── uploads/        # Uploaded files storage
├── saml/          # SAML configuration
└── flask_session/ # Session data
```

### Docker Configuration

The Docker setup includes:
- Resource limits (1 CPU, 1GB RAM)
- Health checks
- Automatic restart
- Bind mounts for persistent data
- Non-root user execution
- Production-grade WSGI server (Gunicorn)

### Manual Docker Build

If you prefer to run without Docker Compose:

```bash
# Build the image
docker build -t urlshortener .

# Run the container
docker run -d \
  -p 8080:8080 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/uploads:/app/uploads \
  -v $(pwd)/saml:/app/saml \
  -v $(pwd)/flask_session:/app/flask_session \
  --env-file .env \
  --name urlshortener \
  urlshortener
```

### Container Management

```bash
# View logs
docker-compose logs -f

# Restart the application
docker-compose restart

# Stop the application
docker-compose down

# Update after code changes
docker-compose up -d --build
```

[Rest of previous content...]