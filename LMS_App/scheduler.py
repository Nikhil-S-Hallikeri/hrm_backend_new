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


@util.close_old_connections
def auto_recrawl_scheduled_websites():
    """
    Automated Midnight Website Crawler.
    Runs every night between 2:00 AM - 3:00 AM (at 2:30 AM).
    Checks all configured AIConfig website URLs.
    If a website URL has not been crawled in the last 3 days (or never),
    triggers re-crawling of the site to keep knowledge base fresh.
    """
    import datetime
    import requests
    from django.conf import settings
    from django.utils import timezone
    from whatsapp_app.models import AIConfig

    logger.info("Starting automated midnight website recrawling check...")
    now = timezone.now()
    three_days_ago = now - datetime.timedelta(days=3)

    try:
        configs = AIConfig.objects.all()
        for config in configs:
            websites = config.websites or []
            if not websites:
                continue
            updated_websites = []
            needs_save = False

            for site in websites:
                url = site.get("url") if isinstance(site, dict) else str(site)
                if not url:
                    continue

                last_crawled_str = site.get("last_crawled_at") if isinstance(site, dict) else None
                last_crawled = None
                if last_crawled_str:
                    try:
                        last_crawled = datetime.datetime.fromisoformat(last_crawled_str)
                    except Exception:
                        pass

                # Recrawl if never crawled or if last crawled >= 3 days ago
                if not last_crawled or last_crawled <= three_days_ago:
                    try:
                        logger.info(f"⏰ [MIDNIGHT CRAWLER]: Recrawling website {url} for AIConfig #{config.id}...")
                        chatbot_url = getattr(settings, "CHATBOT_SERVICE_URL", "http://localhost:8002").rstrip("/")
                        headers = {}
                        ingestion_token = getattr(settings, "INGESTION_API_TOKEN", None) or getattr(settings, "CHATBOT_INGESTION_TOKEN", None)
                        if ingestion_token:
                            headers["X-Ingestion-Token"] = ingestion_token

                        resp = requests.post(f"{chatbot_url}/knowledge/rebuild", headers=headers, data={"url": url}, timeout=120)
                        if resp.status_code == 200:
                            logger.info(f"Successfully recrawled {url}")
                            site_dict = site if isinstance(site, dict) else {"url": url}
                            site_dict["last_crawled_at"] = now.isoformat()
                            updated_websites.append(site_dict)
                            needs_save = True
                        else:
                            updated_websites.append(site if isinstance(site, dict) else {"url": url})
                    except Exception as err:
                        logger.error(f"Error recrawling website {url}: {err}")
                        updated_websites.append(site if isinstance(site, dict) else {"url": url})
                else:
                    updated_websites.append(site if isinstance(site, dict) else {"url": url})

            if needs_save:
                config.websites = updated_websites
                config.save(update_fields=['websites'])
    except Exception as exc:
        logger.error(f"Error in auto_recrawl_scheduled_websites job: {exc}", exc_info=True)


def start_scheduler():
    """
    Initialize and start the background scheduler.
    Called automatically when Django starts.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    
    # Schedule 1: Run on 25th of every month at 11:00 PM
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
    
    # Schedule 2: Run every night at 2:30 AM (between 2-3 AM) to re-crawl websites older than 3 days
    scheduler.add_job(
        auto_recrawl_scheduled_websites,
        'cron',
        hour=2,
        minute=30,
        id='auto_recrawl_scheduled_websites',
        replace_existing=True,
        max_instances=1,
    )
    
    scheduler.start()
    logger.info("Scheduler started successfully - monthly attendance & 3-day website midnight crawler active.")
