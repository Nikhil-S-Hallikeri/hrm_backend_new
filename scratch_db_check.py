import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HRM_Project.settings')
django.setup()

from HRM_App.models import NewDailyAchivesModel

leads = NewDailyAchivesModel.objects.filter(candidate_name__icontains='KUSHAL')
print(f"Found {leads.count()} leads matching KUSHAL:")
for lead in leads:
    print(f"ID: {lead.id}")
    print(f"  Name: {lead.candidate_name}")
    print(f"  Sourcing channel: {lead.sourcing_channel}")
    print(f"  Assigned requirement: {lead.assigned_requirement}")
    print(f"  Created Date: {lead.Created_Date}")
    print(f"  Activity instance details:")
    if lead.current_day_activity and lead.current_day_activity.Activity_instance:
        ai = lead.current_day_activity.Activity_instance
        print(f"    Recruiter: {ai.Employee.Name if ai.Employee else None} ({ai.Employee.EmployeeId if ai.Employee else None})")
        print(f"    Assigned by: {ai.activity_assigned_by.Name if ai.activity_assigned_by else None} ({ai.activity_assigned_by.EmployeeId if ai.activity_assigned_by else None})")
    else:
        print(f"    No activity instance.")
