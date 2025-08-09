# Email Templater - Django Version

This is a Django server-side rendering application that converts the original Flask email templater to Django.

## Features

- **Server-side rendering** with Django templates
- **Automatic CSV loading** from `data.csv` file
- **Email templating** with placeholder replacement
- **SMTP email sending** with Resend integration
- **Responsive UI** with Tailwind CSS
- **CSV preview** with scrollable table

## Project Structure

```
email_sender/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── .env                     # Environment variables (SMTP config)
├── data.csv                 # CSV data file
├── email_sender/            # Django project settings
│   ├── __init__.py
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL configuration
│   ├── wsgi.py              # WSGI application
│   └── asgi.py              # ASGI application
├── email_app/               # Django app
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── tests.py
│   ├── urls.py              # App URL patterns
│   └── views.py             # View functions
└── templates/
    └── email_app/
        └── index.html       # Main template
```

## Installation & Setup

1. **Install Django and dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   Make sure your `.env` file contains:
   ```
   SMTP_SERVER=smtp.resend.com
   SMTP_PORT=465
   SMTP_USERNAME=resend
   SMTP_EMAIL=your-email@domain.com
   SMTP_SENDER_NAME=Your Name
   SMTP_PASSWORD=your-resend-api-key
   ```

3. **Run Django migrations:**
   ```bash
   python manage.py migrate
   ```

4. **Start the development server:**
   ```bash
   python manage.py runserver
   ```

5. **Access the application:**
   Open your browser and go to `http://127.0.0.1:8000/`

## Key Differences from Flask Version

### Django Advantages:
- **Better project structure** with apps and settings separation
- **Built-in admin interface** (if needed in the future)
- **Template inheritance** and better template organization
- **CSRF protection** built-in
- **Better error handling** and debugging
- **Scalability** for future features
- **ORM support** if you want to add database models later

### Code Changes:
1. **Views**: Flask routes converted to Django view functions
2. **Templates**: HTML moved to Django template with `{% load static %}`
3. **URL routing**: Django URL patterns instead of Flask decorators
4. **Settings**: Environment variables managed through Django settings
5. **CSRF**: Added CSRF token handling in JavaScript

## Usage

1. **Prepare your CSV**: Make sure `data.csv` is in the root directory with columns like:
   - `prospect_first_name`
   - `prospect_last_name` 
   - `company_name`
   - `job_title`
   - Email column (any name)

2. **Access the application**: The CSV will load automatically

3. **Select email column**: Choose which column contains email addresses

4. **Customize template**: Edit the email template with `{column_name}` placeholders

5. **Send emails**: Click "Send Emails" to start the campaign

## Environment Configuration

All SMTP settings are configured via environment variables in `.env`:

- `SMTP_SERVER`: SMTP server (default: smtp.resend.com)
- `SMTP_PORT`: SMTP port (default: 465)
- `SMTP_USERNAME`: SMTP username (default: resend)
- `SMTP_EMAIL`: Your email address
- `SMTP_SENDER_NAME`: Display name for emails
- `SMTP_PASSWORD`: Your SMTP password/API key

## Development

To add new features:

1. **Models**: Add database models in `email_app/models.py`
2. **Views**: Add new views in `email_app/views.py`
3. **URLs**: Register new URLs in `email_app/urls.py`
4. **Templates**: Create new templates in `templates/email_app/`
5. **Static files**: Add CSS/JS in `static/` directory

## Production Deployment

For production:
1. Set `DEBUG = False` in settings.py
2. Configure proper `ALLOWED_HOSTS`
3. Use a production WSGI server (gunicorn, uwsgi)
4. Set up proper static file serving
5. Use environment variables for secret keys
