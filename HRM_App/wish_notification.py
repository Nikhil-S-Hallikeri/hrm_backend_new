
from HRM_App.models import EmployeeDataModel,WishNotifications
from django.db.models import Q
import threading
import time
from datetime import timedelta, datetime
from django.core.mail import send_mail
from .imports import *
from django.utils import timezone
from rest_framework import response
from LMS_App.models import CompanyHolidaysDataModel,LeaveRequestForm
from LMS_App.serializers import CompanyHolidaysDataModelSerializer,LeaveRequestFormSerializer
from EMS_App.serializers import ResignationSerializer

from EMS_App.models import EmployeePersonalInformation ,ResignationModel

from django.core.mail import EmailMultiAlternatives

def sendfestivalmails():
    today = timezone.localdate()

    print("today holidays",today)
    # Get today's holidays
    holidays = CompanyHolidaysDataModel.objects.filter(Date=today)

    # Get active employees
    employees = EmployeeInformation.objects.filter(employee_status="active")
    
    
    
    if holidays.exists() and employees.exists():
        holiday = holidays.first()
        holiday_name = holiday.OccasionName  # Assuming 'OccasionName' is the holiday name field
        left_image_url = "https://hrmbackendapi.meridahr.com/media/Profile_Images/merida_logo_bOT3Dnk.jpg"  # Assuming 'left_image_url' is the field for left image
        #right_image_url = holiday.related_image  # Assuming 'right_image_url' is the field for right image  <img src="{right_image_url}" alt="" />

       
        for employee in employees:
            # Create a personalized email
            subject = f"Happy {holiday_name}, {employee.full_name}!"
            from_email = "company@example.com"
            to_email = employee.email

            # HTML content for the email (inline HTML template)
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Festival Greetings</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        background-color: #f4f4f4;
                        padding: 20px;
                        margin: 0;
                    }}
                    .card {{
                        background-color: #fff;
                        padding: 20px;
                        border-radius: 10px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                        max-width: 600px;
                        margin: auto;
                    }}
                    .header {{
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding-bottom: 20px;
                    }}
                    .header img {{
                        max-width: 100px;
                        height: auto;
                    }}
                    .card-header {{
                        text-align: center;
                        padding-bottom: 20px;
                    }}
                    .card-header h1 {{
                        color: #4CAF50;
                        font-size: 24px;
                    }}
                    .card-content {{
                        text-align: center;
                        font-size: 16px;
                        line-height: 1.6;
                    }}
                    .card-content p {{
                        margin: 10px 0;
                    }}
                    .card-footer {{
                        margin-top: 20px;
                        text-align: center;
                        font-size: 14px;
                        color: #777;
                    }}
                </style>
            </head>
            <body>
                <div class="card">
                    <div class="header">
                        <img src="{left_image_url}" alt="Left Image" />
          
                    </div>
                    <div class="card-header">
                        <h1>Happy {holiday_name}!</h1>
                    </div>
                    <div class="card-content">
                        <p>Dear {employee.full_name},</p>
                        <p>We wish you and your loved ones a joyous {holiday_name} filled with happiness and prosperity.</p>
                        <p>May this festival bring you peace, success, and lots of good fortune!</p>
                    </div>
                    <div class="card-footer">
                        <p>Best Regards,</p>
                        <p>Merida Tech Minds</p>
                    </div>
                </div>
            </body>
            </html>
            """

            # Plain text fallback content
            text_content = f"Dear {employee.full_name},\n\nWishing you a very happy {holiday_name}!\n\nBest Regards,\nMerida Tech Minds"

            # Create the email with both plain text and HTML content
            email = EmailMultiAlternatives(
                subject, 
                text_content, 
                from_email, 
                [to_email]
            )

            # Attach the HTML content
            email.attach_alternative(html_content, "text/html")

            # Send the email
            email.send()

        print(f"Festival emails sent to {employees.count()} employees.")
    else:
        print("No holidays or active employees for today.")




def create_email_body(name, message):
    # Define the card style
    card_style = """
        <div style="
            background-color: #ffffff; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1); 
            padding: 20px; 
            max-width: 600px; 
            margin: 20px auto; 
            font-family: Arial, sans-serif; 
        ">
    """
    
    # Construct the full HTML body
    email_body = f"""
        <html>
            <body style="background-color: #f4f4f4; padding: 20px;">
                {card_style}
                <p style="font-size: 18px;">Dear {name},</p><br>
                <p style="font-size: 16px;">{message}</p>
                <p style="font-size: 16px;">Best regards,<br>Merida Tech Minds</p>
                </div>
            </body>
        </html>
    """
    
    return email_body
# orignal

# def send_email_for_unresolved_complaints():
#     today = timezone.localdate()

#     employees = EmployeeDataModel.objects.filter(
#         Q(employeeProfile__date_of_birth__day=today.day, employeeProfile__date_of_birth__month=today.month,employeeProfile__bd_wish_mail=False) |
#         Q(employeeProfile__hired_date__day=today.day, employeeProfile__hired_date__month=today.month,employeeProfile__wish_mail=False)
#     ).exclude(employeeProfile__employee_status="in_active")

#     for employee in employees:
#         email_subject = ""
#         email_body = ""
#         wish_message = ""

#         is_birthday = employee.employeeProfile.date_of_birth.day == today.day and employee.employeeProfile.date_of_birth.month == today.month

        
#         years_of_experience = (today - employee.employeeProfile.hired_date).days // 365

#         is_work_anniversary = employee.employeeProfile.hired_date.day == today.day and employee.employeeProfile.hired_date.month == today.month and years_of_experience >= 1

#         if is_birthday and is_work_anniversary:
#             # employee.employeeProfile.bd_wish_mail=True
#             employee.employeeProfile.bd_wish_mail=False

#             employee.employeeProfile.wish_mail=True
#             employee.employeeProfile.save()
#             wish_message = f"""
#                             Hey everyone,

