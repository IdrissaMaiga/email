#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "Database is ready!"

# Create and run migrations
echo "Creating migrations..."
python manage.py makemigrations

echo "Running database migrations..."
python manage.py migrate

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the server
echo "Starting server..."
if [ "$DJANGO_DEBUG" = "False" ]; then
    echo "Starting production server with Daphne (ASGI)..."
    daphne -b 0.0.0.0 -p 8000 email_sender.asgi:application
else
    echo "Starting development server..."
    python manage.py runserver 0.0.0.0:8000
fi
