[Previous content...]

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