#                             Today is a special day for {employee.employeeProfile.full_name}. We're celebrating both their Birthday and Work Anniversary!

#                             Let's take a moment to appreciate all the hard work and dedication they've brought to our team. Wishing you a fantastic day filled with joy and success, {employee.employeeProfile.full_name}!

#                             Cheers to many more years of growth and happiness.

#                             Best regards,
#                             The Team
#                             """

#             # Combine both messages
#             email_subject = f"Happy Birthday and Work Anniversary {employee.employeeProfile.full_name}!"
#             emp_experience_days = years_of_experience
#             email_body = f"""
#                             Today is a special day as we celebrate both your birthday and your work anniversary with Merida Tech Minds!

#                             Happy Birthday! May your day be filled with joy and happiness.

#                             Also, congratulations on your {emp_experience_days} years with us! Your dedication and hard work are greatly appreciated, and we look forward to many more years of success together.

#                             Enjoy this special day, and thank you for being a valued member of our team.
#                         """

#         elif is_birthday:
#             employee.employeeProfile.bd_wish_mail=True

#             # employee.employeeProfile.bd_wish_mail=True
#             employee.employeeProfile.save()
#             wish_message = f"""
#                             Hey everyone,

#                             Today is a special day as we celebrate {employee.employeeProfile.full_name}'s Birthday!

#                             Let's take a moment to wish {employee.employeeProfile.full_name} a fantastic day filled with joy and success!

#                             Cheers to many more years of growth and happiness.

#                             Best regards,
#                             The Team
#                         """

#             email_subject = f"Happy Birthday {employee.employeeProfile.full_name}!"
#             email_body = f"""
#                                 Dear {employee.employeeProfile.full_name},

#                                 Happy Birthday!

#                                 Wishing you a day filled with happiness, joy, and all the things you love. Your hard work and dedication do not go unnoticed, and we’re grateful to have you as part of our team.

#                                 May this year bring you even more success and fulfillment in both your personal and professional life.

#                                 Enjoy your special day!
#                             """

#         elif is_work_anniversary:
            
#             employee.employeeProfile.wish_mail=True
#             employee.employeeProfile.save()
#             wish_message = f"""
#                     Hey everyone,

#                     Today is a special day as we celebrate the Work Anniversary of {employee.employeeProfile.full_name}!

#                     Let's take a moment to appreciate all the hard work and dedication they've brought to our team. Wishing you a fantastic day filled with joy and success, {employee.employeeProfile.full_name}!

#                     Cheers to many more years of growth and happiness.

#                     Best regards,
#                     Merida Tech Minds
#                     """

#             email_subject = f"Happy Work Anniversary {employee.employeeProfile.full_name}!"
#             emp_experience_days = years_of_experience
#             email_body = f"""
#                             Congratulations on completing {emp_experience_days} year(s) with Merida Tech Minds!

#                             Your commitment and contributions have been invaluable to our success. We are truly grateful for your hard work and dedication.

#                             We look forward to many more years of collaboration and growth together.
#                             """

#         print(email_subject)
#         if email_subject and email_body:
#             # Wrap the email body with the styled card
#             styled_email_body = create_email_body(employee.employeeProfile.full_name, email_body)

#             email = EmailMultiAlternatives(
#                 subject=email_subject,
#                 body='',  # Leave this empty for the plain text part
#                 from_email='from@example.com',
#                 to=[employee.employeeProfile.email]
#             )
#             email.attach_alternative(styled_email_body, "text/html")  # Attach the HTML version
#             email.send(fail_silently=False)

#             # Record the notification
#             emp_info = EmployeeDataModel.objects.all().exclude(employeeProfile__employee_status="in_active")
#             wish_noti_obj = WishNotifications.objects.create(wishes_to_emp=employee, message=f"{email_subject}\n{email_body}",wish_message=wish_message)
            
            
#             for emp in emp_info:
#                 # wish_noti_obj.wished_emps.add(emp) # Use add() to add each employee to the wished_emps field
#                 wish_noti_obj.wished_emps.set(emp_info)  # Use set() 
            
#             # Save the WishNotifications object after all employees have been added
#             wish_noti_obj.save()

#             # Mark the email as sent
#             #employee.employeeProfile.wish_mail = True
#             #employee.employeeProfile.save()

#     yesterday = today - timedelta(days=1)

#     yesterday_employees = EmployeeDataModel.objects.filter(
#         Q(employeeProfile__date_of_birth__day=yesterday.day, employeeProfile__date_of_birth__month=yesterday.month,employeeProfile__bd_wish_mail=True) |
#         # Q(employeeProfile__date_of_birth__day=today.day, employeeProfile__date_of_birth__month=today.month)

#         Q(employeeProfile__hired_date__day=yesterday.day, employeeProfile__hired_date__month=yesterday.month,employeeProfile__wish_mail=True),
        
#     ).exclude(employeeProfile__employee_status="in_active")

#     for emps in yesterday_employees:
#         emps.employeeProfile.wish_mail = False
#         emps.employeeProfile.bd_wish_mail=False
#         emps.employeeProfile.save()
        

#     emp_list = [yes_emp for yes_emp in yesterday_employees]
#     # WishNotifications.objects.filter(wishes_to_emp__in=emp_list).delete()
#     # # Clean up notifications older than 1 day
#     # WishNotifications.objects.filter(created_at__lt=timezone.now() - timedelta(days=1)).delete()
#     WishNotifications.objects.filter(
#         wishes_to_emp__in=emp_list, 
#         created_on__lt=timezone.now() - timedelta(days=1)
#     ).delete()


# #edited Working




# Backuped Function 


# def send_email_for_unresolved_complaints():
#     today = timezone.localdate()

