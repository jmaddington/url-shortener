# URL Shortener with File Hosting

A simple URL shortener and file hosting service built with Flask.

## Features

- Create custom short links for URLs
- Upload and host files with custom short links
- Copy short links to clipboard
- Admin interface for managing links
- File and URL deletion
- Responsive design

## Setup

1. Install requirements:
```bash
pip install flask werkzeug
```

2. Run the application:
```bash
python app.py
```

3. Access the admin interface at:
```
http://localhost:8080/admin
```

## Usage

### Creating URL Shortcuts
1. Go to the admin interface
2. Enter your desired short link and target URL
3. Click "Create URL Link"

### Uploading Files
1. Go to the admin interface
2. Enter your desired short link
3. Select a file
4. Click "Upload File"

### Managing Links
- Use the copy button to copy the full link to clipboard
- Use the delete button to remove links and their associated files

## Technical Details

- Built with Flask
- Uses SQLite for storage
- Supports file uploads up to 16MB
- Includes logging for file operations
- Mobile-responsive design

## Security Notes

This is a development version and should not be used in production without additional security measures:
- Add authentication
- Add CSRF protection
- Add rate limiting
- Configure proper WSGI server
- Set up proper file storage
- Add input validation