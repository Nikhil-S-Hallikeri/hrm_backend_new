# send_wishes_daily.py

import os
import django
from django.utils import timezone

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HRM_Project.settings')  # Update to your correct settings module
django.setup()

# Import and run your wish function
from HRM_app.cron import send_email_for_unresolved_complaints  # Change path if needed

send_email_for_unresolved_complaints()

print(f"Wishes sent successfully at {timezone.now()}")