#     employees = EmployeeDataModel.objects.filter(
#         Q(employeeProfile__date_of_birth__day=today.day, employeeProfile__date_of_birth__month=today.month,employeeProfile__bd_wish_mail=False) |
#         Q(employeeProfile__hired_date__day=today.day, employeeProfile__hired_date__month=today.month,employeeProfile__wish_mail=False)
#     ).exclude(employeeProfile__employee_status="in_active")

#     for employee in employees:
#         email_subject = ""
#         email_body = ""
#         wish_message = ""

#         is_birthday = employee.employeeProfile.date_of_birth.day == today.day and employee.employeeProfile.date_of_birth.month == today.month

        
#         years_of_experience = (today - employee.employeeProfile.hired_date).days // 365

#         is_work_anniversary = employee.employeeProfile.hired_date.day == today.day and employee.employeeProfile.hired_date.month == today.month and years_of_experience >= 1

#         if is_birthday and is_work_anniversary:
#             employee.employeeProfile.bd_wish_mail=True
#             employee.employeeProfile.wish_mail=True
#             employee.employeeProfile.save()
#             wish_message = f"""
#                             Hey everyone,

#                             Today is a special day for {employee.employeeProfile.full_name}. We're celebrating both their Birthday and Work Anniversary!

#                             Let's take a moment to appreciate all the hard work and dedication they've brought to our team. Wishing you a fantastic day filled with joy and success, {employee.employeeProfile.full_name}!

#                             Cheers to many more years of growth and happiness.

#                             Best regards,
#                             The Team
#                             """

#             # Combine both messages
#             email_subject = f"Happy Birthday and Work Anniversary {employee.employeeProfile.full_name}!"
#             emp_experience_days = years_of_experience
#             email_body = f"""
#                             Today is a special day as we celebrate both your birthday and your work anniversary with Merida Tech Minds!

#                             Happy Birthday! May your day be filled with joy and happiness.

#                             Also, congratulations on your {emp_experience_days} years with us! Your dedication and hard work are greatly appreciated, and we look forward to many more years of success together.

#                             Enjoy this special day, and thank you for being a valued member of our team.
#                         """

#         elif is_birthday:
#             employee.employeeProfile.bd_wish_mail=True
#             employee.employeeProfile.save()
#             wish_message = f"""
#                             Hey everyone,

#                             Today is a special day as we celebrate {employee.employeeProfile.full_name}'s Birthday!

#                             Let's take a moment to wish {employee.employeeProfile.full_name} a fantastic day filled with joy and success!

#                             Cheers to many more years of growth and happiness.

#                             Best regards,
#                             The Team
#                         """

#             email_subject = f"Happy Birthday {employee.employeeProfile.full_name}!"
#             email_body = f"""
#                                 Dear {employee.employeeProfile.full_name},

#                                 Happy Birthday!

#                                 Wishing you a day filled with happiness, joy, and all the things you love. Your hard work and dedication do not go unnoticed, and we’re grateful to have you as part of our team.

#                                 May this year bring you even more success and fulfillment in both your personal and professional life.

#                                 Enjoy your special day!
#                             """

#         elif is_work_anniversary:
            
#             employee.employeeProfile.wish_mail=True
#             employee.employeeProfile.save()
#             wish_message = f"""
#                     Hey everyone,

#                     Today is a special day as we celebrate the Work Anniversary of {employee.employeeProfile.full_name}!

#                     Let's take a moment to appreciate all the hard work and dedication they've brought to our team. Wishing you a fantastic day filled with joy and success, {employee.employeeProfile.full_name}!

#                     Cheers to many more years of growth and happiness.

#                     Best regards,
#                     Merida Tech Minds
#                     """

#             email_subject = f"Happy Work Anniversary {employee.employeeProfile.full_name}!"
#             emp_experience_days = years_of_experience
#             email_body = f"""
#                             Congratulations on completing {emp_experience_days} year(s) with Merida Tech Minds!

#                             Your commitment and contributions have been invaluable to our success. We are truly grateful for your hard work and dedication.

#                             We look forward to many more years of collaboration and growth together.
#                             """

#         print(email_subject)
#         if email_subject and email_body:
#             # Wrap the email body with the styled card
#             styled_email_body = create_email_body(employee.employeeProfile.full_name, email_body)

#             email = EmailMultiAlternatives(
#                 subject=email_subject,
#                 body='',  # Leave this empty for the plain text part
#                 from_email='from@example.com',
#                 to=[employee.employeeProfile.email]
#             )
#             email.attach_alternative(styled_email_body, "text/html")  # Attach the HTML version
#             email.send(fail_silently=False)

#             # Record the notification
#             emp_info = EmployeeDataModel.objects.all().exclude(employeeProfile__employee_status="in_active")
#             wish_noti_obj = WishNotifications.objects.create(wishes_to_emp=employee, message=f"{email_subject}\n{email_body}",wish_message=wish_message)
            
            
#             for emp in emp_info:
#                 wish_noti_obj.wished_emps.add(emp)  # Use add() to add each employee to the wished_emps field
            
#             # Save the WishNotifications object after all employees have been added
#             wish_noti_obj.save()

#             # Mark the email as sent
#             #employee.employeeProfile.wish_mail = True
#             #employee.employeeProfile.save()

#     yesterday = today - timedelta(days=1)

#     yesterday_employees = EmployeeDataModel.objects.filter(
#         Q(employeeProfile__date_of_birth__day=yesterday.day, employeeProfile__date_of_birth__month=yesterday.month,employeeProfile__bd_wish_mail=True) |
#         Q(employeeProfile__hired_date__day=yesterday.day, employeeProfile__hired_date__month=yesterday.month,employeeProfile__wish_mail=True),
        
#     ).exclude(employeeProfile__employee_status="in_active")

#     for emps in yesterday_employees:
#         emps.employeeProfile.wish_mail = False
#         emps.employeeProfile.bd_wish_mail=False
#         emps.employeeProfile.save()

