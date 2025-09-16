from django.core.management.base import BaseCommand
from email_monitor.models import EmailSender

class Command(BaseCommand):
    help = 'Check and display email sender configurations'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Checking Email Sender Configurations...")
        self.stdout.write("=" * 50)
        
        # Get all senders
        all_senders = EmailSender.objects.all()
        active_senders = EmailSender.objects.filter(is_active=True)
        
        self.stdout.write(f"📊 Total senders in database: {all_senders.count()}")
        self.stdout.write(f"✅ Active senders: {active_senders.count()}")
        self.stdout.write("")
        
        if not all_senders.exists():
            self.stdout.write("❌ No email senders found in database!")
            self.stdout.write("💡 Add senders via Django admin or the sender management interface")
            return
        
        # Display each sender
        for sender in all_senders:
            status = "✅ ACTIVE" if sender.is_active else "❌ INACTIVE"
            api_key_status = "✅ Configured" if sender.api_key else "❌ Missing"
            webhook_status = "✅ Configured" if sender.webhook_url else "⚠️ Not set"
            
            self.stdout.write(f"{status} {sender.name}")
            self.stdout.write(f"   📧 Email: {sender.email}")
            self.stdout.write(f"   🔑 Key: {sender.key}")
            self.stdout.write(f"   🌐 Domain: {sender.domain}")
            self.stdout.write(f"   🔐 API Key: {api_key_status}")
            if sender.api_key:
                self.stdout.write(f"      Full API Key: {sender.api_key}")
            self.stdout.write(f"   🪝 Webhook: {webhook_status}")
            if sender.webhook_url:
                self.stdout.write(f"      URL: {sender.webhook_url}")
            if sender.webhook_secret:
                self.stdout.write(f"      Secret: {sender.webhook_secret}")
            self.stdout.write("")
        
        # Check for common issues
        self.stdout.write("🔧 TROUBLESHOOTING:")
        
        senders_without_api_key = all_senders.filter(api_key__isnull=True) | all_senders.filter(api_key='')
        if senders_without_api_key.exists():
            self.stdout.write("❌ Senders missing API keys:")
            for sender in senders_without_api_key:
                self.stdout.write(f"   - {sender.name} ({sender.email})")
        
        inactive_senders = all_senders.filter(is_active=False)
        if inactive_senders.exists():
            self.stdout.write("⚠️ Inactive senders:")
            for sender in inactive_senders:
                self.stdout.write(f"   - {sender.name} ({sender.email})")
        
        if active_senders.exists():
            self.stdout.write("✅ Configuration looks good!")
        else:
            self.stdout.write("❌ No active senders found!")
            self.stdout.write("💡 Enable at least one sender for the system to work")
