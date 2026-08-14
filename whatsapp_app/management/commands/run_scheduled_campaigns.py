import time
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from whatsapp_app.models import Campaign
from whatsapp_app.utils import execute_campaign

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Continuously checks and executes scheduled campaigns without requiring Celery'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting scheduled campaigns worker..."))
        self.stdout.write(self.style.WARNING("Press Ctrl+C to stop.\n"))
        
        while True:
            now = timezone.now()
            
            # Find all campaigns that are SCHEDULED and their scheduled time is past or present
            scheduled_campaigns = Campaign.objects.filter(
                status='SCHEDULED',
                scheduled_at__lte=now
            )
            
            if scheduled_campaigns.exists():
                for campaign in scheduled_campaigns:
                    self.stdout.write(self.style.SUCCESS(f"[{now}] Executing scheduled campaign: {campaign.name} (ID: {campaign.id})"))
                    try:
                        execute_campaign(campaign)
                        self.stdout.write(self.style.SUCCESS(f"[{timezone.now()}] Finished executing: {campaign.name}"))
                    except Exception as e:
                        logger.error(f"Error executing scheduled campaign {campaign.id}: {str(e)}")
                        self.stdout.write(self.style.ERROR(f"[{timezone.now()}] Error: {str(e)}"))
                        campaign.status = 'FAILED'
                        campaign.completed_at = timezone.now()
                        campaign.save(update_fields=['status', 'completed_at'])
            
            # Sleep for 10 seconds before checking again
            time.sleep(10)

