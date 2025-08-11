#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the server
echo "Starting server..."
if [ "$DJANGO_DEBUG" = "False" ]; then
    echo "Starting production server with Gunicorn..."
    gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 180 --max-requests 1000 --max-requests-jitter 50 --preload email_sender.wsgi:application
else
    echo "Starting development server..."
    python manage.py runserver 0.0.0.0:8000
fi