#     emp_list = [yes_emp for yes_emp in yesterday_employees]
#     WishNotifications.objects.filter(wishes_to_emp__in=emp_list).delete()

  


























import datetime  # full datetime module
from datetime import timedelta
from django.utils.timezone import make_aware, localdate, get_current_timezone
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.db.models import Q


def send_email_for_unresolved_complaints():
    today = localdate()
    yesterday = today - timedelta(days=1)

    # STEP 1: CLEANUP flags and stale notifications first
    stale_employees = EmployeeDataModel.objects.filter(
        Q(employeeProfile__date_of_birth__day=yesterday.day, employeeProfile__date_of_birth__month=yesterday.month, employeeProfile__bd_wish_mail=True) |
        Q(employeeProfile__hired_date__day=yesterday.day, employeeProfile__hired_date__month=yesterday.month, employeeProfile__wish_mail=True)
    ).exclude(employeeProfile__employee_status="in_active")

    for emp in stale_employees:
        emp.employeeProfile.wish_mail = False
        emp.employeeProfile.bd_wish_mail = False
        emp.employeeProfile.save()

    WishNotifications.objects.filter(
        wishes_to_emp__in=stale_employees,
        created_on__lt=timezone.now() - timedelta(days=1)
    ).delete()

    # STEP 2: ACTUAL WISHING LOGIC FOR TODAY
    employees = EmployeeDataModel.objects.filter(
        Q(employeeProfile__date_of_birth__day=today.day, employeeProfile__date_of_birth__month=today.month) |
        Q(employeeProfile__hired_date__day=today.day, employeeProfile__hired_date__month=today.month)
    ).exclude(employeeProfile__employee_status="in_active")

    for employee in employees:
        email_subject = ""
        email_body = ""
        wish_message = ""

        is_birthday = employee.employeeProfile.date_of_birth and \
                      employee.employeeProfile.date_of_birth.day == today.day and \
                      employee.employeeProfile.date_of_birth.month == today.month

        hired_date = employee.employeeProfile.hired_date
        years_of_experience = (today - hired_date).days // 365 if hired_date else 0
        is_work_anniversary = hired_date and \
                              hired_date.day == today.day and \
                              hired_date.month == today.month and \
                              years_of_experience >= 1
        start_of_day = make_aware(datetime.datetime.combine(today, datetime.time.min))
        end_of_day = make_aware(datetime.datetime.combine(today, datetime.time.max))


        # start_of_day = make_aware(datetime.combine(today, time.min))
        # end_of_day = make_aware(datetime.combine(today, time.max))

        if WishNotifications.objects.filter(
            wishes_to_emp=employee,
            created_on__range=(start_of_day, end_of_day)
        ).exists():
            continue

        if is_birthday and is_work_anniversary:
            employee.employeeProfile.bd_wish_mail = True
            employee.employeeProfile.wish_mail = True
            employee.employeeProfile.save()
            email_subject = f"Happy Birthday and Work Anniversary {employee.employeeProfile.full_name}!"
            email_body = f"""
                Today is a special day as we celebrate both your birthday and your work anniversary with Merida Tech Minds!

                Happy Birthday! May your day be filled with joy and happiness.

                Also, congratulations on your {years_of_experience} years with us! Your dedication and hard work are greatly appreciated, and we look forward to many more years of success together.

                Enjoy this special day, and thank you for being a valued member of our team.
            """
            wish_message = f"""
                Hey everyone,

                Today is a special day for {employee.employeeProfile.full_name}. We're celebrating both their Birthday and Work Anniversary!

                Let's take a moment to appreciate all the hard work and dedication they've brought to our team. Wishing you a fantastic day filled with joy and success, {employee.employeeProfile.full_name}!

                Cheers to many more years of growth and happiness.

                Best regards,
                The Team.....
            """

        elif is_birthday:
            employee.employeeProfile.bd_wish_mail = True
            employee.employeeProfile.save()
            email_subject = f"Happy Birthday {employee.employeeProfile.full_name}!"
            email_body = f"""
                Dear {employee.employeeProfile.full_name},

                Happy Birthday!

                Wishing you a day filled with happiness, joy, and all the things you love. Your hard work and dedication do not go unnoticed, and we’re grateful to have you as part of our team.

                May this year bring you even more success and fulfillment in both your personal and professional life.

                Enjoy your special day!
            """
            wish_message = f"""
                Hey everyone,

                Today is a special day as we celebrate {employee.employeeProfile.full_name}'s Birthday!

                Let's take a moment to wish {employee.employeeProfile.full_name} a fantastic day filled with joy and success!

                Cheers to many more years of growth and happiness.

                Best regards,
                The Team
            """

        elif is_work_anniversary:
            employee.employeeProfile.wish_mail = True
            employee.employeeProfile.save()
            email_subject = f"Happy Work Anniversary {employee.employeeProfile.full_name}!"
            email_body = f"""
                Congratulations on completing {years_of_experience} year(s) with Merida Tech Minds!

                Your commitment and contributions have been invaluable to our success. We are truly grateful for your hard work and dedication.

                We look forward to many more years of collaboration and growth together.
            """
            wish_message = f"""
                Hey everyone,

                Today is a special day as we celebrate the Work Anniversary of {employee.employeeProfile.full_name}!

                Let's take a moment to appreciate all the hard work and dedication they've brought to our team. Wishing you a fantastic day filled with joy and success, {employee.employeeProfile.full_name}!

                Cheers to many more years of growth and happiness.

                Best regards,
                Merida Tech Minds
            """

        # Send email
        if email_subject and email_body:
            styled_email_body = create_email_body(employee.employeeProfile.full_name, email_body)

            email = EmailMultiAlternatives(
                subject=email_subject,
                body='',
                from_email='from@example.com',
                to=[employee.employeeProfile.email]
            )
            email.attach_alternative(styled_email_body, "text/html")
            email.send(fail_silently=False)

            # Notify others
            all_emps = EmployeeDataModel.objects.exclude(
                pk=employee.pk
            ).exclude(employeeProfile__employee_status="in_active")

            wish_noti_obj = WishNotifications.objects.create(
                wishes_to_emp=employee,
                message=f"{email_subject}\n{email_body}",
                wish_message=wish_message,
                is_activate=True
            )
            wish_noti_obj.wished_emps.set(all_emps)
            wish_noti_obj.save()












