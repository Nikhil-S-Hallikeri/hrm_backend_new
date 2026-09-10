# automatic leaves creation

# from .models import *
# import logging
# from apscheduler.schedulers.background import BackgroundScheduler
# from django_apscheduler.jobstores import DjangoJobStore
# from apscheduler.triggers.cron import CronTrigger
# from django.utils import timezone
# from django.core.mail import EmailMessage
# from django.core.management import call_command
# from django.core.management.base import OutputWrapper
# from io import StringIO

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def start():
#     scheduler = BackgroundScheduler()
#     scheduler.add_jobstore(DjangoJobStore(), "default")

#     print("hariiiiiiiiiiiiii")

#     scheduler.add_job(
#             CompanyLeavesCreation,
#             trigger=CronTrigger(minute="*"),
#             id="hello",  # Ensure the job ID is unique
#             max_instances=100,
#             replace_existing=True,

#     )
#     scheduler.start()  # Start the scheduler after adding all jobs

# def CompanyLeavesCreation():
#     print("hello")

# start()
    
# def CompanyLeavesCreation():
#     leave_type_functions = [SickLeavesCreation]
#     for func in leave_type_functions:
#         func()

# def SickLeavesCreation():
#     emp_objs = CompanyLeaveApplicationModel.objects.filter(EmployeeId__employeeProfile__employee_status="active")
#     for emp_item in emp_objs:
#         if emp_item.is_sick_leave:
#             joined_date = emp_item.EmployeeId.employeeProfile.hired_date
#             current_date = timezone.localdate()
#             if current_date.day == 1 and (current_date.month != joined_date.month or current_date.year != joined_date.year):
#                 try:
#                     sick_leave_obj = SickLeavesModel.objects.get(CompanyLeaveApplication=emp_item.pk)
#                     sick_leave_obj.Sick_Leaves += 1
#                     sick_leave_obj.save()
#                 except SickLeavesModel.DoesNotExist:
#                     # Handle the case where SickLeavesModel does not exist
#                     sick_leave_obj = SickLeavesModel.objects.create(
#                         CompanyLeaveApplication=emp_item,
#                         Sick_Leave=1,
#                         Year=current_date
#                     )
#                     emp_item.is_sick_leave = True
#                     emp_item.save()
#         else:
#             SickLeavesModel.objects.create(
#                 CompanyLeaveApplication=emp_item,
#                 Sick_Leave=1,
#                 Year=timezone.localdate()
#             )
#             emp_item.is_sick_leave = True
#             emp_item.save()

# # Add more functions as needed
# def AnotherLeaveCreation():
#     # Your logic for another leave type creation
#     pass

# def YetAnotherLeaveCreation():
#     # Your logic for yet another leave type creation
#     pass


