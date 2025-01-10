#!/bin/bash

# Create required directories if they don't exist
mkdir -p data uploads saml flask_session

# Set permissions (adjust user/group if needed)
chmod 755 data uploads saml flask_session

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.sample .env
    echo "Created .env file from .env.sample. Please edit it with your settings."
fi

# Create empty database directory
touch data/.keep

echo "Directory structure created and permissions set."
echo "Next steps:"
echo "1. Edit .env file with your settings"
echo "2. Run 'docker-compose up -d' to start the application"