# /////////////////////////////////////////////////////////////////////////////////////////////////
#                                   Authentication
# ///////////////////////////////////////////////////////////////////////////////////////////////////
from django.http import JsonResponse
import requests
import geocoder
import geoip2.database
from geopy.distance import geodesic
import urllib.parse
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta
from calendar import monthrange
from collections import defaultdict

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db import IntegrityError

from .models import *
from .serializers import *
from .imports import *
def get_geolocation():
    url = "https://api.opencagedata.com/geocode/v1/json?q=-22.6792%2C+14.5272&key=637117d496de4202b44dc78230d62972&pretty=1"
    
    # Sending a GET request to the API
    response = requests.get(url)
    
    # Print the response in JSON format for better readability
    #print(response.json())
# Call the function
#get_geolocation()

def get_client_ip(request):
    """
    Extract client IP address from the request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]  # Get first IP in list
    else:
        ip = request.META.get('REMOTE_ADDR')  # Fallback to direct IP
    return ip
def get_current_location(request):
    """
    Get the system's current latitude and longitude using geocoder.
    """
    try:
        ip = get_client_ip(request)  # Get IP from request
        g = geocoder.ip(ip)
        if g.ok:
            print(g.latlng)
            return g.latlng  # Returns (latitude, longitude)
        else:
            return None
    except Exception as e:
        print(f"Error getting location: {e}")
        return None

def is_location_within_range(target_lat, target_lon, max_distance_km, request):
    """
    Check if the target location (target_lat, target_lon) is within max_distance_km 
    of the system's current location.
    """
    current_location = get_current_location(request)
    
    if not current_location:
        return {
            "within_range": False,
            "distance_km": None,
            "error": "Could not determine current location"
        }
    
    try:
        current_lat, current_lon = current_location
        distance = geodesic((current_lat, current_lon), (target_lat, target_lon)).kilometers
        within_range = distance <= max_distance_km
        return {
            "within_range": within_range,
            "distance_km": round(distance, 2),
            "current_location": {"latitude": current_lat, "longitude": current_lon},
            "target_location": {"latitude": target_lat, "longitude": target_lon}
        }
    except Exception as e:
        return {
            "within_range": False,
            "distance_km": None,
            "error": f"Error calculating distance: {e}"
        }
# # Example Usage: 12.928768940431825, 77.58535580736807 
# target_latitude = 12.9719  
# target_longitude = 77.5937
# radius_km = 0.05  # Define range in km
# within_range, distance = is_location_within_range(target_latitude, target_longitude, radius_km)
# if within_range:
#     print(f"Target location is within {radius_km} km range. Distance: {distance:.2f} km")
# else:
#     print(f"Target location is OUTSIDE {radius_km} km range. Distance:")
def get_location_by_ip(ip_address):
    # Path to your GeoLite2 database
    db_path = 'geoip/GeoLite2-City.mmdb'
    try:
        reader = geoip2.database.Reader(db_path)
        response = reader.city(ip_address)
        location_data = {
            "city": response.city.name,
            "country": response.country.name,
            "latitude": response.location.latitude,
            "longitude": response.location.longitude,
        }
        return location_data
    except Exception as e:
        print(f"Error: {e}")
        return {"error": "Unable to get location"}
def log_ip_view(request):
    client_ip = get_client_ip(request)
    location = get_location_by_ip(client_ip)
    print(location)
    # Save IP address to the database ,city=location["city"],country=location["country"],latitude=location["latitude"],longitude=location["longitude"]
    AccessLog.objects.create(ip_address=client_ip)
    
    # return JsonResponse({"message": "Your IP is logged.", "ip": client_ip})
class RegistrationView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if serializer.is_valid():
            hashed_password = make_password(serializer.validated_data['Password'])
            serializer.validated_data['Password'] = hashed_password
            empid = serializer.validated_data['EmployeeId']
            subject = f'{empid} Registration Verification mail '
            otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            email = serializer.validated_data['Email']  
            user = RegistrationModel.objects.filter(EmployeeId=empid).first()
            emp=EmployeeDataModel.objects.filter(EmployeeId=empid).exists()
            if emp:
                if user is None :
                    instance = serializer.save()  # Save and get the instance
                    send_mail(subject, f'Verification OTP: {otp}', email, [email], fail_silently=False)
                    response_data = {'Message': "Verify OTP through the Registered Email.", 'OTP': otp}
                    response_data.update(serializer.data)  # Now you can use serializer.data
                    return Response(response_data, status=status.HTTP_201_CREATED)
                else:
                    if not user.is_active:
                        user.EmployeeId=empid
                        user.Email=email
                        user.PhoneNumber=request.data.get("PhoneNumber")
                        user.Password=hashed_password
                        user.save()
                        
                        send_mail(subject, f'Verification OTP: {otp}', email, [email], fail_silently=False)
                        response_data = {
                            'Message': "Verify OTP through the Registered Email.",
                            'OTP': otp
                        }
                        response_data.update(serializer.data)  # Now you can use serializer.data
                        
                        return Response(response_data, status=status.HTTP_201_CREATED)
                    else:
                        return Response({"Message": "Employee Id already exists!"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"Message": "Employee Id Not Available!"}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self,request):
        empid=request.data.get("EmployeeId")
        user = RegistrationModel.objects.filter(EmployeeId=empid).first()
        serializer = RegistrationSerializer(user)
        otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        subject = f'{empid} Registration Verification mail'
        send_mail(subject,f'Verification OTP: {otp}',user.Email, [user.Email],fail_silently=False,)
        serializer_data={"Message":"resend OTP sended successful!",'OTP':otp}.update(serializer.data)
        return Response(serializer_data,status=status.HTTP_201_CREATED)
class OTPVerificationView(APIView):
    def post(self, request):
        otp_entered = request.data.get('OTP')
        verify_otp=request.data.get("OriginalOTP")
        empid=request.data.get("EmployeeId")  
        try:
            reg_employees = EmployeeInformation.objects.filter(Q(employee_Id=empid) | Q(email=empid), employee_status="active").first()
            if not reg_employees:
                return Response("Unauthorised User Data Found !", status=status.HTTP_400_BAD_REQUEST)
            user = RegistrationModel.objects.filter(EmployeeId=reg_employees.employee_Id).first()
        except RegistrationModel.DoesNotExist:
            return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
        if verify_otp == otp_entered:
            user.is_active = True
            user.save()
            return Response({'message':"OTP verification successful"}, status=status.HTTP_200_OK)
        else:
            return Response("Invalid OTP", status=status.HTTP_200_OK)
        
        
class ForgotPasswordView(APIView):
    def post(self, request):
        empid=request.data.get("EmployeeId")
        try:
            reg_employees = EmployeeInformation.objects.filter(Q(employee_Id=empid) | Q(email=empid), employee_status="active").first()
            if not reg_employees:
                return Response("Unauthorised User Data Found !", status=status.HTTP_400_BAD_REQUEST)
            user = RegistrationModel.objects.filter(EmployeeId=reg_employees.employee_Id).first()
            if user  and user.is_active:
                otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
                email = user.Email
                subject = f'Reset Password OTP for Employee ID {empid}'
                send_mail(
                            subject,
                            f'Your Reset Password OTP is: {otp}',
                            settings.EMAIL_HOST_USER,  # Replace with your sender email
                            [email],
                            fail_silently=False,
                    )
                    
                message_dict={"message":f'The verification mail has been sent to your registered email address. Please check your inbox and verify the OTP.',
                            "OTP":otp}
                        
                return Response(message_dict, status=status.HTTP_200_OK)
            else:
                print(f'Entered User is Not Matched')
                return Response(f'Entered User is Not Matched', status=status.HTTP_400_BAD_REQUEST)
        except RegistrationModel.DoesNotExist:
            return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
        
class forgotPassOTPVerificationView(APIView):
    def post(self, request):
        otp_entered = request.data.get('OTP')
        verify_otp=request.data.get("OriginalOTP")
        empid=request.data.get("EmployeeId")
        try:
            reg_employees = EmployeeInformation.objects.filter(Q(employee_Id=empid) | Q(email=empid), employee_status="active").first()
            if not reg_employees:
                return Response("Unauthorised User Data Found !", status=status.HTTP_400_BAD_REQUEST)
            user = RegistrationModel.objects.filter(EmployeeId=reg_employees.employee_Id).first()
        except RegistrationModel.DoesNotExist:
            return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
        if verify_otp == otp_entered:
            user.is_active = True
            user.save()
            return Response("OTP verification successful", status=status.HTTP_200_OK)
        else:
            return Response("Invalid OTP", status=status.HTTP_200_OK)
class SetPasswordView(APIView):
    def post(self, request):
        new_password = request.data.get('NewPassword')
        empid = request.data.get("EmployeeId")
        try:
            reg_employees = EmployeeInformation.objects.filter(Q(employee_Id=empid) | Q(email=empid), employee_status="active").first()
            if not reg_employees:
                return Response("Unauthorised User Data Found !", status=status.HTTP_400_BAD_REQUEST)
            user = RegistrationModel.objects.filter(EmployeeId=reg_employees.employee_Id).first()
            user.Password = make_password(new_password)  # Hash the new password
            user.save()
            serializer=RegistrationSerializer(user)
            reg_dict={"message":"New Password Updated successfully!",
                      "Registred_User":serializer.data}
            notification=Notification.objects.create(sender=None,receiver=user,message=f"Your New Password Updated successfully!")
            return Response(reg_dict, status=status.HTTP_200_OK)
        except RegistrationModel.DoesNotExist:
            return Response("User Not Found", status=status.HTTP_404_NOT_FOUND)
import urllib.parse
class LoginView(APIView):
    def post(self, request):
        empid = request.data.get('EmployeeId')
        # email = request.data.get("email")
        password = request.data.get('Password')
        
        
        encoded_data = password.replace('%20', '+')
        ## Decode the URL-encoded data
        decoded_data = urllib.parse.unquote(encoded_data)
        try:
            # reg_employees = RegistrationModel.objects.filter(Q(EmployeeId=empid) | Q(Email=empid))
            # user_employee_ids = reg_employees.values_list('EmployeeId', flat=True)
            # # Filtering EmployeeDataModel based on EmployeeId from the user list
            # user = EmployeeDataModel.objects.filter(EmployeeId__in=user_employee_ids, employee_status="active").first()
            reg_employees = EmployeeInformation.objects.filter(Q(employee_Id=empid) | Q(email=empid), employee_status="active").first()
           
            if not reg_employees:
                return Response("Unauthorised User Data Found !", status=status.HTTP_400_BAD_REQUEST)
            user=RegistrationModel.objects.filter(EmployeeId=reg_employees.employee_Id).first()
            if user:
                empid=user.EmployeeId
            else:
                return Response("invalied Credentials!",status=status.HTTP_401_UNAUTHORIZED)
            
            # else:
            #     user=RegistrationModel.objects.filter(Email=email).first()
            #     empid=user.EmployeeId
            if user and user.is_active == True:
                Employee=EmployeeDataModel.objects.filter(EmployeeId=empid).first()
                
                try:
                    if  Employee and Employee.employeeProfile.employee_status=="active" and (check_password(password, user.Password) or user.Password==decoded_data):
                        
                        user.is_login = True
                        user.save()
                        reporting_emp_list=EmployeeDataModel.objects.filter(Reporting_To=Employee.pk)
                        rep_to=reporting_emp_list
                        reporting_emp_list =True if reporting_emp_list else False
                           
                        sub_rep_to = False
                        for rep in rep_to:
                            emp_obj = EmployeeDataModel.objects.filter(Reporting_To=rep.pk)
                            if emp_obj.exists():
                                sub_rep_to = True
                                break
                            
                        if Employee.Designation == "Admin":
                            Status = "admin"
                        elif Employee.Designation == "HR" or sub_rep_to:
                            Status = "manager"
                        elif rep_to.exists() and (Employee.Designation == "Employee" or Employee.Designation == "Recruiter"):
                            Status = "team_leader"
                        elif Employee.Designation == "Recruiter" or Employee.Designation == "Employee":
                            Status = "employee"
                        else:
                            Status = None
                        try:
                            dict_data={
                                    "employee_id":Employee.EmployeeId,
                                    "pk":Employee.pk,
                                    "email":Employee.employeeProfile.email if Employee.employeeProfile else None,
                                    "Dash_Status":Status,
                                    "Department":Employee.Position.Department.Dep_Name if Employee.Position else None,
                                    "Position":Employee.Position.Name if Employee.Position else None,
                                    "Reporting_To":Employee.Reporting_To.EmployeeId if Employee.Reporting_To else None,}
                        except:
                            dict_data={}
                        if reg_employees.WFH_Status:
                            # check wether the duration completed or not
                            if reg_employees.from_duration <= timezone.localtime() and reg_employees.to_duration >= timezone.localtime():
                                reg_employees.WFH_Status = True
                            else:
                                reg_employees.WFH_Status = False
                            reg_employees.save()
                            
                        attandance_permission={"WFH_Status":reg_employees.WFH_Status,
                                               "target_latitude":reg_employees.latitude,
                                               "target_longitude":reg_employees.longitude,
                                               "from_duration":reg_employees.from_duration,
                                               "to_duration":reg_employees.from_duration,
                                               "distance":reg_employees.distance
                                               } 
                        
                        login_user = {
                            'message': 'Login Successfull!',
                            "EmployeeId": empid,
                            "UserName": user.UserName,
                            "Designation":Employee.Designation,
                            "Disgnation":Employee.Designation,
                            "is_reporting_manager":reporting_emp_list,
                            "reporting_emp_list":reporting_emp_list,
                            "Email":user.Email,
                            'PhoneNumber': user.PhoneNumber,
                            "Password":user.Password,
                            'is_active': user.is_active,
                            "is_login": user.is_login,
                            "Policies_NDA_Accept":Employee.employeeProfile.Policies_NDA_Accept
                        }
                        permissions={"applied_list_access":Employee.applied_list_access,
                                     "screening_shedule_access":Employee.screening_shedule_access,
                                     "interview_shedule_access":Employee.interview_shedule_access,
                                     "final_status_access":Employee.final_status_access,
                                     "all_applicants_access":Employee.all_applicants_access,
                                     #6/6/26
                                     "leads_access": Employee.leads_access,
                                     "universal_leads_access": Employee.universal_leads_access,
                                     "self_activity_add": Employee.self_activity_add,
                                    "all_employees_view": Employee.all_employees_view,
                                    "all_employees_edit": Employee.all_employees_edit,
                                    "employee_personal_details_view": Employee.employee_personal_details_view,
                                    "massmail_communication": Employee.massmail_communication,
                                    "holiday_calender_creation": Employee.holiday_calender_creation,
                                    "assign_offerletter_prepare": Employee.assign_offerletter_prepare,
                                    "job_post": Employee.job_post,
                                    "attendance_upload": Employee.attendance_upload,
                                    "leave_create": Employee.leave_create,
                                    "leave_edit": Employee.leave_edit,
                                    "salary_component_creation": Employee.salary_component_creation,
                                    "salary_template_creation": Employee.salary_template_creation,
                                    "assign_resignation_apply":Employee.assign_resignation_apply,
                                    "assign_leave_apply":Employee.assign_leave_apply,
                                     }
                        login_user.update(dict_data)
                        login_user.update({"user_permissions":permissions})
                        login_user.update(attandance_permission)
                        #log_ip_view(request)
                        return Response(login_user, status=status.HTTP_200_OK)
                    else:
                        if check_password(password, user.Password):
                            return Response("Unauthorised User Data Found !", status=status.HTTP_400_BAD_REQUEST)
                        else:
                            return Response("Invalid Password.", status=status.HTTP_400_BAD_REQUEST)   
                except Exception as e:
                    print(e)
                    return Response(e) 
            else:
                return Response("User Not Activated!", status=status.HTTP_400_BAD_REQUEST)
        except RegistrationModel.DoesNotExist:
            print("User Not Found")
            return Response("Invalid EmployeeId!", status=status.HTTP_400_BAD_REQUEST)
        
class UserProfileUpdate(APIView):
    def get(self,request,userid):
        try:
            policies_accept=request.GET.get('Policies_NDA_Accept')
            Employee=EmployeeInformation.objects.filter(employee_Id=userid).first()
            if policies_accept and not Employee.Policies_NDA_Accept:
                Employee.Policies_NDA_Accept = json.loads(policies_accept)  #if isinstance(policies_accept,bool) else False
                Employee.save()
            return Response("Policies and NDA Accepted Successfully",status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self,request,userid):
        print(request.data)
        print(request.data.get("profile_img"))
        try:
            # profile=request.data.get("Profile")
            if RegistrationModel.objects.filter(EmployeeId=userid,is_active=True,is_login=True).exists() :
                UO = RegistrationModel.objects.get(EmployeeId=userid)
                serializer = profileUpdateSerializer(UO,data=request.data, context={'request': request},partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response(serializer.errors,status=status.HTTP_404_NOT_FOUND)
            else:
                print("error")
        except:
            return Response("bad",status=status.HTTP_404_NOT_FOUND)
        
class loginuserview(APIView):
    def get(self,request,login_user):
        print(login_user)
        try:   
            login_user_obj=RegistrationModel.objects.filter(EmployeeId=login_user).first()
            serializer=excludeRegistrationSerializer(login_user_obj,context={'request': request})
            print(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(str(e),status=status.HTTP_404_NOT_FOUND)
        
class ChangePasswordView(APIView):
    def post(self, request):
        old_password = request.data.get('OldPassword')
        new_password = request.data.get('NewPassword')
        empid=request.data.get("EmployeeId")
        try:
            user = RegistrationModel.objects.get(EmployeeId=empid)
            if user.is_login:
                if check_password(old_password, user.Password):
                    user.Password = make_password(new_password)
                    user.save()
                    notification=Notification.objects.create(sender=None,receiver=user,message=f"Password Changed successfully!")
                    return Response("Password changed successfully!", status=status.HTTP_200_OK)
                else:
                    return Response("Old password was incorrect.", status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("Please login to change password.",status=status.HTTP_400_BAD_REQUEST)
        except RegistrationModel.DoesNotExist:
            return Response("User not found or not logged in.", status=status.HTTP_404_NOT_FOUND)
        
class LogoutView(APIView):
    def post(self, request,empid):
        # empid=loginuser()
        try:
            loged_in = RegistrationModel.objects.get(EmployeeId=empid)
            if loged_in.is_login == True:
                loged_in.is_login = False
                loged_in.save()
                return Response("Logout Successful", status=status.HTTP_200_OK)
            else:
                return Response('user Alderdy logout!',status=status.HTTP_200_OK)
        except RegistrationModel.DoesNotExist:
            return Response("User not found or not logged in", status=status.HTTP_404_NOT_FOUND)

# /////////////////////////////////////////////////////////////////////////////////////////////////
#                   ...........candidate Application View................
# ///////////////////////////////////////////////////////////////////////////////////////////////////
# from django.db.models import Q
class CandidateApplicationView(APIView):
    def get(self,request,can_id):
        if can_id:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
                # if candidate.Fresher: #candidate.current_position in ['Fresher' , 'Student']
                if candidate.current_position in ['Fresher' , 'Student']:
                    serializer = FresherApplicationSerializer(candidate)
                else:
                    serializer = ExperienceApplicationSerializer(candidate)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except CandidateApplicationModel.DoesNotExist:
                return Response("Candidate Not Found", status=status.HTTP_404_NOT_FOUND)
            
    def post(self,request,param):
        state=request.data.get("State") 
        district=request.data.get("District")
        gender=request.data.get("Gender")
        Position=request.data.get("Position")
        jps=request.data.get("JobPortalSource")
        exist_status=request.data.get("exist_status")
        called_can_id=request.data.get("called_can_id")
        selected_emp_id = request.data.get("selected_emp_id")
        primary_contact = request.data.get("PrimaryContact")
        
        # --- AUTO STATUS UPDATE / DASHBOARD SYNC LOGIC ---
        if selected_emp_id and selected_emp_id != "Other" and primary_contact:
            target_employee = EmployeeDataModel.objects.filter(EmployeeId=selected_emp_id, employeeProfile__employee_status="active").first()
            if target_employee:
                # 1. Ensure 'interview_calls' activity and instances exist for this recruiter
                activity_list, _ = ActivityListModel.objects.get_or_create(
                    activity_name="interview_calls",
                    defaults={"added_by": target_employee}
                )
                
                today = timezone.localtime().date()
                new_activity_instance, _ = NewActivityModel.objects.get_or_create(
                    Activity=activity_list,
                    Employee=target_employee,
                    Activity_assigned_Date__month=today.month,
                    Activity_assigned_Date__year=today.year,
                    defaults={
                        "Activity_assigned_Date": today,
                        "targets": 0,
                        "activity_assigned_by": target_employee
                    }
                )
                
                month_achieve_instance, _ = MonthAchivesListModel.objects.get_or_create(
                    Activity_instance=new_activity_instance,
                    Date=today,
                    defaults={"achieved": 0}
                )

                # 2. Try to find an existing lead for this candidate with this recruiter
                # Check for exact phone match or last 10 digits to be safe
                existing_lead = NewDailyAchivesModel.objects.filter(
                    Q(candidate_phone=primary_contact) | Q(candidate_phone__icontains=primary_contact[-10:]),
                    current_day_activity__Activity_instance__Employee=target_employee
                ).order_by('-Created_Date').first()

                if existing_lead:
                    # Update existing lead to 'walkin'
                    existing_lead.interview_status = 'walkin'
                    existing_lead.lead_status = 'active'
                    existing_lead.interview_walkin_date = timezone.now()
                    existing_lead.save()

                    # No follow-up record created here to avoid double-counting calls in metrics.
                    # Registration via Global Form is tracked via 'walkin' status.

                    # Old Code (Commented for reference):
                    # FollowUpModel.objects.create(
                    #     activity_record=existing_lead,
                    #     follow_up_type='interview',
                    #     expected_date=today,
                    #     expected_time=timezone.now().time(),
                    #     notes="Status Updated: Registered via Global Form. Marked as Interview Attended.",
                    #     status='completed',
                    #     completed_on=timezone.now(),
                    #     created_by=target_employee
                    # )
                else:
                    # Create NEW lead in the dashboard so it's counted
                    new_lead = NewDailyAchivesModel.objects.create(
                        current_day_activity=month_achieve_instance,
                        candidate_name=f"{request.data.get('FirstName', '')} {request.data.get('LastName', '')}".strip(),
                        candidate_phone=primary_contact,
                        candidate_email=request.data.get("Email"),
                        lead_status='active',
                        interview_status='walkin',
                        interview_walkin_date=timezone.now(),
                    )
                    
                    # No follow-up record created here to avoid double-counting calls in metrics.

                    # Old Code (Commented for reference):
                    # FollowUpModel.objects.create(
                    #     activity_record=new_lead,
                    #     follow_up_type='interview',
                    #     expected_date=today,
                    #     expected_time=timezone.now().time(),
                    #     notes="New Walk-in: Registered via Global Form. Marked as Interview Attended.",
                    #     status='completed',
                    #     completed_on=timezone.now(),
                    #     created_by=target_employee
                    # )
                
                # Update achieved count for the day
                daily_achievements_count = NewDailyAchivesModel.objects.filter(
                    current_day_activity=month_achieve_instance
                ).exclude(lead_status='staged').count()
                month_achieve_instance.achieved = daily_achievements_count
                month_achieve_instance.save()
        # ------------------------------------------------
        
        # if Position=="Fresher":# Position == 'Fresher' or Position == 'Student':
        request_data=request.data.copy()
        if jps is not None:
            if str(jps).strip().lower() in ["linkedin","naukri","foundit","direct"]:
                request_data['JobPortalSource'] = str(jps).strip().lower()
            elif jps=="referral":
                request_data["JobPortalSource"] = jps
            else:
                request_data["Other_jps"]=jps
                request_data["JobPortalSource"] ="others"
        
        
        if Position == 'Fresher' or Position == 'Student':
            serializer=FresherApplicationSerializer(data=request_data)
        
            if serializer.is_valid():
                # serializer.validated_data['AppliedDesignation']=param
                formatted_string = f"State: {state}\nDistrict: {district}"
                serializer.validated_data['Location']=formatted_string
                serializer.validated_data['Fresher']=True # serializer.validated_data["current_position"]=Position
                serializer.validated_data["current_position"]=Position
                serializer.validated_data['Gender']=str(gender).lower()
               
                # if jps is not None:
                #     if str(jps).strip().lower() in ["linkedin","naukri","foundit"]:
                #         serializer.validated_data['JobPortalSource'] = str(jps).strip().lower()
                #     else:
                #         serializer.validated_data["Other_jps"]=jps
                #         serializer.validated_data["JobPortalSource"] ="others"
                can_instance=serializer.save()
                can=CandidateApplicationModel.objects.get(id=can_instance.pk)
                can.Filled_by="Candidate"
                can.save()
                receiver=EmployeeDataModel.objects.filter(Designation="HR")#designation__Name="HR"
                if receiver:
                    for rec in receiver:
                        user=RegistrationModel.objects.get(EmployeeId=rec.EmployeeId)
                        obj=Notification.objects.create(sender=None, receiver=user, message=f"{Position} candidate Applied With Id {can_instance.CandidateId}!",candidate_id=can_instance,not_type='cal')
        
                dict_msg={"Message":"Submitted Successfull"}
                serializer_data=serializer.data
                serializer_data.update(dict_msg)
                return Response(serializer_data,status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                dict_msg={"Message":"Submittion Failed"}
                return Response(dict_msg, status=status.HTTP_404_NOT_FOUND)
        else:
            serializer=ExperienceApplicationSerializer(data=request_data)
            if serializer.is_valid():
                # serializer.validated_data['AppliedDesignation']=param
                formatted_string = f"State: {state}\nDistrict: {district}"
                serializer.validated_data['Location']=formatted_string
                serializer.validated_data['Experience']=True# serializer.validated_data["current_position"]=Position
                serializer.validated_data["current_position"]=Position
                serializer.validated_data['Gender']=str(gender).lower()
                
                # if jps is not None:
                #     if str(jps).strip().lower() in ["linkedin","naukri","foundit"]:
                #         serializer.validated_data['JobPortalSource'] = str(jps).strip().lower()
                #     else:
                #         serializer.validated_data["Other_jps"]=jps
                #         serializer.validated_data["JobPortalSource"] ="others"
                can_instance=serializer.save()
                can=CandidateApplicationModel.objects.get(id=can_instance.pk)
                can.Filled_by="Candidate"
                can.save()
                receiver=EmployeeDataModel.objects.filter(Designation="HR")
                if receiver:
                    for rec in receiver:
                        user=RegistrationModel.objects.get(EmployeeId=rec.EmployeeId)
                        obj=Notification.objects.create(sender=None, receiver=user, message=f"{Position} candidate Applied With Id {can_instance.CandidateId}!",candidate_id=can_instance,not_type='cal')
                dict_msg={"Message":"Submitted Successfull"}
                serializer_data=serializer.data
                serializer_data.update(dict_msg)
                return Response(serializer_data,status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                dict_msg={"Message":"Submittion Failed"}
                return Response(dict_msg, status=status.HTTP_404_NOT_FOUND)

#changes
class ScreeningAssigningView(APIView):
    def post(self, request):
        try:
            print(request.data)
            recruiter_id = request.data.get("Recruiterid")
            Candidates=request.data.get("Candidates")
            if not Candidates:
                return Response("Please Select Candidates", status=status.HTTP_404_NOT_FOUND)
            assigned_data = []
            for candidate_id in Candidates:    
                candidate = CandidateApplicationModel.objects.get(CandidateId=candidate_id)
                recruiter_data = EmployeeDataModel.objects.filter(EmployeeId=recruiter_id).first()
                loggedin_user = request.data.get('login_user')
                assiend_by=EmployeeDataModel.objects.get(EmployeeId=loggedin_user)
                rec_dict = {
                    "Candidate": candidate.pk,
                    "Recruiter": recruiter_data.pk,
                    "AssignedBy": assiend_by.pk,
                    "status":"Assigned",
                }
                serializer = ScreeningAssigningSerializer(data=rec_dict)
                if serializer.is_valid():
                    screening_instance=serializer.save()
                    candidate.Telephonic_Round_Status = "Assigned"
                    candidate.save()
                    screening_Schedule = InterviewScheduleStatusModel.objects.create(InterviewScheduledCandidate=candidate,
                                                                             Interview_Schedule_Status="Assigned",
                                                                             screening=screening_instance)
                    screening_Schedule.screening.status='Assigned'
                    screening_Schedule.screening.save()
                #     assigned_data.append(serializer.data)
                #     try:
                #         if recruiter_data:
                #             rec_register_obj=RegistrationModel.objects.get(EmployeeId=recruiter_data.EmployeeId)
                #         if loggedin_user:
                #             sender_register_obj=RegistrationModel.objects.get(EmployeeId=loggedin_user)
                #         obj=Notification.objects.create(sender= sender_register_obj, receiver=rec_register_obj, message=f"{sender_register_obj.EmployeeId} Assigned Screening Process !",candidate_id=candidate,not_type='scr_assign')
                #     except Exception as e:
                #         print(e)
                #         return Response(e, status=status.HTTP_400_BAD_REQUEST)
                    #changes
                    assigned_data.append(serializer.data)
                    try:                        
                        sender_reg = RegistrationModel.objects.filter(EmployeeId=assiend_by.EmployeeId).first()
                        receiver_reg = RegistrationModel.objects.filter(EmployeeId=recruiter_data.EmployeeId).first()
                        if sender_reg and receiver_reg:
                            message = f"{assiend_by.Name} assigned a new candidate for screening: {candidate.FirstName} {candidate.LastName}."
                        Notification.objects.create(
                        sender=sender_reg,
                        receiver=receiver_reg,
                        message=message,
                        candidate_id=candidate,
                        not_type='scr_assign',
                        reference_id=candidate.CandidateId 
                    )
                    except Exception as e:
                        print(f"Failed to create notification: {e}")
                else:
                    print(serializer.errors)
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
            return Response(assigned_data, status=status.HTTP_200_OK)
        except CandidateApplicationModel.DoesNotExist:
            return Response("Candidate Not Found", status=status.HTTP_404_NOT_FOUND)
        
    def get(self,request,can_id=None): 
        if can_id is None:
            Recruiters=EmployeeDataModel.objects.filter(Designation__in=['Recruiter',"HR","Admin"],employeeProfile__employee_status='active')#designation__Name="Recruiter"
            rec_list=[]
            for rec in Recruiters:
                if RegistrationModel.objects.filter(EmployeeId=rec.EmployeeId,is_active=True).exists():
                    serializer = ScreeningEmployeeSerializer(rec).data
                    rec_list.append(serializer)
            return Response(rec_list,status=status.HTTP_200_OK)
        else:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
                # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                if candidate.current_position in ['Fresher' , 'StudNotificationent']:
                    serializer = FresherApplicationSerializer(candidate)
                else:
                    serializer = ExperienceApplicationSerializer(candidate)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except CandidateApplicationModel.DoesNotExist:
                return Response("Candidate Not Found", status=status.HTTP_404_NOT_FOUND)
from django.utils.html import format_html
class InterviewSchedulView(APIView):
    def post(self, request):
    
        cid = request.data.get("Candidate")
        eid = request.data.get("interviewer")
        email_message=request.data.get("Email_Message")
        email_status=request.data.get("mail_status")
        # .....................................start new
        for_whome=request.data.get("for_whom")
        
        if not for_whome:
            return Response("for whome this interview is required",status=status.HTTP_400_BAD_REQUEST)
        
        assigned_req_obj=None
        if for_whome == "client":
        
            assigned_req=request.data.get("assigned_requirement")
            if assigned_req:
                assigned_req=int(assigned_req)
                
            # assigned_req=1
            if not assigned_req:
                return Response("requirement instance is required",status=status.HTTP_400_BAD_REQUEST)
            
            interview_instance=InterviewSchedulModel.objects.filter(Candidate__CandidateId=cid,assigned_requirement__requirement__pk=assigned_req)
            
            if interview_instance.exists():
                return Response("for this requirement Candidate was aldredy exist",status=status.HTTP_400_BAD_REQUEST)
            
            empid = request.data.get('login_user')
            
            assigned_req_obj=RequirementAssign.objects.filter(requirement__pk=int(assigned_req),assigned_to_recruiter__EmployeeId=empid).first()
            
            open_positions=assigned_req_obj.position_count
            closed_positions=assigned_req_obj.closed_pos_count
    
            if open_positions == closed_positions:
                return Response("Assigned Requirement Possitions Interview Schedule limit Exiced",status=status.HTTP_400_BAD_REQUEST)
            # assigned_req_obj.closed_pos_count+=1
            # assigned_req_obj.save()
# ...............................................end new
        if eid:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=cid)
                employee = EmployeeDataModel.objects.get(EmployeeId=eid)
            except CandidateApplicationModel.DoesNotExist:
                return Response("Candidate Not Found",status=status.HTTP_400_BAD_REQUEST)
            except EmployeeDataModel.DoesNotExist:
                return Response("Employee Not Found",status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=cid)
                employee = EmployeeDataModel.objects.filter(Designation="Admin").first()
            except CandidateApplicationModel.DoesNotExist:
                return Response("Candidate Not Found", status=status.HTTP_400_BAD_REQUEST)
            except EmployeeDataModel.DoesNotExist:
                return Response("Employee Not Found", status=status.HTTP_400_BAD_REQUEST)
         
        id=request.data.get("InterviewDate")
        it=request.data.get("InterviewTime")
        id = id.strip('"')
        it = it.strip('"')
        dt_str = id + " " + it+":00"
        datetime_obj = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        formatted_dt_str = datetime_obj.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
        empid = request.data.get('login_user')
        try:
            user = RegistrationModel.objects.get(EmployeeId=empid)
            employee_obj=EmployeeDataModel.objects.get(EmployeeId=empid)
        except RegistrationModel.DoesNotExist:
            print("RegistrationModel not exist")
            pass
        
        serializer_data = {
            "Candidate": candidate.pk,
            "InterviewRoundName":request.data.get("InterviewRoundName"),
            "interviewer": employee.pk,
            "InterviewDate":formatted_dt_str,
            "InterviewType":request.data.get("InterviewType"),
            "ScheduledBy":employee_obj.pk,
            "status":"Assigned",
            "for_whome":for_whome,
            "assigned_requirement":assigned_req_obj.pk if assigned_req_obj else None,
        }
        serializer = InterviewSchedulSerializer(data=serializer_data)
        if serializer.is_valid():
            interviewe_instance=serializer.save()
            interviewe_instance.status="Assigned"
            interviewe_instance.save()
            Interview_Schedule = InterviewScheduleStatusModel.objects.create(InterviewScheduledCandidate=candidate,
                                                                             Interview_Schedule_Status="Assigned",
                                                                             interviewe=interviewe_instance)
            try:
                scr_obj=ScreeningAssigningModel.objects.filter(Candidate__CandidateId=Interview_Schedule.InterviewScheduledCandidate.CandidateId).first()
                if scr_obj:
                    scr_obj.status="Completed"
                    scr_obj.save()
            except:
                pass
            
            Other_EMP_Mail=request.data.get("Other_EMP_Mail")
            
            if not eid and Other_EMP_Mail:
               
                interviewe_instance_obj=InterviewSchedulModel.objects.get(pk=interviewe_instance.pk)
                interviewe_instance_obj.inside_interviewer=False
                interviewe_instance_obj.Out_EMP_email=Other_EMP_Mail
                interviewe_instance_obj.save()
                review_form=request.data.get("review_form")
                name=candidate.FirstName
                if candidate.LastName:
                    name= name +" "+candidate.LastName
                subject= f"Interview Schedule From Merida Tech Minds."
                message=f"click the below link to give the review to Candidate {name}.\n\n{review_form}/{interviewe_instance.pk}/"
                
                send_mail(subject,message,
                        settings.EMAIL_HOST_USER,[Other_EMP_Mail],fail_silently=False)
                
            if email_message and email_status=="Yes":
                subject= f"Interview Schedule From Merida Tech Minds"
                send_mail(subject=subject,message='',
                        from_email=settings.EMAIL_HOST_USER,recipient_list=[candidate.Email],fail_silently=False,html_message=email_message)
            
            candidate.Interview_Schedule="Assigned"
            candidate.save()
            try:
                if  employee:
                    rec_register_obj=RegistrationModel.objects.get(EmployeeId=employee.EmployeeId)
                    obj=Notification.objects.create(sender= user, receiver=rec_register_obj, message=f"{user.EmployeeId} Assigned Interview Schedule ! ",candidate_id=candidate,not_type='int_assign')
            except Exception as e:
                    print(f"notification not created {e}")
            interview_scheduled=serializer.data
            interview_scheduled["interviewer"]=employee.EmployeeId
            return Response(interview_scheduled, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get(self,request):
        Recruiters=EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")
        rec_list=[]
        for rec in Recruiters:
            if RegistrationModel.objects.filter(EmployeeId=rec.EmployeeId,is_active=True).exists():
                serializer = ScreeningEmployeeSerializer(rec).data
                rec_list.append(serializer)
        return Response(rec_list,status=status.HTTP_200_OK)


# reassigning interview to another interviewer
    def patch(self,request):
        data=request.data.copy()
        print(request.data)
        interview_instance=data.get("id")
        interviewer=data.get("interviewer")
        schedular=data.get("ScheduledBy")
         
        interview_obj=InterviewSchedulModel.objects.filter(pk=interview_instance).first()
        if interview_obj:
            emp_obj=EmployeeDataModel.objects.filter(EmployeeId=interviewer).first()
            data["interviewer"]=emp_obj.pk
            scheulded_emp=EmployeeDataModel.objects.filter(EmployeeId=schedular).first()
            data["ScheduledBy"]=scheulded_emp.pk
            interview_serializer=InterviewSchedulSerializer(interview_obj,data=data,partial=True)
            if interview_serializer.is_valid():
                instance=interview_serializer.save()
                return Response("done !",status=status.HTTP_200_OK)
            else:
                return Response("failed !",status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("interview instance was not exist",status=status.HTTP_400_BAD_REQUEST)

# sunday work 
class InterviewScheduledCandidatesData(APIView):
    def get(self,request,interview_id):
        try:
            response_dict={}
            interview_instance=InterviewSchedulModel.objects.get(pk=interview_id)
            interview_serializer=InterviewSchedulSerializer(interview_instance).data
            candidate_data=CandidateApplicationModel.objects.get(CandidateId=interview_instance.Candidate.CandidateId)
            # if candidate_data.Fresher==True:#candidate.current_position in ['Fresher' , 'Student']
            if candidate_data.current_position in ['Fresher' , 'Student']:
                candidate_serializer=FresherApplicationSerializer(candidate_data).data
            else:
                candidate_serializer=ExperienceApplicationSerializer(candidate_data).data
            interview_serializer["Out_EMP_email"]=interview_instance.Out_EMP_email
            interview_serializer["inside_interviewer"]=interview_instance.inside_interviewer
            interview_serializer["ScheduledBy"]=interview_instance.ScheduledBy.EmployeeId
            interview_serializer["status"]=interview_instance.status
            
            response_dict.update(interview_serializer)
            response_dict.update({"candidate_data":candidate_serializer})
            return Response(response_dict,status=status.HTTP_200_OK)
        except Exception as e:
            print("helloooo")
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
class Telephonic_Round_StatusView(APIView):
    def get(self, request, can_id=None,Employee=None,screener=None,loginuser=None,scr_status=None):
        if can_id:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
                interview_employee=ScreeningAssigningModel.objects.filter(id=screener).first()
                interview_status=InterviewScheduleStatusModel.objects.filter(InterviewScheduledCandidate__CandidateId=candidate,screening__Recruiter=interview_employee.Recruiter,review__screeingreview=screener)
                interview_list={}
                list={}
                if interview_status:  
                    for i in interview_status:
                        if i.screening: 
                            Screening_Scheduled_data=ScreeningAssigningModel.objects.get(id=i.screening.pk)
                            if i.review:
                                candidate_review=Review.objects.get(id=i.review.pk)
                                serialised_review=ScreeningReviewSerializer(candidate_review).data
                            else:
                                serialised_review={}
                            serialised_interview=ScreeningAssigningSerializer(Screening_Scheduled_data).data
                            serialised_interview.update({"review":serialised_review})
                            interview_list.update(serialised_interview)
                # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                if candidate.current_position in ['Fresher' , 'Student']:
                        candidate_data=FresherApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                        list.update({"screening_data":interview_list})
                else:
                        candidate_data=ExperienceApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                        list.update({"screening_data":interview_list})
                return Response(list,status=status.HTTP_200_OK)
            except Exception as e:
                print(e) 
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        elif Employee:
            assigned_candidates = InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status=scr_status)
            assigned_candidates_data = []
            for assigned_candidate in assigned_candidates:
                if assigned_candidate.screening:
                    ScreeningScheduleStatus = ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                    assigned_candidate_data = ScreeningAssigningSerializer(ScreeningScheduleStatus).data
                    rpk = assigned_candidate_data.get("Recruiter")
                    cpk = assigned_candidate_data.get("Candidate")
                    epk = assigned_candidate_data.get("AssignedBy")
                    emp = EmployeeDataModel.objects.get(pk=rpk)
                    can = CandidateApplicationModel.objects.get(pk=cpk)
                    assigned_emp = EmployeeDataModel.objects.get(pk=epk)
 
                    # Check if the employee ID matches the specified employee
                    if emp.EmployeeId == Employee:
                        
                        assigned_candidate_data["Recruiter"] = emp.EmployeeId
                        assigned_candidate_data["AssignedBy"]=assigned_emp.EmployeeId
                        assigned_candidate_data["Candidate"] = can.CandidateId
                        assigned_candidate_data["Name"] = can.FirstName
                        assigned_candidate_data["Assigned_Status"] =assigned_candidate.Interview_Schedule_Status
                        assigned_candidate_data["Date_of_assigned"]=ScreeningScheduleStatus.Date_of_assigned.date()
                        assigned_candidate_data["Time_of_assigned"]=ScreeningScheduleStatus.Date_of_assigned.time().replace(second=0, microsecond=0)
                        assigned_candidates_data.append(assigned_candidate_data)
                        if assigned_candidate.review: 
                            review_candidates = Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data = SRS(review_candidates).data
                            rev_data["ReviewedOn"]=review_candidates.ReviewedOn.date()
                            rev_data["Time"]=review_candidates.ReviewedOn.time().replace(second=0, microsecond=0)
                            assigned_candidate_data.update({"Review": rev_data})
                        else:
                            assigned_candidate_data.update({"Review": {}})
            # Return the filtered data
            return Response(assigned_candidates_data, status=status.HTTP_200_OK)
        
        else:
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(screening__AssignedBy__EmployeeId=loginuser,Interview_Schedule_Status=scr_status)
           
            assigned_candidates_data = []
            for assigned_candidate in assigned_candidates:
                if assigned_candidate.screening:
                    ScreeningScheduleStatus=ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                    assigned_candidate_data = ScreeningAssigningSerializer(ScreeningScheduleStatus).data
                    rpk=assigned_candidate_data.get("Recruiter")
                    cpk=assigned_candidate_data.get("Candidate")
                    emp=EmployeeDataModel.objects.get(pk=rpk)
                    can=CandidateApplicationModel.objects.get(pk=cpk)
                    assigned_candidate_data["Recruiter"]=emp.EmployeeId
                    assigned_candidate_data["AssignedBy"]=loginuser
                    assigned_candidate_data["Candidate"]=can.CandidateId
                    assigned_candidate_data["Name"]=can.FirstName
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                    assigned_candidate_data["Date_of_assigned"]=ScreeningScheduleStatus.Date_of_assigned
                    # assigned_candidate_data["Time_of_assigned"]=ScreeningScheduleStatus.Date_of_assigned.time().replace(second=0, microsecond=0)
                    assigned_candidates_data.append(assigned_candidate_data)
                    if assigned_candidate.review:
                        review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                        rev_data=SRS(review_candidates).data
                        rev_data["ReviewedOn"]=review_candidates.ReviewedOn.date()
                        rev_data["Time"]=review_candidates.ReviewedOn.time().replace(second=0, microsecond=0)
                        assigned_candidate_data.update({"Review":rev_data})
                    else:
                        assigned_candidate_data.update({"Review":{}})
            return Response(assigned_candidates_data, status=status.HTTP_200_OK)


# screening assigned list in the shedular dashboard
from django.db.models import F
class Screening_assigned_list(APIView):
    def get(self,request,loginuser=None,scr_status=None):
        # screening assigned list
        emp_obj=EmployeeDataModel.objects.get(EmployeeId=loginuser)
        if emp_obj.Designation in ["HR","Admin"] and scr_status=='Assigned':
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status='Assigned').exclude(
            screening__Recruiter__EmployeeId=loginuser)
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Telephonic_Round_Status=scr_status,InterviewScheduledCandidate__Final_Results="Pending",screening__status="Assigned").exclude(InterviewScheduledCandidate__Interview_Schedule="Assigned")
            assigned_list=[]
            for assigned_candidate in candidates_list:
                if assigned_candidate.screening:
                    ScreeningScheduleStatus=ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                    assigned_candidate_data = NewScreeningAssigningSerializer(ScreeningScheduleStatus).data
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                    if scr_status=="Completed":
                        if assigned_candidate.review:
                            review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data=SRS(review_candidates).data
                            assigned_candidate_data.update({"Review":rev_data})
                        else:
                            assigned_candidate_data.update({"Review":{}})
                    assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
        else:
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(screening__AssignedBy__EmployeeId=loginuser).exclude(
                screening__Recruiter__EmployeeId=loginuser)
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Telephonic_Round_Status=scr_status,InterviewScheduledCandidate__Final_Results="Pending",screening__status="Assigned").exclude(InterviewScheduledCandidate__Interview_Schedule="Assigned")
            assigned_list=[]
            for assigned_candidate in candidates_list:
                ScreeningScheduleStatus=ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                assigned_candidate_data = NewScreeningAssigningSerializer(ScreeningScheduleStatus).data
                assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                if scr_status=="Completed":
                    if assigned_candidate.review:
                        review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                        rev_data=SRS(review_candidates).data
                        assigned_candidate_data.update({"Review":rev_data})
                    else:
                        assigned_candidate_data.update({"Review":{}})
                assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
        
# screening assigned list in the recruiter dashboard 
class Candidate_Screening_list(APIView):
    def get(self,request,loginuser=None,scr_status=None):
        # screening assigned list
        emp_obj=EmployeeDataModel.objects.get(EmployeeId=loginuser)
        if emp_obj.Designation in ["HR","Admin"] and scr_status=='Completed':
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status='Completed')
            
            # candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Telephonic_Round_Status=scr_status,InterviewScheduledCandidate__Final_Results="Pending").exclude(Q(InterviewScheduledCandidate__Interview_Schedule="Assigned") | Q(InterviewScheduledCandidate__Interview_Schedule="Completed"))
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Telephonic_Round_Status=scr_status,InterviewScheduledCandidate__Final_Results="Pending",screening__status="Assigned").exclude(Q(InterviewScheduledCandidate__Interview_Schedule="Assigned"))
            # for i in candidates_list:
            #     print(i.screening,i.InterviewScheduledCandidate.CandidateId,i.InterviewScheduledCandidate.Telephonic_Round_Status,i.InterviewScheduledCandidate.Interview_Schedule)
            #     pass
            assigned_list=[]
            for assigned_candidate in candidates_list:
                if assigned_candidate.screening:
                    ScreeningScheduleStatus=ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                    assigned_candidate_data = NewScreeningAssigningSerializer(ScreeningScheduleStatus).data
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                    if scr_status=="Completed":
                        if assigned_candidate.review:
                            review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data=SRS(review_candidates).data
                            assigned_candidate_data.update({"Review":rev_data})
                        else:
                            assigned_candidate_data.update({"Review":{}})
                    assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
        else:
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(screening__Recruiter__EmployeeId=loginuser)
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Telephonic_Round_Status=scr_status,InterviewScheduledCandidate__Final_Results="Pending",screening__status="Assigned")
            assigned_list=[]
            for assigned_candidate in candidates_list:
                ScreeningScheduleStatus=ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                assigned_candidate_data = NewScreeningAssigningSerializer(ScreeningScheduleStatus).data
                assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                if scr_status=="Completed":
                    if assigned_candidate.review:
                        review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                        rev_data=SRS(review_candidates).data
                        assigned_candidate_data.update({"Review":rev_data})
                    else:
                        assigned_candidate_data.update({"Review":{}})
                assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)


# interview assigned list in the shedular dashboard
class Interview_assigned_list(APIView):
    def get(self,request,loginuser=None,scr_status=None):
        # interview assigned list
        emp_obj=EmployeeDataModel.objects.get(EmployeeId=loginuser)
        if emp_obj.Designation in ["HR","Admin"] and scr_status=='Assigned':
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status='Assigned',interviewe__for_whome="ours").exclude(
                interviewe__interviewer__EmployeeId=loginuser)
            # for i in assigned_candidates:
            #     print(i.interviewe,i.Interview_Schedule_Status)
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Interview_Schedule=scr_status,InterviewScheduledCandidate__Final_Results="Pending",Interview_Schedule_Status=scr_status)
            assigned_list=[]
            for assigned_candidate in candidates_list:
                if assigned_candidate.interviewe:
                    InterviewScheduleStatus=InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                    assigned_candidate_data = NewInterviewSchedulSerializer(InterviewScheduleStatus).data
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                    if scr_status=="Completed":
                        if assigned_candidate.review:
                            review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data=IRS(review_candidates).data
                            assigned_candidate_data.update({"Review":rev_data})
                        else:
                            assigned_candidate_data.update({"Review":{}})
                    assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
        else:
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledBy__EmployeeId=loginuser,interviewe__for_whome="ours").exclude(
            interviewe__interviewer__EmployeeId=loginuser) 
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Interview_Schedule=scr_status,InterviewScheduledCandidate__Final_Results="Pending",Interview_Schedule_Status=scr_status)
            assigned_list=[]
            for assigned_candidate in candidates_list:
                InterviewScheduleStatus=InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                assigned_candidate_data = NewInterviewSchedulSerializer(InterviewScheduleStatus).data
                assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                if scr_status=="Completed":
                    if assigned_candidate.review:
                        review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                        rev_data=IRS(review_candidates).data
                        assigned_candidate_data.update({"Review":rev_data})
                    else:
                        assigned_candidate_data.update({"Review":{}})
                assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
    
    
# interview assigned list in the interviewer dashboard 
class Candidate_Interview_list(APIView):
    def get(self,request,loginuser=None,scr_status=None):
        # interview assigned list
        emp_obj=EmployeeDataModel.objects.get(EmployeeId=loginuser)
        # if emp_obj.Designation in ["HR","Admin"] and scr_status=='Completed':
        if scr_status=='Completed':
            if emp_obj.Designation in ["HR","Admin"]:
                assigned_candidates=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status='Completed',interviewe__for_whome="ours")
                candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Interview_Schedule=scr_status,InterviewScheduledCandidate__Final_Results="Pending",Interview_Schedule_Status=scr_status)
            else:
                assigned_candidates=InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledBy__EmployeeId=loginuser,interviewe__for_whome="ours")
                candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Interview_Schedule=scr_status,InterviewScheduledCandidate__Final_Results="Pending",Interview_Schedule_Status=scr_status)
                
            assigned_list=[]
            for assigned_candidate in candidates_list:
                if assigned_candidate.interviewe:
                    InterviewScheduleStatus=InterviewSchedulModel.objects.filter(id=assigned_candidate.interviewe.pk).first()
                    assigned_candidate_data = NewInterviewSchedulSerializer(InterviewScheduleStatus).data
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.InterviewScheduledCandidate.Interview_Schedule
                    if scr_status=="Completed":
                        if assigned_candidate.review:
                            review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data=IRS(review_candidates).data
                            assigned_candidate_data.update({"Review":rev_data})
                        else:
                            assigned_candidate_data.update({"Review":{}})
                    assigned_list.append(assigned_candidate_data)
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(interviewe__interviewer__EmployeeId=loginuser,interviewe__for_whome="ours")
            if assigned_candidates.exists():
                candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Interview_Schedule=scr_status,InterviewScheduledCandidate__Final_Results="Pending",Interview_Schedule_Status=scr_status)
            for assigned_candidate in candidates_list:
                if assigned_candidate.interviewe:
                    InterviewScheduleStatus=InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                    assigned_candidate_data = NewInterviewSchedulSerializer(InterviewScheduleStatus).data
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.InterviewScheduledCandidate.Interview_Schedule
                    if scr_status=="Completed":
                        if assigned_candidate.review:
                            review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data=IRS(review_candidates).data
                            assigned_candidate_data.update({"Review":rev_data})
                        else:
                            assigned_candidate_data.update({"Review":{}})
                    assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
        else:
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(interviewe__interviewer__EmployeeId=loginuser,interviewe__for_whome="ours")
            candidates_list=assigned_candidates.filter(InterviewScheduledCandidate__Interview_Schedule=scr_status,InterviewScheduledCandidate__Final_Results="Pending",Interview_Schedule_Status=scr_status)
            assigned_list=[]
            for assigned_candidate in candidates_list:
                if assigned_candidate.interviewe:
                    InterviewScheduleStatus=InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                    assigned_candidate_data = NewInterviewSchedulSerializer(InterviewScheduleStatus).data
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.InterviewScheduledCandidate.Interview_Schedule
                    if scr_status=="Completed":
                        if assigned_candidate.review:
                            review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                            rev_data=IRS(review_candidates).data
                            assigned_candidate_data.update({"Review":rev_data})
                        else:
                            assigned_candidate_data.update({"Review":{}})
                    assigned_list.append(assigned_candidate_data)
            return Response(assigned_list,status=status.HTTP_200_OK)
class CandidateScreeningCompletedDetails(APIView):
    def get(self,request,can_id):
        try:
            candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
            interview_status=InterviewScheduleStatusModel.objects.filter(InterviewScheduledCandidate=candidate)
            list={}
            screening_list={}
            for i in interview_status:
                if i.screening: 
                    Interview_Scheduled_data=ScreeningAssigningModel.objects.get(id=i.screening.pk)
                    serialised_interview=ScreeningAssigningSerializer(Interview_Scheduled_data).data
                    if i.review:
                        candidate_review=Review.objects.get(id=i.review.pk)
                        serialised_review=ScreeningReviewSerializer(candidate_review).data
                        serialised_interview.update({"review":serialised_review})
                    else:
                        serialised_review={}
                    screening_list.update(serialised_interview)
                    # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                    if candidate.current_position in ['Fresher' , 'Student']:
                        candidate_data=FresherApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                        list.update({"screening_data":screening_list})
                        
                    else:
                        candidate_data=ExperienceApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                        list.update({"screening_data":screening_list})
            #24/09/24.............           
            if list=={}:
                list=None
            #............
            return Response(list,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)   
class CandidateInterviewCompletedDetails(APIView):
    def get(self,request,can_id):
        try:
            print(can_id)
            candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
            interview_status=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Completed",InterviewScheduledCandidate=candidate)
            list={}
            screening_list={}
            interview_list=[]
            if interview_status:
                for i in interview_status:
                    if i.screening:
                        Interview_Scheduled_data=ScreeningAssigningModel.objects.get(id=i.screening.pk)
                        serialised_interview=ScreeningAssigningSerializer(Interview_Scheduled_data).data
                        if i.review:
                            candidate_review=Review.objects.get(id=i.review.pk)
                            serialised_review=ScreeningReviewSerializer(candidate_review).data
                            serialised_interview.update({"review":serialised_review})
                            screening_list.update(serialised_interview)
                        else:
                            serialised_review={}
                    if i.interviewe: 
                        Interview_Scheduled_data=InterviewSchedulModel.objects.get(id=i.interviewe.pk)
                        serialised_interview=InterviewSchedulSerializer(Interview_Scheduled_data).data
                        if i.review:
                            candidate_review=Review.objects.get(id=i.review.pk)
                            if Interview_Scheduled_data.InterviewRoundName=="technical_round":
                                serialised_review=TrInterviewReviewSerializer(candidate_review).data
                            else:
                                 serialised_review=InterviewReviewSerializer(candidate_review).data
                            serialised_interview.update({"review":serialised_review})
                            interview_list.append(serialised_interview)
                        else:
                            serialised_review={}
        
            # if candidate.Fresher: #candidate.current_position in ['Fresher' , 'Student']
            if candidate.current_position in ['Fresher' , 'Student']:
                candidate_data=FresherApplicationSerializer(candidate).data
                list.update({"candidate_data":candidate_data})
                list.update({"screening_data":screening_list})
                list.update({"interview_data":interview_list})
            else:
                candidate_data=ExperienceApplicationSerializer(candidate).data
                list.update({"candidate_data":candidate_data})
                list.update({"screening_data":screening_list})
                list.update({"interview_data":interview_list})
            return Response(list,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
            
class Interview_Schedule_StatusView(APIView):
    def get(self, request, Interview=None,can_id=None,Employee=None,loginuser=None,scr_status=None):
        if can_id:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
                interview_employee=InterviewSchedulModel.objects.filter(id=Interview).first()
                interview_status=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Completed",InterviewScheduledCandidate=candidate)
                # interview_status=InterviewScheduleStatusModel.objects.filter(InterviewScheduledCandidate__CandidateId=candidate,interviewe__interviewer=interview_employee.interviewer,review__interview_id=Interview)
                if interview_status:
                    if not interview_status:
                        return Response({"message": "No interview data found for the candidate"}, status=status.HTTP_404_NOT_FOUND)
                    list={}
                    interview_list=[]
                    for i in interview_status:
                        print(i)
                        if i.interviewe: 
                            Interview_Scheduled_data=InterviewSchedulModel.objects.get(id=i.interviewe.pk)
                            if i.review:
                                candidate_review=Review.objects.get(id=i.review.pk)
                                serialised_review=InterviewReviewSerializer(candidate_review).data
                            else:
                                serialised_review={}
                            serialised_interview=InterviewSchedulSerializer(Interview_Scheduled_data).data
        
                            serialised_interview.update({"review":serialised_review})
                            interview_list.append(serialised_interview)
    
                    # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                    if candidate.current_position in ['Fresher' , 'Student']:
                        candidate_data=FresherApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                        list.update({"interview_data":interview_list})
                    else:
                        candidate_data=ExperienceApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                        list.update({"interview_data":interview_list})
                    return Response(list,status=status.HTTP_200_OK)
                else:
                    list={}
                    # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                    if candidate.current_position in ['Fresher' , 'Student']:
                        candidate_data=FresherApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                    else:
                        candidate_data=ExperienceApplicationSerializer(candidate).data
                        list.update({"candidate_data":candidate_data})
                    return Response(list,status=status.HTTP_200_OK)
            except Exception as e:
                print(e) 
                return Response(e, status=status.HTTP_400_BAD_REQUEST)
        elif Employee:
            assigned_candidates = InterviewSchedulModel.objects.filter(interviewer__EmployeeId=Employee)
            print(assigned_candidates )
            assigned_candidates_data = []
            if assigned_candidates:
                for assigned_candidate in assigned_candidates:
                    assigned_candidate_data = InterviewSchedulSerializer(assigned_candidate).data
                    ipk=assigned_candidate_data.get("interviewer")
                    emp=EmployeeDataModel.objects.get(pk=ipk)
                    assigned_candidate_data["interviewer"]=emp.EmployeeId
                    cpk=assigned_candidate_data.get("Candidate")
                    can=CandidateApplicationModel.objects.get(pk=cpk)
                    assigned_candidate_data["ScheduledBy"]=assigned_candidate.ScheduledBy.EmployeeId
                    assigned_candidate_data["Candidate"]=can.CandidateId
                    assigned_candidate_data["Name"]=can.FirstName
                    assigned_candidate_data["ScheduledOn"]=assigned_candidate.ScheduledOn.date()
                    assigned_candidate_data["ScheduledTime"]=assigned_candidate.ScheduledOn.time().replace(second=0, microsecond=0)
                    assigned_candidate_data["InterviewDate"]=assigned_candidate.InterviewDate.date()
                    assigned_candidate_data["InterviewTime"]=assigned_candidate.InterviewDate.time().replace(second=0, microsecond=0)
                    rev_obj=InterviewScheduleStatusModel.objects.get(interviewe=assigned_candidate.pk)
                    assigned_candidate_data["Assigned_Status"]=rev_obj.Interview_Schedule_Status
                    if  rev_obj.review:
                        review_candidates=Review.objects.get(id=rev_obj.review.pk)
                        rev_data=IRS(review_candidates).data
                        rev_data["ReviewedOn"]=review_candidates.ReviewedOn.date()
                        rev_data["Time"]=review_candidates.ReviewedOn.time().replace(second=0, microsecond=0)
                        assigned_candidate_data.update({"Review":rev_data})
                    else:
                        assigned_candidate_data.update({"Review":{}})
                    merged_data = {**assigned_candidate_data}
                    assigned_candidates_data.append(merged_data)
            return Response(assigned_candidates_data,status=status.HTTP_200_OK)
        else:
            assigned_candidates=InterviewScheduleStatusModel.objects.filter(Q(interviewe__ScheduledBy__EmployeeId=loginuser) | Q(interviewe__interviewer__EmployeeId=loginuser),Interview_Schedule_Status=scr_status)
            # assigned_candidates=InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledBy__EmployeeId=loginuser)
            assigned_candidates_data = []
            for assigned_candidate in assigned_candidates:
                if assigned_candidate.interviewe:
                    InterviewScheduleStatus=InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                    assigned_candidate_data = InterviewSchedulSerializer(InterviewScheduleStatus).data
                    ipk=assigned_candidate_data.get("interviewer")
                    emp=EmployeeDataModel.objects.get(pk=ipk)
                    cpk=assigned_candidate_data.get("Candidate")
                    can=CandidateApplicationModel.objects.get(pk=cpk)
                    assigned_candidate_data["ScheduledBy"]=InterviewScheduleStatus.ScheduledBy.EmployeeId
                    assigned_candidate_data["interviewer"]=emp.EmployeeId
                    assigned_candidate_data["Candidate"]=can.CandidateId
                    assigned_candidate_data["Name"]=can.FirstName
                    assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                    assigned_candidate_data["ScheduledOn"]=InterviewScheduleStatus.ScheduledOn.date()
                    assigned_candidate_data["ScheduledTime"]=InterviewScheduleStatus.ScheduledOn.time().replace(second=0, microsecond=0)
                    assigned_candidate_data["Date_of_assigned"]=InterviewScheduleStatus.InterviewDate.date()
                    assigned_candidate_data["Time_of_assigned"]=InterviewScheduleStatus.InterviewDate.time().replace(second=0, microsecond=0)
                    assigned_candidates_data.append(assigned_candidate_data)
                    if assigned_candidate.review:
                        review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                        rev_data=IRS(review_candidates).data
                        rev_data["ReviewedOn"]=review_candidates.ReviewedOn.date()
                        rev_data["Time"]=review_candidates.ReviewedOn.time().replace(second=0, microsecond=0)
                        assigned_candidate_data.update({"Review":rev_data})
                    else:
                        assigned_candidate_data.update({"Review":{}})
            return Response(assigned_candidates_data, status=status.HTTP_200_OK)


class ScreeningReviewListView(APIView):
    def post(self, request):
        cid = request.data.get("Can_Id")
        screening_schedule=request.data.get("id")
        loginuser=request.data.get("login_user")
        
        request_data=request.data.copy()
        request_data["ReviewedBy"]=loginuser
         
        try:
            candidate = CandidateApplicationModel.objects.get(CandidateId=cid)
        except CandidateApplicationModel.DoesNotExist:
            return Response("Candidate Not Found", status=status.HTTP_404_NOT_FOUND)
        
        serializer = ScreeningReviewSerializer(data=request_data)
        if serializer.is_valid():
            review_instance=serializer.save()
            candidate.Telephonic_Round_Status="Completed"
            if review_instance.Screening_Status == "rejected":
                candidate.Final_Results="Reject"
    
            elif review_instance.Screening_Status =="to_client":
                candidate.Final_Results="consider_to_client"
            
            elif review_instance.Screening_Status =="walkout":
                candidate.Final_Results="walkout"
            candidate.save()
            response_data = serializer.data
            response_data["CandidateId"] = cid
            if screening_schedule:
                screening_scheule_obj=ScreeningAssigningModel.objects.get(pk=screening_schedule)
                # screening_scheule_obj.status="Completed"
                # screening_scheule_obj.save()
                review_obj=Review.objects.get(pk=review_instance.pk)
                review_obj.screeingreview=screening_scheule_obj
                review_obj.save()
                # candidate.Interview_Schedule="Completed"
                # candidate.save()
                iss_obj=InterviewScheduleStatusModel.objects.get(screening=screening_scheule_obj)
                iss_obj.review=review_instance
                iss_obj.Interview_Schedule_Status="Completed"
                iss_obj.save()
            try:
                sen_register_obj=RegistrationModel.objects.get(EmployeeId=loginuser)
                rec_register_obj=RegistrationModel.objects.get(EmployeeId=screening_scheule_obj.AssignedBy.EmployeeId)
                notification=Notification.objects.create(sender= sen_register_obj, receiver=rec_register_obj, message=f"{ sen_register_obj.EmployeeId} Completed Assigned Screening Round of {candidate.CandidateId} on {iss_obj.review.ReviewedOn}! ",candidate_id=candidate,not_type='scr_com')
            except Exception as e:
                        print(e)
            return Response(response_data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
from django.db import IntegrityError   
class InterviewReviewListView(APIView):
    def post(self, request):
        cid = request.data.get("Can_Id")
        interview_schedule = request.data.get("id")
        login_user = request.data.get("login_user")
        request_data = request.data.copy()
        request_data["ReviewedBy"] = login_user
        try:
            candidate = CandidateApplicationModel.objects.get(CandidateId=cid)
        except CandidateApplicationModel.DoesNotExist:
            return Response("Candidate Not Found", status=status.HTTP_404_NOT_FOUND)
        
        if interview_schedule:
            # Check if a review with the same interview_id already exists
            if Review.objects.filter(interview_id=interview_schedule).exists():
                return Response("A review with this interview ID already exists.", status=status.HTTP_400_BAD_REQUEST)
        
        serializer = InterviewReviewSerializer(data=request_data)
        if serializer.is_valid():
                review_instance = serializer.save()
                if interview_schedule:
                    interview_schedule_obj = InterviewSchedulModel.objects.get(pk=interview_schedule)
                    interview_schedule_obj.status="Completed"
                    interview_schedule_obj.save()
                    review_obj = Review.objects.get(pk=review_instance.pk)
                    review_obj.interview_id = interview_schedule_obj
                    review_obj.save()
                    candidate.Interview_Schedule = "Completed"
                    candidate.save()
                    iss_obj = InterviewScheduleStatusModel.objects.get(interviewe=interview_schedule_obj)
                    iss_obj.review = review_instance
                    iss_obj.Interview_Schedule_Status = "Completed"
                    iss_obj.save()
                    serializer_data=serializer.data
                    serializer_data["review_status"]=iss_obj.Interview_Schedule_Status
                try:
                    sen_register_obj = RegistrationModel.objects.get(EmployeeId=login_user)
                    rec_register_obj = RegistrationModel.objects.get(EmployeeId=interview_schedule_obj.ScheduledBy.EmployeeId)
                    notification = Notification.objects.create(
                        sender=sen_register_obj, 
                        receiver=rec_register_obj, 
                        message=f"{sen_register_obj.EmployeeId} Completed Assigned Interview Round of {candidate.CandidateId} on {iss_obj.review.ReviewedOn}!", 
                        candidate_id=candidate, 
                        not_type='int_com'
                    )
                except Exception as e:
                    print("Notification not created:", e)
                return Response(serializer_data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
class UpdateFinalStatusView(APIView):
    def post(self, request):
        print(request.data)
        requestdata=request.data.copy()
        mail_subject=request.data.get("subject")
        mail_message=request.data.get("Email_Message")
        send_status=request.data.get("mail_status")
        can_id=request.data.get("CandidateId")
        req_id=request.data.get("req_id")
        can_obj=CandidateApplicationModel.objects.filter(CandidateId=can_id).first()
        requestdata["CandidateId"]=can_obj.pk
        requirement_obj=None
        if req_id:
            requirement_obj=Requirement.objects.filter(pk=int(req_id)).first()
        
        requestdata["req_id"] = requirement_obj.pk if requirement_obj else None
        
        serializer = HRInterviewReviewSerializer(data=requestdata)
        if serializer.is_valid():
            instance=serializer.save()
            if requirement_obj and serializer.data["Final_Result"] in ["client_offered", "candidate_joined"]:
                can_obj.Final_Results=serializer.data["Final_Result"]
                can_obj.save()
            elif requirement_obj and serializer.data["Final_Result"] not in ["client_offered", "candidate_joined"]:
                pass
            else:
                can_obj.Final_Results=serializer.data["Final_Result"]
                can_obj.save()
            if mail_message and send_status=='Yes':
                # html_message = render_to_string('email_template.html', mail_message)
                send_mail(
                    subject=mail_subject,
                    message='',
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[can_obj.Email],
                    fail_silently=False, 
                    html_message=mail_message,
                )
            return Response(can_obj.Final_Results, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# .............................................................final list data............................................................................
# from django.db.models import OuterRef, Subquery
# class FinalDataView(APIView):
#     # def get(self, request,login_user):
#     #     try:
#     #         # obj_instance = InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Completed")
#     #         obj_instance = InterviewScheduleStatusModel.objects.exclude(InterviewScheduledCandidate__Final_Results="Pending")
#     #         interview_status_can = []
#     #         set_list=set()
#     #         for review_obj in obj_instance:
#     #             if review_obj.interviewe or review_obj.screening:
#     #                 candidate_id = review_obj.InterviewScheduledCandidate.CandidateId
#     #                 set_list.add(candidate_id)
#     #         for candidate_id in set_list:
#     #             can_obj = CandidateApplicationModel.objects.get(CandidateId=candidate_id)
#     #             serializer = CandidateApplicationSerializer(can_obj)
#     #             serializer=serializer.data
#     #             serializer["FinalResult"]=can_obj.Final_Results
#     #             interview_status_can.append(serializer)
#     #         return Response(interview_status_can, status=status.HTTP_200_OK)
#     #     except Exception as e:
#     #         print(e)
#     #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
#     def get(self, request, login_user):
#         try:
#             # Fetching candidates who have completed interview or screening
#             obj_instance = InterviewScheduleStatusModel.objects.exclude(
#                 InterviewScheduledCandidate__Final_Results="Pending"
#             ).filter(
#                 Q(interviewe=True) | Q(screening=True)
#             ).values_list('InterviewScheduledCandidate__CandidateId', flat=True)
#             # Set of candidate IDs that have undergone interview or screening
#             set_list = set(obj_instance)
#             # Fetch candidates who haven't been interviewed but are not in pending results
#             non_interview_can = CandidateApplicationModel.objects.exclude(
#                 CandidateId__in=obj_instance
#             ).exclude(Final_Results="Pending").values_list('CandidateId', flat=True)
#             # Add non-interviewed candidate IDs to the set
#             set_list.update(non_interview_can)
#             # Fetch candidate details and serialize
#             candidates = CandidateApplicationModel.objects.filter(CandidateId__in=set_list)
#             interview_status_can = [
#                 {**CandidateApplicationSerializer(can_obj).data, "FinalResult": can_obj.Final_Results}
#                 for can_obj in candidates
#             ]
#             return Response(interview_status_can, status=status.HTTP_200_OK)
#         except Exception as e:
#             print(e)
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)




# .............................................................final list data............................................................................
# from django.db.models import OuterRef, Subquery
# class FinalDataView(APIView):
#     # def get(self, request,login_user):
#     #     try:
#     #         # obj_instance = InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Completed")
#     #         obj_instance = InterviewScheduleStatusModel.objects.exclude(InterviewScheduledCandidate__Final_Results="Pending")
#     #         interview_status_can = []
#     #         set_list=set()
#     #         for review_obj in obj_instance:
#     #             if review_obj.interviewe or review_obj.screening:
#     #                 candidate_id = review_obj.InterviewScheduledCandidate.CandidateId
#     #                 set_list.add(candidate_id)
#     #         for candidate_id in set_list:
#     #             can_obj = CandidateApplicationModel.objects.get(CandidateId=candidate_id)
#     #             serializer = CandidateApplicationSerializer(can_obj)
#     #             serializer=serializer.data
#     #             serializer["FinalResult"]=can_obj.Final_Results
#     #             interview_status_can.append(serializer)
#     #         return Response(interview_status_can, status=status.HTTP_200_OK)
#     #     except Exception as e:
#     #         print(e)
#     #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
#     def get(self, request, login_user):
#         try:
#             # Fetching candidates who have completed interview or screening
#             obj_instance = InterviewScheduleStatusModel.objects.exclude(
#                 InterviewScheduledCandidate__Final_Results="Pending"
#             ).filter(
#                 Q(interviewe=True) | Q(screening=True)
#             ).values_list('InterviewScheduledCandidate__CandidateId', flat=True)
#             # Set of candidate IDs that have undergone interview or screening
#             set_list = set(obj_instance)
#             # Fetch candidates who haven't been interviewed but are not in pending results
#             non_interview_can = CandidateApplicationModel.objects.exclude(
#                 CandidateId__in=obj_instance
#             ).exclude(Final_Results="Pending").values_list('CandidateId', flat=True)
#             # Add non-interviewed candidate IDs to the set
#             set_list.update(non_interview_can)
#             # Fetch candidate details and serialize
#             candidates = CandidateApplicationModel.objects.filter(CandidateId__in=set_list)
#             interview_status_can = [
#                 {**CandidateApplicationSerializer(can_obj).data, "FinalResult": can_obj.Final_Results}
#                 for can_obj in candidates
#             ]
#             return Response(interview_status_can, status=status.HTTP_200_OK)
#         except Exception as e:
#             print(e)
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


#24-12-2025 and 25-12-2025
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
class CandidatePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'size'
    max_page_size = 100
class FinalDataView(APIView):
    @method_decorator(cache_page(60 * 5))
    def get(self, request, login_user):
        try:
            queryset = (
                CandidateApplicationModel.objects
                .exclude(Final_Results="Pending")
                .only(
                    "id",
                    "CandidateId",
                    "FirstName",
                    "LastName",
                    "DOB",
                    "Email",
                    "PrimaryContact",
                    "AppliedDesignation",
                    "AppliedDate",
                    "Appling_for",
                    "current_position",
                    "Final_Results",
                    "JobPortalSource",
                    "Other_jps",
                    "Referred_by",
                    "Telephonic_Round_Status",
                    "Interview_Schedule",
                )
                .order_by("-AppliedDate")
            )
            search_query = request.query_params.get('search', None)
            from_date = request.query_params.get('from_date', None)
            to_date = request.query_params.get('to_date', None)
            if from_date and to_date:
                queryset = queryset.filter(DataOfApplied__range=(from_date, to_date))
            if search_query:
                queryset = queryset.filter(
                    Q(CandidateId__icontains=search_query) |
                    Q(FirstName__icontains=search_query) |
                    Q(Email__icontains=search_query) |
                    Q(PrimaryContact__icontains=search_query) |
                    Q(AppliedDesignation__icontains=search_query) |
                    Q(Final_Results__icontains=search_query)
                )
            paginator = CandidatePagination()
            page = paginator.paginate_queryset(queryset, request)
            serializer = CandidateApplicationSerializer(page, many=True)
            data = serializer.data
            for item in data:
                item["FinalResult"] = item.get("Final_Results")
            return paginator.get_paginated_response(data)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
class FinalStatusView(APIView):
    def post(self,request):
        try:
            can_id=request.data.get("CandidateId")
            Can_obj = CandidateApplicationModel.objects.get(CandidateId=can_id)
            CA=CandidateApplicationModel.objects.get(CandidateId=can_id)
            single_can_review=InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Completed",InterviewScheduledCandidate=Can_obj)
            if not single_can_review:
                return Response({"message": "No interview data found for the candidate"}, status=status.HTTP_404_NOT_FOUND)
            list={}
            interview_list=[]
            screening_list=[]
            for i in single_can_review:
                if i.interviewe:
                    Interview_Scheduled_data=InterviewSchedulModel.objects.get(id=i.interviewe.pk)
                    candidate_review=Review.objects.get(id=i.review.pk)
                    serialised_interview=InterviewSchedulSerializer(Interview_Scheduled_data).data
                    serialised_review=InterviewReviewSerializer(candidate_review).data
                    serialised_interview.update(serialised_review)
                    interview_list.append(serialised_interview)
                    
                elif i.screening:
                    Screenied_Assigned_data=ScreeningAssigningModel.objects.get(id=i.screening.pk)
                    candidate_review=Review.objects.get(id=i.review.pk)
    
                    serialised_screening=ScreeningAssigningSerializer(Screenied_Assigned_data).data
                    serialised_review=ScreeningReviewSerializer(candidate_review).data
                    serialised_screening.update(serialised_review)
                    screening_list.append(serialised_screening)
           
            # if Can_obj.Fresher:#candidate.current_position in ['Fresher' , 'Student']
            if Can_obj.current_position in ['Fresher' , 'Student']:
                candidate_data=FresherApplicationSerializer(Can_obj).data
                list.update({"candidate_data":candidate_data})
                list.update({"screening_data":screening_list})
                list.update({"interview_data":interview_list})
            else:
                candidate_data=ExperienceApplicationSerializer(Can_obj).data
                list.update({"candidate_data":candidate_data})
                list.update({"screening_data":screening_list})
                list.update({"interview_data":interview_list})
            return Response(list, status=status.HTTP_200_OK)
        except Exception as e:
            print(e) 
            return Response(e, status=status.HTTP_400_BAD_REQUEST)
            
# class FinalCandidatesListViewView(APIView):
#     def get(self,request,FinalStatus,duration="Today",FromDate=None,ToDate=None,):
#         if duration == "Today":
#             date = timezone.localdate()
#         elif duration=="Week":
#             date = timezone.localdate() - timezone.timedelta(days=7) 
#         elif duration == "Month":
#             date = timezone.localdate() - timezone.timedelta(days=30)
#         elif duration == "Year":
#             date = timezone.localdate() - timezone.timedelta(days=360)
#         else:
#             pass
#         if FinalStatus=="Internal_Hiring":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="Internal_Hiring") 
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True).data
#                 return Response(serializer, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#             # try:
#             #     final_status=HRFinalStatusModel.objects.filter(Final_Result="Internal_Hiring",ReviewedOn__range(date,timezone.localdate()))
#             #     Internal_Hiring_List=[]
#             #     for fs in final_status:
#             #         HiriedCan=CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#             #         serializer=FinalResultCandidateSerializer(HiriedCan).data
#             #         Internal_Hiring_List.append(serializer)
#             #     return Response(Internal_Hiring_List, status=status.HTTP_200_OK)
#             # except Exception as e:
#             #     return Response(e,status=status.HTTP_400_BAD_REQUEST)
            
#         elif FinalStatus=="consider_to_client":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="consider_to_client") 
#                 Screening_review_obj=Review.objects.filter(Screening_Status="to_client",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(serializer)
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True).data
#                 HiriedCan_list=HiriedCan_list+serializer
            
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 print(e)
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="Reject":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="Reject")
#                 Screening_review_obj=Review.objects.filter(Screening_Status="reject",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     can_serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(can_serializer)
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True).data
#                 HiriedCan_list=HiriedCan_list+serializer
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="Offered":
#             try:
#                 offered_candidates=OfferLetterModel.objects.all()
#                 print(offered_candidates)
#                 offered_can_serializer=OfferedCandidatesserializer(offered_candidates,many=True)
#                 return Response(offered_can_serializer.data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 print(e)
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="On_Hold":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="On_Hold")
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
            
#         elif FinalStatus=="Scheduled":
#             try:
#                 Screening_review_obj=Review.objects.filter(Screening_Status="scheduled",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(serializer)
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="walkout":
#             try:
#                 Screening_review_obj=Review.objects.filter(Screening_Status="walkout",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(serializer)
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
            
# class FinalCandidatesListViewView(APIView):
#     def get(self, request, FinalStatus, duration=None):
#         start_date=request.GET.get("start_date")
#         end_date=request.GET.get("end_date")
#         req_id=request.GET.get("req_id")
#         if duration == "Today":
#             date = timezone.localdate()
#         elif duration == "Week":
#             date = timezone.localdate() - timezone.timedelta(days=7)
#         elif duration == "Month":
#             date = timezone.localdate() - timezone.timedelta(days=30)
#         elif duration == "Year":
#             date = timezone.localdate() - timezone.timedelta(days=360)
#         else:
#             date = None
#         if start_date and end_date:
#             try:
#                 start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
#                 end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
#             except ValueError:
#                 return Response(
#                     {"error": "Invalid date format for 'start_date' or 'end_date'. Use YYYY-MM-DD."},
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )
#         try:
#             req_obj=None
#             if req_id:
#                 req_obj=Requirement.objects.filter(pk=req_id).first()
#             if FinalStatus == "Internal_Hiring":
#                 final_status = HRFinalStatusModel.objects.filter(
#                     Final_Result="Internal_Hiring",
#                     CandidateId__Final_Results="Internal_Hiring"
#                 )
#                 if date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#                 elif start_date and end_date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(start_date_parsed, end_date_parsed))
#                     pass
                
#                 Internal_Hiring_List = []
#                 single_can_filter = set()
#                 for fs in final_status:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
                
#                 return Response(Internal_Hiring_List, status=status.HTTP_200_OK)
#             elif FinalStatus == "consider_to_client":
#                 final_status = HRFinalStatusModel.objects.filter(
#                     Final_Result="consider_to_client",
#                     CandidateId__Final_Results="consider_to_client"
#                 )
#                 if date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 Internal_Hiring_List = []
#                 single_can_filter = set()
#                 for fs in final_status:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
                        
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
                
#                 Screening_review_obj = Review.objects.filter(Screening_Status="to_client")
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                     if scr_obj.CandidateId.CandidateId not in single_can_filter:
#                        screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                        if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                        serializer = FinalResultCandidateSerializer(screened_candidate)
#                        HiriedCan_list.append(serializer.data)
#                        single_can_filter.add(scr_obj.CandidateId.CandidateId)
                
#                 HiriedCan_list = Internal_Hiring_List + HiriedCan_list
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             elif FinalStatus == "Reject":
#                 final_status = HRFinalStatusModel.objects.filter(
#                     Final_Result="Reject",
#                     CandidateId__Final_Results="Reject"
#                 )
#                 final_status_by_can = HRFinalStatusModel.objects.filter(
#                     Final_Result="Rejected_by_Candidate",
#                     CandidateId__Final_Results="Rejected_by_Candidate"
#                 )
#                 if date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#                     final_status_by_can=final_status_by_can.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 Internal_Hiring_List = []
#                 single_can_filter = set()
#                 for fs in final_status:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
                
#                 for fs in final_status_by_can:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
#                 Screening_review_obj = Review.objects.filter(Screening_Status="rejected")
                
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                    if scr_obj.CandidateId.CandidateId not in single_can_filter:
#                        screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                        if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                        serializer = FinalResultCandidateSerializer(screened_candidate)
#                        HiriedCan_list.append(serializer.data)
#                        single_can_filter.add(scr_obj.CandidateId.CandidateId)
#                 HiriedCan_list = Internal_Hiring_List + HiriedCan_list
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             elif FinalStatus == "offered":
#                 if date:
#                     offered_candidates = OfferLetterModel.objects.filter(Letter_sended_status=True,OfferedDate__range=(date, timezone.localdate()))
#                 else:
#                     offered_candidates = OfferLetterModel.objects.filter(Letter_sended_status=True)
                
#                 offered_can_serializer = OfferLetterserializer(offered_candidates, many=True)
#                 return Response(offered_can_serializer.data, status=status.HTTP_200_OK)
#             elif FinalStatus == "On_Hold":
#                 HiriedCan = CandidateApplicationModel.objects.filter(Final_Results="On_Hold")
#                 serializer = FinalResultCandidateSerializer(HiriedCan, many=True)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
            
#             elif FinalStatus == "Scheduled":
#                 Screening_review_obj = Review.objects.filter(Screening_Status="scheduled")
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer = FinalResultCandidateSerializer(screened_candidate)
#                     HiriedCan_list.append(serializer.data)
                
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             elif FinalStatus == "walkout":
#                 Screening_review_obj = Review.objects.filter(Screening_Status="walkout")
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer = FinalResultCandidateSerializer(screened_candidate)
#                     HiriedCan_list.append(serializer.data)
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             else:
#                 candidates = CandidateApplicationModel.objects.filter(Filled_by="Candidate")
#                 serializer = CandidateApplicationSerializer(candidates, many=True)
#                 return Response(serializer.data)
#         except Exception as e:
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)



#24-12-2025 and 25-12-2025
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

            
# class FinalCandidatesListViewView(APIView):
#     def get(self,request,FinalStatus,duration="Today",FromDate=None,ToDate=None,):
#         if duration == "Today":
#             date = timezone.localdate()
#         elif duration=="Week":
#             date = timezone.localdate() - timezone.timedelta(days=7) 
#         elif duration == "Month":
#             date = timezone.localdate() - timezone.timedelta(days=30)
#         elif duration == "Year":
#             date = timezone.localdate() - timezone.timedelta(days=360)
#         else:
#             pass
#         if FinalStatus=="Internal_Hiring":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="Internal_Hiring") 
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True).data
#                 return Response(serializer, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#             # try:
#             #     final_status=HRFinalStatusModel.objects.filter(Final_Result="Internal_Hiring",ReviewedOn__range(date,timezone.localdate()))
#             #     Internal_Hiring_List=[]
#             #     for fs in final_status:
#             #         HiriedCan=CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#             #         serializer=FinalResultCandidateSerializer(HiriedCan).data
#             #         Internal_Hiring_List.append(serializer)
#             #     return Response(Internal_Hiring_List, status=status.HTTP_200_OK)
#             # except Exception as e:
#             #     return Response(e,status=status.HTTP_400_BAD_REQUEST)
            
#         elif FinalStatus=="consider_to_client":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="consider_to_client") 
#                 Screening_review_obj=Review.objects.filter(Screening_Status="to_client",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(serializer)
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True).data
#                 HiriedCan_list=HiriedCan_list+serializer
            
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 print(e)
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="Reject":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="Reject")
#                 Screening_review_obj=Review.objects.filter(Screening_Status="reject",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     can_serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(can_serializer)
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True).data
#                 HiriedCan_list=HiriedCan_list+serializer
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="Offered":
#             try:
#                 offered_candidates=OfferLetterModel.objects.all()
#                 print(offered_candidates)
#                 offered_can_serializer=OfferedCandidatesserializer(offered_candidates,many=True)
#                 return Response(offered_can_serializer.data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 print(e)
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="On_Hold":
#             try:
#                 HiriedCan=CandidateApplicationModel.objects.filter(Final_Results="On_Hold")
#                 serializer=FinalResultCandidateSerializer(HiriedCan,many=True)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
            
#         elif FinalStatus=="Scheduled":
#             try:
#                 Screening_review_obj=Review.objects.filter(Screening_Status="scheduled",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(serializer)
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
#         elif FinalStatus=="walkout":
#             try:
#                 Screening_review_obj=Review.objects.filter(Screening_Status="walkout",ReviewedOn__range=(date, timezone.localdate()))
#                 HiriedCan_list=[]
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate=CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer=FinalResultCandidateSerializer(screened_candidate).data
#                     HiriedCan_list.append(serializer)
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(e,status=status.HTTP_400_BAD_REQUEST)
            
# class FinalCandidatesListViewView(APIView):
#     def get(self, request, FinalStatus, duration=None):
#         start_date=request.GET.get("start_date")
#         end_date=request.GET.get("end_date")
#         req_id=request.GET.get("req_id")
#         if duration == "Today":
#             date = timezone.localdate()
#         elif duration == "Week":
#             date = timezone.localdate() - timezone.timedelta(days=7)
#         elif duration == "Month":
#             date = timezone.localdate() - timezone.timedelta(days=30)
#         elif duration == "Year":
#             date = timezone.localdate() - timezone.timedelta(days=360)
#         else:
#             date = None
#         if start_date and end_date:
#             try:
#                 start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
#                 end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
#             except ValueError:
#                 return Response(
#                     {"error": "Invalid date format for 'start_date' or 'end_date'. Use YYYY-MM-DD."},
#                         status=status.HTTP_400_BAD_REQUEST,
#                     )
#         try:
#             req_obj=None
#             if req_id:
#                 req_obj=Requirement.objects.filter(pk=req_id).first()
#             if FinalStatus == "Internal_Hiring":
#                 final_status = HRFinalStatusModel.objects.filter(
#                     Final_Result="Internal_Hiring",
#                     CandidateId__Final_Results="Internal_Hiring"
#                 )
#                 if date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#                 elif start_date and end_date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(start_date_parsed, end_date_parsed))
#                     pass
                
#                 Internal_Hiring_List = []
#                 single_can_filter = set()
#                 for fs in final_status:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
                
#                 return Response(Internal_Hiring_List, status=status.HTTP_200_OK)
#             elif FinalStatus == "consider_to_client":
#                 final_status = HRFinalStatusModel.objects.filter(
#                     Final_Result="consider_to_client",
#                     CandidateId__Final_Results="consider_to_client"
#                 )
#                 if date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 Internal_Hiring_List = []
#                 single_can_filter = set()
#                 for fs in final_status:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
                        
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
                
#                 Screening_review_obj = Review.objects.filter(Screening_Status="to_client")
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                     if scr_obj.CandidateId.CandidateId not in single_can_filter:
#                        screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                        if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                        serializer = FinalResultCandidateSerializer(screened_candidate)
#                        HiriedCan_list.append(serializer.data)
#                        single_can_filter.add(scr_obj.CandidateId.CandidateId)
                
#                 HiriedCan_list = Internal_Hiring_List + HiriedCan_list
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             elif FinalStatus == "Reject":
#                 final_status = HRFinalStatusModel.objects.filter(
#                     Final_Result="Reject",
#                     CandidateId__Final_Results="Reject"
#                 )
#                 final_status_by_can = HRFinalStatusModel.objects.filter(
#                     Final_Result="Rejected_by_Candidate",
#                     CandidateId__Final_Results="Rejected_by_Candidate"
#                 )
#                 if date:
#                     final_status = final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#                     final_status_by_can=final_status_by_can.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 Internal_Hiring_List = []
#                 single_can_filter = set()
#                 for fs in final_status:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
                
#                 for fs in final_status_by_can:
#                     if fs.CandidateId not in single_can_filter:
#                         HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
#                         if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                         serializer = FinalResultCandidateSerializer(HiriedCan)
#                         Internal_Hiring_List.append(serializer.data)
#                         single_can_filter.add(fs.CandidateId)
#                 Screening_review_obj = Review.objects.filter(Screening_Status="rejected")
                
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                    if scr_obj.CandidateId.CandidateId not in single_can_filter:
#                        screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                        if req_obj:
#                             interview_obj=InterviewSchedulModel.objects.filter(Candidate=HiriedCan,for_whome="client",assigned_requirement__requirement=req_obj).first()
#                             if interview_obj:
#                                 continue
#                        serializer = FinalResultCandidateSerializer(screened_candidate)
#                        HiriedCan_list.append(serializer.data)
#                        single_can_filter.add(scr_obj.CandidateId.CandidateId)
#                 HiriedCan_list = Internal_Hiring_List + HiriedCan_list
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             elif FinalStatus == "offered":
#                 if date:
#                     offered_candidates = OfferLetterModel.objects.filter(Letter_sended_status=True,OfferedDate__range=(date, timezone.localdate()))
#                 else:
#                     offered_candidates = OfferLetterModel.objects.filter(Letter_sended_status=True)
                
#                 offered_can_serializer = OfferLetterserializer(offered_candidates, many=True)
#                 return Response(offered_can_serializer.data, status=status.HTTP_200_OK)
#             elif FinalStatus == "On_Hold":
#                 HiriedCan = CandidateApplicationModel.objects.filter(Final_Results="On_Hold")
#                 serializer = FinalResultCandidateSerializer(HiriedCan, many=True)
#                 return Response(serializer.data, status=status.HTTP_200_OK)
            
#             elif FinalStatus == "Scheduled":
#                 Screening_review_obj = Review.objects.filter(Screening_Status="scheduled")
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer = FinalResultCandidateSerializer(screened_candidate)
#                     HiriedCan_list.append(serializer.data)
                
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             elif FinalStatus == "walkout":
#                 Screening_review_obj = Review.objects.filter(Screening_Status="walkout")
#                 if date:
#                     Screening_review_obj = Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                
#                 HiriedCan_list = []
#                 for scr_obj in Screening_review_obj:
#                     screened_candidate = CandidateApplicationModel.objects.get(CandidateId=scr_obj.CandidateId.CandidateId)
#                     serializer = FinalResultCandidateSerializer(screened_candidate)
#                     HiriedCan_list.append(serializer.data)
#                 return Response(HiriedCan_list, status=status.HTTP_200_OK)
#             else:
#                 candidates = CandidateApplicationModel.objects.filter(Filled_by="Candidate")
#                 serializer = CandidateApplicationSerializer(candidates, many=True)
#                 return Response(serializer.data)
#         except Exception as e:
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


#22-12-2025 and 25-12-2025
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
class FinalCandidatePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200
class FinalCandidatesListViewView(APIView):
    pagination_class = FinalCandidatePagination
    def paginate_queryset(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        return paginator, page
    def get(self, request, FinalStatus, duration=None):
        try:
            req_id = request.GET.get("req_id")
            req_obj = Requirement.objects.filter(pk=req_id).first() if req_id else None
            today = timezone.localdate()
            date_filter = {}
            if duration == "Today":
                date_filter = {"ReviewedOn__date": today}
            elif duration == "Week":
                date_filter = {"ReviewedOn__date__range": (today - timezone.timedelta(days=7), today)}
            elif duration == "Month":
                date_filter = {"ReviewedOn__date__range": (today - timezone.timedelta(days=30), today)}
            elif duration == "Year":
                date_filter = {"ReviewedOn__date__range": (today - timezone.timedelta(days=360), today)}
            
            # Custom Date Range Filter (Overrides duration)
            from_date = request.GET.get('from_date')
            to_date = request.GET.get('to_date')
            if from_date and to_date:
                date_filter = {"ReviewedOn__date__range": (from_date, to_date)}
            search_value = request.GET.get('search')
            search_filter = Q()
            if search_value:
                search_filter = (
                    Q(CandidateId__icontains=search_value) |
                    Q(FirstName__icontains=search_value) |
                    Q(LastName__icontains=search_value) |
                    Q(Email__icontains=search_value) |
                    Q(PrimaryContact__icontains=search_value) |
                    Q(AppliedDesignation__icontains=search_value) |
                    Q(JobPortalSource__icontains=search_value) |
                    Q(hrfinalstatusmodel__Comments__icontains=search_value) |
                    Q(review__Comments__icontains=search_value)  #22/05/2026
                )
            serializer_class = FinalResultCandidateSerializer
            # serializer_class = FinalResultCandidateSerializer
            
            if FinalStatus in ["Internal_Hiring", "InternalHiring"]:
                queryset = CandidateApplicationModel.objects.filter(
                    search_filter,
                    Final_Results="Internal_Hiring",
                    hrfinalstatusmodel__Final_Result="Internal_Hiring",
                    **{f"hrfinalstatusmodel__{k}": v for k, v in date_filter.items()}
                )
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
                queryset = queryset.select_related().distinct()
            elif FinalStatus == "consider_to_client":
                queryset = CandidateApplicationModel.objects.filter(
                    search_filter,
                    Q(
                        Final_Results="consider_to_client",
                        hrfinalstatusmodel__Final_Result="consider_to_client"
                    )
                    |
                    Q(review__Screening_Status="to_client"),
                    **{f"hrfinalstatusmodel__{k}": v for k, v in date_filter.items()}
                )
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
                queryset = queryset.select_related().distinct()
            elif FinalStatus == "Reject":
                queryset = CandidateApplicationModel.objects.filter(
                    search_filter,
                    Q(hrfinalstatusmodel__Final_Result__in=["Reject", "Rejected_by_Candidate"])
                    |
                    Q(review__Screening_Status="rejected"),
                    **{f"hrfinalstatusmodel__{k}": v for k, v in date_filter.items()}
                )
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
                queryset = queryset.select_related().distinct()
            elif FinalStatus == "On_Hold":
                queryset = CandidateApplicationModel.objects.filter(
                    search_filter,
                    Final_Results="On_Hold"
                ).distinct() #22/05/2026
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
            elif FinalStatus in ["offered", "OfferdCandidates"]:
                queryset = OfferLetterModel.objects.filter(
                    Letter_sended_status=True
                ).select_related("CandidateId")
                if search_value:
                    queryset = queryset.filter(
                        Q(Name__icontains=search_value)|
                        Q(Email__icontains=search_value)|
                        Q(CandidateId__CandidateId__icontains=search_value)|
                        Q(Designation__icontains=search_value)|
                        Q(CandidateId__hrfinalstatusmodel__Comments__icontains=search_value)|
                        Q(CandidateId__review__Comments__icontains=search_value)
                    ).distinct() #22/05/2026
                
                if from_date and to_date:
                     queryset = queryset.filter(OfferedDate__range=[from_date, to_date])
                
                serializer_class = OfferLetterserializer
                paginator, page = self.paginate_queryset(queryset.order_by("-id"), request)
                serializer = serializer_class(page, many=True)
                return paginator.get_paginated_response(serializer.data)
            #22/05/2026    
            elif FinalStatus in ["yet_to_action", "Yet to Action"]:
                internal_hiring_ids = HRFinalStatusModel.objects.filter(
                    Final_Result="Internal_Hiring",
                    CandidateId__Final_Results="Internal_Hiring"
                ).values_list("CandidateId_id", flat=True)

                consider_hr_ids = HRFinalStatusModel.objects.filter(
                    Final_Result="consider_to_client",
                    CandidateId__Final_Results="consider_to_client"
                ).values_list("CandidateId_id", flat=True)
                consider_review_ids = Review.objects.filter(
                    Screening_Status="to_client"
                ).values_list("CandidateId_id", flat=True)

                on_hold_ids = CandidateApplicationModel.objects.filter(
                    Final_Results="On_Hold"
                ).values_list("id", flat=True)

                rejected_hr_ids = HRFinalStatusModel.objects.filter(
                    Final_Result__in=["Reject", "Rejected_by_Candidate"]
                ).values_list("CandidateId_id", flat=True)
                rejected_review_ids = Review.objects.filter(
                    Screening_Status="rejected"
                ).values_list("CandidateId_id", flat=True)

                offered_ids = OfferLetterModel.objects.filter(
                    Letter_sended_status=True
                ).values_list("CandidateId_id", flat=True)

                actioned_ids = set(internal_hiring_ids) | set(consider_hr_ids) | set(consider_review_ids) | set(on_hold_ids) | set(rejected_hr_ids) | set(rejected_review_ids) | set(offered_ids)
                actioned_ids = {x for x in actioned_ids if x is not None}

                queryset = CandidateApplicationModel.objects.filter(
                    search_filter,
                    Filled_by="Candidate"
                ).exclude(id__in=actioned_ids)

                if from_date and to_date:
                    queryset = queryset.filter(DataOfApplied__range=[from_date, to_date])
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
                queryset = queryset.distinct()
            elif FinalStatus == "All Applicants":
                queryset = CandidateApplicationModel.objects.filter(search_filter)
                if from_date and to_date:
                    queryset = queryset.filter(DataOfApplied__range=[from_date, to_date])
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
                queryset = queryset.distinct()
            elif FinalStatus in ["Scheduled", "walkout"]:
                queryset = CandidateApplicationModel.objects.filter(
                    search_filter,
                    review__Screening_Status=FinalStatus.lower()
                )
                if req_id:
                    queryset = queryset.filter(hrfinalstatusmodel__req_id=req_id)
                queryset = queryset.select_related().distinct()
            else:
                queryset = CandidateApplicationModel.objects.none()
            paginator, page = self.paginate_queryset(queryset.order_by("-AppliedDate"), request)
            serializer = serializer_class(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            import traceback
            print(traceback.format_exc())
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
from rest_framework.parsers import MultiPartParser, FormParser
class DocumentsUploadView(APIView): 
    def post(self,request,can_id,mail_sended_by):
        print("documents",request.data)
        parser_classes = (MultiPartParser, FormParser)
        try:
            candidate_id=request.data.get("CandidateID")
            # mail_sended_by=request.data.get("mail_sended_by")
            if candidate_id==can_id:
                can_obj=CandidateApplicationModel.objects.filter(CandidateId=candidate_id).first()
                emp_obj=EmployeeDataModel.objects.filter(EmployeeId=mail_sended_by).first()
                candidate_data=request.data.copy() 
                candidate_data["CandidateID"]=can_obj.pk
                candidate_data["mail_sended_by"]=emp_obj.pk
                serializer = DocumentsUploadModelSerializer(data=candidate_data, context={'request': request})
                if serializer.is_valid():
                    document_instance=serializer.save()
                    can_obj.Documents_Upload_Status="Uploaded"
                    can_obj.save()
                    DUS=InterviewScheduleStatusModel.objects.create(InterviewScheduledCandidate=can_obj,
                                                                    Interview_Schedule_Status="Uploaded",
                                                                    documents=document_instance)
                    receiver=EmployeeDataModel.objects.filter(Designation="HR")
                    if receiver:
                        for rec in receiver:
                            user=RegistrationModel.objects.get(EmployeeId=rec.EmployeeId)
                            obj=Notification.objects.create(sender=None, receiver=user, message=f"{document_instance.CandidateID} Documents Uploaded Successful !")
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                else:
                    print(serializer.errors)
                    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            else: 
                return Response("Documents  Upload not Successful!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(e,status=status.HTTP_404_NOT_FOUND)
        
    def get(self,request,can_id):
        try:
            documents_model=Documents_Upload_Model.objects.filter(CandidateID__CandidateId=can_id)
            doc_list=[]
            for doc in documents_model:
                doc_serializer=DocumentsUploadModelSerializer(doc,context={"request":request}).data
                doc_interview_obj=InterviewScheduleStatusModel.objects.get(documents__pk=doc.pk)
                doc_serializer.update({"BG_Virification_status":doc_interview_obj.Interview_Schedule_Status})
                doc_list.append(doc_serializer)
                print("hdhdhdhdh",doc_list)
            return Response(doc_list,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
from django.db.models import Q        
class CompleteFinalStatusView(APIView):
    def get(self,request,can_id,login_user=None):
        try:
            Can_obj = CandidateApplicationModel.objects.get(CandidateId=can_id)
    
            single_can_review=InterviewScheduleStatusModel.objects.filter(Q(Interview_Schedule_Status="Completed") | Q(Interview_Schedule_Status="Uploaded") ,InterviewScheduledCandidate=Can_obj)
            print(single_can_review)
            # single_can_review=single_can_review.filter(Q(interviewe__ScheduledBy__EmployeeId=login_user) | Q(screening__AssignedBy__EmployeeId=login_user) | Q(documents__mail_sended_by__EmployeeId=login_user))
            # if not single_can_review:
            #     return Response({"message": "No interview data found for the candidate"}, status=status.HTTP_400_BAD_REQUEST)
            list={}
            interview_list=[]
            screening_list=[]
            final_result=[]
            doc_upload_list=[]
            for i in single_can_review:
                if i.interviewe:
                    Interview_Scheduled_data=InterviewSchedulModel.objects.get(id=i.interviewe.pk)
                    candidate_review=Review.objects.get(id=i.review.pk)
                    serialised_interview=InterviewSchedulSerializer(Interview_Scheduled_data).data
                    serialised_review=InterviewReviewSerializer(candidate_review).data
                    serialised_interview.update({"Intrview_review":serialised_review})
                    interview_list.append(serialised_interview)
                    
                elif i.screening:
                    Screenied_Assigned_data=ScreeningAssigningModel.objects.get(id=i.screening.pk)
                    candidate_review=Review.objects.get(id=i.review.pk)
    
                    serialised_screening=ScreeningAssigningSerializer(Screenied_Assigned_data).data
                    serialised_review=ScreeningReviewSerializer(candidate_review).data
                    serialised_screening.update({"screening_review":serialised_review})
                    screening_list.append(serialised_screening)
                elif i.documents:
                    documents_uploaded_data=Documents_Upload_Model.objects.get(id=i.documents.pk)
                    serialised_documents_uploaded=DocumentsUploadModelSerializer(documents_uploaded_data,context={'request': request}).data
                    if i.bg_verification:
                        bg_verification=BG_VerificationModel.objects.filter(pk=i.bg_verification.pk).first()
                        bg_serializer=BGVerificationSerializer(bg_verification,context={'request': request}).data
                    else:
                        bg_serializer={}
                    serialised_documents_uploaded.update({"bg_verification":bg_serializer})
                    doc_upload_list.append(serialised_documents_uploaded)
            final_serializer=[]
            final_result=HRFinalStatusModel.objects.filter(CandidateId=Can_obj.pk)
            for fr in final_result:
                final_ser=HRInterviewReviewSerializer(fr).data
                final_ser['CandidateId']=fr.CandidateId.CandidateId
                final_serializer.append(final_ser)
            can_list=[]
            # if Can_obj.Fresher:#candidate.current_position in ['Fresher' , 'Student']
            if Can_obj.current_position in ['Fresher' , 'Student']:
                candidate_data=FresherApplicationSerializer(Can_obj).data
                candidate_data["Fresher"]="Fresher"
                can_list.append(candidate_data)
                list.update({"candidate_data":can_list})
                list.update({"screening_data":screening_list})
                list.update({"interview_data":interview_list})
                list.update({"FinalResult":final_serializer})
                list.update({"UploadedDocuments":doc_upload_list})
                # list.update({"BackGroungVerification":BGV})
            else:
                candidate_data=ExperienceApplicationSerializer(Can_obj).data
                candidate_data["Experience"]="Experience"
                can_list.append(candidate_data)
                list.update({"candidate_data":can_list})
                list.update({"screening_data":screening_list})
                list.update({"interview_data":interview_list})
                list.update({"FinalResult":final_serializer})
                list.update({"UploadedDocuments":doc_upload_list})
                # list.update({"BackGroungVerification":BGV})
            return Response(list,status=status.HTTP_200_OK)
        except Exception as e:
            print(e) 
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
from HRM_App import models
from django.utils import timezone
class RecCandidateFillingApplication(APIView):
    def post(self,request):
        print(request.data)
        try:
            login_user=request.data.get("login_user")
            Screening_Recruiter=EmployeeDataModel.objects.get(EmployeeId=login_user)
            request_data=request.data.copy()
            can_fresher=request.data.get("Fresher")
            can_experience=request.data.get("Experience")
            if can_fresher:
                request_data["Fresher"]=True
                request_data["Experience"]=False
            else: 
                request_data["Experience"]=True
                request_data["Fresher"]=False
            serializer=RecCandidateFillingserializer(data=request_data)
            if serializer.is_valid():
                instance=serializer.save()
                candidateId_Update=CandidateApplicationModel.objects.get(id=instance.id)
                candidateId_Update.CandidateId=models.candidate_id()
                candidateId_Update.Filled_by=Screening_Recruiter.Designation
                candidateId_Update.save()
                screen_assign_dict={"Candidate":instance.id,"Recruiter":Screening_Recruiter.id,
                                    "AssignedBy":Screening_Recruiter.pk}
                screen_assign=ScreeningAssigningSerializer(data=screen_assign_dict)
                if screen_assign.is_valid():
                    screening_instance=screen_assign.save()
                    try:
                        screening_Schedule = InterviewScheduleStatusModel.objects.create(InterviewScheduledCandidate=instance,
                                                                             Interview_Schedule_Status="Assigned",
                                                                             screening=screening_instance)
                    except Exception as e:
                        print(e)
                else:
                    print(screen_assign.errors)
                return Response(f"Candidated Added Successfull {candidateId_Update.CandidateId}",status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors)
            
        except Exception as e:
            return Response(e,status=status.HTTP_400_BAD_REQUEST)
        
from rest_framework.parsers import MultiPartParser, FormParser
from .models import candidate_id
class CalledCandidatesListCreate(APIView):
    def get(self, request):
        candidates = CalledCandidatesModel.objects.all()
        serializer = CalledCandidatesSerializer(candidates, many=True)
        return Response(serializer.data)
    def post(self, request):
        try:
            emp_id=request.data.get("emp_id")
            serializer = CalledCandidatesSerializer(data=request.data)
            if serializer.is_valid():
                emp_obj=EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()
                serializer.validated_data["called_by"]=emp_obj
                instance=serializer.save()
                if instance.status=="interview_scheduled":
                    can_obj=CandidateApplicationModel.objects.create(CandidateId=candidate_id())
                    can_obj.FirstName=instance.name
                    can_obj.PrimaryContact=instance.phone
                    can_obj.Location=instance.location
                    pass
                return Response(serializer.data, status=status.HTTP_201_CREATED) 
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
    
class OfferLetterDetails(APIView):
    def get(self, request, offer_id=None,login_user=None,approval_status=None):
        if login_user :
            try:
                # Fetch offer letters prepared by the login user
                prepared_offers = OfferLetterModel.objects.filter(letter_prepared_by__EmployeeId=login_user)
                # Fetch offer letters verified by the login user with the given approval status
                verified_offers = OfferLetterModel.objects.filter(letter_verified_by__EmployeeId=login_user)
                
                # Combine both querysets, removing duplicates
                combined_offers = prepared_offers | verified_offers
                combined_offers = combined_offers.distinct()
                
                # Exclude offer letters that have already been sent
                offer_objs = combined_offers.exclude(Letter_sended_status=True)
                if offer_objs.exists():
                    offer_serializer = OfferLetterserializer(offer_objs, many=True).data
                    return Response(offer_serializer, status=status.HTTP_200_OK)
                else:
                    return Response([], status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                offer_objs=OfferLetterModel.objects.filter(pk=offer_id).first()
                if offer_objs:
                    emp_obj=EmployeeDataModel.objects.filter(Designation="Admin").first()
                    offer_objs.letter_verified_by=emp_obj
                    offer_objs.save()
                    approval_serializer=OfferLetterserializer(offer_objs).data
                    try:
                        if  emp_obj:
                            rec_register_obj=RegistrationModel.objects.filter(EmployeeId=emp_obj.EmployeeId).first()
                            
                            sen_registration=RegistrationModel.objects.filter(EmployeeId=offer_objs.letter_prepared_by.EmployeeId).first()
                            notification_obj=Notification.objects.create(sender= sen_registration, receiver=rec_register_obj, message=f"Action Required !\n sent by {offer_objs.letter_prepared_by.EmployeeId}",not_type='Offer_letter_approval')
                            notification_obj.candidate_id=offer_objs.CandidateId
                            notification_obj.save()
                        
                    except Exception as e:
                            print(f"notification not created {e}")
                    return Response(approval_serializer,status=status.HTTP_200_OK)
                else:
                    return Response("instance not exist",status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e))



	#5/1/2026
    def patch(self, request, offer_id):
        try:
            # print(request.data)
            # request_data=request.data
            # offer_objs=OfferLetterModel.objects.filter(pk=offer_id).first()
            # emp_obj=EmployeeDataModel.objects.filter(EmployeeId=request_data["Letter_sended_by"]).first()
            # if 
            # request_data["Letter_sended_by"]=emp_obj.pk
            # ls=request_data["Letter_sended_by"]
            # print(type)
            # if offer_objs:
            #     approval_serializer=OfferLetterserializer(offer_objs,data=request_data,partial=True)
            #     if approval_serializer.is_valid():
            #         instance=approval_serializer.save()
            #         offer_obj=OfferLetterModel.objects.filter(pk=instance.pk).first()
            #         if offer_obj and offer_obj.verification_status=="Denied":
            #             offer_obj.letter_verified_by=None
            #             offer_obj.save()
            #         return Response(approval_serializer.data,status=status.HTTP_200_OK)
            #     else:
            #         print(approval_serializer.errors)
            #         return Response(approval_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            # else:
            #     return Response("offer instance not exist",status=status.HTTP_400_BAD_REQUEST)
            if hasattr(request.data, 'copy'):
                request_data = request.data.copy()
            else:
                request_data = dict(request.data)
            offer_objs = OfferLetterModel.objects.filter(pk=offer_id).first()
            if not offer_objs:
                return Response("offer instance not exist", status=status.HTTP_400_BAD_REQUEST)
            # Metadata/Approval fields that should NOT trigger a reset
            meta_fields = [
                'verification_status', 'approval_status', 'approval_reason', 
                'letter_verified_by', 'VerifiedDate', 'Mail_Status', 
                'Letter_sended_status', 'PDF_File', 'Accept_status', 
                'id', 'offer_instance', 'CandidateId', 'OfferId', 'position_name',
                'letter_prepared_by', 'letter_prepared_date', 'remarks', 'OfferedDate'
            ]
            # Determine if this is an "Edit" (contains fields other than meta fields)
            detail_edits = [k for k in request_data.keys() if k not in meta_fields]
            
            # Normalize current status
            current_status = str(offer_objs.verification_status or "").strip().lower()
            
            reset_applied = False
            # If there are detail edits and it's not a pure approval action
            # Note: Pure approval actions only send meta fields. Edits send detail fields.
            if detail_edits and current_status != "pending":
                # We force reset to Pending because detail fields are being modified
                request_data["verification_status"] = "Pending"
                request_data["letter_verified_by"] = None
                request_data["approval_status"] = False
                request_data["VerifiedDate"] = None
                request_data["approval_reason"] = "Status reset due to detail edits"
                reset_applied = True
            # Perform the update
            approval_serializer = OfferLetterserializer(offer_objs, data=request_data, partial=True)
            if approval_serializer.is_valid():
                instance = approval_serializer.save()
                # instance=approval_serializer.save()
                # offer_obj=OfferLetterModel.objects.filter(pk=instance.pk).first()
                # if offer_obj and offer_obj.verification_status=="Denied":
                #     offer_obj.letter_verified_by=None
                #     offer_obj.save()
                #     return Response(approval_serializer.data,status=status.HTTP_200_OK)
                
                # Maintain the "Denied" special logic from the original code
                if instance.verification_status == "Denied":
                    instance.letter_verified_by = None
                    instance.save()
                # Add some debug info to the response so we can see what happened in network tab
                response_data = OfferLetterserializer(instance).data
                response_data["_reset_applied"] = reset_applied
                response_data["_detected_edits"] = detail_edits
                
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response(approval_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
from django.core.mail import EmailMessage
class SendOfferLetterEmail(APIView):
    def get(self,request,candidate_id):
        try:
            offer_objs=OfferLetterModel.objects.filter(CandidateId__CandidateId=candidate_id).first()
            can_obj=CandidateApplicationModel.objects.filter(CandidateId=candidate_id).first()
            can_serializer=CandidateApplicationSerializer(can_obj).data
            if offer_objs:
                serializer=OfferLetterserializer(offer_objs).data
                can_serializer.update({"offer_instance":serializer})
                return Response(can_serializer,status=status.HTTP_200_OK)
            else:
                can_serializer.update({"offer_instance":None})
                return Response(can_serializer,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    def post(self, request, candidate_id):
        try:
            print(request.data)
            request_data=request.data.copy()
            offered_letter_obj=OfferLetterModel.objects.filter(CandidateId__CandidateId=candidate_id).first()
            try:
                employee_id=request_data["letter_prepared_by"]
                if employee_id:
                    ls_by=EmployeeDataModel.objects.filter(EmployeeId=employee_id).first()
                    request_data["letter_prepared_by"]=ls_by.pk
                else:
                    return Response("letter_prepared_by field required",status=status.HTTP_400_BAD_REQUEST)
            except:
                pass
            if offered_letter_obj:
                return Response("Candidate offer Letter Details Exist",status=status.HTTP_400_BAD_REQUEST)
            else:
                if not offered_letter_obj:
                    can_obj=CandidateApplicationModel.objects.filter(CandidateId=candidate_id).first()
                    request_data['CandidateId']=can_obj.pk
                    request_data['verification_status']="Pending"
                    ls_by=EmployeeDataModel.objects.filter(EmployeeId=employee_id).first()
                    if ls_by.Designation=="Admin":
                        request_data['verification_status']="Approved"
                        request_data["letter_verified_by"]=ls_by.pk
                        request_data["approval_reason"]="Generated by Admin"
                        request_data["approval_status"]=True
                    offered_letter_serializer=OfferLetterserializer(data=request_data)
                    if offered_letter_serializer.is_valid():
                        instance=offered_letter_serializer.save()
                        return Response(offered_letter_serializer.data,status=status.HTTP_200_OK)
                    else:
                        print(offered_letter_serializer.errors)   
                        return Response(offered_letter_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    def patch(self, request, offer_id):
        try:
            offer_letter = request.data.copy()
            letter_sended_by = offer_letter.get("Letter_sended_by")
            
            offer_letter_obj=OfferLetterModel.objects.filter(pk=offer_id).first()
            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=letter_sended_by).first()
            offer_letter["Letter_sended_by"]=emp_obj.pk
            offer_letter["OfferedDate"]=timezone.localtime()
            offer_letter["Letter_sended_status"]=True
            if offer_letter_obj:
                offer_serializer = OfferLetterserializer(offer_letter_obj,data=offer_letter,partial=True)
                if offer_serializer.is_valid():
                    offer_serializer.save()
                    offer_letter_obj.CandidateId.Offer_Letter_Status = "Offered"
                    offer_letter_obj.CandidateId.Final_Results='offered'
                    offer_letter_obj.CandidateId.save()
                    try:
                        subject=offer_letter["subject"]
                        Message=offer_letter["offer_mail_content"]
                        send_mail(
                        subject=subject,message='',
                        from_email=settings.EMAIL_HOST_USER,  
                        recipient_list=[offer_letter_obj.Email],
                        fail_silently=False,
                        html_message=Message
                        )
                        return Response({'message': 'Email sent successfully'}, status=status.HTTP_200_OK)
                    except Exception as e:
                        print(e)
                        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            #         subject = f"Offer Letter From Merida Tech Minds"
            #         message = f"Congratulations Mrs/Miss {offer_letter_obj.Name}. Click the below {offer_accept_form} to accept or reject the offer."
            #         sender_email = 'sender@example.com'
            #         recipient_email = offer_letter_obj.Email
            #         email = EmailMessage(subject, message, sender_email, [recipient_email])
            #         email.attach(f'{offer_letter_obj.Name}_Offer_Letter.pdf', offer_letter_obj.PDF_File.read(), 'application/pdf')
            #         try:
            #             email.send()
            #             return Response({'message': 'Email sent successfully'}, status=status.HTTP_200_OK)
            #         except Exception as e:
            #             print(e)
            #             return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                else:
                    print(offer_serializer.errors)
                    return Response(offer_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("offer instance is not exist", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
                            
class OfferAcceptStatus(APIView):
    def post(self,request,can_id):
        try:
            oas=request.data.get("Status")
            rem=request.data.get("remarks")
            letter=request.data.get("FormURL")# new thing
            can_obj=OfferLetterModel.objects.filter(CandidateId__CandidateId=can_id).first()
            can_obj.CandidateId.Offer_Accept_Status=oas
            can_obj.Accept_status=oas
            can_obj.remarks=rem
            can_obj.save()
            reg_obj=RegistrationModel.objects.filter(EmployeeId=can_obj.Letter_sended_by.EmployeeId).first()
            notification=Notification.objects.create(sender=None ,
                                                     message=f"Today {can_obj.CandidateId.CandidateId}, {oas} Offer Letter.",
                                                     receiver=reg_obj)
            
            appointment_date=OfferLetterModel.objects.filter(Accept_status="Accept",Mail_Status=False)
            print(appointment_date)
            serializer=AcceptOfferLetterserializer(appointment_date,many=True)
            print("helloooooooooooooooooooooooooooooooooooooooo",serializer.data)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response(str(e),status= status.HTTP_400_BAD_REQUEST)
        
    def get(self,request,can_id):
        try:
            offer_accepted_obj=OfferLetterModel.objects.filter(CandidateId__CandidateId=can_id).first()
            if offer_accepted_obj.Accept_status=="Pending":
                print(offer_accepted_obj.Accept_status) 
                return Response({"message":offer_accepted_obj.Accept_status},status=status.HTTP_200_OK)
            else:
                return Response({"message":"Completed"},status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
#9/1/2026
class JoiningAppointmentMail(APIView):
    def post(self,request):
        letter=request.data.get("FormURL")
        can_id=request.data.get("CandidateId")
        print(can_id)
        Candidates_DOJ=CandidateApplicationModel.objects.filter(pk=can_id)
        for candidate in Candidates_DOJ:
            offer=OfferLetterModel.objects.filter(CandidateId=candidate).first()
            offer.Mail_Status=True
            
            # Track joining form email sending
            if not offer.joining_form_sent_date:
                offer.joining_form_sent_date = timezone.localtime()
            else:
                offer.joining_form_resend_count += 1
            
            offer.save()
            subject= f"{candidate.CandidateId} Joining Formalityes Form"
            form=f"{letter}{candidate.pk}"# {offer.pk} here now i am adding the offer instance also
            Message=f"Dear {candidate.FirstName}{candidate.LastName} Please Click the Below link to Fill  The Joining Formalityes  \n {form}"
        
            send_mail(
                    subject,Message,
                    settings.EMAIL_HOST_USER,  
                    [candidate.Email],
                    fail_silently=False,
                    )
            reg_obj=RegistrationModel.objects.filter(EmployeeId=offer.Letter_sended_by.EmployeeId).first()
            notification=Notification.objects.create(sender=None ,
                                                     message=f"Today {candidate.CandidateId} have Joining Appointment \n The Mail has sent to The Candidate .",
                                                     receiver=reg_obj)
        return Response("success",status=status.HTTP_200_OK)
    
# ............................................................................................................

class DocumentsUploasForm(APIView):
    def post(self,request):
        try:
            FormURL=request.data.get('FormURL')
            can_id=request.data.get("CandidateID")
            mail_content=request.data.get("mail_content")
            # mail_sended_by=request.data.get("mail_sended_by")
            can_obj=CandidateApplicationModel.objects.get(CandidateId=can_id)
            subject= f"{can_id} BackGround Verification Documents Upload Form"
            # form=f"{FormURL}{can_id}/{mail_sended_by}"
            # Message=f"Dear {can_obj.FirstName}{can_obj.LastName} Please Click the Below link to Upload Documents for your BG Verification \n {form}"
            Message = mail_content
            send_mail(
                    subject,Message,
                    settings.EMAIL_HOST_USER,  
                    [can_obj.Email],
                    fail_silently=False,
                    )
            return Response("Form Sent Successfully!", status=status.HTTP_201_CREATED)
        
        except Documents_Upload_Model.DoesNotExist:
            return Response("CandidateId Not Found", status=status.HTTP_404_NOT_FOUND)
        
    
class BG_VerificationView(APIView):
    def post(self,request):
        try:
            print(request.data)
            candidate=request.data.get("candidate")
            doc_instance=request.data.get("Documents")
            can_obj=CandidateApplicationModel.objects.filter(CandidateId=candidate).first()
            request_data=request.data.copy()
            request_data["candidate"]=can_obj.pk
            serializer=BGVerificationSerializer(data=request_data)
            if serializer.is_valid():
                doc_status=InterviewScheduleStatusModel.objects.filter(documents=doc_instance).first()
                bgv_instance=serializer.save()
                doc_status.Interview_Schedule_Status="Completed"
                doc_status.bg_verification=bgv_instance
                doc_status.save()
                try:
                    doc_obj=Documents_Upload_Model.objects.filter(CandidateID__CandidateId=candidate).count()
                    obj=BG_VerificationModel.objects.filter(candidate__CandidateId=candidate).count()
                    if doc_obj==obj:
                        can_obj.BG_Status="Verified"
                        can_obj.save()
                except:
                    pass
                return Response(serializer.data,status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response(serializer.errors,status=status.HTTP_404_NOT_FOUND)
        except BG_VerificationModel.DoesNotExist:
            return Response("CandidateId Not Found",status=status.HTTP_404_NOT_FOUND)
        
    def get(self,request,doc_id):
        try:
            BG_Verification=BG_VerificationModel.objects.get(Documents__pk=doc_id)
            BG_serializer=BGVerificationSerializer(BG_Verification).data
            BG_serializer["candidate"]=BG_Verification.candidate.CandidateId
            return Response(BG_serializer,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
class BG_Status(APIView):
    def get(self,request,doc_instance): 
        try:
            doc_status=InterviewScheduleStatusModel.objects.filter(documents=doc_instance).first()
            doc_dict={"status":doc_status.Interview_Schedule_Status}
            print(doc_dict)
            return Response(doc_dict,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
class BG_VerificationMailSendView(APIView):
    def post(self,request):
        try:
            FormURL=request.data.get('FormURL')
            can_id=request.data.get("CandidateID")
            message=request.data.get("message")
            to_mail=request.data.get("to_mail")
            
            # doc_id=request.data.get("DocumentInstance")
            can_obj=CandidateApplicationModel.objects.get(CandidateId=can_id)
            # doc_obj=Documents_Upload_Model.objects.get(pk=doc_id)   
            subject= f"{can_obj.FirstName} BackGround Verification Form"
            form=f"{FormURL}"
            Message=message+form
            send_mail(
                    subject,Message,
                    settings.EMAIL_HOST_USER,  
                    [to_mail],
                    fail_silently=False,
                    )
            return Response("Form Sent Successfully!", status=status.HTTP_201_CREATED)
        except BG_VerificationModel.DoesNotExist:
            return Response("CandidateId Not Found",status=status.HTTP_404_NOT_FOUND)
class PendingJoiningFormsView(APIView):
    """
    API View to get all candidates who haven't filled their joining forms
    Filters candidates whose joining date has passed or is today
    """
    def get(self, request):
        try:
            from datetime import date, timedelta
            
            today = timezone.localdate()
            
            print(f"Fetching pending forms for date: {today}")
            
            # Get all offer letters where:
            # 1. Form not filled yet (joining_form_filled=False)
            # 2. Joining date has passed or is today
            # Note: We're not filtering by Mail_Status initially to see all potential candidates
            pending_offers = OfferLetterModel.objects.filter(
                joining_form_filled=False,
                Date_of_Joining__lte=today  # Joining date is today or in the past
            ).select_related('CandidateId', 'Letter_sended_by', 'position').order_by('Date_of_Joining')
            
            print(f"Found {pending_offers.count()} potential pending offers")
            
            # Prepare response data
            pending_list = []
            for offer in pending_offers:
                try:
                    if offer.CandidateId and offer.Date_of_Joining:
                        days_overdue = (today - offer.Date_of_Joining).days
                        
                        # Only include if Mail_Status is True (email was sent)
                        if not offer.Mail_Status:
                            continue
                        
                        pending_list.append({
                            'offer_id': offer.id,
                            'candidate_id': offer.CandidateId.CandidateId,
                            'name': offer.Name,
                            'email': offer.Email,
                            'phone': offer.contact_info,
                            'joining_date': offer.Date_of_Joining.strftime('%Y-%m-%d'),
                            'days_overdue': days_overdue,
                            'position': offer.position.Name if offer.position else (offer.CandidateId.AppliedDesignation if offer.CandidateId.AppliedDesignation else 'N/A'),
                            'employment_type': offer.Employeement_Type if offer.Employeement_Type else 'N/A',
                            'form_sent_date': offer.joining_form_sent_date.strftime('%Y-%m-%d %H:%M') if offer.joining_form_sent_date else 'N/A',
                            'resend_count': offer.joining_form_resend_count if hasattr(offer, 'joining_form_resend_count') else 0,
                            'manual_offer_sent': offer.manual_offer_sent if hasattr(offer, 'manual_offer_sent') else False,
                        })
                except Exception as e:
                    print(f"Error processing offer {offer.id}: {e}")
                    continue
            
            print(f"Returning {len(pending_list)} pending forms")
            
            return Response({
                'count': len(pending_list),
                'pending_forms': pending_list
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            print(f"Error in PendingJoiningFormsView: {e}")
            print(traceback.format_exc())
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        """
        Resend joining form email to a specific candidate
        """
        try:
            offer_id = request.data.get('offer_id')
            form_url = request.data.get('FormURL')
            
            if not offer_id or not form_url:
                return Response({'error': 'offer_id and FormURL are required'}, status=status.HTTP_400_BAD_REQUEST)
            
            offer = OfferLetterModel.objects.filter(id=offer_id).first()
            if not offer or not offer.CandidateId:
                return Response({'error': 'Offer not found'}, status=status.HTTP_404_NOT_FOUND)
            
            candidate = offer.CandidateId
            
            # Increment resend count
            offer.joining_form_resend_count += 1
            offer.save()
            
            # Send email (matching original format)
            subject = f"{candidate.CandidateId} Joining Formalityes Form"
            form = f"{form_url}{candidate.pk}"
            message = f"Dear {candidate.FirstName}{candidate.LastName} Please Click the Below link to Fill  The Joining Formalityes  \n {form}"
            
            send_mail(
                subject, message,
                settings.EMAIL_HOST_USER,
                [candidate.Email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'Reminder email sent successfully',
                'resend_count': offer.joining_form_resend_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error resending email: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """
        Mark offer letter as manually sent (removes from pending list)
        """
        try:
            offer_id = request.data.get('offer_id')
            
            if not offer_id:
                return Response({'error': 'offer_id is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            offer = OfferLetterModel.objects.filter(id=offer_id).first()
            if not offer:
                return Response({'error': 'Offer not found'}, status=status.HTTP_404_NOT_FOUND)
            
            offer.manual_offer_sent = True
            offer.save()
            
            return Response({
                'message': 'Marked as manually processed',
                'offer_id': offer_id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Error marking manual offer: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
# ============================================================================================================
# from django.http import HttpResponse
# from HRM_App.wish_notification import send_email_for_unresolved_complaints
# def test_wishes_view(request):
#     send_email_for_unresolved_complaints()
#     return HttpResponse("Test: Wishes sent (if any match today's date).")
##########################################################################################################

# HRM_App/views.py
from rest_framework import viewsets, mixins
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Company, JobPosting, Skill
from .serializers import CompanySerializer, JobPostingSerializer, SkillSerializer
from .permissions import IsHRManager
from rest_framework.permissions import AllowAny
# ====================================================================
# API Views for HR Management (Requires User Login & 'HRM' Group)
# ====================================================================
class HRManagementBaseViewSet(viewsets.ModelViewSet):
    """Base ViewSet for HR Managers. Enforces HR Manager permission."""
    permission_classes = [IsHRManager]
class CompanyManagementViewSet(HRManagementBaseViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    search_fields = ['name', 'industry']
class SkillManagementViewSet(HRManagementBaseViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    search_fields = ['name']
class JobManagementViewSet(HRManagementBaseViewSet):
    queryset = JobPosting.objects.select_related('company').prefetch_related('skills_required').all()
    serializer_class = JobPostingSerializer
    filterset_fields = ['company', 'job_type', 'location', 'is_active']
    search_fields = ['title', 'job_description', 'company__name']
    ordering_fields = ['posted_on', 'application_deadline', 'salary_min']
    def perform_create(self, serializer):
        # Automatically set the poster to the current logged-in HR user
        serializer.save(posted_by=self.request.user)
# ====================================================================
# Public API Views (Requires API Key for service-to-service auth)
# ====================================================================
class PublicJobListingViewSet(mixins.ListModelMixin,
                              mixins.RetrieveModelMixin,
                              viewsets.GenericViewSet):
    """
    A secure, READ-ONLY endpoint for external services (like the CRM) to fetch
    ACTIVE job postings. Requires a valid API Key in the 'Authorization' header.
    """
    queryset = JobPosting.objects.filter(is_active=True).select_related('company').prefetch_related('skills_required')
    serializer_class = JobPostingSerializer
    permission_classes = [AllowAny] 
    # Allow the CRM to use the same powerful filtering
    filterset_fields = ['company', 'job_type', 'location']
    search_fields = ['title', 'job_description', 'company__name', 'skills_required__name']
    ordering_fields = ['posted_on', 'salary_min']
################## Notification  ##########################
class NotificationListView(APIView):
    def get(self, request, *args, **kwargs):
        login_emp_id = request.GET.get("login_emp_id")
        if not login_emp_id:
            return Response({"error": "login_emp_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_instance = RegistrationModel.objects.get(EmployeeId=login_emp_id)
            notifications = Notification.objects.filter(receiver=user_instance).order_by('-timestamp')
            unread_count = notifications.filter(read_status=False).count()
            serializer = NotificationSerializer(notifications, many=True)
            return Response({'unread_count': unread_count, 'notifications': serializer.data})
        except RegistrationModel.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
class NotificationDeleteView(APIView):
    def delete(self, request, notification_id, *args, **kwargs):
        login_emp_id = request.GET.get("login_emp_id")
        if not login_emp_id:
            return Response({"error": "login_emp_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user_instance = RegistrationModel.objects.get(EmployeeId=login_emp_id)
            notification = Notification.objects.get(pk=notification_id, receiver=user_instance)
            notification.delete()
            return Response({"status": "deleted"}, status=status.HTTP_204_NO_CONTENT)
        except Notification.DoesNotExist:
            return Response({"error": "Notification not found or you do not have permission."}, status=status.HTTP_404_NOT_FOUND)
        except RegistrationModel.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
class MarkNotificationsAsReadView(APIView):
    def post(self, request, *args, **kwargs):
        login_emp_id = request.GET.get("login_emp_id")
        if not login_emp_id:
            return Response({"error": "login_emp_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_instance = RegistrationModel.objects.get(EmployeeId=login_emp_id)
            Notification.objects.filter(receiver=user_instance, read_status=False).update(read_status=True)
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except RegistrationModel.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        
#changes
class ClearAllNotificationsView(APIView):
    """
    Deletes ALL notifications for the logged-in user.
    """
    def post(self, request, *args, **kwargs):
        login_emp_id = request.GET.get("login_emp_id")
        if not login_emp_id:
            return Response({"error": "login_emp_id is required for verification."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_instance = RegistrationModel.objects.get(EmployeeId=login_emp_id)
            
            deleted_count, _ = Notification.objects.filter(receiver=user_instance).delete() # 
            
            return Response(
                {"status": "success", "message": f"Successfully deleted {deleted_count} notifications."},
                status=status.HTTP_200_OK
            )
        except RegistrationModel.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#changes2
class ActivityDashboardAnalyticsView(APIView):
    """
    Provides aggregated activity data for the dashboard based on role and date filters.
    """
    def get(self, request, *args, **kwargs):
        login_emp_id = request.GET.get("login_emp_id")
        filter_type = request.GET.get("filter_type", "this_month") 
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        target_emp_id = request.GET.get("target_emp_id")
        if not login_emp_id:
            return Response({"error": "login_emp_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        # Role-Based Filters 
        if target_emp_id:
             target_employees_q = Q(EmployeeId=target_emp_id) # target employee filter - for admin and hr and recruiter  
        else:
            target_employees_q = Q(pk=current_user.pk) # default filter - for employee 
            if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
                
                if current_user.Designation == 'Admin':
                    target_employees_q = Q() # Q() object means 'no filter' 
                
                else: 
                    team_members_q = Q(Reporting_To=current_user)
                    
                    if current_user.Designation == 'HR':
                        target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk) 
                    
                    elif current_user.Designation == 'Recruiter':
                        target_employees_q = team_members_q | Q(pk=current_user.pk)
        
        
        target_employees = EmployeeDataModel.objects.filter(target_employees_q) # get the target employee objects
        target_activity_instances = NewActivityModel.objects.filter(Employee__in=target_employees) # get their activity instances
        # Date Range
        today = timezone.localdate()
        if filter_type == 'this_month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1]) 
        elif filter_type == 'prev_month':
            prev_month = today - relativedelta(months=1) 
            start_date = prev_month.replace(day=1)
            end_date = prev_month.replace(day=monthrange(prev_month.year, prev_month.month)[1])
        elif filter_type == 'custom' and start_date_str and end_date_str:
            try:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date() 
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            start_date = end_date = today 
        daily_achievements = MonthAchivesListModel.objects.filter(
            Activity_instance__in=target_activity_instances,
            Date__range=(start_date, end_date)
        )
        
        daily_records = NewDailyAchivesModel.objects.filter(
            current_day_activity__in=daily_achievements
        )
        
        requirement_id = request.GET.get("requirement_id")
        if requirement_id:
            daily_records = daily_records.filter(assigned_requirement_id=requirement_id)

        # total_activities = daily_records.count()
        # successful_outcomes_count = daily_records.filter(
        #     Q(interview_status='interview_scheduled') | Q(interview_status='offer') | Q(interview_status='walkin') | Q(client_status='job')
        # ).count()
        # Achieving metrics calculate based on non-staged records
        
        #17/04/2026
        non_staged_records = daily_records.exclude(lead_status='staged')
        total_activities = non_staged_records.count()
        
        successful_outcomes_count = non_staged_records.filter(
            Q(interview_status__in=['joined', 'offer']) | 
            Q(client_status__in=['job', 'consider_to_client', 'converted_to_client'])
        ).count()

        joined_count = non_staged_records.filter(
            Q(interview_status='joined') | Q(client_status='job')
        ).count()

        selected_count = non_staged_records.filter(
            Q(interview_status='offer') | 
            Q(client_status__in=['consider_to_client', 'converted_to_client'])
        ).count()

        screening_count = non_staged_records.filter(
            interview_status='screening'
        ).count()

        scheduled_count = non_staged_records.filter(
            Q(interview_scheduled_date__isnull=False) | Q(interview_status='interview_scheduled')
        ).count()
        
        # Rejected: Prioritize lead_status if set, otherwise use interview_status
        # rejected_count = daily_records.filter(
        #17/04/2026
        rejected_count = non_staged_records.filter(
            Q(lead_status='rejected') | 
            (Q(lead_status__isnull=True) & (Q(interview_status='rejected') | Q(interview_status='Rejected_by_Candidate')))
        ).count()
        
        # Closed: Prioritize lead_status if set, otherwise use client_status
        # closed_count = daily_records.filter(
        #17/04/2026
        closed_count = non_staged_records.filter(
            Q(lead_status='closed') | 
            (Q(lead_status__isnull=True) & Q(client_status='closed'))
        ).count()
        
        # Pending Follow Ups
        # pending_followups_count = FollowUpModel.objects.filter(
        #17/04/2026
        pending_followups_count = FollowUpModel.objects.filter(
            activity_record__in=non_staged_records,
            status='pending'
        ).count()
        
        # Completed Follow Ups
        # completed_followups_count = FollowUpModel.objects.filter(
        #17/04/2026
        completed_followups_count = FollowUpModel.objects.filter(
            activity_record__in=non_staged_records,
            status='completed'
        ).count()
 
        # job_posts_count = daily_records.filter(
        #17/04/2026
        job_posts_count = non_staged_records.filter(
            current_day_activity__Activity_instance__Activity__activity_name='job_posts'
        ).count()
        
        # interview_calls_count = daily_records.filter(
        interview_calls_count = non_staged_records.filter(
            current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
        ).count()
 
        # client_calls_count = daily_records.filter(
        client_calls_count = non_staged_records.filter(
            current_day_activity__Activity_instance__Activity__activity_name='client_calls'
        ).count()
 
        # total_calls_count = daily_records.filter(
        total_calls_count = non_staged_records.filter(
            Q(current_day_activity__Activity_instance__Activity__activity_name='interview_calls') | 
            Q(current_day_activity__Activity_instance__Activity__activity_name='client_calls')
        ).count()

        # Lead Activity Metrics (New Card)
        completed_followups = FollowUpModel.objects.filter(
            activity_record__in=non_staged_records,
            status='completed'
        )
        fup_interview_count = completed_followups.filter(follow_up_type='interview').count()
        fup_client_count = completed_followups.filter(follow_up_type='client').count()

        # lead_total_calls = total_calls_count + completed_followups_count
        lead_total_calls = total_calls_count 
        # lead_interview_calls = interview_calls_count + fup_interview_count
        lead_interview_calls = interview_calls_count
        # lead_client_calls = client_calls_count + fup_client_count
        lead_client_calls = client_calls_count

        # Old Code (Commented for reference):
        # lead_interview_calls = interview_calls_count + fup_interview_count
        # lead_client_calls = client_calls_count + fup_client_count

        lead_fresh_calls = total_calls_count
        lead_followup_calls = completed_followups_count
        #17/4/2026
        # Requirement breakdown (17/04/2026)
        requirement_breakdown = non_staged_records.filter(
            assigned_requirement__isnull=False
        ).values(
            'assigned_requirement',
            'assigned_requirement__requirement__job_title',
            'assigned_requirement__requirement__client__client_name'
        ).annotate(
            total_calls=Count('id'),
            successful_outcomes=Count('id', filter=Q(interview_status__in=['interview_scheduled', 'offer', 'walkin']) | Q(client_status__in=['job', 'consider_to_client', 'converted_to_client']))
        ).order_by('-total_calls')

        # ============================
        # COMPREHENSIVE ANALYTICS (28/05/2026)
        # ============================
        # Base interview-only queryset (includes both staged and active)
        all_interview_records = daily_records.filter(
            current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
        )

        # --- SECTION 1: Profiles Added ---
        profiles_total = all_interview_records.count()
        
        # Bulk Uploaded query filter
        bulk_q = Q(sourcing_channel='bulk_upload') | Q(lead_status='staged')
        profiles_bulk = all_interview_records.filter(bulk_q).count()
        
        # Other profiles (exclude bulk uploads and assigned profiles to keep categories mutually exclusive)
        non_bulk_records = all_interview_records.exclude(bulk_q).exclude(sourcing_channel='assigned')
        
        # Walk-in / Direct: candidate physically walked in
        direct_q = Q(sourcing_channel='direct') | (
            (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                Q(source__icontains='direct') | Q(source__icontains='walkin') | Q(source__icontains='walk-in') | Q(source__icontains='walk in')
            )
        )
        profiles_walkin = non_bulk_records.filter(direct_q).count()
        
        # Website / Platform: from standard external web platforms
        website_q = Q(sourcing_channel='website') | (
            (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                Q(source__icontains='website') | Q(source__icontains='linkedin') |
                Q(source__icontains='naukri') | Q(source__icontains='indeed') |
                Q(source__icontains='portal') | Q(source__icontains='online') |
                Q(source__icontains='api')
            )
        )
        profiles_website = non_bulk_records.filter(website_q).exclude(
            Q(source__icontains='crm') | Q(source__icontains='facebook') | Q(source__icontains='meta') | Q(source__icontains='social')
        ).count()

        # CRM: from CRM external integrations
        crm_q = Q(sourcing_channel='crm') | (
            (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & Q(source__icontains='crm')
        )
        profiles_crm = non_bulk_records.filter(crm_q).count()

        # Facebook / Social Media: from Facebook or other social channels
        facebook_q = Q(sourcing_channel='facebook') | (
            (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                Q(source__icontains='facebook') | Q(source__icontains='meta') | Q(source__icontains='social')
            )
        )
        profiles_facebook = non_bulk_records.filter(facebook_q).count()
        
        # Self Added: employee manually added from Add Activity form
        self_q = Q(sourcing_channel='self_adding') | (
            (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                Q(source__icontains='self') | Q(source__icontains='manual') | Q(source__iexact='')
            )
        )
        profiles_self = non_bulk_records.filter(self_q).exclude(
            Q(source__icontains='crm') | Q(source__icontains='facebook') | Q(source__icontains='meta') | Q(source__icontains='social')
        ).count()
        
        #6/6/26
        # Assigned to recruiter (both sourced daily leads and candidate applications assigned)
        sourced_assigned_count = all_interview_records.filter(sourcing_channel='assigned').count()
        import datetime as datetime_mod
        from .models import ScreeningAssigningModel
        tz = timezone.get_current_timezone()
        start_datetime = timezone.make_aware(datetime_mod.datetime.combine(start_date, datetime_mod.time.min), tz)
        end_datetime = timezone.make_aware(datetime_mod.datetime.combine(end_date, datetime_mod.time.max), tz)
        cand_assigned_count = ScreeningAssigningModel.objects.filter(
            Recruiter__in=target_employees,
            Date_of_assigned__range=(start_datetime, end_datetime)
        ).count()
        profiles_assigned = sourced_assigned_count + cand_assigned_count

        # Base interview-only queryset (non-staged) for Calls and subsequent sections
        interview_records = non_staged_records.filter(
            current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
        )

        # --- SECTION 2: Calls Made ---
        # A call is counted only when interview_status is set (recruiter changed status from fresh state)
        calls_total = lead_total_calls
        # New calls: status is set but no completed follow-ups exist (first-time contact)
        completed_fup_record_ids = FollowUpModel.objects.filter(
            activity_record__in=interview_records,
            status='completed'
        ).values_list('activity_record_id', flat=True)
        calls_new = interview_records.filter(
            interview_status__isnull=False
        ).exclude(interview_status='').exclude(id__in=completed_fup_record_ids).count()
        # Follow-up calls: completed follow-ups of type interview
        calls_followup = FollowUpModel.objects.filter(
            activity_record__in=interview_records,
            status='completed',
            follow_up_type='interview'
        ).count()
        # Sub-breakdown by status
        calls_not_picked = interview_records.filter(interview_status='call_notpicked').count()
        calls_disconnect = interview_records.filter(interview_status='dis_connect').count()
        calls_will_revert = interview_records.filter(interview_status='will_revert_back').count()

        # --- SECTION 3: Interview Pipeline ---
        import datetime as dt
        tz = timezone.get_current_timezone()
        
        today_local = timezone.localdate()
        tomorrow_local = today_local + timedelta(days=1)
        
        today_start = timezone.make_aware(dt.datetime.combine(today_local, dt.time.min), tz)
        today_end = timezone.make_aware(dt.datetime.combine(today_local, dt.time.max), tz)
        
        tomorrow_start = timezone.make_aware(dt.datetime.combine(tomorrow_local, dt.time.min), tz)
        tomorrow_end = timezone.make_aware(dt.datetime.combine(tomorrow_local, dt.time.max), tz)
        
        # Scheduled today
        interview_scheduled_today = interview_records.filter(
            interview_status='interview_scheduled',
            interview_scheduled_date__range=(today_start, today_end)
        ).count()
        # Scheduled tomorrow
        interview_scheduled_tomorrow = interview_records.filter(
            interview_status='interview_scheduled',
            interview_scheduled_date__range=(tomorrow_start, tomorrow_end)
        ).count()
        # Scheduled future (beyond tomorrow)
        interview_scheduled_future = interview_records.filter(
            interview_status='interview_scheduled',
            interview_scheduled_date__gt=tomorrow_end
        ).count()
        # Attended / Conducted (walkin status or walkin date not null)
        interview_attended_total = interview_records.filter(
            Q(interview_walkin_date__isnull=False) | Q(interview_status='walkin')
        ).count()
        interview_conducted = interview_attended_total  # same metric, alias

        #1/6/2026
        # Not Attended: scheduled date has passed, status still "interview_scheduled"
        interview_not_attended = interview_records.filter(
            interview_status='interview_scheduled',
            interview_scheduled_date__lt=today_start
        ).count()

        # Follow-up Pending: not attended (scheduled date passed, status still "interview_scheduled")
        # OR has pending follow-up of type 'interview'
        not_attended_ids = interview_records.filter(
            interview_status='interview_scheduled',
            interview_scheduled_date__lt=today_start
        ).values_list('id', flat=True)
        
        explicit_fup_ids = FollowUpModel.objects.filter(
            activity_record__in=interview_records,
            status='pending',
            follow_up_type='interview'
        ).values_list('activity_record_id', flat=True)
        
        interview_followup_pending = interview_records.filter(
            Q(id__in=not_attended_ids) | Q(id__in=explicit_fup_ids)
        ).distinct().count()


        # --- SECTION 4: Client Requirement Calls ---
        # These are interview_calls records that are tagged to a client requirement
        client_req_records = interview_records.filter(assigned_requirement__isnull=False)
        client_req_total = client_req_records.count()
        
        # Closed requirement leads: status closed or rejected
        client_req_closed = client_req_records.filter(lead_status__in=['closed', 'rejected']).count()

        # Converted / Selected: forwarded to client, offered, or joined (excluding closed/rejected)
        client_req_converted = client_req_records.filter(
            interview_status__in=['to_client', 'offer', 'joined']
        ).exclude(lead_status__in=['closed', 'rejected']).count()

        # Follow-up: lead status is follow_up (excluding closed/rejected and converted)
        client_req_followup = client_req_records.filter(
            lead_status='follow_up'
        ).exclude(lead_status__in=['closed', 'rejected']).exclude(interview_status__in=['to_client', 'offer', 'joined']).count()

        # Prospects: contacted and active (excluding follow_up, closed/rejected)
        client_req_prospect = client_req_records.filter(
            lead_status='active',
            interview_status__in=['call_notpicked', 'dis_connect', 'will_revert_back', 'interview_scheduled', 'walkin']
        ).count()

        # New: lead status is active and interview_status is not set/empty
        client_req_new = client_req_records.filter(
            lead_status='active'
        ).filter(Q(interview_status__isnull=True) | Q(interview_status='')).count()

        # --- SECTION 5: Final Status ---
        final_offered = interview_records.filter(interview_status='offer').count()
        final_joined = interview_records.filter(interview_status='joined').count()
        # Not joined: offered but lead is closed (without joining)
        final_not_joined = interview_records.filter(
            interview_status='offer',
            lead_status='closed'
        ).count()
        # Rejected by us
        final_rejected_by_us = interview_records.filter(
            Q(interview_status='rejected') | Q(rejection_type='emp_rejected')
        ).count()
        # Rejected by candidate
        final_rejected_by_candidate = interview_records.filter(
            Q(interview_status='Rejected_by_Candidate') | Q(rejection_type='candidate_rejected')
        ).count()

        # --- SECTION 6: Pending ---
        pending_followups_new = FollowUpModel.objects.filter(
            activity_record__in=non_staged_records,
            status='pending'
        ).count()
        # Walkins pending: scheduled but date is today or future (not yet happened)
        pending_walkins = interview_records.filter(
            interview_status='interview_scheduled',
            interview_scheduled_date__gte=today_start
        ).count()
        # Profiles yet to contact: interview_calls records with NO status set
        pending_yet_to_contact = interview_records.filter(
            Q(interview_status__isnull=True) | Q(interview_status='')
        ).count()

        dashboard_data = {
            "date_range": {"start": start_date, "end": end_date},
            "metrics": {
                "total_activities_count": total_activities,
                "successful_outcomes_count": successful_outcomes_count,
                "pending_followups_count": pending_followups_count,
                "completed_followups_count": completed_followups_count,
                "rejected_count": rejected_count,
                "closed_count": closed_count,
                "job_posts_count": job_posts_count,
                "total_calls_count": total_calls_count,
                "interview_calls_count": interview_calls_count,
                #17/04/2026
                # "job_post_count": job_posts_count,
                "client_calls_count": client_calls_count,
                # New Lead Activity Metrics
                "lead_total_calls": lead_total_calls,
                "lead_interview_calls": lead_interview_calls,
                "lead_client_calls": lead_client_calls,
                "lead_fresh_calls": lead_fresh_calls,
                "lead_followup_calls": lead_followup_calls,
                # Outcome Breakdown
                "selected_count": selected_count,
                "joined_count": joined_count,
                "screening_count": screening_count,
                "scheduled_count": scheduled_count,

                # ============================
                # COMPREHENSIVE ANALYTICS (28/05/2026)
                # ============================
                # Section 1: Profiles Added
                "profiles_total": profiles_total,
                "profiles_walkin": profiles_walkin,
                "profiles_website": profiles_website,
                "profiles_crm": profiles_crm,
                "profiles_facebook": profiles_facebook,
                "profiles_self": profiles_self,
                "profiles_bulk": profiles_bulk,
                "profiles_assigned": profiles_assigned,

                # Section 2: Calls Made
                "calls_total": calls_total,
                "calls_new": calls_new,
                "calls_followup": calls_followup,
                "calls_not_picked": calls_not_picked,
                "calls_disconnect": calls_disconnect,
                "calls_will_revert": calls_will_revert,

                # Section 3: Interview Pipeline
                "interview_scheduled_today": interview_scheduled_today,
                "interview_scheduled_tomorrow": interview_scheduled_tomorrow,
                "interview_scheduled_future": interview_scheduled_future,
                "interview_attended_total": interview_attended_total,
                "interview_conducted": interview_conducted,
                "interview_not_attended": interview_not_attended,
                "interview_followup_pending": interview_followup_pending,


                # Section 4: Client Requirement Calls
                "client_req_total": client_req_total,
                "client_req_new": client_req_new,
                "client_req_followup": client_req_followup,
                "client_req_prospect": client_req_prospect,
                "client_req_converted": client_req_converted,
                "client_req_closed": client_req_closed,

                # Section 5: Final Status
                "final_offered": final_offered,
                "final_joined": final_joined,
                "final_not_joined": final_not_joined,
                "final_rejected_by_us": final_rejected_by_us,
                "final_rejected_by_candidate": final_rejected_by_candidate,

                # Section 6: Pending
                "pending_followups_new": pending_followups_new,
                "pending_walkins": pending_walkins,
                "pending_yet_to_contact": pending_yet_to_contact,
            },
            "daily_performance": list(daily_records.values('current_day_activity__Date').annotate(count=Count('pk')).order_by('current_day_activity__Date')),
            "status_breakdown": list(daily_records.values('interview_status').annotate(count=Count('interview_status')).order_by()),
            "requirement_breakdown": list(requirement_breakdown) #17/4/2026
        }
        return Response(dashboard_data, status=status.HTTP_200_OK)
class ActivityDashboardDetailsView(APIView):
    """
    Provides the detailed list of records for a specific dashboard metric.
    """
    def get(self, request, *args, **kwargs):
        login_emp_id = request.GET.get("login_emp_id")
        filter_type = request.GET.get("filter_type", "this_month") 
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        
        metric_type = request.GET.get("metric_type")
        target_emp_id = request.GET.get("target_emp_id")
        if not login_emp_id or not metric_type:
            return Response({"error": "login_emp_id and metric_type are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if target_emp_id:
             target_employees_q = Q(EmployeeId=target_emp_id)
        else:
            target_employees_q = Q(pk=current_user.pk)
            if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
                if current_user.Designation == 'Admin':
                    target_employees_q = Q()
                else: 
                    team_members_q = Q(Reporting_To=current_user)
                    if current_user.Designation == 'HR':
                        target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk) 
                    elif current_user.Designation == 'Recruiter':
                        target_employees_q = team_members_q | Q(pk=current_user.pk)
        
        target_employees = EmployeeDataModel.objects.filter(target_employees_q)
        target_activity_instances = NewActivityModel.objects.filter(Employee__in=target_employees)
        today = timezone.localdate()
        if filter_type == 'this_month':
            start_date = today.replace(day=1)
            end_date = today.replace(day=monthrange(today.year, today.month)[1]) 
        elif filter_type == 'prev_month':
            prev_month = today - relativedelta(months=1) 
            start_date = prev_month.replace(day=1)
            end_date = prev_month.replace(day=monthrange(prev_month.year, prev_month.month)[1])
        elif filter_type == 'custom' and start_date_str and end_date_str:
            try:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date() 
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            start_date = end_date = today 
        daily_achievements = MonthAchivesListModel.objects.filter(
            Activity_instance__in=target_activity_instances,
            Date__range=(start_date, end_date)
        )
        
        base_records = NewDailyAchivesModel.objects.filter(
            current_day_activity__in=daily_achievements
        )
        detailed_records = None
        if metric_type == 'total_activities':
            detailed_records = base_records
        elif metric_type == 'total_calls':
            # detailed_records = base_records.filter(Q(current_day_activity__Activity_instance__Activity_id=1) | Q(current_day_activity__Activity_instance__Activity_id=3))
            detailed_records = base_records.filter(Q(current_day_activity__Activity_instance__Activity__activity_name='interview_calls') | Q(current_day_activity__Activity_instance__Activity__activity_name='client_calls'))
        elif metric_type == 'successful_outcomes':
            # detailed_records = base_records.filter(Q(interview_status='interview_scheduled') | Q(interview_status='offer') | Q(interview_status='walkin') | Q(client_status='job'))
            detailed_records = base_records.filter(
                Q(interview_status__in=['interview_scheduled', 'offer', 'walkin']) | 
                Q(client_status__in=['job', 'consider_to_client', 'converted_to_client'])
            )
        elif metric_type == 'follow_ups':
            detailed_records = base_records.filter(Q(interview_status='will_revert_back') | Q(client_status='followup'))
        elif metric_type == 'rejected':
            detailed_records = base_records.filter(
                Q(lead_status='rejected') | 
                (Q(lead_status__isnull=True) & (Q(interview_status='rejected') | Q(interview_status='Rejected_by_Candidate')))
            )
        elif metric_type == 'closed':
            detailed_records = base_records.filter(
                Q(lead_status='closed') | 
                (Q(lead_status__isnull=True) & Q(client_status='closed'))
            )
        elif metric_type == 'rejected_closed':
            detailed_records = base_records.filter(
                Q(interview_status='rejected') | Q(client_status='closed') | Q(interview_status='Rejected_by_Candidate')
            )
        elif metric_type == 'job_posts':
            # detailed_records = base_records.filter(current_day_activity__Activity_instance__Activity_id=2)
            detailed_records = base_records.filter(current_day_activity__Activity_instance__Activity__activity_name='job_posts')
        #changes3
        elif metric_type == 'interview_calls':
            # detailed_records = base_records.filter(current_day_activity__Activity_instance__Activity_id=1)
            detailed_records = base_records.filter(current_day_activity__Activity_instance__Activity__activity_name='interview_calls')
        elif metric_type == 'client_calls':
            #  detailed_records = base_records.filter(current_day_activity__Activity_instance__Activity_id=3)
            detailed_records = base_records.filter(current_day_activity__Activity_instance__Activity__activity_name='client_calls')
        elif metric_type == 'lead_total_calls':
            # Combined fresh calls and follow-up associated records
            fup_records = FollowUpModel.objects.filter(activity_record__in=base_records, status='completed').values_list('activity_record_id', flat=True)
            detailed_records = base_records.filter(
                Q(current_day_activity__Activity_instance__Activity__activity_name__in=['interview_calls', 'client_calls']) |
                Q(id__in=fup_records)
            ).distinct()
        elif metric_type == 'lead_interview_calls':
            fup_records = FollowUpModel.objects.filter(activity_record__in=base_records, status='completed', follow_up_type='interview').values_list('activity_record_id', flat=True)
            detailed_records = base_records.filter(
                Q(current_day_activity__Activity_instance__Activity__activity_name='interview_calls') |
                Q(id__in=fup_records)
            ).distinct()
        elif metric_type == 'lead_client_calls':
            fup_records = FollowUpModel.objects.filter(activity_record__in=base_records, status='completed', follow_up_type='client').values_list('activity_record_id', flat=True)
            detailed_records = base_records.filter(
                Q(current_day_activity__Activity_instance__Activity__activity_name='client_calls') |
                Q(id__in=fup_records)
            ).distinct()
        elif metric_type == 'lead_fresh_calls':
            detailed_records = base_records.filter(Q(current_day_activity__Activity_instance__Activity__activity_name='interview_calls') | Q(current_day_activity__Activity_instance__Activity__activity_name='client_calls'))
        elif metric_type == 'lead_followup_calls':
            fup_records = FollowUpModel.objects.filter(activity_record__in=base_records, status='completed').values_list('activity_record_id', flat=True)
            detailed_records = base_records.filter(id__in=fup_records)
        else:
            return Response({"error": "Invalid metric_type specified."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = NewDailyAchivesModelSerializer(detailed_records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from collections import defaultdict
from django.db.models.functions import Cast
from django.db.models import DateField
from .models import Review, HRFinalStatusModel, NewDailyAchivesModel, CandidateApplicationModel , EmployeeDataModel 
class InterviewActivitySummaryView(APIView):
    
    def get(self, request, employee_id, *args, **kwargs):
        current_month = request.GET.get("current_month")
        current_year = request.GET.get("current_year")
        if not current_month or not current_year:
            return Response({"error": "current_month and current_year are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            current_month = int(current_month)
            current_year = int(current_year)
        except ValueError:
            return Response({"error": "Month and year must be valid integers."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # Base Query: All reviews conducted by the target employee in the month/year
            # NOTE: We assume 'ReviewedBy' links to EmployeeDataModel.
            base_reviews = Review.objects.filter(
                ReviewedBy=employee_id,
                ReviewedDate__month=current_month,
                ReviewedDate__year=current_year
            )
            
            # Use range filters for database compatibility
            start_date = timezone.datetime(current_year, current_month, 1)
            if current_month == 12:
                next_month_date = timezone.datetime(current_year + 1, 1, 1)
            else:
                next_month_date = timezone.datetime(current_year, current_month + 1, 1)
            
            if timezone.is_aware(timezone.now()):
                start_date = timezone.make_aware(start_date)
                next_month_date = timezone.make_aware(next_month_date)

            # Daily Activities (Interview Schedules & Attended/Walkins)
            daily_interview_records = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__EmployeeId=employee_id,
            #     current_day_activity__Activity_instance__Activity__activity_name='interview_calls', # Activity ID for Interview Calls
            #     Created_Date__month=current_month,
            #     Created_Date__year=current_year
            # )

                current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
            ).filter(
                Q(Created_Date__gte=start_date, Created_Date__lt=next_month_date) |
                Q(interview_walkin_date__gte=start_date, interview_walkin_date__lt=next_month_date) |
                Q(interview_scheduled_date__gte=start_date, interview_scheduled_date__lt=next_month_date)
            ).distinct()
            
            interview_schedule_count = daily_interview_records.filter(interview_status='interview_scheduled').count()
            walkins_attended_count = daily_interview_records.filter(Q(interview_status='walkin')).count()
            # Aggregation of Final Statuses
            # NOTE: We assume 'CandidateId' is the Foreign Key field name on the Review model.
            candidate_ids_reviewed = base_reviews.values_list('CandidateId', flat=True).distinct()
            
            final_statuses = HRFinalStatusModel.objects.filter(
                CandidateId__in=candidate_ids_reviewed,
                ReviewedOn__month=current_month,
                ReviewedOn__year=current_year
            )
            outcome_counts = defaultdict(int)
            outcome_counts['screening'] = base_reviews.count()
            
            # Count all final statuses (from your FR choices)
            # NOTE: CandidateApplicationModel.FR must be correctly available in this scope.
            for choice_key, choice_display in CandidateApplicationModel.FR:
                if choice_key != "Pending":
                    count = final_statuses.filter(Final_Result=choice_key).count()
                    
                    # Clean up the key name for frontend display
                    key = choice_key.replace('_by_Candidate', '_by_Candidates').replace('_', ' ').title().replace(' ', '')
                    outcome_counts[key] = count
            
            # Set the simple counts
            outcome_counts['InterviewSchedules'] = interview_schedule_count
            outcome_counts['InterviewAttended'] = walkins_attended_count
            outcome_counts['Reject'] += base_reviews.filter(Screening_Status='rejected').count()
            outcome_counts['RejectedbyCandidates'] += base_reviews.filter(Screening_Status='Rejected_by_Candidate').count()
            outcome_counts['Walkout'] += base_reviews.filter(Screening_Status='walkout').count()
            
            
            # Prepare the Final Response
            final_data = {
                "InterviewSchedules": outcome_counts['InterviewSchedules'],
                "InterviewAttended": outcome_counts['InterviewAttended'],
                "Screening": outcome_counts['screening'],
                "InternalHiring": outcome_counts['InternalHiring'],
                "OnHold": outcome_counts['OnHold'],
                "Reject": outcome_counts['Reject'],
                "RejectedbyCandidates": outcome_counts['RejectedbyCandidates'],
                "Considertoclient": outcome_counts.get('ConsiderToClient', outcome_counts.get('Considertoclient', 0)),
                "Offers": outcome_counts.get('Offered', 0), # 'offered' key in DB
                "OfferRejectedbyCandidates": outcome_counts.get('OfferDidNotAccept', 0),
                "Walkout": outcome_counts['Walkout'],
            }
            return Response(final_data, status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            print("ERROR IN InterviewActivitySummaryView:")
            traceback.print_exc()
            return Response({"error": f"An unhandled error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from collections import defaultdict
from .models import Review, HRFinalStatusModel, NewDailyAchivesModel, CandidateApplicationModel, EmployeeDataModel # <-- CRUCIAL IMPORTS
class EmployeeInterviewDashboardView(APIView):
    """
    Provides a summary of all 11 interview pipeline statuses for a single employee.
    """
    def get(self, request, employee_id, *args, **kwargs):
        try:
            current_month = int(request.GET.get("month"))
            current_year = int(request.GET.get("year"))
        except (ValueError, TypeError):
            return Response({"error": "A valid integer 'month' and 'year' are required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            # NewDailyAchivesModel Counts (Schedules & Walkins)
            # daily_records = NewDailyAchivesModel.objects.filter(
            base_qs = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__EmployeeId=employee_id,
                current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
            )
            
            dashboard_counts = defaultdict(int)
            # dashboard_counts['interview_schedule'] = daily_records.filter(interview_status='interview_scheduled').count()
            # dashboard_counts['walkins'] = daily_records.filter(interview_status='walkin').count()
            # Count based on specific action dates
            dashboard_counts['interview_schedule'] = base_qs.filter(
                interview_status='interview_scheduled',
                interview_scheduled_date__month=current_month,
                interview_scheduled_date__year=current_year
            ).count()
            
            dashboard_counts['walkins'] = base_qs.filter(
                interview_status='walkin',
                interview_walkin_date__month=current_month,
                interview_walkin_date__year=current_year
            ).count()
            
            # Additional Activity Statuses (Leads created/handled this month)
            daily_records = base_qs.filter(
                Created_Date__month=current_month,
                Created_Date__year=current_year
            )
            dashboard_counts['Reject'] += daily_records.filter(interview_status='rejected').count()
            dashboard_counts['consider_to_client'] += daily_records.filter(interview_status='to_client').count()
            dashboard_counts['Rejected_by_Candidate'] += daily_records.filter(interview_status='Rejected_by_Candidate').count()
            dashboard_counts['On_Hold'] += daily_records.filter(interview_status='will_revert_back').count()
            dashboard_counts['Internal_Hiring'] += daily_records.filter(candidate_for='Internal_Hiring').count()
            # Review Model Counts (Base Screenings)
            base_reviews = Review.objects.filter(
                ReviewedBy=employee_id,
                ReviewedDate__month=current_month,
                ReviewedDate__year=current_year
            )
            dashboard_counts['screening'] = base_reviews.count()
            # HRFinalStatusModel Counts (The outcomes)
            candidate_ids_reviewed = base_reviews.values_list('CandidateId', flat=True).distinct()
            final_statuses = HRFinalStatusModel.objects.filter(
                CandidateId__in=candidate_ids_reviewed,
                ReviewedOn__month=current_month,
                ReviewedOn__year=current_year
            )
            
            # Aggregate all Final_Result statuses directly
            status_counts = final_statuses.values('Final_Result').annotate(count=Count('Final_Result'))
            
            # Map aggregated counts to the dashboard_counts dictionary
            for item in status_counts:
                # Use the DB key for initial mapping
                dashboard_counts[item['Final_Result']] = item['count']
            # Fallback Counts (Screening_Status - for early actions)
            dashboard_counts['Reject'] += base_reviews.filter(Screening_Status='rejected').count()
            dashboard_counts['Rejected_by_Candidate'] += base_reviews.filter(Screening_Status='Rejected_by_Candidate').count()
            dashboard_counts['walkout'] += base_reviews.filter(Screening_Status='walkout').count()
            dashboard_counts['consider_to_client'] += base_reviews.filter(Screening_Status='to_client').count()
            # Final Response Formatting
            # Keys must be camelCase or snake_case, but consistent with the frontend types
            final_response = {
                # Direct Activity Logged
                "interview_schedule": dashboard_counts['interview_schedule'],
                "interview_attended": dashboard_counts['walkins'], # Mapped to your frontend name
                "screening": dashboard_counts['screening'],
                
                # Final Outcomes (keys from your model choices)
                "Internal_Hiring": dashboard_counts['Internal_Hiring'],
                "On_Hold": dashboard_counts['On_Hold'],
                "Reject": dashboard_counts['Reject'],
                "Rejected_by_Candidate": dashboard_counts['Rejected_by_Candidate'],
                "consider_to_client": dashboard_counts['consider_to_client'],
                "Offers": dashboard_counts['offered'],
                "Offer_did_not_accept": dashboard_counts['Offer_did_not_accept'],
                "walkout": dashboard_counts['walkout']
            }
            
            return Response(final_response, status=status.HTTP_200_OK)
        except Exception as e:
            # Re-introduce the diagnostic error to catch the next bug
            import traceback
            traceback.print_exc()
            return Response({"error": f"An unhandled error occurred: {type(e).__name__}: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Activity Dashboard Paginated Views (29-01-2026) ---

from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from datetime import datetime, timedelta
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from .models import EmployeeDataModel, NewActivityModel, MonthAchivesListModel, NewDailyAchivesModel, FollowUpModel
from .serializers import NewDailyAchivesModelSerializer, FollowUpSerializer

class ActivityDashboardPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class BaseActivityPaginationView(APIView):
    pagination_class = ActivityDashboardPagination

    def get_target_employees(self, current_user, target_emp_id=None):
        if target_emp_id and target_emp_id not in ['', 'undefined', 'null', 'None']:
            return EmployeeDataModel.objects.filter(EmployeeId=target_emp_id)
        
        if current_user.Designation == 'Admin':
            return EmployeeDataModel.objects.all()
        
        team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
        if current_user.Designation == 'HR':
            return team_members | EmployeeDataModel.objects.filter(Designation='Recruiter') | EmployeeDataModel.objects.filter(pk=current_user.pk)
        elif current_user.Designation == 'Recruiter':
            return team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
        
        return EmployeeDataModel.objects.filter(pk=current_user.pk)

    def filter_by_requirement(self, queryset, requirement_id, is_followup=False):
        if not requirement_id or requirement_id in ['', 'undefined', 'null', 'None']:
            return queryset
        if is_followup:
            return queryset.filter(activity_record__assigned_requirement_id=requirement_id)
        return queryset.filter(assigned_requirement_id=requirement_id)

    def filter_by_date(self, queryset, filter_type, start_date_str, end_date_str):
        today = timezone.localdate()
        if filter_type == 'today':
            return queryset.filter(current_day_activity__Date=today)
        elif filter_type == 'this_week':
            start_of_week = today - timedelta(days=today.weekday())
            return queryset.filter(current_day_activity__Date__range=(start_of_week, today))
        elif filter_type == 'this_month':
            start_date = today.replace(day=1)
            return queryset.filter(current_day_activity__Date__range=(start_date, today))
        elif filter_type == 'prev_month':
            prev_month = today - relativedelta(months=1)
            start_date = prev_month.replace(day=1)
            end_date = prev_month.replace(day=monthrange(prev_month.year, prev_month.month)[1])
            return queryset.filter(current_day_activity__Date__range=(start_date, end_date))
        elif filter_type == 'custom' and start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                return queryset.filter(current_day_activity__Date__range=(start_date, end_date))
            except ValueError:
                pass
        return queryset

    #30-01-2026
    def search_queryset(self, queryset, search_query):
        if not search_query:
            return queryset
        return queryset.filter(
            Q(candidate_name__icontains=search_query) |
            Q(candidate_phone__icontains=search_query) |
            Q(client_name__icontains=search_query) |
            Q(client_phone__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(client_company_name__icontains=search_query) | # New Field
            Q(client_email__icontains=search_query) |    # New Field
            Q(candidate_designation__icontains=search_query) # New Field
        )

    def get_paginated_response(self, queryset, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = NewDailyAchivesModelSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = NewDailyAchivesModelSerializer(queryset, many=True)
        return Response(serializer.data)

class TotalActivitiesView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees
        ).order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

#17/04/2026
class StagedActivitiesView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees,
            lead_status='staged'
        ).order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

class SuccessfulOutcomesView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees
        ).filter(
            Q(interview_status__in=['interview_scheduled', 'offer', 'walkin']) |
            Q(client_status__in=['job', 'consider_to_client', 'converted_to_client'])
        ).order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

class RejectedLeadsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees
        ).filter(
            Q(lead_status='rejected') | 
            (Q(lead_status__isnull=True) & (Q(interview_status='rejected') | Q(interview_status='Rejected_by_Candidate')))
        ).order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

class ClosedLeadsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees
        ).filter(
            Q(lead_status='closed') | 
            (Q(lead_status__isnull=True) & Q(client_status='closed'))
        ).order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

class PendingFollowUpsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        # Using FollowUpModel for more accurate tracking
        queryset = FollowUpModel.objects.filter(
            activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
            status='pending'
        ).select_related('activity_record').order_by('expected_date', 'expected_time')

        queryset = self.filter_by_requirement(queryset, requirement_id, is_followup=True)

        if search:
            queryset = queryset.filter(
                Q(activity_record__candidate_name__icontains=search) |
                Q(activity_record__candidate_phone__icontains=search) |
                Q(activity_record__client_name__icontains=search) |
                Q(activity_record__client_phone__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = FollowUpSerializer(page, many=True)
            # Customizing for current frontend modal expectation while keeping pagination data
            response_data = paginator.get_paginated_response(serializer.data).data
            response_data['pending_followups'] = serializer.data
            return Response(response_data)
            
        serializer = FollowUpSerializer(queryset, many=True)
        return Response({"pending_followups": serializer.data})

class CompletedFollowUpsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        queryset = FollowUpModel.objects.filter(
            activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
            status='completed'
        ).select_related('activity_record').order_by('-expected_date', '-expected_time')

        queryset = self.filter_by_requirement(queryset, requirement_id, is_followup=True)

        if search:
            queryset = queryset.filter(
                Q(activity_record__candidate_name__icontains=search) |
                Q(activity_record__candidate_phone__icontains=search) |
                Q(activity_record__client_name__icontains=search) |
                Q(activity_record__client_phone__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = FollowUpSerializer(page, many=True)
            # Customizing for current frontend modal expectation while keeping pagination data
            response_data = paginator.get_paginated_response(serializer.data).data
            response_data['completed_followups'] = serializer.data
            return Response(response_data)

        serializer = FollowUpSerializer(queryset, many=True)
        return Response({"completed_followups": serializer.data})

class InterviewCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees,
            current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
        ).order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

class ClientCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees,
            current_day_activity__Activity_instance__Activity__activity_name='client_calls'
        # ).order_by('-Created_Date')
        ).exclude(lead_status='staged').order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

#29/04/2026
class LeadTotalCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        fresh_q = Q(current_day_activity__Activity_instance__Employee__in=target_employees,
                   current_day_activity__Activity_instance__Activity__activity_name__in=['interview_calls', 'client_calls'])
        
        fup_records = FollowUpModel.objects.filter(
            activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
            status='completed'
        ).values_list('activity_record_id', flat=True)
        
        # queryset = NewDailyAchivesModel.objects.filter(fresh_q | Q(id__in=fup_records)).distinct().order_by('-Created_Date')
        queryset = NewDailyAchivesModel.objects.filter(fresh_q | Q(id__in=fup_records)).distinct().exclude(lead_status='staged').order_by('-Created_Date')
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class LeadInterviewCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        fresh_q = Q(current_day_activity__Activity_instance__Employee__in=target_employees,
                   current_day_activity__Activity_instance__Activity__activity_name='interview_calls')
        
        fup_records = FollowUpModel.objects.filter(
            activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
            status='completed',
            follow_up_type='interview'
        ).values_list('activity_record_id', flat=True)
        
        # queryset = NewDailyAchivesModel.objects.filter(fresh_q | Q(id__in=fup_records)).distinct().order_by('-Created_Date')
        queryset = NewDailyAchivesModel.objects.filter(fresh_q | Q(id__in=fup_records)).distinct().exclude(lead_status='staged').order_by('-Created_Date')
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class LeadClientCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        fresh_q = Q(current_day_activity__Activity_instance__Employee__in=target_employees,
                   current_day_activity__Activity_instance__Activity__activity_name='client_calls')
        
        fup_records = FollowUpModel.objects.filter(
            activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
            status='completed',
            follow_up_type='client'
        ).values_list('activity_record_id', flat=True)
        
        # queryset = NewDailyAchivesModel.objects.filter(fresh_q | Q(id__in=fup_records)).distinct().order_by('-Created_Date')
        queryset = NewDailyAchivesModel.objects.filter(fresh_q | Q(id__in=fup_records)).distinct().exclude(lead_status='staged').order_by('-Created_Date')
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class LeadFreshCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees,
            current_day_activity__Activity_instance__Activity__activity_name__in=['interview_calls', 'client_calls']
        # ).order_by('-Created_Date')
        ).exclude(lead_status='staged').order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class LeadFollowupCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        queryset = FollowUpModel.objects.filter(
            activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
            status='completed'
        # ).select_related('activity_record').order_by('-expected_date', '-expected_time')
        ).exclude(activity_record__lead_status='staged').select_related('activity_record').order_by('-expected_date', '-expected_time')
        
        queryset = self.filter_by_requirement(queryset, requirement_id, is_followup=True)
        
        # Manual date filtering for FollowUpModel
        today = timezone.localdate()
        if filter_type == 'today':
            queryset = queryset.filter(activity_record__current_day_activity__Date=today)
        elif filter_type == 'this_week':
            s_date = today - timedelta(days=today.weekday())
            queryset = queryset.filter(activity_record__current_day_activity__Date__range=(s_date, today))
        elif filter_type == 'this_month':
            s_date = today.replace(day=1)
            queryset = queryset.filter(activity_record__current_day_activity__Date__range=(s_date, today))
        elif filter_type == 'prev_month':
            prev_month = today - relativedelta(months=1)
            s_date = prev_month.replace(day=1)
            e_date = prev_month.replace(day=monthrange(prev_month.year, prev_month.month)[1])
            queryset = queryset.filter(activity_record__current_day_activity__Date__range=(s_date, e_date))
        elif filter_type == 'custom' and start_date and end_date:
            try:
                s_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                e_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                queryset = queryset.filter(activity_record__current_day_activity__Date__range=(s_date, e_date))
            except ValueError:
                pass

        # For FollowUpModel, search needs to look into the activity_record
        if search:
            queryset = queryset.filter(
                Q(activity_record__candidate_name__icontains=search) |
                Q(activity_record__candidate_phone__icontains=search) |
                Q(activity_record__client_name__icontains=search) |
                Q(activity_record__client_phone__icontains=search)
            )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = FollowUpSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
            
        serializer = FollowUpSerializer(queryset, many=True)
        return Response(serializer.data)

#30/04/2026
class ScreeningCallsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        queryset = NewDailyAchivesModel.objects.filter(
            interview_status='screening',
            current_day_activity__Activity_instance__Employee__in=target_employees
        # ).order_by('-Created_Date')
        ).exclude(lead_status='staged').order_by('-Created_Date')
        
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class ScheduledInterviewsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees
        ).filter(
            Q(interview_scheduled_date__isnull=False) | Q(interview_status='interview_scheduled')
        ).exclude(lead_status='staged').order_by('-Created_Date')
        
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

# 01/05/2026 
class JoinedCandidatesView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        queryset = NewDailyAchivesModel.objects.filter(
            Q(interview_status='joined') | Q(client_status='job'),
            current_day_activity__Activity_instance__Employee__in=target_employees
        # ).order_by('-Created_Date')
        ).exclude(lead_status='staged').order_by('-Created_Date')
        
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class SelectedCandidatesView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        
        queryset = NewDailyAchivesModel.objects.filter(
            Q(interview_status='offer') | 
            Q(client_status__in=['consider_to_client', 'converted_to_client']),
            current_day_activity__Activity_instance__Employee__in=target_employees
        # ).order_by('-Created_Date')
        ).exclude(lead_status='staged').order_by('-Created_Date')
        
        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)
        return self.get_paginated_response(queryset, request)

class JobPostsView(BaseActivityPaginationView):
    def get(self, request):
        login_emp_id = request.GET.get("login_emp_id")
        target_emp_id = request.GET.get("target_emp_id")
        filter_type = request.GET.get("filter_type", "this_month")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        search = request.GET.get("search")
        requirement_id = request.GET.get("requirement_id")

        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        target_employees = self.get_target_employees(current_user, target_emp_id)
        queryset = NewDailyAchivesModel.objects.filter(
            current_day_activity__Activity_instance__Employee__in=target_employees,
            current_day_activity__Activity_instance__Activity__activity_name='job_posts'
        # ).order_by('-Created_Date')
        ).exclude(lead_status='staged').order_by('-Created_Date')

        queryset = self.filter_by_requirement(queryset, requirement_id)
        queryset = self.filter_by_date(queryset, filter_type, start_date, end_date)
        queryset = self.search_queryset(queryset, search)

        return self.get_paginated_response(queryset, request)

class ConvertToFollowUpView(APIView):
    def post(self, request):
        activity_record_id = request.data.get("activity_record_id")
        expected_date = request.data.get("expected_date")
        expected_time = request.data.get("expected_time")
        notes = request.data.get("notes", "")
        login_emp_id = request.data.get("login_emp_id")
        
        if not all([activity_record_id, expected_date, expected_time, login_emp_id]):
            return Response({"error": "activity_record_id, expected_date, expected_time, and login_emp_id are required."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            if activity_record_id and isinstance(activity_record_id, str) and activity_record_id.startswith("c_"):
                candidate_id = int(activity_record_id[2:])
                activity_record = NewDailyAchivesModel.objects.get(url=f"candidate:{candidate_id}")
            else:
                activity_record = NewDailyAchivesModel.objects.get(pk=activity_record_id)
            #17/04/2026
            # If the record is staged (bulk uploaded), we activate it now
            if activity_record.lead_status == 'staged':
                activity_record.lead_status = 'active'
                activity_record.save()
                
                # Recalculate daily achievement now that it's active
                if activity_record.current_day_activity:
                    parent = activity_record.current_day_activity
                    parent.achieved = NewDailyAchivesModel.objects.filter(
                        current_day_activity=parent
                    ).exclude(lead_status='staged').count()  #17/04/2026
                    parent.save()
                    
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except NewDailyAchivesModel.DoesNotExist:
            return Response({"error": "Activity record not found."}, status=status.HTTP_404_NOT_FOUND)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
            
        # Determine follow_up_type
        activity_name = ""
        if activity_record.current_day_activity and activity_record.current_day_activity.Activity_instance and activity_record.current_day_activity.Activity_instance.Activity:
            activity_name = activity_record.current_day_activity.Activity_instance.Activity.activity_name
            
        follow_up_type = 'client' if activity_name == 'client_calls' else 'interview'
            
        followup = FollowUpModel.objects.create(
            activity_record=activity_record,
            follow_up_type=follow_up_type,
            expected_date=expected_date,
            expected_time=expected_time,
            notes=notes,
            status='pending',
            created_by=current_user
        )
        
        # Update original record status
        activity_record.lead_status = 'follow_up'
        activity_record.save()
        
        return Response({
            "message": "Successfully converted to follow-up", 
            "followup_id": followup.id,
            "follow_up": {"id": followup.id}
        }, status=status.HTTP_201_CREATED)

class FollowUpActionView(APIView):
    def post(self, request, followup_id):
        return self.handle_action(request, followup_id)

    def patch(self, request, followup_id):
        return self.handle_action(request, followup_id)

    def handle_action(self, request, followup_id):
        action = request.data.get("action") # 'complete', 'rejected', 'closed', 'call_again'
        remarks = request.data.get("remarks", "")
        notes = request.data.get("notes", "")
        
        try:
            followup = FollowUpModel.objects.get(pk=followup_id)
        except FollowUpModel.DoesNotExist:
            return Response({"error": "Follow-up not found."}, status=status.HTTP_404_NOT_FOUND)
            
        if action == 'complete':
            followup.status = 'completed'
            followup.completed_on = timezone.localtime()
            comment = notes or remarks
            if comment:
                followup.notes = comment
            followup.save()

            if comment:
                activity_record = followup.activity_record
                if followup.follow_up_type == 'interview':
                    activity_record.interview_call_remarks = comment
                elif followup.follow_up_type == 'client':
                    activity_record.client_call_remarks = comment
                activity_record.save()

            return Response({"message": "Follow-up marked as completed"})
        
        elif action == 'call_again':
            expected_date = request.data.get("expected_date")
            expected_time = request.data.get("expected_time")
            
            if not all([expected_date, expected_time]):
                return Response({"error": "expected_date and expected_time are required for scheduling another call."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Mark current as completed
            followup.status = 'completed'
            followup.completed_on = timezone.localtime()
            followup.save()
            
            # Create a new follow-up record
            new_followup = FollowUpModel.objects.create(
                activity_record=followup.activity_record,
                follow_up_type=followup.follow_up_type,
                expected_date=expected_date,
                expected_time=expected_time,
                notes=notes or remarks,
                status='pending',
                created_by=followup.created_by
            )
            return Response({"message": "Another call scheduled", "new_followup_id": new_followup.id})

        elif action in ['rejected', 'closed', 'reject', 'close']:
            effective_action = 'rejected' if action in ['rejected', 'reject'] else 'closed'
            followup.status = 'completed'
            followup.completed_on = timezone.localtime()
            followup.save()
            
            # Update parent record
            activity_record = followup.activity_record
            activity_record.lead_status = effective_action
            
            # Handle rejection type
            if effective_action == 'rejected':
                rejection_type = request.data.get("rejection_type")
                if rejection_type:
                    activity_record.rejection_type = rejection_type
                    
            activity_record.closure_reason = request.data.get("reason") or remarks or notes
            activity_record.save()
            return Response({"message": f"Follow-up handled and lead {effective_action}"})
            
        return Response({"error": "Invalid action."}, status=status.HTTP_400_BAD_REQUEST)

		
# ============================================
# DAS AUTO-LOGIN ENDPOINTS
# ============================================

class GetActiveEmployeesView(APIView):
    """
    Get all active employees from HRM for DAS sync
    Called by DAS to fetch employee data
    """
    permission_classes = []  # Will add proper auth later
    
    def get(self, request):
        try:
            # Get all active employees
            employees = EmployeeInformation.objects.filter(
                employee_status='active'
            )
            
            employee_list = []
            for emp in employees:
                employee_data = {
                    'employee_Id': emp.employee_Id,
                    'full_name': emp.full_name,
                    'email': emp.email,
                    'Employeement_Type': emp.Employeement_Type,
                    'work_location': emp.work_location,
                    'hired_date': emp.hired_date.isoformat() if emp.hired_date else None,
                    'employee_status': emp.employee_status,
                    'date_of_birth': emp.date_of_birth.isoformat() if emp.date_of_birth else None,
                    'phone': emp.mobile,
                }
                
                # Get designation from EmployeeDataModel (Admin/HR/Employee/Recruiter)
                try:
                    emp_data = EmployeeDataModel.objects.filter(employeeProfile=emp).first()
                    if emp_data and emp_data.Designation:
                        employee_data['designation'] = emp_data.Designation
                        # Also include position name if available
                        if emp_data.Position:
                            employee_data['position'] = emp_data.Position.Name
                            # Include department from Position
                            if emp_data.Position.Department:
                                employee_data['department'] = emp_data.Position.Department.Dep_Name
                            else:
                                employee_data['department'] = None
                        else:
                            employee_data['position'] = None
                            employee_data['department'] = None
                    else:
                        employee_data['designation'] = None
                        employee_data['position'] = None
                        employee_data['department'] = None
                except Exception as e:
                    employee_data['designation'] = None
                    employee_data['position'] = None
                    employee_data['department'] = None
                
                employee_list.append(employee_data)
            
            return Response({
                'count': len(employee_list),
                'employees': employee_list
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerateDASCodeView(APIView):
    """
    Generate temporary auth code for DAS auto-login
    Called when user clicks "DAS" button in HRM frontend
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            # Get logged-in user email
            user_email = request.data.get('email')
            
            if not user_email:
                return Response({
                    'error': 'Email is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if employee exists and is active
            employee = EmployeeInformation.objects.filter(
                email=user_email,
                employee_status='active'
            ).first()
            
            if not employee:
                return Response({
                    'error': 'Employee not found or inactive'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Generate auth code and create record
            code = DASAuthCode.generate_code()
            auth_code = DASAuthCode.objects.create(
                code=code,
                user_email=user_email,
                employee_id=employee.employee_Id
            )
            
            # Build DAS redirect URL
            das_url = settings.DAS_URL if hasattr(settings, 'DAS_URL') else 'http://localhost:63105'
            redirect_url = f"{das_url}?code={code}&email={user_email}"
            
            return Response({
                'code': code,
                'redirect_url': redirect_url,
                'expires_in': 300  # 5 minutes
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ValidateDASCodeView(APIView):
    """
    Validate DAS auth code and return employee data
    Called by DAS backend during auto-login process
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            code = request.data.get('code')
            email = request.data.get('email')
            
            if not code or not email:
                return Response({
                    'valid': False,
                    'error': 'Code and email are required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find the auth code
            try:
                auth_code = DASAuthCode.objects.get(code=code, user_email=email)
            except DASAuthCode.DoesNotExist:
                return Response({
                    'valid': False,
                    'error': 'Invalid code or email'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if code is still valid
            if not auth_code.is_valid():
                error_msg = 'Code has already been used' if auth_code.is_used else 'Code has expired'
                return Response({
                    'valid': False,
                    'error': error_msg
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Get employee data
            employee = EmployeeInformation.objects.filter(
                email=email,
                employee_status='active'
            ).first()
            
            if not employee:
                return Response({
                    'valid': False,
                    'error': 'Employee not found or inactive'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get employee data model for designation
            employee_data = EmployeeDataModel.objects.filter(
                EmployeeId=employee.employee_Id
            ).first()
            
            designation = employee_data.Designation if employee_data else None
            
            # Mark code as used
            auth_code.mark_used()
            
            # Return employee data for DAS to create/update user
            return Response({
                'valid': True,
                'employee': {
                    'employee_Id': employee.employee_Id,
                    'full_name': employee.full_name,
                    'email': employee.email,
                    'Employeement_Type': employee.Employeement_Type,
                    'work_location': employee.work_location,
                    'hired_date': employee.hired_date.isoformat() if employee.hired_date else None,
                    'employee_status': employee.employee_status,
                    'date_of_birth': employee.date_of_birth.isoformat() if employee.date_of_birth else None,
                    'phone': employee.mobile,
                    'designation': designation,
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response({
                'valid': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#27/05/2026
class LeadStageListView(APIView):
    """
    Returns the choices from NewDailyAchivesModel.interview_status dynamically.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            choices = NewDailyAchivesModel._meta.get_field('interview_status').choices
            # Map choice keys to display names and styling options
            style_map = {
                "joined": {"text_color": "text-green-600", "border_color": "border-green-500"},
                "offer": {"text_color": "text-blue-600", "border_color": "border-blue-500"},
                "interview_scheduled": {"text_color": "text-purple-600", "border_color": "border-purple-500"},
                "walkin": {"text_color": "text-amber-600", "border_color": "border-amber-500"},
                "rejected": {"text_color": "text-red-600", "border_color": "border-red-500"},
                "Rejected_by_Candidate": {"text_color": "text-red-600", "border_color": "border-red-500"},
                "call_notpicked": {"text_color": "text-slate-600", "border_color": "border-slate-400"},
                "dis_connect": {"text_color": "text-slate-600", "border_color": "border-slate-400"},
                "will_revert_back": {"text_color": "text-indigo-600", "border_color": "border-indigo-500"},
                "to_client": {"text_color": "text-indigo-600", "border_color": "border-indigo-500"},
            }
            
            data = []
            for code, display_name in choices:
                style = style_map.get(code, {"text_color": "text-indigo-600", "border_color": "border-indigo-500"})
                data.append({
                    "code": code,
                    "display_name": display_name,
                    "text_color": style["text_color"],
                    "border_color": style["border_color"]
                })
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)