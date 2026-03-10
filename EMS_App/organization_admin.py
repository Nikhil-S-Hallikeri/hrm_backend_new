from django.shortcuts import render
# Create your views here.
from EMS_App.imports import *
from HRM_App.models import *
from HRM_App.serializers import *

class EmployeeIdList(APIView):
    def get(self,request,loginuser):
        try:
            login_user=EmployeeDataModel.objects.get(EmployeeId=loginuser)
            if login_user.Designation=="Admin":
                employee_list=EmployeeDataModel.objects.filter(Designation="Admin").exclude()
                # employee_serializer=EmployeeDataSerializer(employee_list,many=True)
                employee_serializer_list= [emp_ids.EmployeeId for emp_ids in employee_list]
                
                return Response(employee_serializer_list,status=status.HTTP_200_OK)
            else:
                employee_serializer_list= []
                return Response(employee_serializer_list,status=status.HTTP_200_OK)
        except:
            return Response("error",status=status.HTTP_400_BAD_REQUEST)
        
class EmployeeRollAssigning(APIView):
    def get(self,request,Emp_id):
        try:
            login_user=EmployeeDataModel.objects.get(EmployeeId=Emp_id)
            employee_serializer=EmployeeDataSerializer(login_user)
            return Response(employee_serializer.data,status=status.HTTP_200_OK)
        except:
            return Response("error",status=status.HTTP_400_BAD_REQUEST)
    

# view applied list
# here i need to show in the admin dash like permission allow list  and employees list based on 
# all filters like des dep,rep emp,
# add employees
# allow to add screening   

class EmployeePermissions(APIView):
    def post(self,request,assign_to):
        try:
            emp_data=EmployeeDataModel.objects.get(EmployeeId=assign_to)
            emp_data.Designation=request.data.get("Dashboard")
            emp_data.save()
            return Response(f"{emp_data.EmployeeId} Employee Dasboard Changed Successfully To{emp_data.Designation}")
        except:
            return Response("Employee Dasboard Changed Failed")
        
    # def get(self,request,assign_to=None):
    #     try:
    #         if assign_to=="Reporting_Manager":
    #             all_employees=EmployeeDataModel.objects.all()
    #             rep_employees=[ emps.Reporting_To.pk for emps in all_employees if emps.Reporting_To]
    #             rep_team=EmployeeDataModel.objects.filter(pk__in=rep_employees)
    #             serializer_data=EmergencyDetailsSerializer(rep_team)
    #             return Response(serializer_data.data,status=status.HTTP_200_OK)
    #         elif assign_to=="Employees":
    #             all_employees=EmployeeDataModel.objects.all()
    #             rep_employees=[ emps.Reporting_To.pk for emps in all_employees if emps.Reporting_To]
    #             rep_team=EmployeeDataModel.objects.filter(pk__in=rep_employees).exclude()
    #             serializer_data=EmergencyDetailsSerializer(rep_team)
    #             return Response(serializer_data.data,status=status.HTTP_200_OK)
    #         elif "l":
    #             pass
    #     except:
    #         pass


    
        
