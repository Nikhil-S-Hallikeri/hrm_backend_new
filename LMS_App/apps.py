from django.apps import AppConfig
# from LMS_App.file import loopfun

class LmsAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'LMS_App'

    #9/2/2026
    def ready(self):
        """
        Called when Django starts.
        Starts the attendance scheduler for automatic monthly generation.
        """
        try:
            from . import scheduler
            scheduler.start_scheduler()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to start scheduler: {e}")
