"""
Attendance Scheduler - Automatic Monthly Attendance Generation

This scheduler runs automatically when Django starts.
It creates attendance records for the next month on the 25th of each month.

No manual configuration needed - just deploy and it works!
"""

from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler import util
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


@util.close_old_connections
def generate_next_month_attendance():
    """
    Scheduled job to generate attendance records for next month.
    Runs on the 25th of every month at 11:00 PM.
    """
    try:
        logger.info("Starting monthly attendance generation...")
        call_command('generate_monthly_attendance', '--next-month')
        logger.info("Monthly attendance generation completed successfully")
    except Exception as e:
        logger.error(f"Error in monthly attendance generation: {e}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the background scheduler.
    Called automatically when Django starts.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Schedule: Run on 25th of every month at 11:00 PM
    scheduler.add_job(
        generate_next_month_attendance,
        'cron',
        day=25,
        hour=23,
        minute=0,
        id='generate_monthly_attendance',
        replace_existing=True,
        max_instances=1,  # Prevent overlapping runs
    )
    
    scheduler.start()
    logger.info("Attendance scheduler started successfully - will run on 25th of each month at 11:00 PM")