from datetime import datetime, timedelta, time
from django.utils.timezone import make_aware, localdate
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from HRM_App.models import EmployeeDataModel, WishNotifications


def send_email_for_employee_celebrations():
    today = localdate()
    yesterday = today - timedelta(days=1)

    # STEP 1: CLEANUP old flags and stale notifications
    stale_employees = EmployeeDataModel.objects.filter(
        Q(employeeProfile__date_of_birth__day=yesterday.day,
          employeeProfile__date_of_birth__month=yesterday.month,
          employeeProfile__bd_wish_mail=True) |
        Q(employeeProfile__hired_date__day=yesterday.day,
          employeeProfile__hired_date__month=yesterday.month,
          employeeProfile__wish_mail=True)
    ).exclude(employeeProfile__employee_status="in_active")

    for emp in stale_employees:
        emp.employeeProfile.bd_wish_mail = False
        emp.employeeProfile.wish_mail = False
        emp.employeeProfile.save()

    WishNotifications.objects.filter(
        wishes_to_emp__in=stale_employees,
        created_on__lt=make_aware(datetime.combine(today, time.min))
    ).delete()

    # STEP 2: Actual wish generation
    employees = EmployeeDataModel.objects.filter(
        Q(employeeProfile__date_of_birth__day=today.day,
          employeeProfile__date_of_birth__month=today.month) |
        Q(employeeProfile__hired_date__day=today.day,
          employeeProfile__hired_date__month=today.month)
    ).exclude(employeeProfile__employee_status="in_active")

    for employee in employees:
        profile = employee.employeeProfile
        full_name = profile.full_name
        dob = profile.date_of_birth
        hired = profile.hired_date
        email = profile.email

        is_birthday = dob and dob.day == today.day and dob.month == today.month
        years = (today - hired).days // 365 if hired else 0
        is_anniversary = hired and hired.day == today.day and hired.month == today.month and years >= 1

        start_day = make_aware(datetime.combine(today, time.min))
        end_day = make_aware(datetime.combine(today, time.max))

        # Skip if already wished today
        if WishNotifications.objects.filter(wishes_to_emp=employee, created_on__range=(start_day, end_day)).exists():
            continue

        subject = ""
        message = ""
        wish_message = ""

        if is_birthday and is_anniversary:
            profile.bd_wish_mail = True
            profile.wish_mail = True
            subject = f"🎉 Happy Birthday & Work Anniversary {full_name}!"
            message = f"""
Dear {full_name},

🎂 Happy Birthday! May your day be filled with happiness and success.

🏆 Also, congratulations on completing {years} year(s) with Merida Tech Minds. Your hard work and commitment are appreciated.

Enjoy your double celebration!

Regards,
Merida Tech Minds
"""
            wish_message = f"""
Hey Team,

Let's all wish {full_name} a 🎉 Happy Birthday & Work Anniversary 🎉 today!

They've completed {years} year(s) with us and it's also their special day.

Cheers,
HR
"""

        elif is_birthday:
            profile.bd_wish_mail = True
            subject = f"🎂 Happy Birthday {full_name}!"
            message = f"""
Dear {full_name},

🎉 Wishing you a wonderful birthday filled with joy and success.

We’re lucky to have you in our team!

Best wishes,
Merida Tech Minds
"""
            wish_message = f"""
Hi Team,

It's {full_name}'s birthday today! 🎂

Let’s shower them with wishes.

Cheers,
HR
"""

        elif is_anniversary:
            profile.wish_mail = True
            subject = f"🏆 Happy Work Anniversary {full_name}!"
            message = f"""
Dear {full_name},

Congratulations on completing {years} year(s) with Merida Tech Minds!

Thank you for your dedication and contributions.

Warm regards,
HR Team
"""
            wish_message = f"""
Hey Team,

{full_name} is celebrating their work anniversary today! 🏆

Let’s show appreciation for their journey with us.

Regards,
HR
"""

        # Save flags and send email
        if subject:
            profile.save()

            # Send email
            styled_html = f"<html><body><p>{message.replace(chr(10), '<br>')}</p></body></html>"
            email_obj = EmailMultiAlternatives(
                subject=subject,
                body='',
                from_email='info@meridatechminds.com',
                to=[email]
            )
            email_obj.attach_alternative(styled_html, "text/html")
            email_obj.send(fail_silently=False)

            # Create notification for others
            others = EmployeeDataModel.objects.exclude(pk=employee.pk).exclude(employeeProfile__employee_status="in_active")
            wish_noti = WishNotifications.objects.create(
                wishes_to_emp=employee,
                message=subject,
                wish_message=wish_message,
                is_activate=True
            )
            wish_noti.wished_emps.set(others)
            wish_noti.save()













# def send_daily_emails():
#     while True:
#         send_email_for_unresolved_complaints()
#         time.sleep(360from pytz import timezone as pytz_timezone
import time
import datetime
from django.utils import timezone
from LMS_App.attendance_view import EmployeesAttendanceStatusUpdating

