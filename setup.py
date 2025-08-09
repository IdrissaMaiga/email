#!/usr/bin/env python
"""
Setup script for Email Sender Django application with monitoring
"""
import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e.stderr}")
        return False

def main():
    print("🚀 Setting up Email Sender Django Application with Monitoring")
    print("=" * 60)
    
    # Check if Django is installed
    try:
        import django
        print(f"✅ Django {django.get_version()} is installed")
    except ImportError:
        print("❌ Django is not installed. Please run: pip install -r requirements.txt")
        return
    
    # Run migrations
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return
    
    if not run_command("python manage.py makemigrations email_monitor", "Creating email_monitor migrations"):
        return
    
    if not run_command("python manage.py migrate", "Running migrations"):
        return
    
    # Check if data.csv exists
    if os.path.exists("data.csv"):
        print("✅ data.csv file found")
    else:
        print("⚠️  data.csv file not found - you'll need to add this file")
    
    # Check .env file
    if os.path.exists(".env"):
        print("✅ .env file found")
    else:
        print("⚠️  .env file not found - you'll need to configure SMTP settings")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next Steps:")
    print("1. Make sure your .env file has the correct SMTP settings")
    print("2. Add your RESEND_WEBHOOK_SECRET to .env")
    print("3. Place your CSV file as 'data.csv' in the root directory")
    print("4. Run: python manage.py runserver")
    print("5. Configure Resend webhook to: http://127.0.0.1:8000/monitor/webhook/")
    print("\n🔗 URLs:")
    print("   • Email Sender: http://127.0.0.1:8000/")
    print("   • Email Dashboard: http://127.0.0.1:8000/monitor/dashboard/")
    print("   • Events List: http://127.0.0.1:8000/monitor/events/")
    print("   • Webhook Endpoint: http://127.0.0.1:8000/monitor/webhook/")

if __name__ == "__main__":
    main()
