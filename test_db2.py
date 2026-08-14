import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrm_project.settings')
django.setup()
from HRM_App.models import ActivityListModel
for act in ActivityListModel.objects.all():
    print(act.activity_name)
