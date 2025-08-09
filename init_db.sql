-- Initialize the database with required tables
-- This script runs when the PostgreSQL container starts

-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE email_sender_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'email_sender_db');
