import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hrm_project.settings')
django.setup()
from HRM_App.models import NewDailyAchivesModel
from django.utils import timezone
from datetime import date, datetime, time
from django.db.models import Q

start_d = date(2026, 7, 2)
end_d = date(2026, 7, 2)

start_dt = timezone.make_aware(datetime.combine(start_d, time.min))
end_dt = timezone.make_aware(datetime.combine(end_d, time.max))

qs = NewDailyAchivesModel.objects.filter(
    current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
).exclude(lead_status="staged")

print(f"Total valid interview calls: {qs.count()}")

filtered_qs = qs.filter(
    Q(interview_scheduled_date__range=(start_dt, end_dt))
    | Q(
        interview_scheduled_date__isnull=True,
        interview_status="interview_scheduled",
        Created_Date__range=(start_dt, end_dt),
    )
)
print(f"Filtered count using datetime range: {filtered_qs.count()}")

filtered_qs_date = qs.filter(
    Q(interview_scheduled_date__date__range=(start_d, end_d))
    | Q(
        interview_scheduled_date__isnull=True,
        interview_status="interview_scheduled",
        Created_Date__date__range=(start_d, end_d),
    )
)
print(f"Filtered count using __date__range: {filtered_qs_date.count()}")
