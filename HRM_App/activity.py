from .imports import *
from django.utils import timezone
from calendar import monthrange
from django.db.models import Sum
import pandas as pd
from django.http import HttpResponse
import csv
from io import StringIO


# .............................................New Activity Functionality......................................

class FeatchCalledCandidateWalkinDetails(APIView):
    def get(self,request):
        unique_identity=request.GET.get("unique_identity")
        called_candidate=NewDailyAchivesModel.objects.filter(Q(candidate_phone=unique_identity) | Q(candidate_email=unique_identity)).first()

        if called_candidate:
            serializer=NewDailyAchivesModelSerializer(called_candidate).data
            serializer["exist_status"]=True
            return Response(serializer,status=status.HTTP_200_OK)
        return Response({"exist_status":False},status=status.HTTP_200_OK)


class AssignServices(APIView):
    def get(self, request,id):
        # Check if client_id is provided
        if not id:
            return Response("client id is required", status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve all services assigned to the specified client
            assigned_services = ClientServicesModel.objects.filter(client_contact__pk=id)
            
            if not assigned_services.exists():
                return Response("No services found for this client", status=status.HTTP_404_NOT_FOUND)
            
            # Serialize the retrieved data
            serializer = ClientServicesSerializer(assigned_services, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Catch any unexpected errors and return the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self, request):
        request_data = request.data.copy()
        client_id = request_data.get("client_contact")
    
        # Check if client_id is provided
        if not client_id:
            return Response("client id is required", status=status.HTTP_400_BAD_REQUEST)
        
        # Check if services are provided and is a list
        services = request_data.get("services_list")
        if not services and not isinstance(services, list):
            return Response("services required in the list form", status=status.HTTP_400_BAD_REQUEST)
        # Try to handle services addition
        try:
            for service in services:
                request_data["service_name"] = service
                
                service_serializer = ClientServicesSerializer(data=request_data)
                
                if service_serializer.is_valid():
                    # Save the instance if the serializer is valid
                    instance = service_serializer.save()
                else:
                    return Response(service_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            return Response("Services added successfully", status=status.HTTP_200_OK)
        
        except Exception as e:
            # Catch any unexpected errors and return the error message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self,request,id):
        if not id:
            return Response("client id is required", status=status.HTTP_400_BAD_REQUEST)
        try:
            # Retrieve all services assigned to the specified client
            assigned_services = ClientServicesModel.objects.filter(pk=id).first()
            
            if not assigned_services:
                return Response("No services found ", status=status.HTTP_404_NOT_FOUND)
            service_serializer=ClientServicesSerializer(assigned_services,data=request.data,partial=True)
            if service_serializer.is_valid():
                service_serializer.save()
                return Response("Services Updated successfully", status=status.HTTP_200_OK)
            else:
                return Response(service_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def delete(self,request,id):

        if not id:
            return Response("client id is required", status=status.HTTP_400_BAD_REQUEST)
        try:
            # Retrieve all services assigned to the specified client
            assigned_services = ClientServicesModel.objects.filter(pk=id).first()
            
            if not assigned_services:
                return Response("No services found ", status=status.HTTP_404_NOT_FOUND)
            assigned_services.delete()
            return Response("Services Deleted successfully", status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
       

# get all activity lists
class DisplayActivityListView(APIView):
    def get(self, request, employee_id, activity_status=None):
        current_month = timezone.localdate().month
        try:
            assigned_activities = NewActivityModel.objects.filter(
                Employee__EmployeeId=employee_id,
                Activity_assigned_Date__month=current_month
            ).values_list('Activity_id', flat=True)
            
            # Determine the queryset for ActivityListModel based on activity_status
            if activity_status == "pending":
                activities = ActivityListModel.objects.exclude(id__in=assigned_activities)
            else:
                activities = ActivityListModel.objects.filter(id__in=assigned_activities)
            
            serializer = ActivityListModelSerializer(activities, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
def month_target_percentage_cal_function(total_achieved,targets):
    if total_achieved==None:
        total_achieved=0
    else:
        total_achieved
    percentage = (total_achieved / targets) * 100 if targets != 0 else 0 

    if percentage < 60:
        color="red"
    elif percentage >= 60 and percentage < 80 :
        color="orange"
    elif percentage >= 80 and percentage < 90 :
        color="yellow"
    else:
        color="green"
    return color
        
class AddNewActivitys(APIView):
    # def get(self,request,login_user):
    #     try:
    #         currentdata=timezone.localdate()
    #         current_month=currentdata.month
    #         current_year=currentdata.year

    #         activity_obj=NewActivityModel.objects.filter(Employee__EmployeeId=login_user,Activity_assigned_Date__month=current_month,Activity_assigned_Date__year=current_year)
    #         Activity_list=[]

    #         for Activity in activity_obj:
    #             employee_daily_achives=MonthAchivesListModel.objects.filter(Activity_instance=Activity.pk)

    #             Monthly_Activity_List=[]
    #             c=0
    #             for daily_achives in employee_daily_achives:
    #                 monthserializer=MonthAchivesListSerializer(daily_achives).data
    #                 per_day_achieves=NewDailyAchivesModel.objects.filter(current_day_activity__pk=daily_achives.pk)
    #                 monthserializer["achieved"]=per_day_achieves.count()
    #                 Monthly_Activity_List.append(monthserializer)
    #                 c+=per_day_achieves.count()

    #             total_achieved_count = employee_daily_achives.aggregate(total=Sum('achieved'))['total'] 
    #             print(total_achieved_count)
    #             activityserializer=NewActivityModelSerializer(Activity).data
    #             activityserializer['MonthAchivesList'] = Monthly_Activity_List
    #             activityserializer['Achived_target'] = c

    #             Activity_list.append(activityserializer)
    #         return Response(Activity_list,status=status.HTTP_200_OK)
    
    #     except Exception as e:
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    def get(self, request, login_user=None,assigned_by=None):
        try:
            cm=request.GET.get("current_month")
            cy=request.GET.get("current_year")
            # Get current date, month, and year
            if cm and cy:
                current_month=cm
                current_year=cy
            else:
                current_date = timezone.localdate()
                current_month = current_date.month
                current_year = current_date.year

            if login_user:
                # Fetch all activities for the given user within the current month and year
                activities = NewActivityModel.objects.filter(
                    Employee__EmployeeId=login_user,
                    Activity_assigned_Date__month=current_month,
                    Activity_assigned_Date__year=current_year
                )
            else:
                # Fetch all activities for the given user within the current month and year
                activities = NewActivityModel.objects.filter(
                    activity_assigned_by__EmployeeId=assigned_by,
                    Activity_assigned_Date__month=current_month,
                    Activity_assigned_Date__year=current_year
                )
                
            # Helper function to process achievements
            def process_daily_achievements(activity_instance,targets):
                daily_achievements = MonthAchivesListModel.objects.filter(Activity_instance=activity_instance)
                total_achieved = 0
                monthly_activity_list = []

                for daily_achievement in daily_achievements:
                    # Serialize daily achievement
                    serialized_data = MonthAchivesListSerializer(daily_achievement).data
                    # Count related per-day achievements
                    per_day_achievements = NewDailyAchivesModel.objects.filter(
                        current_day_activity__pk=daily_achievement.pk
                    )
                    perday_achieved_serializer=NewDailyAchivesModelSerializer(per_day_achievements,many=True)
                    achieved_count = per_day_achievements.count()
                    serialized_data["achieved"] = achieved_count
                    serialized_data["per_day_achievements"]=perday_achieved_serializer.data

                    days=daily_achievements.count()
                    daily_targets=(int(targets)/days)

                    total_achieved_per_day = (daily_achievement.achieved / daily_targets) * 100 if daily_targets != 0 else 0
                    total_achieved_per_day = int(total_achieved_per_day)

                    if daily_targets == 0:
                        serialized_data["status"]="4"
                    elif total_achieved_per_day < 60:
                        serialized_data["status"]="0"
                    elif total_achieved_per_day >= 60 and total_achieved_per_day < 80 :
                        serialized_data["status"]="1"
                    elif total_achieved_per_day >= 80 and total_achieved_per_day < 90 :
                        serialized_data["status"]="2"
                    else:
                        serialized_data["status"]="3"
                    # Add to monthly activity list
                    monthly_activity_list.append(serialized_data)
                    # Update total achieved count
                    total_achieved += achieved_count

                return monthly_activity_list, total_achieved

            # Build activity list with achievements
            activity_list = []
            for activity in activities:
                monthly_activity_list, total_achieved_count = process_daily_achievements(activity.pk,activity.targets)

                # Serialize activity and append achievements
                activity_serializer = NewActivityModelSerializer(activity).data
                activity_serializer['MonthAchivesList'] = monthly_activity_list
                activity_serializer['Achived_target'] = total_achieved_count

                color_status=month_target_percentage_cal_function(total_achieved=total_achieved_count,targets=activity.targets)
                activity_serializer["status"]=color_status

                activity_list.append(activity_serializer)

            return Response(activity_list, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request, login_user):
        try:
            request_data = request.data.copy()
            # Fetching employee and activity details
            employee_id = request_data.get("Employee")
            activity_id = request_data.get("Activity")
            services=request.data.get("service_list")

            if not employee_id or not activity_id:
                return Response(
                    {"error": "Both Employee and Activity fields are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                ) 
            login_emp_obj = EmployeeDataModel.objects.get(EmployeeId=login_user)
            emp_instance = EmployeeDataModel.objects.get(EmployeeId=employee_id)
            activity_instance = ActivityListModel.objects.filter(pk=int(activity_id)).first()

            if services and not isinstance(services, list):
                return Response("services required in the list form", status=status.HTTP_400_BAD_REQUEST)

            if not activity_instance:
                return Response(
                    {"error": f"Activity with ID {activity_id} does not exist."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Update request data
            request_data["Activity"] = activity_instance.pk
            request_data["Employee"] = emp_instance.pk
            request_data["activity_assigned_by"] = login_emp_obj.pk
            request_data["targets"] = request_data.get("targets", 0) or 0  # Default targets to 0 if not provided
            # Serialize and validate
            serializer = NewActivityModelSerializer(data=request_data)
            
            if serializer.is_valid():
                instance = serializer.save()
                # Get the current date and last day of the current month
                current_date = timezone.localdate()
                current_year = current_date.year
                current_month = current_date.month
                
                last_day_of_month = monthrange(current_year, current_month)[1]
                end_date = current_date.replace(day=last_day_of_month)

                # Create MonthAchivesListModel entries
                activity_obj=NewActivityModel.objects.filter(pk=instance.pk).first()
                print(activity_obj)
                
                while current_date <= end_date:
                    MonthAchivesListModel.objects.create(
                        Activity_instance=instance, Date=current_date
                    )
                    current_date += timedelta(days=1)
                    
                # Create notification
                
                # if login_user != employee_id:
                #     sender = RegistrationModel.objects.get(EmployeeId=login_user)
                #     receiver = RegistrationModel.objects.get(EmployeeId=employee_id)
                    # Notification.objects.create(
                    #     sender=sender,
                    #     receiver=receiver,
                    #     message=f"The activity '{instance.Activity.activity_name}' was assigned to you on {timezone.localdate()} by {login_emp_obj.Name}.",
                    # )

                return Response({'status': 'success'}, status=status.HTTP_200_OK)
            print("serializer.errors",serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        except EmployeeDataModel.DoesNotExist as e:
            return Response(
                {"error": f"Employee not found: {str(e)}"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self,request,activity_id):

        activity_obj=NewActivityModel.objects.filter(pk=activity_id).first()
        new_activity_serilaizer=NewActivityModelSerializer(activity_obj,data=request.data,partial=True)
        if new_activity_serilaizer.is_valid():
            instance=new_activity_serilaizer.save()
            return Response("Done",status=status.HTTP_200_OK)
        else:
            return Response(new_activity_serilaizer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request,activity_id):
        
        activity_obj=NewActivityModel.objects.filter(pk=activity_id).first()
        if activity_obj:
            activity_obj.delete()
            return Response("Done",status=status.HTTP_200_OK)
        else:
            return Response("id not exist",status=status.HTTP_400_BAD_REQUEST)

class CreateNewDailyAchievedActivitys(APIView):
    def get(self, request):
        # Extract query parameters
        # interview__date=request.GET.get("interview_date")
        current_month=request.GET.get("current_month")
        current_year=request.GET.get("current_year")
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        date_str = request.GET.get("date")
        activity_list_id = request.GET.get("activity_list_id")
        employee = request.GET.get("login_emp_id")
        activity_status = request.GET.get("activity_status") 
        activity_name = request.GET.get("activity_name")

        # Validate and parse date
        if not date_str:
            particular_day = timezone.localdate()  # Default to today's date
        else:
            try:
                particular_day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
            
            if activity_name:
                new_activity_instance = NewActivityModel.objects.filter(
                    Activity__activity_name=activity_name,
                    Employee__EmployeeId=employee,
                    Activity_assigned_Date__month__range=(start_date.month,end_date.month),
                    Activity_assigned_Date__year__range=(start_date.year,end_date.year)
                )
            else:
                new_activity_instance = NewActivityModel.objects.filter(
                    Activity_id=activity_list_id,
                    Employee__EmployeeId=employee,
                    Activity_assigned_Date__month__range=(start_date.month,end_date.month),
                    Activity_assigned_Date__year__range=(start_date.year,end_date.year)
                )
            
            range_activies=[]
            
            for activity in new_activity_instance:
                month_achieve_instances = MonthAchivesListModel.objects.filter(
                Activity_instance=activity,Date__range=(start_date,end_date))
                if not month_achieve_instances.exists():
                    return Response({"error": "Monthly achievement instance not found."}, status=status.HTTP_400_BAD_REQUEST)
                # Serialize monthly achievement instances
                monthly_achieved_data = MonthAchivesListSerializer(month_achieve_instances, many=True).data
                
                for idx, month_achieve in enumerate(month_achieve_instances):

                    daily_achieved_activities = NewDailyAchivesModel.objects.filter(current_day_activity=month_achieve)
                    
                    daily_achieved_data = NewDailyAchivesModelSerializer(daily_achieved_activities, many=True).data
                    # Add per-day achievements to each monthly instance
                    monthly_achieved_data[idx]["per_day_achievements"] = daily_achieved_data

                range_activies+=monthly_achieved_data
                
            return Response(range_activies, status=status.HTTP_200_OK)
            

        # Extract month and year
        cm = particular_day.month
        cy = particular_day.year

        # Fetch the NewActivityModel instance
        if current_month and current_year:
            if activity_name:
                new_activity_instance = NewActivityModel.objects.filter(
                    Activity__activity_name=activity_name,
                    Employee__EmployeeId=employee,
                    Activity_assigned_Date__month=current_month,
                    Activity_assigned_Date__year=current_year
                ).first()
            else:
                new_activity_instance = NewActivityModel.objects.filter(
                    Activity_id=activity_list_id,
                    Employee__EmployeeId=employee,
                    Activity_assigned_Date__month=current_month,
                    Activity_assigned_Date__year=current_year
                ).first()

        else:
            if activity_name:
                new_activity_instance = NewActivityModel.objects.filter(
                    Activity__activity_name=activity_name,
                    Employee__EmployeeId=employee,
                    Activity_assigned_Date__month=cm,
                    Activity_assigned_Date__year=cy
                ).first()
            else:
                new_activity_instance = NewActivityModel.objects.filter(
                    Activity_id=activity_list_id,
                    Employee__EmployeeId=employee,
                    Activity_assigned_Date__month=cm,
                    Activity_assigned_Date__year=cy
                ).first()

        if not new_activity_instance:
            return Response(
                {"error": f"The activity is not assigned to {employee} on the date of {particular_day}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the MonthAchivesListModel instances
        if not date_str:
            month_achieve_instances = MonthAchivesListModel.objects.filter(
                Activity_instance=new_activity_instance  
            )
        else:
            month_achieve_instances = MonthAchivesListModel.objects.filter(
                Activity_instance=new_activity_instance,
                Date=particular_day
            )

        if not month_achieve_instances.exists():
            return Response({"error": "Monthly achievement instance not found."}, status=status.HTTP_400_BAD_REQUEST)

        # Serialize monthly achievement instances
        monthly_achieved_data = MonthAchivesListSerializer(month_achieve_instances, many=True).data

        # Fetch and serialize daily achievements related to the monthly instances
        for idx, month_achieve in enumerate(month_achieve_instances):

            daily_achieved_activities = NewDailyAchivesModel.objects.filter(
                current_day_activity=month_achieve
            )
            
            daily_achieved_data = NewDailyAchivesModelSerializer(daily_achieved_activities, many=True).data
            # Add per-day achievements to each monthly instance
            monthly_achieved_data[idx]["per_day_achievements"] = daily_achieved_data

        return Response(monthly_achieved_data, status=status.HTTP_200_OK)
    
    def post(self,request):
        try:
            request_data=request.data.copy()
            activity_list_id=int(request_data["activity_list_id"])
            employee = request.GET.get("login_emp_id")
            particular_day = timezone.localdate()

            
            if request_data.get("candidate_for") and request_data.get("candidate_for") == "OJT":
                a= "OJT"
            elif request_data.get("candidate_for") and request_data.get("candidate_for") == "Internal_Hiring":
                a= "Internal_Hiring"
            else:
                a=None
                
            
            request_data["candidate_for"] = a

            print(request_data)
            print("hellooooooooooooooooooooooooooo",type(request_data["candidate_for"]))

            cm = particular_day.month
            cy = particular_day.year

            # Fetch the NewActivityModel instance
            new_activity_instance = NewActivityModel.objects.filter(
                Activity_id=activity_list_id,
                Employee__EmployeeId=employee,
                Activity_assigned_Date__month=cm,
                Activity_assigned_Date__year=cy
            ).first()

            # Filter MonthAchivesListModel based on NewActivityModel instance and date
            month_achieve_instance = MonthAchivesListModel.objects.filter(
                Activity_instance=new_activity_instance,
                Date=particular_day
            ).first()

            request_data["current_day_activity"]=month_achieve_instance.pk
            if request_data["candidate_current_status"] and request_data["candidate_current_status"] == "fresher":
                del request_data["candidate_experience"]

            #changes2
            if new_activity_instance.Activity.activity_name == "client_calls":
                services=request.data.get("service_name", [])
                if services is None:
                    services = []
                print(type(services))
                if not isinstance(services,list):
                    return Response("services are requide are in the list form",status=status.HTTP_400_BAD_REQUEST)
                
    
            if not month_achieve_instance:

                print("id not found")
                return Response("id not found",status=status.HTTP_400_BAD_REQUEST)
            
            monthly_achived_serializer=NewDailyAchivesModelSerializer(data=request_data)

            if monthly_achived_serializer.is_valid():
                instance=monthly_achived_serializer.save()
                try:
                    for service in services:
                        ClientServicesModel.objects.create(client_contact=instance,service_name=service)
                except Exception as e:
                    print(str(e))

                daily_achievements = NewDailyAchivesModel.objects.filter(current_day_activity__pk=month_achieve_instance.pk)
                month_achieve_instance.achieved=daily_achievements.count()
                month_achieve_instance.save()

                # month_achievements = MonthAchivesListModel.objects.filter(Activity_instance=new_activity_instance)
                # achieved_target=new_activity_instance.Achived_target
                # for month_achievement in month_achievements:
                #     achieved_target += month_achievement.achieved
                # new_activity_instance.Achived_target = achieved_target
                # new_activity_instance.save()
                
                return Response(f"{instance.current_day_activity.Activity_instance.Activity.activity_name} Done",status=status.HTTP_200_OK)
            else:
                print(monthly_achived_serializer.errors)
                return Response(monthly_achived_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self,request,id=None):
        achieved_act_id=request.GET.get("achieved_act_id")
        if achieved_act_id:
            daily_achived_obj=NewDailyAchivesModel.objects.filter(pk=achieved_act_id).first()
            if not daily_achived_obj:
                return Response("id not exise",status=status.HTTP_400_BAD_REQUEST)
            daily_achived_activity_serializer=NewDailyAchivesModelSerializer(daily_achived_obj)
            return Response(daily_achived_activity_serializer.data,status=status.HTTP_200_OK)
        
        else:
            
            request_data=request.data.copy()
            if request_data.get("interview_status") and request_data.get("interview_status") == "walkin":
                request_data["interview_walkin_date"]=timezone.localtime()
               
            daily_achived_obj=NewDailyAchivesModel.objects.filter(pk=id).first()
            if not daily_achived_obj:
                return Response("id not exise",status=status.HTTP_400_BAD_REQUEST)
            daily_achived_activity_serializer=NewDailyAchivesModelSerializer(daily_achived_obj,data=request_data,partial=True)
            
            if daily_achived_activity_serializer.is_valid():
                daily_achived_activity_serializer.save()
                return Response("achived activity changed",status=status.HTTP_200_OK)
            else:
                return Response(daily_achived_activity_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self,request,id):
        daily_achived_obj=NewDailyAchivesModel.objects.filter(pk=id).first()
        if not daily_achived_obj:
            return Response("id not exise",status=status.HTTP_400_BAD_REQUEST)
        daily_achived_obj.delete()
        return Response("deleted successfully",status=status.HTTP_200_OK)

            
class DisplayInterviewCallsDate(APIView):
    def get(self, request):

        
        # Extract query parameters
        
        activity_status = request.GET.get("activity_status")
        date_str = request.GET.get("date")
        employee = request.GET.get("login_emp_id")

        # Extract filter values for candidates
        candidate_name = request.GET.get("candidate_name")
        candidate_phone = request.GET.get("candidate_phone")
        candidate_email = request.GET.get("candidate_email")
        candidate_location = request.GET.get("candidate_location")
        candidate_designation = request.GET.get("candidate_designation")
        candidate_current_status = request.GET.get("candidate_current_status")
        candidate_experience = request.GET.get("candidate_experience")

        # Validate and parse the date
        if not date_str:
            particular_day = timezone.localdate()
        else:
            try:
                particular_day = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        Achived_Activity_list = {}

        # Build the query filter for interviews
        interview_filters = {
            "current_day_activity__pk": id,
            "interview_scheduled_date__date": particular_day,
        }
        if candidate_name:
            interview_filters["candidate_name__icontains"] = candidate_name
        if candidate_phone:
            interview_filters["candidate_phone__icontains"] = candidate_phone
        if candidate_email:
            interview_filters["candidate_email__icontains"] = candidate_email
        if candidate_location:
            interview_filters["candidate_location__icontains"] = candidate_location
        if candidate_designation:
            interview_filters["candidate_designation__icontains"] = candidate_designation
        if candidate_current_status:
            interview_filters["candidate_current_status__icontains"] = candidate_current_status
        if candidate_experience:
            try:
                interview_filters["candidate_experience"] = int(candidate_experience)
            except ValueError:
                return Response({"error": "Invalid candidate_experience value."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter interviews
        
        daily_achieved_activities = NewDailyAchivesModel.objects.filter(**interview_filters)
        daily_achieved_interviews_data = NewDailyAchivesModelSerializer(daily_achieved_activities, many=True).data
        Achived_Activity_list.update({"daily_achieved_interviews_data": daily_achieved_interviews_data})

        # Filter walk-ins
        walkin_filters = {
            # "current_day_activity__pk": id,
            "interview_walkin_date__date": particular_day,
        }
        daily_achieved_walkins = NewDailyAchivesModel.objects.filter(**walkin_filters)
        daily_achieved_walkins_data = NewDailyAchivesModelSerializer(daily_achieved_walkins, many=True).data
        Achived_Activity_list.update({"daily_achieved_walkins_data": daily_achieved_walkins_data})

        # Filter screening reviews
        screening_review = Review.objects.filter(ReviewedBy=employee, ReviewedOn__date=particular_day)
        screening_review_serializer = SRS(screening_review, many=True).data
        Achived_Activity_list.update({"daily_achieved_screening_data": screening_review_serializer})

        return Response(Achived_Activity_list, status=status.HTTP_200_OK)


        if activity_status == "interview_schedule":
            daily_achieved_activities = NewDailyAchivesModel.objects.filter(
            current_day_activity__pk=id,interview_scheduled_date__date = particular_day
            )
           
            daily_achieved_interviews_data = NewDailyAchivesModelSerializer(daily_achieved_activities, many=True).data

            # monthly_achieved_data["per_day_achievements"] = daily_achieved_interviews_data

            return Response(daily_achieved_interviews_data,status=status.HTTP_200_OK)
        
        elif activity_status == "walkins":
            daily_achieved_activities = NewDailyAchivesModel.objects.filter(
            current_day_activity__pk=id,interview_walkin_date__date = particular_day
            )
            daily_achieved_walkins_data = NewDailyAchivesModelSerializer(daily_achieved_activities, many=True).data

            # monthly_achieved_data["per_day_achievements"] = daily_achieved_interviews_data

            return Response(daily_achieved_walkins_data,status=status.HTTP_200_OK)
        
        elif activity_status=="screening" and employee:
            screening_review=Review.objects.filter(ReviewedBy=employee,ReviewedOn__date=particular_day)
            screening_review_serializer=SRS(screening_review,many=True).data
            # monthly_achieved_data["per_day_achievements"]=screening_review_serializer.data
            return Response(screening_review_serializer,status=status.HTTP_200_OK)
    

from collections import defaultdict
import calendar
from django.db.models import Q
from django.utils.timezone import localtime

class DisplayEmployeeActivitys(APIView):
    def get(self, request, login_user=None, assigned_by=None):
        try:
            requirement = request.GET.get("requirement")
            activity_status=request.GET.get("activity_status")
            cm = request.GET.get("current_month")
            cy = request.GET.get("current_year")
            cd = request.GET.get("current_date")

            # Determine current month and year
            if cm and cy:
                current_month = int(cm)
                current_year = int(cy)
            else:
                current_date = timezone.localdate()
                current_month = current_date.month
                current_year = current_date.year

            # Get all days in the current month
            _, last_day = calendar.monthrange(current_year, current_month)
            all_dates = [
                timezone.datetime(current_year, current_month, day).date()
                for day in range(1, last_day + 1)
            ]

            # Initialize structures
            interview_schedules = {date: [] for date in all_dates}
            walkins_schedules = {date: [] for date in all_dates}
            screenings = {date: [] for date in all_dates}

            consider_to_client = {date: [] for date in all_dates}
            Internal_Hiring = {date: [] for date in all_dates}
            Reject = {date: [] for date in all_dates}
            Rejected_by_Candidate = {date: [] for date in all_dates}
            On_Hold = {date: [] for date in all_dates}
            Offers= {date: [] for date in all_dates}
            walkout= {date: [] for date in all_dates}
            Offer_did_not_accept = {date: [] for date in all_dates}

            #5/1/2026
            # Fetch activities based on login_user or assigned_by
            if login_user:
                activities = NewActivityModel.objects.filter(
                    # Employee__EmployeeId=login_user,
                    # Activity_assigned_Date__month=current_month,
                    # Activity_assigned_Date__year=current_year
                    Employee__EmployeeId=login_user
                )
            else:
                activities = NewActivityModel.objects.filter(
                    # activity_assigned_by__EmployeeId=assigned_by,
                    # Activity_assigned_Date__month=current_month,
                    # Activity_assigned_Date__year=current_year
                    activity_assigned_by__EmployeeId=assigned_by
                )

            for activity in activities:
                if activity.Activity.activity_name == "interview_calls":
                    daily_achievements = MonthAchivesListModel.objects.filter(Activity_instance=activity)

                    for daily_achievement in daily_achievements:
                        # interview_data = NewDailyAchivesModel.objects.filter(
                        #     current_day_activity=daily_achievement.pk,
                        #     interview_scheduled_date__isnull=False
                        # )

                        # filtered_interview_data = [
                        #     data for data in interview_data
                        #     if localtime(data.interview_scheduled_date).month == current_month
                        #     and localtime(data.interview_scheduled_date).year == current_year
                        # ]

                        # # Add interview data
                        # for interview in filtered_interview_data:
                        #     date_key = timezone.localtime(interview.interview_scheduled_date).date()
                        #     interview_schedules[date_key].append(NewDailyAchivesModelSerializer(interview).data)

                        date_key = daily_achievement.Date
                        
                        # Fetch all daily records for this day
                        all_daily_records = NewDailyAchivesModel.objects.filter(
                            current_day_activity=daily_achievement.pk
                        )

                        for record in all_daily_records:
                            serialized_record = NewDailyAchivesModelSerializer(record).data
                            
                            # Interview Schedules
                            if record.interview_scheduled_date and localtime(record.interview_scheduled_date).month == current_month and localtime(record.interview_scheduled_date).year == current_year:
                                interview_schedules[timezone.localtime(record.interview_scheduled_date).date()].append(serialized_record)
                            
                        # # Walk-in data
                        # walkin_data = NewDailyAchivesModel.objects.filter(
                        #     current_day_activity=daily_achievement.pk,
                        #     interview_walkin_date__isnull=False
                        # )

                        # filtered_walkin_data = [
                        #     data for data in walkin_data
                        #     if localtime(data.interview_walkin_date).month == current_month
                        #     and localtime(data.interview_walkin_date).year == current_year
                        # ]


                        # # Add walk-in data
                        # for walkin in filtered_walkin_data:
                        #     date_key = timezone.localtime(walkin.interview_walkin_date).date()
                        #     walkins_schedules[date_key].append(NewDailyAchivesModelSerializer(walkin).data)
                            # Walk-ins
                            if record.interview_walkin_date and localtime(record.interview_walkin_date).month == current_month and localtime(record.interview_walkin_date).year == current_year:
                                walkins_schedules[timezone.localtime(record.interview_walkin_date).date()].append(serialized_record)

                            # Detailed Statuses (Reject, To Client, etc.)
                            if record.interview_status == "rejected":
                                Reject[date_key].append(serialized_record)
                            elif record.interview_status == "to_client":
                                consider_to_client[date_key].append(serialized_record)
                            elif record.interview_status == "Rejected_by_Candidate":
                                Rejected_by_Candidate[date_key].append(serialized_record)
                            elif record.interview_status == "will_revert_back":
                                On_Hold[date_key].append(serialized_record)
                            
                            if record.candidate_for == "Internal_Hiring":
                                Internal_Hiring[date_key].append(serialized_record)

            # Screening reviews
            screening_review = Review.objects.filter(
                ~Q(screeingreview=None),
                ~Q(screeingreview__isnull=True),
                ReviewedBy=login_user,
                ReviewedDate__month=current_month,
                ReviewedDate__year=current_year
            )

            for screening in screening_review:
                screenings[screening.ReviewedDate].append(ActivityScreeningReviewSerializer(screening).data)
            
            for candidate in screening_review:
               
                # candidate_final_result=HRFinalStatusModel.objects.filter(
                #     CandidateId=candidate.CandidateId,
                #     Final_Result=candidate.CandidateId.Final_Results,
                #     ReviewedOn__month=current_month,
                #     ReviewedOn__year=current_year,
                #     ).first()
                
                candidate_final_result=None
                HR_final_result=HRFinalStatusModel.objects.filter(
                    CandidateId=candidate.CandidateId,
                    Final_Result=candidate.CandidateId.Final_Results)
                
                for final_result in HR_final_result:
                    reviewed_on_local = localtime(final_result.ReviewedOn)  # Convert ReviewedOn to local time
                    if reviewed_on_local.month == current_month and reviewed_on_local.year == current_year:
                        candidate_final_result = final_result
                        break
                
                if candidate_final_result and candidate_final_result.Final_Result == "consider_to_client":
                    print(candidate_final_result.Final_Result)
                    consider_to_client_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    consider_to_client[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(consider_to_client_serilaizer)
                    
                elif candidate.Screening_Status == "to_client":
                    consider_to_client_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    consider_to_client[candidate.ReviewedDate].append(consider_to_client_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Internal_Hiring":
                    internal_hiring_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Internal_Hiring[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(internal_hiring_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Reject":
                    reject_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Reject[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(reject_serilaizer)
                
                elif candidate.Screening_Status == "rejected":
                    print("rejected")
                    reject_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    Reject[candidate.ReviewedDate].append(reject_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Rejected_by_Candidate":
                    rejected_by_candidate_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Rejected_by_Candidate[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(rejected_by_candidate_serilaizer)

                elif candidate.Screening_Status == "Rejected_by_Candidate":
                    rejected_by_candidate_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    Rejected_by_Candidate[candidate.ReviewedDate].append(rejected_by_candidate_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "On_Hold":
                    on_hold_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    On_Hold[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(on_hold_serilaizer)

                elif candidate.CandidateId.Final_Results == "offered":
                    offered_candidate=None
                    offered_candidate_obj= OfferLetterModel.objects.filter(CandidateId=candidate.CandidateId,
                                                                        Letter_sended_status=True)
                    for final_result in offered_candidate_obj:
                        offered_on_local = localtime(final_result.OfferedDate)  # Convert ReviewedOn to local time
                        if offered_on_local.month == current_month and offered_on_local.year == current_year:
                            offered_candidate = final_result
                            break

                    if offered_candidate:
                        offered_serilaizer=CandidateApplicationSerializer(offered_candidate.CandidateId).data
                        Offers[timezone.localtime(offered_candidate.OfferedDate).date()].append(offered_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Offer_did_not_accept":
                    offered_rejections_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Offer_did_not_accept[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(offered_rejections_serilaizer)

                elif candidate.Screening_Status == "walkout":
                    walkout_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    walkout[candidate.ReviewedDate].append(walkout_serilaizer)

                
            # Full month logic
            if requirement == "full_month":
                # Flatten interview schedules
                if activity_status =="interview_schedule":
                    all_interviews = [
                        interview for date_interviews in interview_schedules.values() for interview in date_interviews
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_interviews}]    
                    )

                # Flatten walk-in schedules
                if activity_status =="walkins":
                    all_walkins = [
                        walkin for date_walkins in walkins_schedules.values() for walkin in date_walkins
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_walkins}])

                # Flatten screenings
                if activity_status =="screening":

                    all_screenings = [
                        screen for date_screenings in screenings.values() for screen in date_screenings
                    ]
                    return Response(
                        [{
                                "activity_id": 1,
                                "per_day_achievements": all_screenings}])
                
                if activity_status =="consider_to_client":
                    all_clients = [
                        clients for date_clients in consider_to_client.values() for clients in date_clients
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_clients}])
                
                if activity_status =="Internal_Hiring":
                    all_internal_hiring = [
                        internal_hiring for date_internal_hiring in Internal_Hiring.values() for internal_hiring in date_internal_hiring
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_internal_hiring}])
                
                if activity_status =="Reject":

                    all_Rejects = [
                        Rejections for date_Reject in Reject.values() for Rejections in date_Reject
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Rejects}])


                if activity_status =="Rejected_by_Candidate":

                    all_Rejects_by_Candidate = [
                        candidate_rejection for date_Rejected_by_Candidate in Rejected_by_Candidate.values() for candidate_rejection in date_Rejected_by_Candidate
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Rejects_by_Candidate}])

                if activity_status =="On_Hold":

                    all_On_Hold = [
                        hold_candidates for date_On_Hold in On_Hold.values() for hold_candidates in date_On_Hold
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_On_Hold}])

                if activity_status =="walkout":

                    all_walkout = [
                        walkout_candidates for date_walkout in walkout.values() for walkout_candidates in date_walkout
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_walkout}])
                
                if activity_status =="Offers":

                    all_Offers = [
                        Offers_candidates for date_Offers in Offers.values() for Offers_candidates in date_Offers
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Offers}])
                
                if activity_status == "Offer_did_not_accept":

                    all_Offer_did_not_accept = [
                        Offers_rejects_candidates for date_Offers_rejects in Offer_did_not_accept.values() for Offers_rejects_candidates in date_Offers_rejects
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Offer_did_not_accept}])
                   
            # Default behavior: group by date

            interview_schedules_list = [
                {"activity_id": 1, "date": date, "interview_schedule_data": interview_schedules[date]}
                for date in sorted(interview_schedules.keys())
            ]

            walkins_schedules_list = [
                {"activity_id": 1, "date": date, "walkin_schedule_data": walkins_schedules[date]}
                for date in sorted(walkins_schedules.keys())
            ]

            screening_conducted_list = [
                {"activity_id": 1, "date": date, "screening_conducted_data": screenings[date]}
                for date in sorted(screenings.keys())
            ]

            consider_to_client_list = [
                {"activity_id": 1, "date": date, "consider_to_client_data": consider_to_client[date]}
                for date in sorted(consider_to_client.keys())
            ]

            internal_hiring_list = [
                {"activity_id": 1, "date": date, "internal_hiring_data": Internal_Hiring[date]}
                for date in sorted(Internal_Hiring.keys())
            ]

            Rejections_list = [
                {"activity_id": 1, "date": date, "Rejections_data": Reject[date]}
                for date in sorted(Reject.keys())
            ]

            Rejected_by_Candidate_list = [
                {"activity_id": 1, "date": date, "Rejected_by_Candidate_data": Rejected_by_Candidate[date]}
                for date in sorted(Rejected_by_Candidate.keys())
            ]

            On_Hold_list = [
                {"activity_id": 1, "date": date, "On_Hold_data": On_Hold[date]}
                for date in sorted(On_Hold.keys())
            ]

            offers_list = [
                {"activity_id": 1, "date": date, "offers_data": Offers[date]}
                for date in sorted(Offers.keys())
            ]

            offer_rejected_list = [
                {"activity_id": 1, "date": date, "offers_tejects_data": Offer_did_not_accept[date]}
                for date in sorted(Offer_did_not_accept.keys())
            ]

            walkout_list = [
                {"activity_id": 1, "date": date, "walkouts_data": walkout[date]}
                for date in sorted(walkout.keys())
            ]


            return Response(
                {
                    "interview_schedules": interview_schedules_list,
                    "walkins_schedules": walkins_schedules_list,
                    "screening": screening_conducted_list,
                    "walkout": walkout_list,
                    "Reject" : Rejections_list,
                    "Rejected_by_Candidate": Rejected_by_Candidate_list,
                    "consider_to_client" : consider_to_client_list,
                    "On_Hold": On_Hold_list,
                    "Internal_Hiring" : internal_hiring_list,
                    "Offers" : offers_list,
                    "Offer_did_not_accept":offer_rejected_list,
                },
                status=status.HTTP_200_OK,
            )
        
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

from django.db.models import DateField
from django.db.models.functions import Cast
from django.utils.timezone import make_aware

class CreateInterviewAchievedActivitys(APIView):
    def get(self, request):
        # Extract query parameters
        interview_date = request.GET.get("date")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        activity_status = request.GET.get("activity_status")
        employee = request.GET.get("login_emp_id")
        assigned_by= request.GET.get("assigned_by")
        activity_id=request.GET.get("activity_list_id")

        
        # Validate date parameters
        if not interview_date:
            if start_date and end_date:
                try:
                    start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid date format for 'start_date' or 'end_date'. Use YYYY-MM-DD."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                    {"error": "The 'date' or 'start_date' and 'end_date' query parameters are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                interview_date_parsed = datetime.strptime(interview_date, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format for 'date'. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Initialize activities dictionary

        activities = {
            "screening": defaultdict(list),
            "consider_to_client": defaultdict(list),
            "Internal_Hiring": defaultdict(list),
            "Reject": defaultdict(list),
            "Rejected_by_Candidate": defaultdict(list),
            "On_Hold": defaultdict(list),
            "walkout": defaultdict(list),
            "Offers": defaultdict(list),
            "Offer_did_not_accept": defaultdict(list),
            "interview_schedule": defaultdict(list),
            "walkins": defaultdict(list),
        }


# today          27/02/2025
        perticular_day=[]
        if start_date and end_date:

            perticular_day=activities = NewDailyAchivesModel.objects.filter(
                interview_scheduled_date__gte=start_date,interview_scheduled_date__lte=end_date)
            perticular_day.filter(current_day_activity__Activity_instance__Employee__EmployeeId=employee).exclude(interview_scheduled_date__isnull=True)
        
        if interview_date:
            # Filter records where interview_scheduled_date is not null and matches the given employee
            perticular_day = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__EmployeeId=employee
            ).exclude(
                interview_scheduled_date__isnull=True
            )
        
            # Convert interview_scheduled_date to local time before filtering
            perticular_day_filtered = [
                data for data in perticular_day if localtime(data.interview_scheduled_date).date() == interview_date
            ]

            # Serialize and return response
            a = NewDailyAchivesModelSerializer(perticular_day_filtered, many=True)
            return Response(a.data)
                    
        
        if interview_date:
            perticular_day = NewDailyAchivesModel.objects.exclude(
                    interview_scheduled_date__isnull=True
                ).annotate(
                    # Convert interview_scheduled_date to local time before extracting date
                    local_interview_date=Cast(localtime('interview_scheduled_date'), DateField())
                ).filter(local_interview_date=interview_date)
            
            perticular_day.filter(current_day_activity__Activity_instance__Employee__EmployeeId=employee)
        
        a=NewDailyAchivesModelSerializer(perticular_day,many=True)
        # return Response(a.data)

        

        
        # Filter screening reviews
        screening_review = Review.objects.filter(
            ~Q(screeingreview=None),
            ~Q(screeingreview__isnull=True),
            ReviewedBy=employee,
        )

        # Apply date filters for day-wise or range
        if start_date and end_date:
            screening_review = screening_review.filter(
                ReviewedDate__year__gte=start_date_parsed.year,
                ReviewedDate__month__gte=start_date_parsed.month,
                ReviewedDate__year__lte=end_date_parsed.year,
                ReviewedDate__month__lte=end_date_parsed.month,
            )
        elif interview_date:
            screening_review = screening_review.filter(
                ReviewedDate__month=interview_date_parsed.month,
                ReviewedDate__year=interview_date_parsed.year,
            )

        # Iterate through screening reviews
        for candidate in screening_review:
            candidate_final_result = None

            # Fetch HR Final Result within the filtered range
            HR_final_result = HRFinalStatusModel.objects.filter(
                CandidateId=candidate.CandidateId,
                Final_Result=candidate.CandidateId.Final_Results,
            )
            for final_result in HR_final_result:
                reviewed_on_local = localtime(final_result.ReviewedOn).date()  # Ensure date consistency
                if (start_date and end_date and start_date_parsed <= reviewed_on_local <= end_date_parsed) or \
                (interview_date and reviewed_on_local == interview_date_parsed):
                    candidate_final_result = final_result
                    break
            
            if interview_date and candidate.ReviewedDate == interview_date_parsed:
                # Screening activity for a specific interview date
                screening_serializer = ActivityScreeningReviewSerializer(candidate).data
                activities["screening"][candidate.ReviewedDate].append(screening_serializer)

            elif start_date and end_date and start_date_parsed <= candidate.ReviewedDate <= end_date_parsed:
                # Screening activity for a date range
                screening_serializer = ActivityScreeningReviewSerializer(candidate).data
                activities["screening"][candidate.ReviewedDate].append(screening_serializer)

            # Handle client consideration
            if candidate_final_result and candidate_final_result.Final_Result == "consider_to_client":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["consider_to_client"][localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            if candidate.ReviewedDate == interview_date_parsed:
                if candidate.Screening_Status == "to_client":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["consider_to_client"][candidate.ReviewedDate].append(serializer)
            elif start_date and end_date and start_date_parsed <= candidate.ReviewedDate <= end_date_parsed:
                if candidate.Screening_Status == "to_client":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["consider_to_client"][candidate.ReviewedDate].append(serializer)

            # Handle internal hiring
            if candidate_final_result and candidate_final_result.Final_Result == "Internal_Hiring":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Internal_Hiring"][localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            # Handle rejections
            if candidate_final_result and candidate_final_result.Final_Result == "Reject":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Reject"][localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            if candidate.ReviewedDate == interview_date_parsed:
                if candidate.Screening_Status == "rejected":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["Reject"][candidate.ReviewedDate].append(serializer)

            elif start_date and end_date and start_date_parsed <= candidate.ReviewedDate <= end_date_parsed:
                if candidate.Screening_Status == "rejected":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["Reject"][candidate.ReviewedDate].append(serializer)

            # Handle rejections by candidates
            if candidate_final_result and candidate_final_result.Final_Result == "Rejected_by_Candidate":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Rejected_by_Candidate"][localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            if candidate.ReviewedDate == interview_date_parsed:
                if candidate.Screening_Status == "Rejected_by_Candidate":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["Rejected_by_Candidate"][candidate.ReviewedDate].append(serializer)
            elif start_date and end_date and start_date_parsed <= candidate.ReviewedDate <= end_date_parsed:
                if candidate.Screening_Status == "Rejected_by_Candidate":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["Rejected_by_Candidate"][candidate.ReviewedDate].append(serializer)

            # Handle offers
            if candidate.CandidateId.Final_Results == "offered":
                offered_candidate = None
                offered_candidates = OfferLetterModel.objects.filter(
                    CandidateId=candidate.CandidateId,
                    Letter_sended_status=True,
                )
                for offer in offered_candidates:
                    offered_on_local = localtime(offer.OfferedDate).date()
                    if (start_date and end_date and start_date_parsed <= offered_on_local <= end_date_parsed) or \
                    (interview_date and offered_on_local == interview_date_parsed):
                        offered_candidate = offer
                        break
                if offered_candidate:
                    serializer = CandidateApplicationSerializer(offered_candidate.CandidateId).data
                    activities["Offers"][localtime(offered_candidate.OfferedDate).date()].append(serializer)

            # Handle offer rejections
            if candidate_final_result and candidate_final_result.Final_Result == "Offer_did_not_accept":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Offer_did_not_accept"][localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            # Handle walkouts
            if candidate.ReviewedDate == interview_date_parsed:
                if candidate.Screening_Status == "walkout":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["walkout"][candidate.ReviewedDate].append(serializer)
            elif start_date and end_date and start_date_parsed <= candidate.ReviewedDate <= end_date_parsed:
                if candidate.Screening_Status == "walkout":
                    serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                    activities["walkout"][candidate.ReviewedDate].append(serializer)

        # Prepare the final response based on activity_status
        filtered_data = []

        if activity_status in activities:
            if activity_status in ["interview_schedule", "walkins"]:
                if start_date and end_date:
                    for date in sorted(activities[activity_status].keys()):
                        if start_date_parsed <= date <= end_date_parsed:
                            date_activities = activities[activity_status][date]
                            filtered_data.append({"date": date, "per_day_achievements": date_activities})
                elif interview_date:
                    date_activities = activities[activity_status].get(interview_date_parsed, [])
                    filtered_data.append({"date": interview_date_parsed, "per_day_achievements": date_activities})
            else:
                all_activities = [
                    act for date_activities in activities[activity_status].values() for act in date_activities
                ]
                for date_activities,j in activities[activity_status].values():
                    print(date_activities,j)


                filtered_data.append({"date": "all", "per_day_achievements": all_activities})
        elif activity_status == "all":
            for activity, status_activities in activities.items():
                all_activities = [
                    act for date_activities in status_activities.values() for act in date_activities
                ]
                if all_activities:
                    filtered_data.append({"status": activity, "per_day_achievements": all_activities})
        else:
            return Response(
                {"error": f"Unsupported activity_status: {activity_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(filtered_data, status=status.HTTP_200_OK)

    

class DisplayEmployeeActivitys420(APIView):
    def get(self, request, login_user=None, assigned_by=None):
        try:
            requirement = request.GET.get("requirement")
            activity_status=request.GET.get("activity_status")
            cm = request.GET.get("current_month")
            cy = request.GET.get("current_year")
            cd = request.GET.get("current_date")

            # Determine current month and year
            if cm and cy:
                current_month = int(cm)
                current_year = int(cy)
            else:
                current_date = timezone.localdate()
                current_month = current_date.month
                current_year = current_date.year

            # Get all days in the current month
            _, last_day = calendar.monthrange(current_year, current_month)
            all_dates = [
                timezone.datetime(current_year, current_month, day).date()
                for day in range(1, last_day + 1)
            ]

            # Initialize structures
            interview_schedules = {date: [] for date in all_dates}
            walkins_schedules = {date: [] for date in all_dates}
            screenings = {date: [] for date in all_dates}

            consider_to_client = {date: [] for date in all_dates}
            Internal_Hiring = {date: [] for date in all_dates}
            Reject = {date: [] for date in all_dates}
            Rejected_by_Candidate = {date: [] for date in all_dates}
            On_Hold = {date: [] for date in all_dates}
            Offers= {date: [] for date in all_dates}
            walkout= {date: [] for date in all_dates}
            Offer_did_not_accept = {date: [] for date in all_dates}

            # Fetch activities based on login_user or assigned_by
            if login_user:
                activities = NewActivityModel.objects.filter(
                    Employee__EmployeeId=login_user,
                    Activity_assigned_Date__month=current_month,
                    Activity_assigned_Date__year=current_year
                )
            else:
                activities = NewActivityModel.objects.filter(
                    activity_assigned_by__EmployeeId=assigned_by,
                    Activity_assigned_Date__month=current_month,
                    Activity_assigned_Date__year=current_year
                )

            for activity in activities:
                if activity.Activity.activity_name == "interview_calls":
                    daily_achievements = MonthAchivesListModel.objects.filter(Activity_instance=activity)

                    for daily_achievement in daily_achievements:
                        interview_data = NewDailyAchivesModel.objects.filter(
                            current_day_activity=daily_achievement.pk,
                            interview_scheduled_date__isnull=False
                        )

                        filtered_interview_data = [
                            data for data in interview_data
                            if localtime(data.interview_scheduled_date).month == current_month
                            and localtime(data.interview_scheduled_date).year == current_year
                        ]

                        # Add interview data
                        for interview in filtered_interview_data:
                            date_key = timezone.localtime(interview.interview_scheduled_date).date()
                            interview_schedules[date_key].append(NewDailyAchivesModelSerializer(interview).data)

                        # Walk-in data
                        walkin_data = NewDailyAchivesModel.objects.filter(
                            current_day_activity=daily_achievement.pk,
                            interview_walkin_date__isnull=False
                        )

                        filtered_walkin_data = [
                            data for data in walkin_data
                            if localtime(data.interview_walkin_date).month == current_month
                            and localtime(data.interview_walkin_date).year == current_year
                        ]


                        # Add walk-in data
                        for walkin in filtered_walkin_data:
                            date_key = timezone.localtime(walkin.interview_walkin_date).date()
                            walkins_schedules[date_key].append(NewDailyAchivesModelSerializer(walkin).data)

            # Screening reviews
            screening_review = Review.objects.filter(
                ~Q(screeingreview=None),
                ~Q(screeingreview__isnull=True),
                ReviewedBy=login_user,
                ReviewedDate__month=current_month,
                ReviewedDate__year=current_year
            )

            for screening in screening_review:
                screenings[screening.ReviewedDate].append(ActivityScreeningReviewSerializer(screening).data)
            
            for candidate in screening_review:
               
                # candidate_final_result=HRFinalStatusModel.objects.filter(
                #     CandidateId=candidate.CandidateId,
                #     Final_Result=candidate.CandidateId.Final_Results,
                #     ReviewedOn__month=current_month,
                #     ReviewedOn__year=current_year,
                #     ).first()
                
                candidate_final_result=None
                HR_final_result=HRFinalStatusModel.objects.filter(
                    CandidateId=candidate.CandidateId,
                    Final_Result=candidate.CandidateId.Final_Results)
                
                for final_result in HR_final_result:
                    reviewed_on_local = localtime(final_result.ReviewedOn)  # Convert ReviewedOn to local time
                    if reviewed_on_local.month == current_month and reviewed_on_local.year == current_year:
                        candidate_final_result = final_result
                        break
                
                if candidate_final_result and candidate_final_result.Final_Result == "consider_to_client":
                    print(candidate_final_result.Final_Result)
                    consider_to_client_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    consider_to_client[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(consider_to_client_serilaizer)
                    
                elif candidate.Screening_Status == "to_client":
                    consider_to_client_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    consider_to_client[candidate.ReviewedDate].append(consider_to_client_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Internal_Hiring":
                    internal_hiring_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Internal_Hiring[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(internal_hiring_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Reject":
                    reject_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Reject[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(reject_serilaizer)
                
                elif candidate.Screening_Status == "rejected":
                    print("rejected")
                    reject_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    Reject[candidate.ReviewedDate].append(reject_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Rejected_by_Candidate":
                    rejected_by_candidate_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Rejected_by_Candidate[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(rejected_by_candidate_serilaizer)

                elif candidate.Screening_Status == "Rejected_by_Candidate":
                    rejected_by_candidate_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    Rejected_by_Candidate[candidate.ReviewedDate].append(rejected_by_candidate_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "On_Hold":
                    on_hold_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    On_Hold[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(on_hold_serilaizer)

                elif candidate.CandidateId.Final_Results == "offered":
                    offered_candidate=None
                    offered_candidate_obj= OfferLetterModel.objects.filter(CandidateId=candidate.CandidateId,
                                                                        Letter_sended_status=True)
                    for final_result in offered_candidate_obj:
                        offered_on_local = localtime(final_result.OfferedDate)  # Convert ReviewedOn to local time
                        if offered_on_local.month == current_month and offered_on_local.year == current_year:
                            offered_candidate = final_result
                            break

                    if offered_candidate:
                        offered_serilaizer=CandidateApplicationSerializer(offered_candidate.CandidateId).data
                        Offers[timezone.localtime(offered_candidate.OfferedDate).date()].append(offered_serilaizer)

                elif candidate_final_result and candidate_final_result.Final_Result == "Offer_did_not_accept":
                    offered_rejections_serilaizer=CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                    Offer_did_not_accept[timezone.localtime(candidate_final_result.ReviewedOn).date()].append(offered_rejections_serilaizer)

                elif candidate.Screening_Status == "walkout":
                    walkout_serilaizer=CandidateApplicationSerializer(candidate.CandidateId).data
                    walkout[candidate.ReviewedDate].append(walkout_serilaizer)

                
            # Full month logic
            if requirement == "full_month":
                # Flatten interview schedules
                if activity_status =="interview_schedule":
                    all_interviews = [
                        interview for date_interviews in interview_schedules.values() for interview in date_interviews
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_interviews}]    
                    )

                # Flatten walk-in schedules
                if activity_status =="walkins":
                    all_walkins = [
                        walkin for date_walkins in walkins_schedules.values() for walkin in date_walkins
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_walkins}])

                # Flatten screenings
                if activity_status =="screening":

                    all_screenings = [
                        screen for date_screenings in screenings.values() for screen in date_screenings
                    ]
                    return Response(
                        [{
                                "activity_id": 1,
                                "per_day_achievements": all_screenings}])
                
                if activity_status =="consider_to_client":
                    all_clients = [
                        clients for date_clients in consider_to_client.values() for clients in date_clients
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_clients}])
                
                if activity_status =="Internal_Hiring":
                    all_internal_hiring = [
                        internal_hiring for date_internal_hiring in Internal_Hiring.values() for internal_hiring in date_internal_hiring
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_internal_hiring}])
                
                if activity_status =="Reject":

                    all_Rejects = [
                        Rejections for date_Reject in Reject.values() for Rejections in date_Reject
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Rejects}])


                if activity_status =="Rejected_by_Candidate":

                    all_Rejects_by_Candidate = [
                        candidate_rejection for date_Rejected_by_Candidate in Rejected_by_Candidate.values() for candidate_rejection in date_Rejected_by_Candidate
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Rejects_by_Candidate}])

                if activity_status =="On_Hold":

                    all_On_Hold = [
                        hold_candidates for date_On_Hold in On_Hold.values() for hold_candidates in date_On_Hold
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_On_Hold}])

                if activity_status =="walkout":

                    all_walkout = [
                        walkout_candidates for date_walkout in walkout.values() for walkout_candidates in date_walkout
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_walkout}])
                
                if activity_status =="Offers":

                    all_Offers = [
                        Offers_candidates for date_Offers in Offers.values() for Offers_candidates in date_Offers
                    ]

                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Offers}])
                
                if activity_status == "Offer_did_not_accept":

                    all_Offer_did_not_accept = [
                        Offers_rejects_candidates for date_Offers_rejects in Offer_did_not_accept.values() for Offers_rejects_candidates in date_Offers_rejects
                    ]
                    return Response(
                            [{
                                "activity_id": 1,
                                "per_day_achievements": all_Offer_did_not_accept}])
                   
            # Default behavior: group by date

            interview_schedules_list = [
                {"activity_id": 1, "date": date, "interview_schedule_data": interview_schedules[date]}
                for date in sorted(interview_schedules.keys())
            ]

            walkins_schedules_list = [
                {"activity_id": 1, "date": date, "walkin_schedule_data": walkins_schedules[date]}
                for date in sorted(walkins_schedules.keys())
            ]

            screening_conducted_list = [
                {"activity_id": 1, "date": date, "screening_conducted_data": screenings[date]}
                for date in sorted(screenings.keys())
            ]

            consider_to_client_list = [
                {"activity_id": 1, "date": date, "consider_to_client_data": consider_to_client[date]}
                for date in sorted(consider_to_client.keys())
            ]

            internal_hiring_list = [
                {"activity_id": 1, "date": date, "internal_hiring_data": Internal_Hiring[date]}
                for date in sorted(Internal_Hiring.keys())
            ]

            Rejections_list = [
                {"activity_id": 1, "date": date, "Rejections_data": Reject[date]}
                for date in sorted(Reject.keys())
            ]

            Rejected_by_Candidate_list = [
                {"activity_id": 1, "date": date, "Rejected_by_Candidate_data": Rejected_by_Candidate[date]}
                for date in sorted(Rejected_by_Candidate.keys())
            ]

            On_Hold_list = [
                {"activity_id": 1, "date": date, "On_Hold_data": On_Hold[date]}
                for date in sorted(On_Hold.keys())
            ]

            offers_list = [
                {"activity_id": 1, "date": date, "offers_data": Offers[date]}
                for date in sorted(Offers.keys())
            ]

            offer_rejected_list = [
                {"activity_id": 1, "date": date, "offers_tejects_data": Offer_did_not_accept[date]}
                for date in sorted(Offer_did_not_accept.keys())
            ]

            walkout_list = [
                {"activity_id": 1, "date": date, "walkouts_data": walkout[date]}
                for date in sorted(walkout.keys())
            ]

            return Response(
                {
                    "interview_schedules": interview_schedules_list,
                    "walkins_schedules": walkins_schedules_list,
                    "screening": screening_conducted_list,
                    "walkout": walkout_list,
                    "Reject" : Rejections_list,
                    "Rejected_by_Candidate": Rejected_by_Candidate_list,
                    "consider_to_client" : consider_to_client_list,
                    "On_Hold": On_Hold_list,
                    "Internal_Hiring" : internal_hiring_list,
                    "Offers" : offers_list,
                    "Offer_did_not_accept":offer_rejected_list,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CreateInterviewAchievedActivitys420(APIView):
    def get(self, request):
        # Extract query parameters
        interview_date = request.GET.get("date")
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")
        activity_status = request.GET.get("activity_status")
        employee = request.GET.get("login_emp_id")

        # Validate date parameters
        if not interview_date:
            if start_date and end_date:
                try:
                    start_date_parsed = datetime.strptime(start_date, "%Y-%m-%d").date()
                    end_date_parsed = datetime.strptime(end_date, "%Y-%m-%d").date()
                except ValueError:
                    return Response(
                        {"error": "Invalid date format for 'start_date' or 'end_date'. Use YYYY-MM-DD."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                    {"error": "The 'date' or 'start_date' and 'end_date' query parameters are required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            try:
                interview_date_parsed = datetime.strptime(interview_date, "%Y-%m-%d").date()
            except ValueError:
                return Response(
                    {"error": "Invalid date format for 'date'. Use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Prepare data containers for all activity statuses
        activities = {
            "screening": defaultdict(list),
            "consider_to_client": defaultdict(list),
            "Internal_Hiring": defaultdict(list),
            "Reject": defaultdict(list),
            "Rejected_by_Candidate": defaultdict(list),
            "On_Hold": defaultdict(list),
            "walkout": defaultdict(list),
            "Offers": defaultdict(list),
            "Offer_did_not_accept": defaultdict(list),
            "interview_schedule": defaultdict(list),
            "walkins": defaultdict(list),
        }

        # Filter screening and related activities
        screening_review = Review.objects.filter(
            ~Q(screeingreview=None),
            ~Q(screeingreview__isnull=True),
            ReviewedBy=employee,
        )
        if start_date and end_date:
            screening_review = screening_review.filter(
                ReviewedDate__range=(start_date_parsed, end_date_parsed)
            )
        elif interview_date:
            screening_review = screening_review.filter(
                ReviewedDate=interview_date_parsed
            )

        for candidate in screening_review:
            candidate_final_result = None
            HR_final_result = HRFinalStatusModel.objects.filter(
                CandidateId=candidate.CandidateId,
                Final_Result=candidate.CandidateId.Final_Results,
            )
            for final_result in HR_final_result:
                reviewed_on_local = localtime(final_result.ReviewedOn)
                if (start_date and end_date and start_date_parsed <= reviewed_on_local.date() <= end_date_parsed) or \
                   (interview_date and reviewed_on_local.date() == interview_date_parsed):
                    candidate_final_result = final_result
                    break

            screening_serializer = ActivityScreeningReviewSerializer(candidate).data
            activities["screening"][candidate.ReviewedDate].append(screening_serializer)

            # Handle client consideration
            if candidate_final_result and candidate_final_result.Final_Result == "consider_to_client":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["consider_to_client"][timezone.localtime(candidate_final_result.ReviewedOn).date()].append(serializer)
            elif candidate.Screening_Status == "to_client":
                serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                activities["consider_to_client"][candidate.ReviewedDate].append(serializer)

            # Handle internal hiring
            if candidate_final_result and candidate_final_result.Final_Result == "Internal_Hiring":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Internal_Hiring"][timezone.localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            # Handle rejections
            if candidate_final_result and candidate_final_result.Final_Result == "Reject":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Reject"][timezone.localtime(candidate_final_result.ReviewedOn).date()].append(serializer)
            elif candidate.Screening_Status == "rejected":
                serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                activities["Reject"][candidate.ReviewedDate].append(serializer)

            # Handle rejections by candidates
            if candidate_final_result and candidate_final_result.Final_Result == "Rejected_by_Candidate":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Rejected_by_Candidate"][timezone.localtime(candidate_final_result.ReviewedOn).date()].append(serializer)
            elif candidate.Screening_Status == "Rejected_by_Candidate":
                serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                activities["Rejected_by_Candidate"][candidate.ReviewedDate].append(serializer)

            # Handle offers
            if candidate.CandidateId.Final_Results == "offered":
                offered_candidate = None
                offered_candidates = OfferLetterModel.objects.filter(
                    CandidateId=candidate.CandidateId,
                    Letter_sended_status=True,
                )
                for offer in offered_candidates:
                    offered_on_local = localtime(offer.OfferedDate)
                    if (start_date and end_date and start_date_parsed <= offered_on_local.date() <= end_date_parsed) or \
                       (interview_date and offered_on_local.date() == interview_date_parsed):
                        offered_candidate = offer
                        break
                if offered_candidate:
                    serializer = CandidateApplicationSerializer(offered_candidate.CandidateId).data
                    activities["Offers"][timezone.localtime(offered_candidate.OfferedDate).date()].append(serializer)

            if candidate_final_result and candidate_final_result.Final_Result == "Offer_did_not_accept":
                serializer = CandidateApplicationSerializer(candidate_final_result.CandidateId).data
                activities["Offer_did_not_accept"][timezone.localtime(candidate_final_result.ReviewedOn).date()].append(serializer)

            # Handle walkouts
            if candidate.Screening_Status == "walkout":
                serializer = CandidateApplicationSerializer(candidate.CandidateId).data
                activities["walkout"][candidate.ReviewedDate].append(serializer)

        # Handle interview schedules and walkins
        new_activity_instance = NewActivityModel.objects.filter(
            Employee__EmployeeId=employee,
        ).first()

        if new_activity_instance:
            month_achieve_instances = MonthAchivesListModel.objects.filter(
                Activity_instance=new_activity_instance,
            )

            for month_achieve in month_achieve_instances:
                # Fetch interview schedules
                interview_schedules = NewDailyAchivesModel.objects.filter(
                    interview_scheduled_date__isnull=False,
                    current_day_activity=month_achieve,
                )

                if start_date and end_date:
                    interview_schedules = interview_schedules.filter(
                        interview_scheduled_date__date__range=(start_date_parsed, end_date_parsed)
                    )
                elif interview_date:
                    interview_schedules = interview_schedules.filter(
                        interview_scheduled_date__date=interview_date_parsed
                    )

                for activity in interview_schedules:
                    activity_date = localtime(activity.interview_scheduled_date).date()
                    serializer = NewDailyAchivesModelSerializer(activity).data
                    activities["interview_schedule"][activity_date].append(serializer)

                # Fetch walkins
                walkin_schedules = NewDailyAchivesModel.objects.filter(
                    interview_walkin_date__isnull=False,
                    current_day_activity=month_achieve,
                )

                if start_date and end_date:
                    walkin_schedules = walkin_schedules.filter(
                        interview_walkin_date__date__range=(start_date_parsed, end_date_parsed)
                    )
                elif interview_date:
                    walkin_schedules = walkin_schedules.filter(
                        interview_walkin_date__date=interview_date_parsed
                    )

                for activity in walkin_schedules:
                    activity_date = localtime(activity.interview_walkin_date).date()
                    serializer = NewDailyAchivesModelSerializer(activity).data
                    activities["walkins"][activity_date].append(serializer)

        # Prepare the final response based on activity_status
        filtered_data = []

        if activity_status in activities:
            if activity_status in ["interview_schedule", "walkins"]:
                if start_date and end_date:
                    for date in sorted(activities[activity_status].keys()):
                        if start_date_parsed <= date <= end_date_parsed:
                            date_activities = activities[activity_status][date]
                            filtered_data.append({"date": date, "per_day_achievements": date_activities})
                elif interview_date:
                    date_activities = activities[activity_status].get(interview_date_parsed, [])
                    filtered_data.append({"date": interview_date_parsed, "per_day_achievements": date_activities})
            else:
                all_activities = [
                    act for date_activities in activities[activity_status].values() for act in date_activities
                ]
                filtered_data.append({"date": "all", "per_day_achievements": all_activities})
        elif activity_status == "all":
            for activity, status_activities in activities.items():
                all_activities = [
                    act for date_activities in status_activities.values() for act in date_activities
                ]
                if all_activities:
                    filtered_data.append({"status": activity, "per_day_achievements": all_activities})
        else:
            return Response(
                {"error": f"Unsupported activity_status: {activity_status}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(filtered_data, status=status.HTTP_200_OK)









def HRSub_function(total_achieved,targets):
    if total_achieved==None:
        total_achieved=0
    else:
        total_achieved
    percentage = (total_achieved / targets) * 100 if targets != 0 else 0 

    if percentage < 60:
        color="red"
    elif percentage >= 60 and percentage < 80 :
        color="orange"
    elif percentage >= 80 and percentage < 90 :
        color="yellow"
    else:
        color="green"
    return color

class ActivityView(APIView):
    def get(self,request,login_user):
        try:
            currentdata=timezone.localdate()
            current_month=currentdata.month
            current_year=currentdata.year

            activity_obj=Activity.objects.filter(Employee__EmployeeId=login_user,Activity_added_Date__month=current_month,Activity_added_Date__year=current_year)
            Activity_list=[]

            for emp in activity_obj:
                employee_daily_achives=DailyAchives.objects.filter(Activity_instance=emp.pk)
                total_achieved = employee_daily_achives.aggregate(total=Sum('achieved'))['total']
                serializer=ActivitySerializer(emp).data
                serializer["Total_Achived"]=total_achieved
                targets=serializer["targets"]
                days=DailyAchives.objects.filter(Activity_instance=emp.pk).count()
                daily_targets=int(targets)

                if emp.day_or_month_wise == True:
                    daily_targets=(int(targets)/days)

                daily_achive_list=[]
                for  achived in employee_daily_achives:
                    daily_achive_serializer = DailyAchiveSerializer(achived).data
                    achieved_value = achived.achieved or 0
                    total_achieved_per_day = (achieved_value / daily_targets) * 100 if daily_targets != 0 else 0
                    total_achieved_per_day = int(total_achieved_per_day)

                    if daily_targets == 0:
                        daily_achive_serializer["status"]="4"
                    elif total_achieved_per_day < 60:
                        daily_achive_serializer["status"]="0"
                    elif total_achieved_per_day >= 60 and total_achieved_per_day < 80 :
                        daily_achive_serializer["status"]="1"
                    elif total_achieved_per_day >= 80 and total_achieved_per_day < 90 :
                        daily_achive_serializer["status"]="2"
                    else:
                        daily_achive_serializer["status"]="3"

                    daily_achive_list.append(daily_achive_serializer)

                color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                serializer["status"]=color_status

                serializer.update({"daily_achives":daily_achive_list})
                Activity_list.append(serializer)

            # today = datetime.today()
            # start_date = today.replace(day=1)
            # dates = []   
            # while start_date.month == today.month:
            #     dates.append(start_date.strftime("%Y-%m-%d"))
            #     start_date += timedelta(days=1)  
            # Activity_list.append(dates)
            
            return Response(Activity_list,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response("bad",status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request):
        try:
            request_data=request.data.copy()
            employee_list = request_data["EmployeeId"]
            login_user=request_data["login_user"]
            activity_list=request_data["Activity_data"]
    
            print(activity_list)

            login_emp_obj=EmployeeDataModel.objects.get(EmployeeId=login_user)

            for employee in employee_list:
                emp_instance = EmployeeDataModel.objects.get(EmployeeId=employee)
                activity_instance_list=[]
                for activity in activity_list:
                    if activity["targets"]=='':
                        activity["targets"]=0

                    activity["Employee"]=emp_instance.pk
                    
                    serializer = ActivitySerializer(data=activity)
                    if serializer.is_valid():
                        instance = serializer.save()
                        activity_obj=Activity.objects.get(pk=instance.pk)
                        activity_obj.Assigned_by=login_emp_obj
                        activity_obj.save()
                        activity_instance_list.append(instance.pk)

                        current_date = timezone.localdate()
                        # DailyAchives.objects.create(Activity_instance=instance,Date=current_date)
                        # Get the last day of the current month
                        current_year = current_date.year
                        current_month = current_date.month
                        last_day_of_month = monthrange(current_year, current_month)[1]
                        end_date = current_date.replace(day=last_day_of_month)
                        # Create DailyAchives objects for each day from current date to the end of the month
                        while current_date <= end_date:
                            DailyAchives.objects.create(Activity_instance=instance, Date=current_date)
                            current_date += timedelta(days=1)
                    else:
                        print(serializer.errors)
                        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
                    
                Sender=RegistrationModel.objects.get(EmployeeId=login_user)
                Receiver=RegistrationModel.objects.get(EmployeeId=employee)
                
                activity=Activity.objects.filter(pk__in=activity_instance_list)
                activity_name=[item.Activity_Name for item in activity]

                if login_user==employee:
                    pass
                else:
                    notification=Notification.objects.create(sender=Sender,receiver=Receiver,message=f"The {activity_name} Added to you on {timezone.localdate()} \n By {login_user} .")
            return Response({'status': 'success'}, status=201)
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=500)

    def patch(self, request, instance):
        try:
            activity= Activity.objects.filter(id=instance).first()
            activityserializer = ActivitySerializer(activity, data=request.data, partial=True)
            if activityserializer.is_valid():
                activityserializer.save()
                list_data=[activityserializer.data]
                return Response(list_data, status=status.HTTP_200_OK)
            else:
                return Response(activityserializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request, instance):
        try:
            # Retrieve the instance you want to delete
            activity_instance = Activity.objects.filter(pk=instance).first()
            if not activity_instance:
                return Response("Activity not found", status=status.HTTP_404_NOT_FOUND)
            # Delete the instance
            activity_instance.delete()
            return Response("Activity deleted successfully", status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
class DailyActivityView(APIView):
    def patch(self, request, instance):
        try:
            daily_achive_obj= DailyAchives.objects.filter(pk=instance).first()
            activityserializer = DailyAchiveSerializer(daily_achive_obj, data=request.data, partial=True)
            if activityserializer.is_valid():
                activityserializer.save()
                return Response(activityserializer.data, status=status.HTTP_200_OK)
            else:
                return Response(activityserializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
# ..............Interview Scheduleeee
def sub_function(lu,model,serializer):
    currentdata=timezone.localdate()
    current_month=currentdata.month
    current_year=currentdata.year 
    interview_obj=InterviewSchedule.objects.filter(Employee__EmployeeId=lu,Interview_Added_Date__month=current_month,Interview_Added_Date__year=current_year)
    Activity_list=[]
    for emp in interview_obj:
        employee_daily_achives=model.objects.filter(InterviewSchedule=emp.pk)
        total_achieved = employee_daily_achives.aggregate(total=Sum('achieved'))['total']
        # daily_achive_serializer=serializer(employee_daily_achives,many=True).data
        if model==DailyAchivesInterviewSchedule:
            emp_serializer=ActivityInterviewScheduleSerializer(emp).data
            emp_serializer["Total_Achived"]=total_achieved
            targets=emp_serializer["targets"]
        elif model==WalkIns:
            emp_serializer=ActivityInterviewWalkinsSerializer(emp).data
            emp_serializer["Total_Achived"]=total_achieved
            targets=emp_serializer["Walkins_target"]
        elif model==OfferedPosition:
            emp_serializer=ActivityInterviewOffersSerializer(emp).data
            emp_serializer["Total_Achived"]=total_achieved
            targets=emp_serializer["Offers_target"]
        
        days=model.objects.filter(InterviewSchedule=emp.pk).count()
        # daily_targets=(int(targets)/days)
        daily_targets=int(targets)
        daily_achive_list=[]
        for  achived in employee_daily_achives:
            daily_achive_serializer=serializer(achived).data
            achieved_value = achived.achieved or 0
            total_achieved_per_day = (achieved_value / daily_targets) * 100 if daily_targets != 0 else 0
            total_achieved_per_day = int(total_achieved_per_day)

            if daily_targets == 0:
                daily_achive_serializer["status"]="4"
            elif total_achieved_per_day < 60:
                daily_achive_serializer["status"]="0"
            elif total_achieved_per_day >= 60 and total_achieved_per_day < 80:
                daily_achive_serializer["status"]="1"#Orange
            elif total_achieved_per_day >= 80 and total_achieved_per_day < 90:
                daily_achive_serializer["status"]="2"#Yellow
            else:
                daily_achive_serializer["status"]="3"#Green

            daily_achive_list.append(daily_achive_serializer)
        color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
        emp_serializer["status"]=color_status

        emp_serializer.update({"daily_achives":daily_achive_list})
        Activity_list.append(emp_serializer)
    return Activity_list
   
class InterviewScheduleView(APIView):
    def post(self, request):
        try:
            request_data=request.data.copy()
            employee_list = request_data["EmployeeId"]
            login_user=request_data["login_user"]
            interview_list=request_data["Interview_Scheduled_Data"]

            login_emp_obj=EmployeeDataModel.objects.get(EmployeeId=login_user)
            for employee in employee_list:
                emp_instance = EmployeeDataModel.objects.get(EmployeeId=employee)
                interview_instance_list=[]
                for Position in interview_list:
                    if Position["targets"]=="":
                        Position["targets"]=0
                        Position["Walkins_target"]=0
                        Position["Offers_target"]=0

    
                    Position["Employee"]=emp_instance.pk
                    serializer = ActivityInterviewScheduleSerializer(data=Position)
                    if serializer.is_valid():
                        instance = serializer.save()
                        interview_obj=InterviewSchedule.objects.get(pk=instance.pk)
                        interview_obj.Assigned_by=login_emp_obj
                        interview_obj.save()
                        interview_instance_list.append(instance.pk)
                        current_date = timezone.localdate()
                        # Get the last day of the current month
                        current_year = current_date.year
                        current_month = current_date.month
                        last_day_of_month = monthrange(current_year, current_month)[1]
                        
                        end_date = current_date.replace(day=last_day_of_month)
                        # Create DailyAchives objects for each day from current date to the end of the month
                        while current_date <= end_date:
                            DailyAchivesInterviewSchedule.objects.create(InterviewSchedule=instance, Date=current_date)
                            WalkIns.objects.create(InterviewSchedule=instance, Date=current_date)
                            OfferedPosition.objects.create(InterviewSchedule=instance, Date=current_date)
                            current_date += timedelta(days=1)
                    else:
                        print(serializer.errors)
                        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
                    
                Sender=RegistrationModel.objects.get(EmployeeId=login_user)
                Receiver=RegistrationModel.objects.get(EmployeeId=employee)
                
                interview=InterviewSchedule.objects.filter(pk__in=interview_instance_list)
                interview_name=[item.position  for item in interview]

                if login_user==employee:
                    pass
                else:
                    notification=Notification.objects.create(sender=Sender,receiver=Receiver,message=f"The Interview Schedule Position {interview_name} Added to you on {timezone.localdate()} \n By {login_user} .")
            return Response({'status': 'success'}, status=201)
        except Exception as e:
            print(e)
            return Response({'error': str(e)}, status=500)
    
    def patch(self, request, instance):
        try:
            # Retrieve the instance you want to update
            Interview_instance = InterviewSchedule.objects.filter(id=instance).first()
            if not Interview_instance:
                return Response("Interview Schedule not found", status=status.HTTP_404_NOT_FOUND)
            # Serialize the updated data
            serializer = ActivityInterviewScheduleSerializer(Interview_instance, data=request.data, partial=True)
            if serializer.is_valid():
                # Update the instance with the serialized data
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
class InterviewScheduledAchived(APIView):
    def get(self,request,login_user):
        try:
            model=DailyAchivesInterviewSchedule
            serializer=DailyAchiveInterviewScheduleSerializer
            interview_schedule_list=sub_function(lu=login_user,model=model,serializer=serializer)

            # print(interview_schedule_list)
            return Response(interview_schedule_list,status=status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

    def patch(self,request,instance):
        try:
            daily_achive_obj= DailyAchivesInterviewSchedule.objects.filter(pk=instance).first()
            activityserializer = DailyAchiveInterviewScheduleSerializer(daily_achive_obj, data=request.data, partial=True)
            if activityserializer.is_valid():
                activityserializer.save()
                return Response(activityserializer.data, status=status.HTTP_200_OK)
            else:
                return Response(activityserializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST) 
            
        
class WalkinView(APIView):
    def get(self,request,login_user):
        try:
            model=WalkIns
            serializer=WalkInSerializer
            Walkins_list=sub_function(lu=login_user,model=model,serializer=serializer)
            return Response(Walkins_list,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response("bad",status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request, instance):
        try:
            WalkIn_instance = WalkIns.objects.filter(id=instance).first()
            if not WalkIn_instance:
                return Response("WalkIn not found", status=status.HTTP_404_NOT_FOUND)
            serializer = WalkInSerializer(WalkIn_instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

class OfferedView(APIView):
    def get(self,request,login_user):
        try:
            model=OfferedPosition
            serializer=OffredScheduleSerializer
            Offers_list=sub_function(lu=login_user,model=model,serializer=serializer)
            # print(Offers_list)
            return Response(Offers_list,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response("bad",status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request, instance):
        try:
            Offered_instance = OfferedPosition.objects.filter(id=instance).first()
            if not Offered_instance:
                return Response("WalkIn not found", status=status.HTTP_404_NOT_FOUND)
            serializer = OffredScheduleSerializer(Offered_instance, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        

# in rm ActivityListDisplay
from django.utils.dateparse import parse_date
class ActivityListDisplay(APIView):
    def get(self,request,filter_value=None,login_user=None,activity=None,employee=None):
        try:
            if isinstance(filter_value, str):
                filter_value = parse_date(filter_value + "-01")  # Add a day to parse it correctly

            if filter_value and employee:
                year = filter_value.year
                month = filter_value.month

                employee=EmployeeDataModel.objects.get(EmployeeId=employee)
                activity_object = Activity.objects.filter(Activity_added_Date__year=year, Activity_added_Date__month=month,Employee=employee.pk)
                activity_list=[]

                for activity in activity_object:
                    activity_object_serializer=ActivitySerializer(activity).data
                    daily_achives=DailyAchives.objects.filter(Activity_instance=activity.pk)
                    total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                    # daily_achives_serializer=DailyAchiveSerializer(daily_achives,many=True).data
                    activity_object_serializer["Total_Achived"]=total_achieved
                    targets=activity_object_serializer["targets"]

# /////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

                    days=DailyAchives.objects.filter(Activity_instance=activity.pk).count()
                    # daily_targets=(int(targets)/days)
                    daily_targets=int(targets)
                    if activity.day_or_month_wise == True:
                        daily_targets=(int(targets)/days)
                    daily_achive_list=[]
                    for  achived in daily_achives:
                        daily_achive_serializer = DailyAchiveSerializer(achived).data
                        achieved_value = achived.achieved or 0
                        total_achieved_per_day = (achieved_value / daily_targets) * 100 if daily_targets != 0 else 0
                        total_achieved_per_day = int(total_achieved_per_day)

                        if total_achieved_per_day < 60:
                            daily_achive_serializer["status"]="0"
                        elif total_achieved_per_day >= 60 and total_achieved_per_day < 80 :
                            daily_achive_serializer["status"]="1"
                        elif total_achieved_per_day >= 80 and total_achieved_per_day < 90 :
                            daily_achive_serializer["status"]="2"
                        else:
                            daily_achive_serializer["status"]="3"

                        daily_achive_list.append(daily_achive_serializer)
                        # print(daily_achive_list)

# ////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

                    color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                    activity_object_serializer["status"]=color_status

                    # activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                    activity_object_serializer.update({"daily_achives":daily_achive_list})
                    activity_list.append(activity_object_serializer)

                return Response(activity_list,status=status.HTTP_200_OK)
            
            elif activity:
                activity_object=Activity.objects.filter(Activity_Name=activity)
                activity_list=[]
                for activity in activity_object:
                    activity_object_serializer=ActivitySerializer(activity).data
                    daily_achives=DailyAchives.objects.filter(Activity_instance=activity.pk)
                    total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                    daily_achives_serializer=DailyAchiveSerializer(daily_achives,many=True).data
                    activity_object_serializer["Total_Achived"]=total_achieved
                    targets=activity_object_serializer["targets"]

                    color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                    activity_object_serializer["status"]=color_status

                    activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                    activity_list.append(activity_object_serializer)
                return Response(activity_list,status=status.HTTP_200_OK)
            elif employee:
                employee=EmployeeDataModel.objects.get(EmployeeId=employee)
                activity_object=Activity.objects.filter(Employee=employee.pk)
                activity_list=[]
                for activity in activity_object:
                    activity_object_serializer=ActivitySerializer(activity).data
                    daily_achives=DailyAchives.objects.filter(Activity_instance=activity.pk)
                    total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                    daily_achives_serializer=DailyAchiveSerializer(daily_achives,many=True).data
                    activity_object_serializer["Total_Achived"]=total_achieved

                    targets=activity_object_serializer["targets"]

                    color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                    activity_object_serializer["status"]=color_status

                    activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                    activity_list.append(activity_object_serializer)
                return Response(activity_list,status=status.HTTP_200_OK)
            else:
                activity_object=Activity.objects.filter(Assigned_by__EmployeeId=login_user)
                activity_list=[]

                for activity in activity_object:
                    activity_object_serializer=ActivitySerializer(activity).data
                    daily_achives=DailyAchives.objects.filter(Activity_instance=activity.pk)
                    total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                    daily_achives_serializer=DailyAchiveSerializer(daily_achives,many=True).data
                    activity_object_serializer["Total_Achived"]=total_achieved
                    targets=activity_object_serializer["targets"]

                    color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                    activity_object_serializer["status"]=color_status

                    activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                    activity_list.append(activity_object_serializer)
                return Response(activity_list,status=status.HTTP_200_OK)
            
        except Exception as e:
            print(e)
            return Response("bad",status=status.HTTP_400_BAD_REQUEST)



def get_activity_data(activity, model, serializer):

    if model == DailyAchivesInterviewSchedule :
        activity_serializer = ActivityInterviewScheduleSerializer(activity).data
        daily_achives = model.objects.filter(InterviewSchedule=activity.pk)
        total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
        # emp_daily_achives_serializer = serializer(daily_achives, many=True).data

        activity_serializer["Total_Achived"] = total_achieved
        targets = activity_serializer.get("targets", 0)

        daily_achive_list=[]
        daily_targets=int(targets)
        for  achived in daily_achives:
            daily_achives_serializer = serializer(achived).data
            # daily_achive_serializer=DailyAchiveInterviewScheduleSerializer(achived).data
            achieved_value = achived.achieved or 0
            total_achieved_per_day = (achieved_value / daily_targets) * 100 if daily_targets != 0 else 0
            total_achieved_per_day = int(total_achieved_per_day)

            if daily_targets == 0:
                daily_achives_serializer["status"]="4"
            elif total_achieved_per_day < 60:
                daily_achives_serializer["status"]="0"
            elif total_achieved_per_day >= 60 and total_achieved_per_day < 80:
                daily_achives_serializer["status"]="1"#Orange
            elif total_achieved_per_day >= 80 and total_achieved_per_day < 90:
                daily_achives_serializer["status"]="2"#Yellow
            else:
                daily_achives_serializer["status"]="3"#Green

            daily_achive_list.append(daily_achives_serializer)

        activity_serializer["status"] = HRSub_function(total_achieved, targets)
        activity_serializer.update({"daily_achives": daily_achive_list})

    elif model == OfferedPosition :
        activity_serializer =  ActivityInterviewOffersSerializer(activity).data

        daily_achives = model.objects.filter(InterviewSchedule=activity.pk)
        total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
        # emp_daily_achives_serializer = serializer(daily_achives, many=True).data

        activity_serializer["Total_Achived"] = total_achieved
        targets = activity_serializer.get("Offers_target", 0)

        daily_achive_list=[]
        daily_targets=int(targets)
        for  achived in daily_achives:
            daily_achives_serializer = serializer(achived).data
            # daily_achive_serializer=DailyAchiveInterviewScheduleSerializer(achived).data
            achieved_value = achived.achieved or 0
            total_achieved_per_day = (achieved_value / daily_targets) * 100 if daily_targets != 0 else 0
            total_achieved_per_day = int(total_achieved_per_day)

            if daily_targets == 0:
                daily_achives_serializer["status"]="4"
            elif total_achieved_per_day < 60:
                daily_achives_serializer["status"]="0"
            elif total_achieved_per_day >= 60 and total_achieved_per_day < 80:
                daily_achives_serializer["status"]="1"#Orange
            elif total_achieved_per_day >= 80 and total_achieved_per_day < 90:
                daily_achives_serializer["status"]="2"#Yellow
            else:
                daily_achives_serializer["status"]="3"#Green

            daily_achive_list.append(daily_achives_serializer)

        activity_serializer["status"] = HRSub_function(total_achieved, targets)
        activity_serializer.update({"daily_achives": daily_achive_list})

        # daily_achives = model.objects.filter(InterviewSchedule=activity.pk)

        # total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
        # daily_achives_serializer = serializer(daily_achives, many=True).data

        # activity_serializer["Total_Achieved"] = total_achieved

        # targets = activity_serializer.get("Offers_target", 0)

        # activity_serializer["status"] = HRSub_function(total_achieved, targets)

        # activity_serializer.update({"daily_achives": daily_achives_serializer})

    elif model == WalkIns :
        activity_serializer = ActivityInterviewWalkinsSerializer(activity).data
        daily_achives = model.objects.filter(InterviewSchedule=activity.pk)
        total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
        # emp_daily_achives_serializer = serializer(daily_achives, many=True).data

        activity_serializer["Total_Achived"] = total_achieved
        targets = activity_serializer.get("Walkins_target", 0)
 
        daily_achive_list=[]
        daily_targets=int(targets)
        for  achived in daily_achives:
            daily_achives_serializer = serializer(achived).data
            # daily_achive_serializer=DailyAchiveInterviewScheduleSerializer(achived).data
            achieved_value = achived.achieved or 0
            total_achieved_per_day = (achieved_value / daily_targets) * 100 if daily_targets != 0 else 0
            total_achieved_per_day = int(total_achieved_per_day)

            if daily_targets == 0:
                daily_achives_serializer["status"]="4"
            elif total_achieved_per_day < 60:
                daily_achives_serializer["status"]="0"
            elif total_achieved_per_day >= 60 and total_achieved_per_day < 80:
                daily_achives_serializer["status"]="1"#Orange
            elif total_achieved_per_day >= 80 and total_achieved_per_day < 90:
                daily_achives_serializer["status"]="2"#Yellow
            else:
                daily_achives_serializer["status"]="3"#Green

            daily_achive_list.append(daily_achives_serializer)

        activity_serializer["status"] = HRSub_function(total_achieved, targets)
        activity_serializer.update({"daily_achives": daily_achive_list})
        
    return activity_serializer

class InterviewListDisplay(APIView):
    def get(self, request, filter_value=None, login_user=None, activity=None,employee=None):
        try:
            if isinstance(filter_value, str):
                filter_value = parse_date(filter_value + "-01")

            if filter_value and employee:
                year = filter_value.year
                month = filter_value.month

                employee = EmployeeDataModel.objects.get(EmployeeId=employee)
                activity_objects = InterviewSchedule.objects.filter(
                    Interview_Added_Date__year=year,
                    Interview_Added_Date__month=month,
                    Employee=employee.pk
                )

                activity_list1 = []
                activity_list2 = []
                activity_list3 = []

               

                for activity in activity_objects:
                    
                    activity_list1.append(get_activity_data(activity, DailyAchivesInterviewSchedule, DailyAchiveInterviewScheduleSerializer))
                    activity_list2.append(get_activity_data(activity, WalkIns, WalkInSerializer))
                    activity_list3.append(get_activity_data(activity, OfferedPosition, OffredScheduleSerializer))

                activity_dict = {
                    "interview": activity_list1,
                    "walkins": activity_list2,
                    "offers": activity_list3
                }

                return Response(activity_dict, status=status.HTTP_200_OK)
            
            elif activity:
                activity_object=InterviewSchedule.objects.filter(position=activity)
                activity_list=[]
                for activity in activity_object:
                    activity_object_serializer=ActivityInterviewScheduleSerializer(activity).data
                    daily_achives=DailyAchivesInterviewSchedule.objects.filter(InterviewSchedule=activity.pk)
                    total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                    daily_achives_serializer=DailyAchiveInterviewScheduleSerializer(daily_achives,many=True).data
                    activity_object_serializer["Total_Achived"]=total_achieved

                    targets=activity_object_serializer["targets"]

                    color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                    activity_object_serializer["status"]=color_status

                    activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                    activity_list.append(activity_object_serializer)
                return Response(activity_list,status=status.HTTP_200_OK)
            elif employee:
                employee=EmployeeDataModel.objects.get(EmployeeId=employee)
                activity_object=InterviewSchedule.objects.filter(Employee=employee.pk)
                activity_list=[]
                for activity in activity_object:
                    activity_object_serializer=ActivityInterviewScheduleSerializer(activity).data
                    daily_achives=DailyAchivesInterviewSchedule.objects.filter(InterviewSchedule=activity.pk)
                    total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                    daily_achives_serializer=DailyAchiveInterviewScheduleSerializer(daily_achives,many=True).data
                    activity_object_serializer["Total_Achived"]=total_achieved

                    targets=activity_object_serializer["targets"]

                    color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                    activity_object_serializer["status"]=color_status

                    activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                    activity_list.append(activity_object_serializer)
                return Response(activity_list,status=status.HTTP_200_OK)
            else:
                activity_object=InterviewSchedule.objects.filter(Assigned_by__EmployeeId=login_user)
                activity_list=[]

                activity_list1 = []
                activity_list2 = []
                activity_list3 = []

                for activity in activity_object:
                    activity_list1.append(get_activity_data(activity, DailyAchivesInterviewSchedule, DailyAchiveInterviewScheduleSerializer))
                    activity_list2.append(get_activity_data(activity, WalkIns, WalkInSerializer))
                    activity_list3.append(get_activity_data(activity, OfferedPosition, OffredScheduleSerializer))

                activity_dict = {
                    "interview": activity_list1,
                    "walkins": activity_list2,
                    "offers": activity_list3
                }

                return Response(activity_dict, status=status.HTTP_200_OK)


                # for activity in activity_object:
                #     activity_object_serializer=ActivityInterviewScheduleSerializer(activity).data
                #     daily_achives=DailyAchivesInterviewSchedule.objects.filter(InterviewSchedule=activity.pk)
                #     total_achieved = daily_achives.aggregate(total=Sum('achieved'))['total']
                #     daily_achives_serializer=DailyAchiveInterviewScheduleSerializer(daily_achives,many=True).data
                #     activity_object_serializer["Total_Achived"]=total_achieved

                #     targets=activity_object_serializer["targets"]

                #     color_status=HRSub_function(total_achieved=total_achieved,targets=targets)
                #     activity_object_serializer["status"]=color_status
                     
                #     activity_object_serializer.update({"daily_achives":daily_achives_serializer})
                #     activity_list.append(activity_object_serializer)
                # return Response(activity_list,status=status.HTTP_200_OK)
            
        except Exception as e:
            print(e)
            return Response("bad",status=status.HTTP_400_BAD_REQUEST)
        


# activity download 
from openpyxl.utils import get_column_letter

class ActivityListDisplayDownload(APIView):
    def get(self, request, start_date=None, end_date=None, employee=None):
        try:
            # start_date = '2024-06-01'
            # end_date = '2024-06-30'
            # employee = 'MTM24EMP8E'

            # Parse start and end dates
            if start_date:
                start_date = parse_date(start_date)
            if end_date:
                end_date = parse_date(end_date)

            print(f"Received parameters - start_date: {start_date}, end_date: {end_date}, employee_id: {employee}")

            if start_date and end_date and employee:
                employee_instance = EmployeeDataModel.objects.get(EmployeeId=employee)

                # Calculate end of the month
                end_date_month = end_date.replace(day=1) + timezone.timedelta(days=31)
                end_date_month = end_date_month.replace(day=1) - timezone.timedelta(days=1)

                activities = Activity.objects.filter(
                    Activity_added_Date__gte=start_date,
                    Activity_added_Date__lt=end_date_month,
                    Employee=employee_instance.pk
                )

                # Prepare data for export
                wb = Workbook()
                ws = wb.active
                ws.title = "Activity Data"

                # Header row
                header = [
                    "Employee",
                    "Date of Assigned",
                    "Activity Name",
                    "targets",
                    "Total Achieved",
                ]

                # Collect unique dates and build header
                date_set = set()
                for activity in activities:
                    daily_achieves = DailyAchives.objects.filter(Activity_instance=activity.pk)
                    for da in daily_achieves:
                        date_set.add(da.Date.strftime('%Y-%m-%d'))

                sorted_dates = sorted(date_set)
                for date in sorted_dates:
                    header.append(date)

                ws.append(header)

                # Data rows
                for activity in activities:
                    activity_serializer = ActivitySerializer(activity).data
                    daily_achieves = DailyAchives.objects.filter(Activity_instance=activity.pk)
                    daily_achieves_dict = {da.Date.strftime('%Y-%m-%d'): da.achieved for da in daily_achieves}
                    total_achieved = sum(daily_achieves_dict.values())
                    row_data = [
                        activity_serializer.get("Employee"),
                        activity_serializer.get("Activity_added_Date"),
                        activity_serializer.get("Activity_Name", "Unknown"),
                        activity_serializer.get("targets"),
                        total_achieved,
                    ]

                    for date in sorted_dates:
                        row_data.append(daily_achieves_dict.get(date, 0))

                    ws.append(row_data)

                # Save workbook to response
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="activity_data.xlsx"'
                wb.save(response)

                return response
            else:
                return Response({"error": "Missing or invalid date range or employee"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(str(e))
            return Response({"error": "An error occurred while processing your request."}, status=status.HTTP_400_BAD_REQUEST)
          
# class BulkInterviewCallUploadView(APIView):
#     """
#     This view handles the bulk upload of interview call records from an Excel or CSV file.
#     It automatically creates the activity context and handles date conversion.
#     """
#     def post(self, request, *args, **kwargs):
#         # (The first part of the code remains the same...)
#         activity_list_id = request.GET.get("activity_list_id")
#         employee_id = request.GET.get("login_emp_id")

#         if not activity_list_id or not employee_id:
#             return Response({"error": "activity_list_id and login_emp_id are required in the URL."}, status=status.HTTP_400_BAD_REQUEST)
#         if 'file' not in request.FILES:
#             return Response({"error": "No file was provided."}, status=status.HTTP_400_BAD_REQUEST)

#         try:
#             today = timezone.localdate()
#             new_activity_instance, created = NewActivityModel.objects.get_or_create(
#                 Activity_id=int(activity_list_id),
#                 Employee__EmployeeId=employee_id,
#                 Activity_assigned_Date__month=today.month,
#                 Activity_assigned_Date__year=today.year,
#                 defaults={
#                     'activity_assigned_by': EmployeeDataModel.objects.get(EmployeeId=employee_id),
#                     'targets': 0
#                 }
#             )
#             if created:
#                 current_date = timezone.localdate()
#                 last_day_of_month = monthrange(current_date.year, current_date.month)[1]
#                 end_date = current_date.replace(day=last_day_of_month)
#                 while current_date <= end_date:
#                     MonthAchivesListModel.objects.create(Activity_instance=new_activity_instance, Date=current_date)
#                     current_date += timedelta(days=1)
            
#             month_achieve_instance, _ = MonthAchivesListModel.objects.get_or_create(
#                 Activity_instance=new_activity_instance, Date=today
#             )
#         except (EmployeeDataModel.DoesNotExist, ActivityListModel.DoesNotExist):
#             return Response({"error": "The provided employee ID or activity ID is invalid."}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({"error": f"An error occurred while preparing the activity context: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         try:
#             file = request.FILES['file']
#             filename = file.name.lower()

#             if filename.endswith('.csv'):
#                 df = pd.read_csv(file)
#             elif filename.endswith(('.xlsx', '.xls')):
#                 df = pd.read_excel(file)
#             else:
#                 return Response({"error": "Unsupported file format. Please upload a .csv or .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)

#             column_mapping = {
#                 'Candidate Name': 'candidate_name', 'Candidate Phone': 'candidate_phone', 'Candidate Email': 'candidate_email',
#                 'Candidate Location': 'candidate_location', 'Designation': 'candidate_designation', 'Fresher/Experience': 'candidate_current_status',
#                 'Experience In Years': 'candidate_experience', 'Source': 'source', 'Expected CTC': 'expected_ctc', 'Current CTC': 'current_ctc',
#                 'Date of Joining': 'DOJ', 'Able to bring laptop': 'have_laptop', 'Candidate Status': 'interview_status',
#                 'Interview Call Remark': 'interview_call_remarks', 'Message Sent to Candidate': 'message_to_candidates',
#             }
#             df.rename(columns=column_mapping, inplace=True)
            
#             records_to_create = []
#             errors = []

#             for index, row in df.iterrows():
#                 record_data = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
#                 record_data["current_day_activity"] = month_achieve_instance.pk

#                 # --- NEW LINE TO FIX THE DATE ISSUE ---
#                 if 'DOJ' in record_data:
#                     record_data['DOJ'] = pd.to_datetime(record_data['DOJ']).date()
#                 # --- END OF FIX ---

#                 if 'candidate_current_status' in record_data:
#                     status_val = str(record_data['candidate_current_status']).lower()
#                     if status_val == 'fresher':
#                         record_data['candidate_current_status'] = 'fresher'
#                         record_data.pop('candidate_experience', None)
#                     elif status_val == 'experience':
#                         record_data['candidate_current_status'] = 'experience'
#                     else:
#                         errors.append(f"Row {index + 2}: Invalid value for 'Fresher/Experience'. Use 'Fresher' or 'Experience'.")
#                         continue
                
#                 if 'have_laptop' in record_data:
#                     record_data['have_laptop'] = str(record_data['have_laptop']).lower() == 'yes'

#                 serializer = NewDailyAchivesModelSerializer(data=record_data)
#                 if serializer.is_valid():
#                     records_to_create.append(NewDailyAchivesModel(**serializer.validated_data))
#                 else:
#                     errors.append({f"Row {index + 2}": serializer.errors})
            
#             if errors:
#                 return Response({"status": "failed", "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
            
#             NewDailyAchivesModel.objects.bulk_create(records_to_create)

#             month_achieve_instance.achieved = NewDailyAchivesModel.objects.filter(current_day_activity=month_achieve_instance).count()
#             month_achieve_instance.save()

#             return Response(
#                 {"status": "success", "message": f"Successfully uploaded {len(records_to_create)} records."},
#                 status=status.HTTP_201_CREATED
#             )

#         except Exception as e:
#             return Response({"error": f"An error occurred while processing the file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class BulkActivityUploadView(APIView):
    """
    A single, robust endpoint for bulk uploads that handles all activity types,
    including the special 'candidate_for' logic for freshers.
    """
    def post(self, request, *args, **kwargs):
        try:
            activity_list_id = int(request.GET.get("activity_list_id")) 
            employee_id = request.GET.get("login_emp_id")
        except (ValueError, TypeError):
            return Response({"error": "A valid integer 'activity_list_id' is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not employee_id:
            return Response({"error": "'login_emp_id' is required in the URL."}, status=status.HTTP_400_BAD_REQUEST)
        if 'file' not in request.FILES:
            return Response({"error": "No file was provided."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            today = timezone.localdate()
            employee_instance = EmployeeDataModel.objects.get(EmployeeId=employee_id)
            new_activity_instance, created = NewActivityModel.objects.get_or_create( 
                Activity_id=activity_list_id, Employee=employee_instance,
                Activity_assigned_Date__month=today.month, Activity_assigned_Date__year=today.year,
                defaults={'activity_assigned_by': employee_instance, 'targets': 0}
            )
            if created:
                current_date = timezone.localdate()
                last_day_of_month = monthrange(current_date.year, current_date.month)[1] 
                end_date = current_date.replace(day=last_day_of_month)
                while current_date <= end_date:
                    MonthAchivesListModel.objects.create(Activity_instance=new_activity_instance, Date=current_date)
                    current_date += timedelta(days=1)
            month_achieve_instance, _ = MonthAchivesListModel.objects.get_or_create( 
                Activity_instance=new_activity_instance, Date=today
            )
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": f"The employee with ID '{employee_id}' does not exist."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"An error occurred preparing the activity context: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            file = request.FILES['file']
            filename = file.name.lower()
            if filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(file) 
            else:
                return Response({"error": "Unsupported file format. Please upload a .csv or .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)

            records_to_create = []
            errors = []
            
            #  INTERVIEW CALLS LOGIC (ID = 1) 
            if activity_list_id == 1:
                required_columns = ['Candidate Name', 'Candidate Phone', 'Candidate Email', 'Candidate Status']
                
                if not set(required_columns).issubset(df.columns):
                    missing_cols = list(set(required_columns) - set(df.columns))
                    return Response(
                        {"error": f"Invalid file format for Interview Calls. Missing required columns: {missing_cols}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Add the new column to the mapping
                column_mapping = {
                    'Candidate Name': 'candidate_name', 'Candidate Phone': 'candidate_phone', 'Candidate Email': 'candidate_email',
                    'Candidate Location': 'candidate_location', 'Designation': 'candidate_designation', 'Fresher/Experience': 'candidate_current_status',
                    'Experience In Years': 'candidate_experience', 'Source': 'source', 'Expected CTC': 'expected_ctc', 'Current CTC': 'current_ctc',
                    'Date of Joining': 'DOJ', 'Able to bring laptop': 'have_laptop', 'Candidate Status': 'interview_status',
                    'Interview Call Remark': 'interview_call_remarks', 'Message Sent to Candidate': 'message_to_candidates',
                    'Candidate For (OJT/Internal Hiring)': 'candidate_for' # <-- NEW MAPPING
                }
                df.rename(columns=column_mapping, inplace=True)
                
                for index, row in df.iterrows():
                    record_data = {k: v for k, v in row.to_dict().items() if pd.notna(v)} 
                    
                    if 'DOJ' in record_data: record_data['DOJ'] = pd.to_datetime(record_data['DOJ'], errors='coerce').date()
                    if 'have_laptop' in record_data: record_data['have_laptop'] = str(record_data['have_laptop']).lower() == 'yes'
                    if 'interview_status' in record_data:
                        status_val = str(record_data['interview_status']).lower()
                        record_data['interview_status'] = 'offer' if status_val == 'offered' else status_val

                    if 'candidate_current_status' in record_data:
                        record_data['candidate_current_status'] = str(record_data['candidate_current_status']).lower()
                        if record_data['candidate_current_status'] == 'fresher':
                            record_data.pop('candidate_experience', None)
                            
                            if 'candidate_for' in record_data:
                                cf_val = str(record_data['candidate_for']).strip().lower()
                                if cf_val == 'ojt':
                                    record_data['candidate_for'] = 'OJT'
                                elif cf_val == 'internal hiring':
                                    record_data['candidate_for'] = 'Internal_Hiring'
                                else:
                                    record_data.pop('candidate_for', None)
                        
                        else: # If candidate is 'experience', remove the 'candidate_for' field
                            record_data.pop('candidate_for', None)
                            
                    records_to_create.append(record_data)

            #  JOB POSTS LOGIC (ID = 2)  : after, if needed can change fields 
            elif activity_list_id == 2:
                required_columns = ['Position', 'URL']
                
                if not set(required_columns).issubset(df.columns):
                    missing_cols = list(set(required_columns) - set(df.columns))
                    return Response(
                        {"error": f"Invalid file format for Job Posts. Missing required columns: {missing_cols}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                column_mapping = {'Position': 'position', 'URL': 'url', 'Remarks': 'job_post_remarks'}
                df.rename(columns=column_mapping, inplace=True)
                for index, row in df.iterrows():
                    records_to_create.append({k: v for k, v in row.to_dict().items() if pd.notna(v)})

            #  CLIENT CALLS LOGIC (ID = 3) 
            elif activity_list_id == 3:
                required_columns = ['Client Name', 'Client Phone', 'Client Status']
                
                if not set(required_columns).issubset(df.columns):
                    missing_cols = list(set(required_columns) - set(df.columns))
                    return Response(
                        {"error": f"Invalid file format for Client Calls. Missing required columns: {missing_cols}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                #30/01/2026
                column_mapping = {
                    # 'Client Organization': 'client_organization', 'Client Name': 'client_name', 'Client Phone': 'client_phone',
                    'Client Organization': 'client_company_name', 'Client Name': 'client_name', 'Client Phone': 'client_phone',
                    'Purpose': 'client_enquire_purpose', "Client's Spoke": 'client_spok', 'Client Status': 'client_status',
                    # 'Client Remarks': 'client_call_remarks'
                    'Client Remarks': 'client_call_remarks', 'Client Email': 'client_email'
                }
                df.rename(columns=column_mapping, inplace=True)
                for index, row in df.iterrows():
                    record_data = {k: v for k, v in row.to_dict().items() if pd.notna(v)}
                    if 'client_status' in record_data:
                        #30/01/2026
                        # status_map = {"converted to client": "job", "closed": "closed", "follow up": "followup"}
                        # record_data['client_status'] = status_map.get(str(record_data['client_status']).lower(), None)
                        status_val = str(record_data['client_status']).lower().strip()
                        status_map = {
                            "converted to client": "converted_to_client", 
                            "converted_to_client": "converted_to_client",
                            "job": "job",
                            "closed": "closed", 
                            "follow up": "followup",
                            "followup": "followup"
                        }
                        record_data['client_status'] = status_map.get(status_val, None)
                    records_to_create.append(record_data)
            else:
                return Response({"error": f"Unsupported activity_list_id: {activity_list_id}"}, status=status.HTTP_400_BAD_REQUEST)

            # The final validation and save part 
            final_records = []
            for index, record_data in enumerate(records_to_create):
                record_data["current_day_activity"] = month_achieve_instance.pk
                serializer = NewDailyAchivesModelSerializer(data=record_data)
                if serializer.is_valid():
                    final_records.append(NewDailyAchivesModel(**serializer.validated_data))
                else:
                    errors.append({f"Row {index + 2}": serializer.errors})
            
            if errors:
                return Response({"status": "failed", "errors": errors}, status=status.HTTP_400_BAD_REQUEST)
            
            NewDailyAchivesModel.objects.bulk_create(final_records)
            month_achieve_instance.achieved = NewDailyAchivesModel.objects.filter(current_day_activity=month_achieve_instance).count()
            month_achieve_instance.save()
            return Response({"status": "success", "message": f"Successfully uploaded {len(final_records)} records."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"An error occurred while processing the file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class DownloadActivityTemplateView(APIView):
    """
    Generates and serves a CSV template file based on the activity_list_id.
    """
    def get(self, request, *args, **kwargs):
        try:
            activity_list_id = int(request.GET.get('activity_list_id'))
        except (ValueError, TypeError):
            return Response(
                {"error": "A valid integer 'activity_list_id' is required as a query parameter."},
                status=status.HTTP_400_BAD_REQUEST
            )

        headers = []
        filename = "template.csv"

        if activity_list_id == 1:
            # Interview Calls Template
            headers = [
                'Candidate Name', 'Candidate Phone', 'Candidate Email', 'Candidate Location', 'Designation', 
                'Fresher/Experience', 'Experience In Years', 'Candidate For (OJT/Internal Hiring)', 'Source', 
                'Expected CTC', 'Current CTC', 'Date of Joining', 'Able to bring laptop', 
                'Candidate Status', 'Interview Call Remark', 'Message Sent to Candidate'
            ]
            filename = "interview_calls_template.csv"

        elif activity_list_id == 2:
            # Job Posts Template
            headers = ['Position', 'URL', 'Remarks']
            filename = "job_posts_template.csv"

        elif activity_list_id == 3:
            # Client Calls Template
            headers = [
                'Client Organization', 'Client Name', 'Client Phone', 'Client Email', 'Purpose', 
                'Client\'s Spoke', 'Client Status', 'Client Remarks'
            ]
            filename = "client_calls_template.csv"

        else:
            return Response({"error": f"Invalid activity_list_id: {activity_list_id}. Must be 1, 2, or 3."}, status=status.HTTP_400_BAD_REQUEST)

        df = pd.DataFrame(columns=headers)
        
        csv_data = df.to_csv(index=False)

        response = HttpResponse(content=csv_data, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

#changes2
class PublicCandidateInterviewCallView(APIView):
    """
    Public API endpoint for candidate form submissions.
    Handles employee reference and Admin fallback logic.
    """
    
    def post(self, request):
        try:
            request_data = request.data.copy()
            ref_emp_id = request_data.get("ref")  # Employee ID from QR code
            
            particular_day = timezone.localdate()
            cm = particular_day.month
            cy = particular_day.year
            
            target_employee = None
            
            if ref_emp_id:
                ref_employee = EmployeeDataModel.objects.filter(EmployeeId=ref_emp_id , employeeProfile__employee_status="active").first()
                
                if ref_employee:
                    activity_list = ActivityListModel.objects.filter(activity_name="interview_calls").first()
                    
                    if activity_list:
                        has_assignment = NewActivityModel.objects.filter(
                            Activity=activity_list,
                            Employee=ref_employee,
                            Activity_assigned_Date__month=cm,
                            Activity_assigned_Date__year=cy
                        ).exists()
                        
                        if has_assignment:
                            target_employee = ref_employee
            
            if not target_employee:
                admin_employee = EmployeeDataModel.objects.filter(
                    Designation="Admin",
                    employeeProfile__employee_status="active"
                ).first()
                
                if not admin_employee:
                    return Response(
                        {"error": "No Admin user found in the system. Please contact support."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
                
                target_employee = admin_employee
            
            activity_list, _ = ActivityListModel.objects.get_or_create(
                activity_name="interview_calls",
                defaults={"added_by": target_employee}
            )
            
            new_activity_instance, created = NewActivityModel.objects.get_or_create(
                Activity=activity_list,
                Employee=target_employee,
                Activity_assigned_Date__month=cm,
                Activity_assigned_Date__year=cy,
                defaults={
                    "Activity_assigned_Date": particular_day,
                    "targets": 0,
                    "activity_assigned_by": target_employee
                }
            )
            
            month_achieve_instance, _ = MonthAchivesListModel.objects.get_or_create(
                Activity_instance=new_activity_instance,
                Date=particular_day,
                defaults={"achieved": 0}
            )
            
            request_data["current_day_activity"] = month_achieve_instance.pk
            
            if request_data.get("candidate_for") == "OJT":
                request_data["candidate_for"] = "OJT"
            elif request_data.get("candidate_for") == "Internal_Hiring":
                request_data["candidate_for"] = "Internal_Hiring"
            else:
                request_data["candidate_for"] = None
            
            if request_data.get("candidate_current_status") == "fresher":
                request_data.pop("candidate_experience", None)
            
            serializer = NewDailyAchivesModelSerializer(data=request_data)
            
            if serializer.is_valid():
                instance = serializer.save()
                
                # Update achieved count
                daily_achievements = NewDailyAchivesModel.objects.filter(
                    current_day_activity=month_achieve_instance
                )
                month_achieve_instance.achieved = daily_achievements.count()
                month_achieve_instance.save()
                
                return Response(
                    {
                        "message": "Candidate details submitted successfully!",
                        "assigned_to": target_employee.EmployeeId,
                        "activity_id": instance.pk
                    },
                    status=status.HTTP_201_CREATED
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
#30/01/2026
class LeadActivityLogView(APIView):
    def get(self, request, activity_id):
        try:
            # Fetch the reference activity to get the phone number
            reference_activity = NewDailyAchivesModel.objects.filter(pk=activity_id).first()
            
            if not reference_activity:
                return Response({"error": "Activity not found"}, status=status.HTTP_404_NOT_FOUND)

            # Extract Phone Number (Candidate or Client)
            phone = reference_activity.candidate_phone or reference_activity.client_phone
            
            if not phone:
                return Response({"error": "No phone number associated with this lead to track history."}, status=status.HTTP_400_BAD_REQUEST)

            # 1. Fetch Main Activities (NewDailyAchivesModel)
            main_activities_qs = NewDailyAchivesModel.objects.filter(
                Q(candidate_phone=phone) | Q(client_phone=phone)
            )

            # 2. Fetch Follow-Ups (FollowUpModel)
            # We want all follow-ups linked to ANY of the main activities found above.
            followups_qs = FollowUpModel.objects.filter(
                activity_record__in=main_activities_qs
            ).select_related('activity_record').order_by('-created_on')

            # Identify the "Closing" follow-up for each activity record
            # We assume the LATEST completed follow-up for a 'closed' activity is the one that closed it.
            # Since followups_qs is ordered by -created_on (Newest first), the first completed one we see for an ID is the latest.
            closing_followup_ids = {}
            for f in followups_qs:
                if f.activity_record.id not in closing_followup_ids:
                    if f.activity_record.lead_status in ['closed', 'rejected'] and f.status == 'completed':
                        closing_followup_ids[f.activity_record.id] = f.id

            # Combine and Sort
            timeline_items = []

            # Process Main Activities
            for item in main_activities_qs:
                activity_name = "Unknown Activity"
                employee_name = "Unknown"
                try:
                    if item.current_day_activity and item.current_day_activity.Activity_instance:
                        if item.current_day_activity.Activity_instance.Activity:
                             activity_name = item.current_day_activity.Activity_instance.Activity.activity_name
                        if item.current_day_activity.Activity_instance.Employee:
                             employee_name = item.current_day_activity.Activity_instance.Employee.Name
                except:
                    pass

                timeline_items.append({
                    "item_type": "activity",
                    "sort_date": item.Created_Date,
                    "data": item,
                    "activity_name": activity_name,
                    "employee_name": employee_name
                })

            # Process Follow-ups
            for item in followups_qs:
                employee_name = "Unknown"
                try:
                    if item.created_by:
                        employee_name = item.created_by.Name
                except:
                    pass

                timeline_items.append({
                    "item_type": "followup",
                    "sort_date": item.created_on,
                    "data": item,
                    "activity_name": f"Follow Up ({item.follow_up_type})",
                    "employee_name": employee_name
                })

            # Sort by date descending (Newest first)
            timeline_items.sort(key=lambda x: x["sort_date"], reverse=True)

            # Serialize
            serialized_history = []
            
            for entry in timeline_items:
                data = entry["data"]
                if entry["item_type"] == "activity":
                    # It's a NewDailyAchivesModel (The START of the activity)
                    
                    notes = data.client_call_remarks or data.interview_call_remarks or data.job_post_remarks or data.closure_reason or data.client_enquire_purpose
                    
                    serialized_history.append({
                        "id": data.id,
                        "created_date": data.Created_Date,
                        "activity_name": entry["activity_name"],
                        "status": "active", # Lowercase for frontend color matching
                        "sub_status": data.rejection_type or data.client_status or data.interview_status,
                        "notes": notes,
                        "expected_date": None,
                        "expected_time": None,
                        "employee_name": entry["employee_name"],
                        "type": "Main Activity"
                    })
                else:
                    # It's a FollowUpModel
                    status_label = "Follow Up"
                    
                    # Check if this ID was identified as the closing one
                    if data.activity_record.id in closing_followup_ids and closing_followup_ids[data.activity_record.id] == data.id:
                        status_label = data.activity_record.lead_status # Keep lowercase (closed/rejected)
                    elif data.status == 'pending':
                        status_label = "Pending Follow Up"
                    else:
                        status_label = "Follow Up" # Completed intermediate step

                    serialized_history.append({
                        "id": data.id,
                        "created_date": data.created_on,
                        "activity_name": entry["activity_name"],
                        "status": status_label, 
                        "sub_status": None,
                        "notes": data.notes,
                        "expected_date": data.expected_date,
                        "expected_time": data.expected_time,
                        "employee_name": entry["employee_name"],
                        "type": "Follow Up"
                    })

            # Lead Details (Take from the latest MAIN activity, or the very first item if valid)
            latest_main = main_activities_qs.order_by('-Created_Date').first()
            if not latest_main and reference_activity:
                latest_main = reference_activity

            response_data = {
                "lead_details": {
                    "name": latest_main.candidate_name or latest_main.client_name if latest_main else "Unknown",
                    "phone": latest_main.candidate_phone or latest_main.client_phone if latest_main else "Unknown",
                    "email": latest_main.candidate_email or latest_main.client_email if latest_main else "",
                    "company_name": latest_main.client_company_name if latest_main else "",
                    "current_status": latest_main.lead_status or "Active" if latest_main else "Unknown" 
                },
                "history": serialized_history
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)