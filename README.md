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

## SSO Configuration

### Microsoft Entra ID Setup

1. Register an Enterprise Application in Azure Portal
2. Configure the following URLs:
   - Identifier (Entity ID): Your application ID
   - Reply URL (ACS URL): `https://your-domain/sso/acs`
   - Sign-on URL: `https://your-domain/sso/login`
   - Logout URL: `https://your-domain/sso/logout`

3. Update SAML settings in `saml/settings.json`:
   - Entity ID
   - Certificate
   - SSO endpoints

### Local Authentication

To disable SSO and use local authentication:
1. Set `ENABLE_SSO=false` in `.env`
2. Restart the application
3. A default local user will be used

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
- View click statistics for each link

## Technical Details

- Built with Flask
- Uses SQLite for storage
- Supports file uploads up to 16MB
- SAML-based SSO integration
- Click tracking with IP address
- Mobile-responsive design

## Security Notes

This is a development version and should not be used in production without additional security measures:
- Add CSRF protection
- Add rate limiting
- Configure proper WSGI server
- Set up proper file storage
- Add input validation
- Configure secure session handling
- Set up proper logging

## Directory Structure

```
.
├── app.py              # Main application file
├── auth.py            # Authentication handling
├── config.py          # Configuration management
├── database.py        # Database operations
├── requirements.txt   # Python dependencies
├── schema.sql        # Database schema
├── uploads/          # Uploaded files storage
├── saml/            # SAML SSO configuration
│   └── settings.json
└── shortener.db     # SQLite database
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.