def send_daily_emails():
    # Define your local timezone
    tz=settings.TIME_ZONE
    local_tz = pytz_timezone(tz)  

    # Define the target time to send the emails (e.g., 12:00 AM every day)
    target_hour = 0
    target_minute = 5

    while True:
        # Get the current time in UTC and convert to local time
        now_utc = timezone.now()
        now_local = now_utc.astimezone(local_tz)

        target_time = now_local.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)

        if now_local > target_time:
            target_time += datetime.timedelta(days=1)

        sleep_seconds = (target_time - now_local).total_seconds()

        #time.sleep(sleep_seconds)

        # Call the function to send emails at the specified time
        
        send_email_for_unresolved_complaints()
        
        try:
            today = timezone.localdate()
            yesterday = today - timedelta(days=1)
            EmployeesAttendanceStatusUpdating(yesterday)#pass a yesterday
        except:
            pass
        
        sendfestivalmails()
        
        time.sleep(sleep_seconds)

def start_background_thread():
    thread = threading.Thread(target=send_daily_emails)
    thread.daemon = True
    thread.start()
    
def setup_background_tasks():
    start_background_thread()

#orignal
# class GetEmployeeCelebrations(APIView):
#     def get(self,request):

#         emp=request.GET.get("EmployeeId")
#         emp_obj=EmployeeDataModel.objects.get(EmployeeId=emp)
#         wish_noti=WishNotifications.objects.filter(wished_emps=emp_obj)
#         wiahes_list=[]
#         if wish_noti.exists():
#             for wishes in wish_noti:
#                 wiahes_serializer=WishNotificationsSerializer(wishes).data

#                 if wishes.wishes_to_emp.EmployeeId!=emp_obj.EmployeeId:
#                     wiahes_serializer["message"]=wiahes_serializer["wish_message"]

#                 wiahes_list.append(wiahes_serializer)

            
#             # for wish in wish_noti:
#             #     wish.wished_emps.remove(emp_obj)  # Remove the employee from the ManyToManyField
#             #     wish.save() 

#             return Response(wiahes_list,status=status.HTTP_200_OK)
#         else:
#             return Response([],status.HTTP_400_BAD_REQUEST)


#latest

from django.utils.timezone import make_aware
from datetime import datetime, time  #  Correct import
from django.utils.timezone import make_aware, localdate



# #orignal from Server
# class GetEmployeeCelebrations(APIView):
#     def get(self,request):

#         emp=request.GET.get("EmployeeId")
#         emp_obj=EmployeeDataModel.objects.get(EmployeeId=emp)
#         wish_noti=WishNotifications.objects.filter(wished_emps=emp_obj)
#         wiahes_list=[]
#         if wish_noti.exists():
#             for wishes in wish_noti:
#                 wiahes_serializer=WishNotificationsSerializer(wishes).data

#                 if wishes.wishes_to_emp.EmployeeId!=emp_obj.EmployeeId:
#                     wiahes_serializer["message"]=wiahes_serializer["wish_message"]

#                 wiahes_list.append(wiahes_serializer)

            
#             # for wish in wish_noti:
#             #     wish.wished_emps.remove(emp_obj)  # Remove the employee from the ManyToManyField
#             #     wish.save() 

#             return Response(wiahes_list,status=status.HTTP_200_OK)
#         else:
#             return Response([],status.HTTP_400_BAD_REQUEST)
        




class GetEmployeeCelebrations(APIView):
    def get(self, request):
        emp_id = request.GET.get("EmployeeId")
        try:
            emp_obj = EmployeeDataModel.objects.get(EmployeeId=emp_id)  
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Employee not found"}, status=404)

        # today = timezone.localdate()
        # start_of_day = datetime.combine(today, datetime.min.time()).astimezone()
        # end_of_day = datetime.combine(today, datetime.max.time()).astimezone()
        
        today = localdate()

        start_of_day = make_aware(datetime.combine(today, time.min))
        end_of_day = make_aware(datetime.combine(today, time.max))

        # wish_noti = WishNotifications.objects.filter(
        #     wished_emps=emp_obj,
        #     created_on__range=(start_of_day, end_of_day)
        # )     
        wish_noti = WishNotifications.objects.filter(
        wished_emps__EmployeeId=emp_id,
        created_on__range=(start_of_day, end_of_day)
        )


        print(f"Found {wish_noti.count()} wishes for emp {emp_id} between {start_of_day} and {end_of_day}")

        wishes_list = []
        for wishes in wish_noti:
            wishes_serializer = WishNotificationsSerializer(wishes).data
            wishes_serializer["wish_message"] = wishes.wish_message
            wishes_list.append(wishes_serializer)

        return Response(wishes_list)


from django.db.models.functions import ExtractMonth, ExtractDay

# class DisplayEmployeeCelebrations(APIView):
#     def get(self, request):
        
#         today = timezone.localdate()
#         days = request.GET.get("days", 7)  # Default to 7 days if not provided
#         days = int(days)  # Ensure it's an integer
#         end_date = today + timedelta(days=days)

#         # 1. Get birthday wishes

#         start_month, start_day = today.month, today.day
#         end_month, end_day = end_date.month, end_date.day

#         # Birthday filter
#         if start_month == end_month:
#             # If within the same month, filter within the day range
#             birthday_wishes = EmployeeInformation.objects.annotate(
#                 birth_month=ExtractMonth('date_of_birth'),
#                 birth_day=ExtractDay('date_of_birth')
#             ).filter(employee_status="active",
#                 birth_month=start_month,
#                 birth_day__range=[start_day, end_day]
#             )

#             work_anniversary_wishes = EmployeeInformation.objects.annotate(
#                 hired_month=ExtractMonth('hired_date'),
#                 hired_day=ExtractDay('hired_date')
#             ).filter(employee_status="active",
#                 hired_month=start_month,
#                 hired_day__range=[start_day, end_day]
#             )


