from django.core.management.base import BaseCommand
from HRM_App.wish_notification import send_email_for_unresolved_complaints

class Command(BaseCommand):
    help = 'Send birthday and anniversary wishes to employees and notifications to all.'

    def handle(self, *args, **kwargs):
        send_email_for_unresolved_complaints()
        self.stdout.write(self.style.SUCCESS("🎉 Birthday/Anniversary wishes sent successfully!"))
