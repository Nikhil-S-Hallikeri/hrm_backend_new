from celery import shared_task
from time import sleep
from datetime import datetime
from LMS_App.attendance_view import process_attendance


@shared_task
def exit_time_shedule():
    print(f"I am in the tasks.py and executing at the exit time scheduled time: ")
    return f"Task executed"


from datetime import datetime, timedelta

@shared_task
def EmployeeAttendance():
    # Get yesterday's date
    yesterday_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Call the function with yesterday's date
    response = process_attendance(yesterday_date, yesterday_date)
    print(response)