#         else:
#             # If spanning across two months, use Q objects to combine conditions
#             birthday_wishes = EmployeeInformation.objects.annotate(
#                 birth_month=ExtractMonth('date_of_birth'),
#                 birth_day=ExtractDay('date_of_birth')
#             ).filter(Q(employee_status="active") &
#                 Q(birth_month=start_month, birth_day__gte=start_day) |
#                 Q(birth_month=end_month, birth_day__lte=end_day)
#             )

#             work_anniversary_wishes = EmployeeInformation.objects.annotate(
#                 hired_month=ExtractMonth('hired_date'),
#                 hired_day=ExtractDay('hired_date')
#             ).filter(Q(employee_status="active") &
#                 Q(hired_month=start_month, hired_day__gte=start_day) |
#                 Q(hired_month=end_month, hired_day__lte=end_day)
#             )

#         birthday_wishes_list=[]
#         for birthday_wish in birthday_wishes:
#             info = EmployeeDataModel.objects.filter(EmployeeId=birthday_wish.employee_Id).first()
#             birthday_wishes_serializer = EmployeeInformationSerializer(birthday_wish).data
#             birthday_wishes_serializer["Department"] = info.Position.Department.Dep_Name if info.Position else None
#             birthday_wishes_serializer["Designation"] = info.Position.Name if info.Position else None
#             birthday_wishes_serializer["Reporting_To"] = info.Reporting_To.EmployeeId if info.Reporting_To else None
#             birthday_wishes_serializer["Reporting_To_Name"] = info.Reporting_To.Name if info.Reporting_To else None
#             birthday_wishes_list.append(birthday_wishes_serializer)

#         work_anniversary_wishes_list=[]
#         for work_anniversary_wish in work_anniversary_wishes:
#             info = EmployeeDataModel.objects.filter(EmployeeId=work_anniversary_wish.employee_Id).first()
#             work_anniversary_wishes_serializer = EmployeeInformationSerializer(work_anniversary_wish).data
#             work_anniversary_wishes_serializer["Department"] = info.Position.Department.Dep_Name if info.Position else None
#             work_anniversary_wishes_serializer["Designation"] = info.Position.Name if info.Position else None
#             work_anniversary_wishes_serializer["Reporting_To"] = info.Reporting_To.EmployeeId if info.Reporting_To else None
#             work_anniversary_wishes_serializer["Reporting_To_Name"] = info.Reporting_To.Name if info.Reporting_To else None
#             work_anniversary_wishes_list.append(work_anniversary_wishes_serializer)
        
#         # work_anniversary_wishes_serializer = EmployeeInformationSerializer(work_anniversary_wishes, many=True).data
#         # birthday_wishes = WishNotifications.objects.filter(created_on__date=today, wish_reason="birthday")
#         # birthday_wishes_serializer = WishNotificationsSerializer(birthday_wishes, many=True).data
#         # 2. Get work anniversary wishes
#         # work_anniversary_wishes = WishNotifications.objects.filter(created_on__date=today, wish_reason="work_anniversary")
#         # work_anniversary_wishes_serializer = WishNotificationsSerializer(work_anniversary_wishes, many=True).data
#         # 3. Get new hires
#         new_employees_list=[]

#         new_employees = EmployeeInformation.objects.filter(employee_status="active",hired_date=today)
#         for new_emp in new_employees:
#             info = EmployeeDataModel.objects.filter(EmployeeId=new_emp.employee_Id).first()
#             new_employees_serializer = EmployeeInformationSerializer(new_emp).data
#             new_employees_serializer["Department"] = info.Position.Department.Dep_Name if info.Position else None
#             new_employees_serializer["Designation"] = info.Position.Name if info.Position else None
#             new_employees_serializer["Reporting_To"] = info.Reporting_To.EmployeeId if info.Reporting_To else None
#             new_employees_serializer["Reporting_To_Name"] = info.Reporting_To.Name if info.Reporting_To else None
#             new_employees_list.append(new_employees_serializer)
            
#         # new_employees_serializer = EmployeeInformationSerializer(new_emp).data
#         # 4. Get upcoming holidays within the specified range
#         upcoming_holidays = CompanyHolidaysDataModel.objects.filter(Date__range=[today, end_date])
#         upcoming_holidays_serializer = CompanyHolidaysDataModelSerializer(upcoming_holidays, many=True).data

#         # 5. Get employees currently on leave
#         on_leaves = LeaveRequestForm.objects.filter(
#             approved_status="approved",
#             from_date__lte=end_date,  # Leave starts on or before end_date
#             to_date__gte=today  # Leave ends on or after today
#         )
#         on_leaves_serializer = LeaveRequestFormSerializer(on_leaves, many=True).data

#         # 6. Get pending resignations and leave requests
#         pending_resignations = ResignationModel.objects.filter(resignation_verification="pending")
#         pending_resignations_serializer = ResignationSerializer(pending_resignations, many=True).data

#         pending_leave_requests = LeaveRequestForm.objects.filter(approved_status="pending")
#         pending_leave_requests_serializer = LeaveRequestFormSerializer(pending_leave_requests, many=True).data

#         # Structure the final response
#         response_data = {
#             "today_birthdays": birthday_wishes_list,
#             "today_work_anniversaries": work_anniversary_wishes_list,
#             "new_hires": new_employees_list,
#             "upcoming_holidays": upcoming_holidays_serializer,
#             "on_leaves": on_leaves_serializer,
#             "pending_approvals": {
#                 "resignation_approvals": pending_resignations_serializer,
#                 "leave_approvals": pending_leave_requests_serializer
#             }
#         }

#         return Response(response_data, status=status.HTTP_200_OK)

