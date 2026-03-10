from django.apps import AppConfig


class HrmAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'HRM_App'

    # def ready(self):
    
    #     from HRM_App.wish_notification import setup_background_tasks
    #     setup_background_tasks()
    #     import HRM_App.signals

    def ready(self):
    
        
        import HRM_App.signals



    
    
