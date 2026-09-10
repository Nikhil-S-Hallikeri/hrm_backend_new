import logging
from celery import shared_task
from django.utils import timezone
from .models import Campaign
from .utils import execute_campaign

logger = logging.getLogger(__name__)

@shared_task
def check_scheduled_campaigns():
    """
    Periodic task to check for and execute scheduled campaigns.
    Runs every minute.
    """
    now = timezone.now()
    
    # Find all campaigns that are SCHEDULED and their scheduled time is past or present
    scheduled_campaigns = Campaign.objects.filter( # type: ignore
        status='SCHEDULED',
        scheduled_at__lte=now
    )
    
    if not scheduled_campaigns.exists():
        return "No scheduled campaigns to execute at this time."

    executed_count = 0
    for campaign in scheduled_campaigns:
        try:
            logger.info(f"Starting execution for scheduled campaign: {campaign.name} (ID: {campaign.id})")
            # execute_campaign manages status changes from RUNNING to COMPLETED/FAILED
            # and handles the sending logic.
            execute_campaign(campaign)
            executed_count += 1
        except Exception as e:
            logger.error(f"Error executing scheduled campaign {campaign.id}: {str(e)}")
            # In case of unhandled exception, mark as FAILED
            campaign.status = 'FAILED'
            campaign.completed_at = timezone.now()
            campaign.save(update_fields=['status', 'completed_at'])

    return f"Successfully initiated {executed_count} scheduled campaigns."