class DisplayEmployeeCelebrations(APIView):
    def get(self, request):
        
        today = timezone.localdate()
        days = int(request.GET.get("days", 7))  # Default to 7 days if not provided
        end_date = today + timedelta(days=days)
        
        start_month, start_day = today.month, today.day
        end_month, end_day = end_date.month, end_date.day

        # Define a helper function to handle employee data enrichment
        def enrich_employee_data(employee_queryset):
            enriched_data = []
            for employee in employee_queryset:
                info = EmployeeDataModel.objects.filter(EmployeeId=employee.employee_Id).first()
                serializer_data = EmployeeInformationSerializer(employee).data
                serializer_data["Department"] = info.Position.Department.Dep_Name if info and info.Position else None
                serializer_data["Designation"] = info.Position.Name if info and info.Position else None
                serializer_data["Reporting_To"] = info.Reporting_To.EmployeeId if info and info.Reporting_To else None
                serializer_data["Reporting_To_Name"] = info.Reporting_To.Name if info and info.Reporting_To else None
                enriched_data.append(serializer_data)
            return enriched_data

        # 1. Get birthday wishes within the date range
        def get_birthday_wishes():
            if start_month == end_month:
                return EmployeeInformation.objects.annotate(
                    birth_month=ExtractMonth('date_of_birth'),
                    birth_day=ExtractDay('date_of_birth')
                ).filter(
                    employee_status="active",
                    birth_month=start_month,
                    birth_day__range=[start_day, end_day]
                )
            else:
                return EmployeeInformation.objects.annotate(
                    birth_month=ExtractMonth('date_of_birth'),
                    birth_day=ExtractDay('date_of_birth')
                ).filter(
                    Q(employee_status="active") & (
                        Q(birth_month=start_month, birth_day__gte=start_day) |
                        Q(birth_month=end_month, birth_day__lte=end_day)
                    )
                )

        # 2. Get work anniversary wishes for employees with at least 1 year completed
        def get_work_anniversary_wishes():
            if start_month == end_month:
                return EmployeeInformation.objects.annotate(
                    hired_month=ExtractMonth('hired_date'),
                    hired_day=ExtractDay('hired_date')
                ).filter(
                    employee_status="active",
                    hired_month=start_month,
                    hired_day__range=[start_day, end_day],
                    #hired_date__lte=today - timedelta(days=365)  # Only include if hired at least one year ago
                )
            else:
                return EmployeeInformation.objects.annotate(
                    hired_month=ExtractMonth('hired_date'),
                    hired_day=ExtractDay('hired_date')
                ).filter(
                    Q(employee_status="active") & (
                        Q(hired_month=start_month, hired_day__gte=start_day) |
                        Q(hired_month=end_month, hired_day__lte=end_day)
                    ),
                    #hired_date__lte=today - timedelta(days=365)  # Only include if hired at least one year ago
                )

        # Fetch and enrich birthday and work anniversary lists
        birthday_wishes = get_birthday_wishes()
        birthday_wishes_list = enrich_employee_data(birthday_wishes)
        
        work_anniversary_wishes = get_work_anniversary_wishes()
        work_anniversary_wishes_list = enrich_employee_data(work_anniversary_wishes)

        # 3. Get new hires for today
        new_employees = EmployeeInformation.objects.filter(employee_status="active", hired_date=today)
        new_employees_list = enrich_employee_data(new_employees)
        
        # 4. Get upcoming holidays within the specified range
        upcoming_holidays = CompanyHolidaysDataModel.objects.filter(Date__range=[today, end_date])
        upcoming_holidays_serializer = CompanyHolidaysDataModelSerializer(upcoming_holidays, many=True).data

        # 5. Get employees currently on leave
        on_leaves = LeaveRequestForm.objects.filter(
            approved_status="approved",
            from_date__lte=end_date,  # Leave starts on or before end_date
            to_date__gte=today  # Leave ends on or after today
        )
        on_leaves_serializer = LeaveRequestFormSerializer(on_leaves, many=True).data

        # 6. Get pending resignations and leave requests
        pending_resignations = ResignationModel.objects.filter(resignation_verification="pending")
        pending_resignations_serializer = ResignationSerializer(pending_resignations, many=True).data

        pending_leave_requests = LeaveRequestForm.objects.filter(approved_status="pending")
        pending_leave_requests_serializer = LeaveRequestFormSerializer(pending_leave_requests, many=True).data

        # Structure the final response
        response_data = {
            "today_birthdays": birthday_wishes_list,
            "today_work_anniversaries": work_anniversary_wishes_list,
            "new_hires": new_employees_list,
            "upcoming_holidays": upcoming_holidays_serializer,
            "on_leaves": on_leaves_serializer,
            "pending_approvals": {
                "resignation_approvals": pending_resignations_serializer,
                "leave_approvals": pending_leave_requests_serializer
            }
        }
        return Response(response_data, status=status.HTTP_200_OK)



class employeeReportingTeam(APIView):
    def get(self,request,login_user=None):

        if not login_user:
            return Response("login user required",status=status.HTTP_400_BAD_REQUEST)
        emp_id=EmployeeDataModel.objects.filter(EmployeeId=login_user).first()
        emp_team=EmployeeDataModel.objects.filter(Q(Reporting_To__pk=emp_id.Reporting_To.pk)| 
                                                  Q(pk=emp_id.Reporting_To.pk)).exclude(employeeProfile__employee_status="in_active")
        if not  emp_team.exists():
            return response("No Reporting Team",status=status.HTTP_200_OK)
        all_employees = []
        for info in emp_team:
            if info.employeeProfile:
                # Fetch Employee Information Profile
                emp_info = get_object_or_404(EmployeeInformation, pk=info.employeeProfile.pk)
                employee_info = EmployeeInformationSerializer(emp_info, context={'request': request}).data
                    
                # Populate department, designation, and reporting information
                employee_info["Department"] = info.Position.Department.Dep_Name if info.Position else None
                employee_info["Designation"] = info.Position.Name if info.Position else None
                employee_info["Reporting_To"] = info.Reporting_To.Name if info.Reporting_To else None
                all_employees.append(employee_info)

        return Response(all_employees, status=status.HTTP_200_OK)
            
            
            
            




        