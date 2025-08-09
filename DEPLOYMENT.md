# Docker Deployment Guide

## Quick Start

1. **Clone and prepare the project:**
   ```bash
   git clone <your-repo>
   cd email_sender
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` file with your production values.

3. **Make sure your CSV file is in place:**
   ```bash
   # Place your data.csv file in the root directory
   ls data.csv
   ```

4. **Build and run with Docker Compose:**
   ```bash
   docker-compose up --build -d
   ```

5. **Access your application:**
   - Web interface: http://localhost:2001
   - Admin interface: http://localhost:2001/admin

## Production Deployment

### Environment Variables
Update these in your `.env` file:

- `DJANGO_SECRET_KEY`: Generate a new secret key
- `DJANGO_DEBUG`: Set to `False`
- `DJANGO_ALLOWED_HOSTS`: Add your domain
- `POSTGRES_PASSWORD`: Use a strong password
- `RESEND_API_KEY`: Your Resend API key

### SSL/HTTPS Setup
For production, you'll need to:

1. **Add nginx reverse proxy** (recommended)
2. **Set up SSL certificates** (Let's Encrypt)
3. **Update ALLOWED_HOSTS** with your domain

### Database Backup
```bash
# Backup database
docker-compose exec db pg_dump -U postgres email_sender_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres email_sender_db < backup.sql
```

## Docker Commands

### Development
```bash
# Start services
docker-compose up

# Build and start
docker-compose up --build

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f web

# Stop services
docker-compose down
```

### Production Commands
```bash
# Start production stack
DJANGO_DEBUG=False docker-compose up -d

# Scale web service
docker-compose up --scale web=3

# Update application
docker-compose down
git pull
docker-compose up --build -d
```

### Maintenance
```bash
# Access Django shell
docker-compose exec web python manage.py shell

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic

# View application logs
docker-compose logs -f web

# View database logs
docker-compose logs -f db
```

## File Structure
```
email_sender/
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── .env.example
├── data.csv                 # Your contact data
├── email_sender/           # Django project
├── email_app/              # Django app
└── templates/              # HTML templates
```

## Troubleshooting

### Database Connection Issues
```bash
# Check if database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Restart database
docker-compose restart db
```

### Application Issues
```bash
# Check application logs
docker-compose logs web

# Restart web service
docker-compose restart web

# Rebuild application
docker-compose down
docker-compose up --build
```

### Port Conflicts
If port 2001 is in use:
```bash
# Edit docker-compose.yml and change ports
ports:
  - "3001:8000"  # Change 2001 to any available port
```

## Security Notes

1. **Change default passwords** in production
2. **Use environment variables** for secrets
3. **Enable HTTPS** with proper SSL certificates
4. **Regularly backup** your database
5. **Monitor logs** for security issues
6. **Keep Docker images updated**
