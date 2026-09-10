from HRM_App.models import *
from HRM_App.imports import *
from EMS_App.models import *
from .models import *
from .serializers import *
from rest_framework import viewsets
from django.utils import timezone

class LeaveTypeAddingView(viewsets.ModelViewSet):
    queryset = LeaveTypesModel.objects.all()
    serializer_class = LeaveTypeSerializer

    def perform_create(self, serializer):
        employee_id = self.request.data.get('EmployeeId')
        try:
            employee = EmployeeDataModel.objects.get(EmployeeId=employee_id)
        except EmployeeDataModel.DoesNotExist:
            return Response(
                {"error": "Employee not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer.save(added_By=employee)

        
class LeaveTypeDetailsView(viewsets.ModelViewSet):
    serializer_class = LeaveTypeDetailSerializer
    def get_queryset(self):
        if self.kwargs != {}:
            LeaveType_id = self.kwargs['Leave_id']
            current_year=timezone.localdate().year
            
            return LeavesTypeDetailModel.objects.filter(leave_type=LeaveType_id)
            #,applicable_year__year=current_year
        return LeavesTypeDetailModel.objects.all()
    def update(self, request, *args, **kwargs):
        
        partial = True  # PATCH method is partial update
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        leave_type_id = serializer.validated_data.get("leave_type", instance.leave_type)
        year = serializer.validated_data.get("applicable_year", instance.applicable_year)
        # Logic to handle updating leave details
        leave_details_instance = LeavesTypeDetailModel.objects.filter(leave_type=leave_type_id, applicable_year=year).exclude(pk=instance.pk).exists()
        if leave_details_instance:
            return Response("This Leave Exists for Next year!", status=status.HTTP_400_BAD_REQUEST)
        
        leave_details_obj = serializer.instance
        
        if leave_details_obj.applicable_to == "both":
            emp_obj = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")
        else:
            emp_obj = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active", employeeProfile__probation_status=leave_details_obj.applicable_to)

        EmployeeLeaveTypesEligiblity.objects.filter(LeaveType=leave_details_obj).delete()
        
        for emp in emp_obj:
            EmployeeLeaveTypesEligiblity.objects.create(employee=emp, LeaveType=leave_details_obj)

        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def perform_update(self, serializer):
        # Call the parent class's perform_update method
        super().perform_update(serializer)
    
class LeavesTypesDetailsCreating(APIView):
    
    def post(self, request):
        # Create a modifiable copy of the request data
        request_data = request.data.copy()
        leave_type_id = request_data["leave_type"]  # Retrieve the leave type ID from the request data
        year = request_data["applicable_year"]  # Retrieve the applicable year from the request data

        # Check if a leave type detail already exists for the given leave type and year
        leave_details_instance = LeavesTypeDetailModel.objects.filter(leave_type=leave_type_id, applicable_year=year).exists()

        if not leave_details_instance:
            # If no existing leave type detail is found, initialize the serializer with the request data
            leave_details_serializers = LeaveTypeDetailSerializer(data=request_data)
            if leave_details_serializers.is_valid():
                # Validate the serializer data and save the new leave type detail to the database
                instance = leave_details_serializers.save()

                # Retrieve the saved leave type detail object
                leave_details_obj = LeavesTypeDetailModel.objects.get(pk=instance.pk)
                
                # Determine eligible employees based on the applicable_to field
                if leave_details_obj.applicable_to == "both":
                    emp_obj = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")
                   
                else:
                    emp_obj = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active", employeeProfile__probation_status=leave_details_obj.applicable_to)

                # Create EmployeeLeaveTypesEligiblity records for each eligible employee
                for emp in emp_obj:
                   
                    leave_eligible_instance = EmployeeLeaveTypesEligiblity.objects.create(employee=emp, LeaveType=leave_details_obj)

                # Return a success response with the serialized data of the newly created leave type details
                return Response(leave_details_serializers.data, status=status.HTTP_200_OK)
            else:
                # If serializer validation fails, return a response with validation errors
                print(leave_details_serializers.errors)  # Debugging: print serializer errors
                return Response(leave_details_serializers.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # If leave type details already exist for the specified year, return an error response
            return Response("This Leave Exists for Next year!", status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, emp_id):
        try:
            # Retrieve the current date and year
            current_date = timezone.localdate()
            current_year = current_date.year
            
            # Fetch eligible leave records for the specified employee ID and current year
            employees_eligible_leaves_list = EmployeeLeaveTypesEligiblity.objects.filter(employee__EmployeeId=emp_id, LeaveType__applicable_year__year=current_year,LeaveType__is_active=True).exclude(is_active=False)

            available_leaves = []
            for leaves in employees_eligible_leaves_list:
                # Process each leave record to determine the available leave details
                if leaves.LeaveType.carry_forward and leaves.LeaveType.earned_leave:
                    # If the leave type allows carry forward and is earned, add available leave days to the list
                    if leaves.Available_leaves > 0:
                        leave_dict = {
                            "leave_name": leaves.LeaveType.leave_type.leave_name,
                            "id": leaves.pk,
                            "no_of_days": leaves.Available_leaves
                        }
                        available_leaves.append(leave_dict)

                elif leaves.LeaveType.earned_leave:
                    # If the leave type is earned but does not carry forward, check monthly leave data
                    month_leave_data = MonthWiseLeavesModel.objects.filter(emp_Applicable_LT_Inst__pk=leaves.pk, month=current_date.month, year__year=current_year).first()
                    if month_leave_data and month_leave_data.leaves_count_per_month > 0:
                        leave_dict = {
                            "leave_name": leaves.LeaveType.leave_type.leave_name,
                            "id": leaves.pk,
                            "no_of_days": month_leave_data.leaves_count_per_month
                        }
                        available_leaves.append(leave_dict)

                else:
                    # For other leave types, add the number of utilized leave days to the list
                    leave_dict = {
                        "leave_name": leaves.LeaveType.leave_type.leave_name,
                        "id": leaves.pk,
                        "no_of_days_utilised": leaves.utilised_leaves
                    }
                    available_leaves.append(leave_dict)

            # Return a success response with the list of available leaves
            return Response(available_leaves, status=status.HTTP_200_OK)
        except Exception as e:
            # Return an error response if an exception occurs
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

class EmployeeLeaveEligibilityView(APIView):
    def post(self,request):
        request_data=request.data.copy()
        emp_obj=EmployeeDataModel.objects.get(EmployeeId=request.data["employee"])
        request_data["employee"]=emp_obj.pk
        
        leave_object=LeavesTypeDetailModel.objects.get(pk=request.data["LeaveType"])
        emp_info_obj=EmployeeInformation.objects.get(employee_Id=emp_obj.EmployeeId)

        LT_obj=LeavesTypeDetailModel.objects.all()
        Available_Leaves=[]
        if emp_info_obj.probation_status=="probationer":

            for al in LT_obj:
                if al.applicable_to=="probationer" or al.applicable_to=="both":
                    Available_Leaves.append(al.leave_type.leave_name)

            if leave_object.leave_type.leave_name in Available_Leaves:
                serializer=EmployeeLeaveTypesEligiblitySerializer(data=request_data)
                if serializer.is_valid():
                    instance=serializer.save()
                    Emp_LT_Elibible_Obj=EmployeeLeaveTypesEligiblity.objects.get(id=instance.pk)
                    leave_obj=LeavesTypeDetailModel.objects.get(id=Emp_LT_Elibible_Obj.LeaveType.pk)
                    Emp_LT_Elibible_Obj.no_of_leaves=leave_obj.No_Of_leaves
                    Emp_LT_Elibible_Obj.Available_leaves=leave_obj.No_Of_leaves
                    Emp_LT_Elibible_Obj.no_of_leaves_per_month=int(leave_obj.No_Of_leaves/12)
                    Emp_LT_Elibible_Obj.save()
                    
                    return Response(serializer.data,status=status.HTTP_200_OK)
                else:
                    return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            else:
                message=f"{leave_object.leave_type.leave_name} is not applicable for this employee"
                return Response(message,status=status.HTTP_200_OK)

        elif emp_info_obj.probation_status=="confirmed":
            Available_Leaves=[]
            for al in LT_obj:
                if al.applicable_to=="confirmed" or al.applicable_to=="both":
                    Available_Leaves.append(al.leave_type.leave_name)
            if leave_object.leave_type.leave_name in Available_Leaves:
                serializer=EmployeeLeaveTypesEligiblitySerializer(data=request_data)
                if serializer.is_valid():
                    instance=serializer.save()
                    Emp_LT_Elibible_Obj=EmployeeLeaveTypesEligiblity.objects.get(id=instance.pk)
                    leave_obj=LeavesTypeDetailModel.objects.get(id=Emp_LT_Elibible_Obj.LeaveType.pk)
                    Emp_LT_Elibible_Obj.no_of_leaves=leave_obj.No_Of_leaves
                    Emp_LT_Elibible_Obj.Available_leaves=leave_obj.No_Of_leaves
                    Emp_LT_Elibible_Obj.no_of_leaves_per_month=int(leave_obj.No_Of_leaves/12)
                    Emp_LT_Elibible_Obj.save()

                    return Response(serializer.data,status=status.HTTP_200_OK)
                else:
                    return Response(serializer.errors,status=status.HTTP_200_OK)
            else:
                message=f"{leave_object.leave_type.leave_name} is not applicable for this employee"
                return Response(message,status=status.HTTP_200_OK)
        else:
            message=f"Paid Leaves are not applicable for this employee"
            return Response(message,status=status.HTTP_200_OK)

    def get(self,request,login_user=None):

        try:
            current_date=timezone.localdate()
            current_year=current_date.year
            employees_eligible_leaves_list=EmployeeLeaveTypesEligiblity.objects.filter(employee__EmployeeId=login_user,LeaveType__applicable_year__year=current_year,LeaveType__is_active=True).exclude(is_active=False)
            
            serializer_data_list=[]
            for leave_type in employees_eligible_leaves_list:
                serializer_list=EmployeeLeaveTypesEligiblitySerializer(leave_type).data
                if leave_type.LeaveType.earned_leave:
                    month_leave_data=MonthWiseLeavesModel.objects.filter(emp_Applicable_LT_Inst__pk=leave_type.pk,month=current_date.month,year__year=current_year).first()
                    month_leave_serializer=MonthWiseLeavesSerializer(month_leave_data).data
                    serializer_list["leave_discription"]=leave_type.LeaveType.leave_type.description
                    serializer_list.update({"month_data":month_leave_serializer})
                else:
                    serializer_list.update({"month_data":{}})
                serializer_data_list.append(serializer_list)

            print(serializer_data_list)

            return Response(serializer_data_list,status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(str(e))
        
    def patch(self,request,emp_lye_id):
        emp_lye_obj=EmployeeLeaveTypesEligiblity.objects.get(id=emp_lye_id)
        serializer=EmployeeLeaveTypesEligiblitySerializer(emp_lye_obj,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors,status=status.HTTP_200_OK)
        
    def delete(self,request,emp_lye_id):
        try:
            emp_lye_obj=EmployeeLeaveTypesEligiblity.objects.get(id=emp_lye_id)
            emp_lye_obj.delete()
            return Response("deleted Successfull",status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_200_OK)
        

# def Loss_Off_Pay_Function(extra_days):
#     emp_eligibile_obj=EmployeeLeaveTypesEligiblity.objects.filter(LeaveType__earned_leave=False,LeaveType__carry_forward=False).first()
#     emp_eligibile_obj.utilised_leaves=emp_eligibile_obj.utilised_leaves + extra_days
#     emp_eligibile_obj.save()
    
# def leaves_function(from_date,to_date,leave_id):
#     for i in range(from_date,to_date):
#         leave_request=LeaveRequestForm.objects.get(pk=leave_id)
#         leave_type=leave_request.LeaveType.LeaveType.leave_type.leave_name
#         leaves=EmployeesLeavesmodel.objects.create(leave_request=leave_request,leave_date=i,leave_type=leave_type)

def Loss_Off_Pay_Function(extra_days,emp_id):
    current_year=timezone.localdate().year

    emp_eligible_obj = EmployeeLeaveTypesEligiblity.objects.filter(employee__EmployeeId=emp_id,
        LeaveType__earned_leave=False, LeaveType__carry_forward=False,LeaveType__applicable_year__year=current_year
    ).first()

    emp_eligible_obj.utilised_leaves += extra_days
    emp_eligible_obj.save()
    
    return emp_eligible_obj


# def approval_notification(leave_req_obj):

#     sender=RegistrationModel.objects.filter(EmployeeId=leave_req_obj.report_to.EmployeeId).first()
#     receiver=RegistrationModel.objects.filter(EmployeeId=leave_req_obj.employee.EmployeeId).first()

#     ad=leave_req_obj.approved_date if leave_req_obj.approved_date else timezone.localtime
#     # message=f"Dear {receiver.UserName}/{receiver.EmployeeId}\n your Applied Leave Verified by Reporting manager \n approval status {leave_req_obj.approved_status}\non {ad} Regards\nReporting Head",
    
#     if sender and receiver:
#         obj=Notification.objects.create(sender=sender, receiver=receiver, 
#             message=f"Dear {receiver.UserName}/{receiver.EmployeeId}\n your Applied Leave Verified by Reporting manager \n approval status `{leave_req_obj.approved_status}`\non {ad} Regards\nReporting Head",
#             candidate_id=None,not_type='Leave_Approval')

# def approval_notification(leave_obj):
#     """
#     Creates and sends a notification to the employee about their leave status.
#     """
#     try:
#         # The sender is the manager who approved/rejected the leave.
#         sender_reg = RegistrationModel.objects.filter(EmployeeId=leave_obj.approved_by.EmployeeId).first()

#         # The receiver is the employee who applied for the leave.
#         receiver_reg = RegistrationModel.objects.filter(EmployeeId=leave_obj.employee.EmployeeId).first()

#         if sender_reg and receiver_reg:
#             status_text = leave_obj.approved_status
#             message = f"Your leave request from {leave_obj.from_date} to {leave_obj.to_date} has been {status_text}."

#             # Create the notification in the database
#             Notification.objects.create(
#                 sender=sender_reg,
#                 receiver=receiver_reg,
#                 message=message,
#                 not_type='Leave_Status' # NOTE: Add 'Leave_Status' to the choices in your Notification model
#             )
#     except Exception as e:
#         print(f"Failed to send approval notification: {e}")

# def approval_notification(leave_req_obj):

#     sender=RegistrationModel.objects.filter(EmployeeId=leave_req_obj.report_to.EmployeeId).first()
#     receiver=RegistrationModel.objects.filter(EmployeeId=leave_req_obj.employee.EmployeeId).first()

#     ad=leave_req_obj.approved_date if leave_req_obj.approved_date else timezone.localtime
#     # message=f"Dear {receiver.UserName}/{receiver.EmployeeId}\n your Applied Leave Verified by Reporting manager \n approval status {leave_req_obj.approved_status}\non {ad} Regards\nReporting Head",
    
#     if sender and receiver:
#         obj=Notification.objects.create(sender=sender, receiver=receiver, 
#             message=f"Dear {receiver.UserName}/{receiver.EmployeeId}\n your Applied Leave Verified by Reporting manager \n approval status `{leave_req_obj.approved_status}`\non {ad} Regards\nReporting Head",
#             candidate_id=None,not_type='Leave_Approval')

def approval_notification(leave_obj):
    try:
        sender_reg = RegistrationModel.objects.filter(EmployeeId=leave_obj.approved_by.EmployeeId).first()
        receiver_reg = RegistrationModel.objects.filter(EmployeeId=leave_obj.employee.EmployeeId).first()

        if sender_reg and receiver_reg:
            status_text = leave_obj.approved_status
            message = f"Your leave request from {leave_obj.from_date} to {leave_obj.to_date} has been {status_text}."

            Notification.objects.create(
                sender=sender_reg,
                receiver=receiver_reg,
                message=message,
                not_type='Leave_Status',
                reference_id=leave_obj.pk
            )
    except Exception as e:
        print(f"Failed to send approval notification: {e}")

class EmployeeLeaveRequestView(APIView):
    def get(self,request,emp_id):
        try:
            leave_obj=EmployeeLeaveTypesEligiblity.objects.filter(employee__EmployeeId=emp_id)
            serializer=EmployeeLeaveTypesEligiblitySerializer(leave_obj,many=True,context={'request': request})
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    #changes    
    # def post(self,request):
    #     try:
    #         request_data=request.data.copy()
    #         print(request_data)
    #         empid=EmployeeDataModel.objects.get(EmployeeId=request_data["employee"])
    #         request_data['employee']=empid.pk
    #         request_data['report_to']= empid.Reporting_To.pk if empid.Reporting_To else None
    #         request_data['approved_status']="pending"

    #         leave_request_serializer=LeaveRequestFormSerializer(data=request_data,context={'request': request})
    #         if leave_request_serializer.is_valid():
    #             emp_id=leave_request_serializer.validated_data["employee"]
    #             f_d=leave_request_serializer.validated_data["from_date"]
    #             t_d=leave_request_serializer.validated_data["to_date"]
                
    #             if LeaveRequestForm.objects.filter(employee=emp_id,approved_status="pending").exists():
    #                 return Response("Last Leave Request still on Pending",status=status.HTTP_400_BAD_REQUEST)
                
    #             elif LeaveRequestForm.objects.filter(employee=emp_id,approved_status="approved",from_date__lte=t_d,to_date__gte=f_d).exists():
    #                     return Response("Leave request overlaps with an existing approved leave", status=status.HTTP_400_BAD_REQUEST)       
    #             else:
    #                 instance=leave_request_serializer.save()

    #                 leave_obj=LeaveRequestForm.objects.filter(pk=instance.pk).first()
    #                 if leave_obj.restricted_leave_type:
    #                     leave_obj.restricted_leave_type.is_applied=True
    #                     leave_obj.restricted_leave_type.save()

    #                 # notification creation
    #                 applied_leave = leave_obj.LeaveType.LeaveType.leave_type.leave_name if leave_obj.LeaveType else leave_obj.restricted_leave_type.holiday.OccasionName

    #                 sender=RegistrationModel.objects.filter(EmployeeId=request_data["employee"]).first()
    #                 receiver=RegistrationModel.objects.filter(EmployeeId=empid.Reporting_To.EmployeeId).first()
    #                 obj=Notification.objects.create(sender=sender, receiver=receiver, 
    #                 message=f"{empid.Name} applied a {applied_leave}!\n from {leave_obj.from_date} to {leave_obj.to_date}\n on {leave_obj.applied_date}",
    #                 candidate_id=None,not_type='Leave_Apply')

    #                 if leave_obj.LeaveType and leave_obj.days > 2 and leave_obj.report_to.Designation != "HR":
                       
    #                     Emp_obj=EmployeeDataModel.objects.filter(Designation="HR").first()
    #                     receiver=RegistrationModel.objects.filter(EmployeeId=Emp_obj.EmployeeId).first()
    #                     obj=Notification.objects.create(sender=sender, receiver=receiver, 
    #                     message=f"{empid.Name} applied a {applied_leave}!\n from {leave_obj.from_date} to {leave_obj.to_date}\n on {leave_obj.applied_date}",
    #                     candidate_id=None,not_type='Leave Apply')

    #                 return Response(leave_request_serializer.data,status=status.HTTP_200_OK)
    #         else:
    #             print(leave_request_serializer.errors)
    #             return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    #     except Exception as e:
    #         print(e)
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def post(self,request):
        try:
            request_data=request.data.copy()
            print(request_data)
            empid=EmployeeDataModel.objects.get(EmployeeId=request_data["employee"])
            request_data['employee']=empid.pk
            request_data['report_to']= empid.Reporting_To.pk if empid.Reporting_To else None
            request_data['approved_status']="pending"

            leave_request_serializer=LeaveRequestFormSerializer(data=request_data,context={'request': request})
            if leave_request_serializer.is_valid():
                emp_id=leave_request_serializer.validated_data["employee"]
                f_d=leave_request_serializer.validated_data["from_date"]
                t_d=leave_request_serializer.validated_data["to_date"]
                
                if LeaveRequestForm.objects.filter(employee=emp_id,approved_status="pending").exists():
                    return Response("Last Leave Request still on Pending",status=status.HTTP_400_BAD_REQUEST)
                
                elif LeaveRequestForm.objects.filter(employee=emp_id,approved_status="approved",from_date__lte=t_d,to_date__gte=f_d).exists():
                        return Response("Leave request overlaps with an existing approved leave", status=status.HTTP_400_BAD_REQUEST)       
                else:
                    instance=leave_request_serializer.save()

                    leave_obj=LeaveRequestForm.objects.filter(pk=instance.pk).first()
                    if leave_obj.restricted_leave_type:
                        leave_obj.restricted_leave_type.is_applied=True
                        leave_obj.restricted_leave_type.save()

                    # notification creation
                    applied_leave = leave_obj.LeaveType.LeaveType.leave_type.leave_name if leave_obj.LeaveType else leave_obj.restricted_leave_type.holiday.OccasionName

                    sender = RegistrationModel.objects.filter(EmployeeId=request_data["employee"]).first()
                    receiver = RegistrationModel.objects.filter(EmployeeId=empid.Reporting_To.EmployeeId).first()

                    local_applied_date = timezone.localtime(leave_obj.applied_date)

                    formatted_date = local_applied_date.strftime("%Y-%m-%d %H:%M")

                    message_text = f"{empid.Name} applied for {applied_leave} from {leave_obj.from_date} to {leave_obj.to_date}."

                    obj = Notification.objects.create(
                        sender=sender, 
                        receiver=receiver, 
                        message=message_text,
                        candidate_id=None,
                        not_type='Leave_Apply',
                        reference_id=instance.pk
                    )

                    if leave_obj.LeaveType and leave_obj.days > 2 and leave_obj.report_to.Designation != "HR":
                       
                        Emp_obj=EmployeeDataModel.objects.filter(Designation="HR").first()
                        receiver=RegistrationModel.objects.filter(EmployeeId=Emp_obj.EmployeeId).first()
                        obj=Notification.objects.create(sender=sender, receiver=receiver, 
                        message=f"{empid.Name} applied a {applied_leave}!\n from {leave_obj.from_date} to {leave_obj.to_date}\n on {leave_obj.applied_date}",
                        candidate_id=None,not_type='Leave Apply')

                    return Response(leave_request_serializer.data,status=status.HTTP_200_OK)
            else:
                print(leave_request_serializer.errors)
                return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request):
        try:
           
            id = request.data.get("id")
            leave_request_obj = LeaveRequestForm.objects.filter(pk=id, approved_status="pending").first()
            if not leave_request_obj:
                return Response("Leaves are not available", status=status.HTTP_200_OK)
            
            data = request.data.copy()
            approvedby = data.get("approved_by")

            # Try to resolve approved_by to EmployeeDataModel.pk. Frontend may send either
            # - the employeeProfile PK (numeric), or
            # - the EmployeeId string (e.g. "MTM24EMP1E").
            emp_obj = None
            if approvedby is not None:
                # Try treating approvedby as profile PK first
                try:
                    emp_obj = EmployeeDataModel.objects.filter(employeeProfile__pk=approvedby).first()
                except Exception:
                    emp_obj = None

                # If not found, try matching by EmployeeId (string code)
                if not emp_obj:
                    try:
                        emp_obj = EmployeeDataModel.objects.filter(EmployeeId=approvedby).first()
                    except Exception:
                        emp_obj = None

            if emp_obj:
                data["approved_by"] = emp_obj.pk

            data['employee'] = leave_request_obj.employee.pk
            data["approved_date"] = timezone.localtime()

            leave_request_serializer = LeaveRequestFormSerializer(
                leave_request_obj, data=data, partial=True, context={'request': request}
            )

            if not leave_request_serializer.is_valid():
                return Response(leave_request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
            if leave_request_serializer.validated_data["approved_status"]=="pending":
                instance=leave_request_serializer.save()

                try:
                    if leave_request_obj.hr_status == "approved" and leave_request_obj.rm_status == "approved": 
                        leave_request_obj.approved_status="approved"
                        leave_request_obj.is_approved_by_hr=True
                        leave_request_obj.is_approved_by_rm=True
                        leave_request_obj.save()
                        self.approve_leave(leave_request_obj)
                        approval_notification(leave_request_obj) #changes - approval_notification
                        return Response("Leave Approved successfully", status=status.HTTP_200_OK)
                except:
                    pass

                try:
                    if leave_request_obj.hr_status == "rejected" and leave_request_obj.rm_status == "rejected": 
                        leave_request_obj.approved_status="rejected"
                        leave_request_obj.is_approved_by_hr=True
                        leave_request_obj.is_approved_by_rm=True
                        leave_request_obj.save()
                        self.cancel_leave(instance)
                        approval_notification(leave_request_obj)
                        return Response("Leave Rejected successfully", status=status.HTTP_200_OK)
                except:
                    pass
                    
                try:
                    hr_s=leave_request_serializer.validated_data["hr_status"]
                    if hr_s in ["approved",'rejected']:
                        # leave_request_obj.is_approved_by_hr=True
                        # leave_request_obj.save()
                        return Response(hr_s,status=status.HTTP_200_OK)
                except:
                    pass

                try:
                    rm_s=leave_request_serializer.validated_data["rm_status"]
                    if rm_s in ["approved",'rejected']:
                        # leave_request_obj.is_approved_by_rm=True
                        # leave_request_obj.save()
                        msg_dict={"m1":rm_s,"m2":leave_request_obj.hr_status}
                        return Response(msg_dict,status=status.HTTP_200_OK)
                except:
                    pass

                # return Response("unauthorised approve",status=status.HTTP_400_BAD_REQUEST)


            elif leave_request_serializer.validated_data["approved_status"] == "approved":
                
                self.approve_leave(leave_request_obj)
                instance = leave_request_serializer.save()
                approval_notification(leave_request_obj)
                return Response("Leave Approved successfully", status=status.HTTP_200_OK)
            else:

                instance = leave_request_serializer.save()
                self.cancel_leave(instance)
                approval_notification(leave_request_obj)
                return Response("Leave Rejected successfully", status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def approve_leave(self, leave_request_obj):
        days = leave_request_obj.days
        if leave_request_obj.LeaveType:
            leave_eligible_obj = EmployeeLeaveTypesEligiblity.objects.filter(
                employee=leave_request_obj.employee.pk, pk=leave_request_obj.LeaveType.pk
            ).first()
            monthly_leave_eligible_obj = MonthWiseLeavesModel.objects.filter(
                emp_Applicable_LT_Inst=leave_eligible_obj.pk, month=timezone.localdate().month, year__year=timezone.localdate().year
            ).first()

            if leave_request_obj.LeaveType.LeaveType.carry_forward and leave_request_obj.LeaveType.LeaveType.earned_leave:
                self.handle_carry_forward_leave(days, leave_eligible_obj, leave_request_obj)
            elif leave_request_obj.LeaveType.LeaveType.earned_leave:
                self.handle_earned_leave(days, leave_eligible_obj, monthly_leave_eligible_obj, leave_request_obj)
            else:
                self.handle_loss_of_pay(days, leave_request_obj)
        else:
            self.handle_restricted_leave(leave_request_obj)

    def handle_carry_forward_leave(self, days, leave_eligible_obj, leave_request_obj):
        fall_under = "Paid_Leave" if leave_request_obj.LeaveType.LeaveType.earned_leave else "Other Leave"
        leave_date = leave_request_obj.from_date
        eligible_leave_obj_id = None  # Initialize as None
        if int(days) <= leave_eligible_obj.Available_leaves:
            self.update_leave_eligibility(leave_eligible_obj, days)
            eligible_leave_obj_id = leave_eligible_obj.pk  # Store the eligible_leave_obj_id
            self.apply_leaves(leave_request_obj, days, leave_date, eligible_leave_obj_id, fall_under=fall_under)
        else:
            extra_days = days - leave_eligible_obj.Available_leaves
            al = leave_eligible_obj.Available_leaves
            eligible_leave_obj_id = leave_eligible_obj.pk  # Store the eligible_leave_obj_id
            self.apply_leaves(leave_request_obj, al, leave_date, eligible_leave_obj_id, fall_under=fall_under)
            self.update_leave_eligibility(leave_eligible_obj, al)
            leave_date += timedelta(days=al)
            self.handle_loss_of_pay(extra_days, leave_request_obj, leave_date)

    def handle_earned_leave(self, days, leave_eligible_obj, monthly_leave_eligible_obj, leave_request_obj):
        fall_under = "Paid_Leave" if leave_request_obj.LeaveType.LeaveType.earned_leave else "Other Leave"
        leave_date = leave_request_obj.from_date
        eligible_leave_obj_id = leave_eligible_obj.pk  # Store the eligible_leave_obj_id
        if int(days) <= monthly_leave_eligible_obj.leaves_count_per_month:
            monthly_leave_eligible_obj.leaves_count_per_month = 0
            monthly_leave_eligible_obj.save()
            self.update_leave_eligibility(leave_eligible_obj, days)
            self.apply_leaves(leave_request_obj, days, leave_date, eligible_leave_obj_id, fall_under=fall_under)
        else:
            extra_days = days - monthly_leave_eligible_obj.leaves_count_per_month
            self.apply_leaves(leave_request_obj, monthly_leave_eligible_obj.leaves_count_per_month, leave_date, eligible_leave_obj_id, fall_under=fall_under)
            available_leaves = leave_eligible_obj.Available_leaves - monthly_leave_eligible_obj.leaves_count_per_month
            leave_eligible_obj.Available_leaves = available_leaves
            leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves - available_leaves
            leave_eligible_obj.save()
            leave_date += timedelta(days=monthly_leave_eligible_obj.leaves_count_per_month)
            monthly_leave_eligible_obj.leaves_count_per_month = 0
            monthly_leave_eligible_obj.save()
            self.handle_loss_of_pay(extra_days, leave_request_obj, leave_date)

    def handle_loss_of_pay(self, days, leave_request_obj, leave_date=None):
        fall_under = "Unpaid_Leave"
        if leave_date is None:
            leave_date = leave_request_obj.from_date
        emp_id = leave_request_obj.employee.EmployeeId
        a = Loss_Off_Pay_Function(days, emp_id=emp_id)
        leave_type = a.LeaveType.leave_type.leave_name

        eligible_leave_obj_id=a.pk
        self.apply_leaves(leave_request_obj, days, leave_date, eligible_leave_obj_id,leave_type, fall_under=fall_under)

    def handle_restricted_leave(self, leave_request_obj):
        fall_under = "Restricted Leave"
        employee_id = leave_request_obj.employee.pk
        holiday_id = leave_request_obj.restricted_leave_type.holiday.pk
        leave_date = leave_request_obj.from_date
        leave_type = leave_request_obj.restricted_leave_type.holiday.leave_type
        eligible_leave_obj_id = None  # Restricted Leave doesn't have an eligible leave object
        self.apply_leaves(leave_request_obj, leave_request_obj.days, leave_date, eligible_leave_obj_id, leave_type, fall_under=fall_under)
        restrictes_leave_obj = AvailableRestrictedLeaves.objects.filter(
            employee__pk=employee_id, holiday__pk=holiday_id
        ).first()
        if restrictes_leave_obj:
            restrictes_leave_obj.is_utilised = True
            restrictes_leave_obj.utilised_date = timezone.localtime()
            restrictes_leave_obj.save()

    def apply_leaves(self, leave_request_obj, days, leave_date, eligible_leave_obj_id, leave_type=None, fall_under=None):
        if leave_type is None:
            leave_type = leave_request_obj.LeaveType.LeaveType.leave_type.leave_name

        for i in range(days):
            current_leave_type = leave_type
            if leave_type is None:
                if i < leave_request_obj.LeaveType.LeaveType.leaves_count_per_month:
                    current_leave_type = leave_request_obj.LeaveType.LeaveType.leave_type.leave_name
                else:
                    current_leave_type = "Loss of Pay"

            self.leaves_function(leave_date, leave_request_obj, current_leave_type, fall_under, eligible_leave_obj_id=eligible_leave_obj_id)
            leave_date += timedelta(days=1)

    def leaves_function(self, leave_date, leave_request, leave_type, fall_under, eligible_leave_obj_id):
        try:
            EmployeesLeavesmodel.objects.create(
                leave_request=leave_request,
                leave_date=leave_date,
                leave_type=leave_type,
                fall_under=fall_under,
                eligible_leave_obj_id=eligible_leave_obj_id  # Storing the eligible leave object ID
            )
        except Exception as e:
            print(f"Error in leaves_function: {str(e)}")

    def update_leave_eligibility(self, leave_eligible_obj, days):
        leave_eligible_obj.Available_leaves -= days
        leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves - leave_eligible_obj.Available_leaves
        leave_eligible_obj.save()

    def cancel_leave(self, leave_obj):
        if leave_obj.restricted_leave_type:
            leave_obj.restricted_leave_type.is_applied = False
            leave_obj.restricted_leave_type.save()


    # def patch(self,request):
    #     try:
    #         id=request.data.get("id")
    #         # leave_request_obj=LeaveRequestForm.objects.filter(employee__EmployeeId=employee_id,approved_status="pending").first()
    #         leave_request_obj=LeaveRequestForm.objects.filter(pk=id,approved_status="pending").first()
    #         if leave_request_obj:
    #             data = request.data.copy()

    #             approvedby=data["approved_by"]
    #             emp_obj=EmployeeDataModel.objects.filter(employeeProfile__pk=approvedby).first()

    #             if emp_obj:
    #                 data["approved_by"]=emp_obj.pk

    #             data['employee'] =  leave_request_obj.employee.pk
    #             days=leave_request_obj.days
    #             data["approved_date"]=timezone.localtime()
    #             leave_request_serializer=LeaveRequestFormSerializer(leave_request_obj,data=data,partial=True,context={'request': request})
    #             if leave_request_serializer.is_valid():
                    
    #                 if leave_request_serializer.validated_data["approved_status"]=="approved":
    #                     leave_req=LeaveRequestForm.objects.filter(pk=id).first()
    #                     if leave_req.LeaveType:
    #                         leave_eligible_obj=EmployeeLeaveTypesEligiblity.objects.filter(employee=leave_request_obj.employee.pk,pk=leave_request_obj.LeaveType.pk).first()
    #                         monthly_leave_eligible_obj=MonthWiseLeavesModel.objects.filter(emp_Applicable_LT_Inst=leave_eligible_obj.pk,month=timezone.localdate().month,year__year=timezone.localdate().year).first()
                    
    #                         if leave_request_obj.LeaveType.LeaveType.carry_forward and leave_request_obj.LeaveType.LeaveType.earned_leave:
    #                             # here the carry forword logic has to write
    #                             if int(days)<=leave_eligible_obj.Available_leaves:
                                    
    #                                 leave_eligible_obj.Available_leaves=leave_eligible_obj.no_of_leaves-int(days)
    #                                 leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves-leave_eligible_obj.Available_leaves
    #                                 leave_eligible_obj.save()

    #                                 leave_date=leave_req.from_date
    #                                 leave_type=leave_req.LeaveType.LeaveType.leave_type.leave_name
    #                                 for i in range(1,days+1):
    #                                     leaves_function(leave_date, leave_req,leave_type)
    #                                     leave_date = leave_req.from_date + timedelta(days=i)

    #                             else:
    #                                 extra_days=days-leave_eligible_obj.Available_leaves

    #                                 al=leave_eligible_obj.Available_leaves
    #                                 leave_date=leave_req.from_date
    #                                 leave_type=leave_req.LeaveType.LeaveType.leave_type.leave_name
    #                                 for i in range(1,al+1):
    #                                     leaves_function(leave_date, leave_req, leave_type)
    #                                     leave_date = leave_req.from_date + timedelta(days = i)

    #                                 leave_eligible_obj.Available_leaves=leave_eligible_obj.no_of_leaves-leave_eligible_obj.utilised_leaves
    #                                 leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves
    #                                 leave_eligible_obj.save()
                                
    #                                 a=Loss_Off_Pay_Function(extra_days)
    #                                 leave_type=a.LeaveType.leave_type.leave_name
    #                                 for i in range(1,extra_days+1):
    #                                     leaves_function(leave_date, leave_req,leave_type)

    #                         elif leave_request_obj.LeaveType.LeaveType.earned_leave:
    #                             # here the earned logic has to write
    #                             if int(days)<=monthly_leave_eligible_obj.leaves_count_per_month:
    #                                 monthly_leave_eligible_obj.leaves_count_per_month=0
    #                                 monthly_leave_eligible_obj.save()

    #                                 leave_eligible_obj.Available_leaves=leave_eligible_obj.no_of_leaves-int(days)
    #                                 leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves-leave_eligible_obj.Available_leaves
    #                                 leave_eligible_obj.save()

    #                                 leave_date=leave_req.from_date
    #                                 leave_type=leave_req.LeaveType.LeaveType.leave_type.leave_name
    #                                 for i in range(1,days+1):
    #                                     leaves_function(leave_date, leave_req,leave_type)
    #                                     leave_date = leave_req.from_date + timedelta(days=i)
                                    
    #                             else:
    #                                 extra_days=days-monthly_leave_eligible_obj.leaves_count_per_month

    #                                 al=leave_eligible_obj.Available_leaves
    #                                 leave_date=leave_req.from_date
    #                                 leave_type=leave_req.LeaveType.LeaveType.leave_type.leave_name
    #                                 for i in range(1,al+1):
    #                                     leaves_function(leave_date, leave_req, leave_type)
    #                                     leave_date = leave_req.from_date + timedelta(days = i)

    #                                 available_leaves = leave_eligible_obj.no_of_leaves - monthly_leave_eligible_obj.leaves_count_per_month
    #                                 leave_eligible_obj.Available_leaves = available_leaves
    #                                 leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves - available_leaves
    #                                 leave_eligible_obj.save()

    #                                 monthly_leave_eligible_obj.leaves_count_per_month=0
    #                                 monthly_leave_eligible_obj.save()

    #                                 a=Loss_Off_Pay_Function(extra_days)
    #                                 leave_type=a.LeaveType.leave_type.leave_name
    #                                 for i in range(1,extra_days+1):
    #                                     leaves_function(leave_date, leave_req,leave_type)

    #                         else:
    #                             extra_days=days
    #                             a=Loss_Off_Pay_Function(extra_days)
    #                             leave_type=a.LeaveType.leave_type.leave_name
    #                             for i in range(1,extra_days+1):
    #                                 leaves_function(leave_date, leave_req,leave_type)

    #                     else:
    #                         employee_id = leave_request_obj.employee.pk
    #                         holiday_id = leave_request_obj.restricted_leave_type.holiday.pk

    #                         leave_date=leave_request_obj.from_date
    #                         leave_type=leave_request_obj.restricted_leave_type.holiday.leave_type
    #                         for i in range(1,days+1):
    #                             leaves_function(leave_date, leave_req,leave_type)
    #                             leave_date = leave_req.from_date + timedelta(days=i)
                            
    #                         restrictes_leave_obj = AvailableRestrictedLeaves.objects.filter(
    #                                 employee__pk=employee_id,
    #                                 holiday__pk=holiday_id
    #                             ).first()

    #                         if restrictes_leave_obj:
    #                             restrictes_leave_obj.is_utilised=True
    #                             restrictes_leave_obj.utilised_date=timezone.localtime()
    #                             restrictes_leave_obj.save()

    #                     instance=leave_request_serializer.save()
    #                     return Response("Leave Approved successfully",status=status.HTTP_200_OK)
    #                 else:
    #                     instance=leave_request_serializer.save()
    #                     leave_obj=LeaveRequestForm.objects.filter(pk=instance.pk).first()
    #                     if leave_obj.restricted_leave_type:
    #                         leave_obj.restricted_leave_type.is_applied=False
    #                         leave_obj.restricted_leave_type.save()
    #                     return Response("Leave Cancled successfully",status=status.HTTP_200_OK)
    #             else:
    #                 return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    #         else:
    #             return Response("Leaves are not available",status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)


class LeavesRequestHandlingByAdmin(APIView):
    def patch(self,request):
        try:
            id=request.data.get("id")
            leave_request_obj=LeaveRequestForm.objects.filter(pk=id,approved_status="approved").first()#approved_status="approved"
            if leave_request_obj:
                data = request.data.copy()
                approvedby = data.get("approved_by")
                emp_obj = None
                if approvedby is not None:
                    try:
                        emp_obj = EmployeeDataModel.objects.filter(employeeProfile__pk=approvedby).first()
                    except Exception:
                        emp_obj = None
                    if not emp_obj:
                        try:
                            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=approvedby).first()
                        except Exception:
                            emp_obj = None

                if emp_obj:
                    data["approved_by"] = emp_obj.pk

                data['employee'] =  leave_request_obj.employee.pk
                days=leave_request_obj.days
                data["approved_date"]=timezone.localtime()
                leave_request_serializer=LeaveRequestFormSerializer(leave_request_obj,data=data,partial=True,context={'request': request})
                if leave_request_serializer.is_valid():
                   
                    if leave_request_serializer.validated_data["approved_status"]=="approved":
                        # print("hellooooo2")
                        # target_view = EmployeeLeaveRequestView()
                        # response = target_view.patch(request)  # Pass the original request object
                        # return response
                        return Response("Request aldredy in Approved status")
                    
                    if leave_request_serializer.validated_data["approved_status"]=="rejected":
                        instance=leave_request_serializer.save()
                        f_data=instance.from_date
                        t_date=instance.to_date
                        emp_leave_objs = EmployeesLeavesmodel.objects.filter(leave_request__pk=id,
                                                                leave_date__range=(f_data, t_date))
                        for leave_typ in emp_leave_objs:
                            leave_type_obj=EmployeeLeaveTypesEligiblity.objects.get(pk=leave_typ.eligible_leave_obj.pk)

                            if leave_type_obj.LeaveType.carry_forward and leave_type_obj.LeaveType.earned_leave:
                                leave_type_obj.utilised_leaves -= 1
                                leave_type_obj.Available_leaves += 1
                                leave_type_obj.save()
                                
                            elif leave_type_obj.LeaveType.earned_leave:
                            
                                leave_type_obj.utilised_leaves -= 1
                                leave_type_obj.Available_leaves += 1
                                leave_type_obj.save()

                                current_year=timezone.localdate().year
                                current_month=timezone.localdate().month
                                ml_obj=MonthWiseLeavesModel.objects.get(emp_Applicable_LT_Inst__pk=leave_type_obj.pk,month=current_month,year__year=current_year)
                                ml_obj.leaves_count_per_month += 1
                                ml_obj.save()

                            else:
                                leave_type_obj.utilised_leaves -= 1
                                leave_type_obj.save()
                            leave_typ.delete()

                        return Response("Request Rejected successfully!")
                else:
                    return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
                    
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

class AppliedLeaveVerification(APIView):
    def patch(self,request,leave_req_id):
        data=request.data.copy()
        login_user=request.data.get("login_user")
        leave_req_obj=LeaveRequestForm.objects.get(pk=leave_req_id)
        admin=EmployeeDataModel.objects.get(EmployeeId=login_user)
        if leave_req_obj.employee.Reporting_To==login_user:
            if data["is_approved_by_rm"]=="approved":  
                leave_req_obj.is_approved_by_rm=True
            else:
                leave_req_obj.is_approved_by_rm=False
                # leave_req_obj.approved_status="rejected"
                # leave_req_obj.approved_by=leave_req_obj.employee.Reporting_To.pk
                # leave_req_obj.approved_date=timezone.localtime()
            leave_req_obj.rm_approved_date=timezone.localtime()
            leave_req_obj.save()

        elif admin.Designation=="HR" :
            if data["is_approved_by_hr"]=="approved":  
                leave_req_obj.is_approved_by_hr=True
            else:
                leave_req_obj.is_approved_by_hr=False
                # leave_req_obj.approved_status="rejected"
                # leave_req_obj.approved_by=admin.pk
                # leave_req_obj.approved_date=timezone.localtime()
            leave_req_obj.hr_approved_date=timezone.localtime()
            leave_req_obj.save()

class LeaveWithDrawnViewFunction(APIView):
    def patch(self,request,leave_req_id,withdraw=None):
        login_user=request.data.get("login_user")
        leave_req_obj=LeaveRequestForm.objects.get(pk=leave_req_id)
        admin=EmployeeDataModel.objects.get(EmployeeId=login_user)

        if (admin.Designation=="HR" or leave_req_obj.employee.Reporting_To==login_user) and withdraw==None:

            data=request.data.copy()
            if data["is_approved_by_hr"]=="approved":  
                leave_req_obj.is_approved_by_hr=True
            else:

                leave_req_obj.is_approved_by_hr=False
                leave_req_obj.approved_status="rejected"
                leave_req_obj.approved_by=admin.pk
                leave_req_obj.approved_date=timezone.localtime()
                # mail has to sent
            leave_req_obj.hr_approved_date=timezone.localtime()
            leave_req_obj.save()
        else:
            data=request.data.copy()
            if leave_req_obj.approved_status=="pending":
                data["Leave_Withdrawn"]=True
                data["approved_status"]="canceled"
                data["Withdrawn_Date"]=timezone.localtime()
                leave_cancle_serializer=LeaveRequestFormSerializer(leave_req_obj,data=data,context={"request":request},partial=True)
                if leave_cancle_serializer.is_valid():
                    instance=leave_cancle_serializer.save()

                    leave_obj=LeaveRequestForm.objects.filter(pk=instance.pk).first()
                    if leave_obj.restricted_leave_type:
                        leave_obj.restricted_leave_type.is_applied=False
                        leave_obj.restricted_leave_type.save()
                    return Response("Leave Withdraw Successfull",status=status.HTTP_200_OK)
                else:
                    print(leave_cancle_serializer.errors)
                    return Response(leave_cancle_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("Leave Process Completed!")
        
    # def get(self,request,emp_id):
    #     try:
    #         leave_requests=LeaveRequestForm.objects.filter(employee__EmployeeId=emp_id)
    #         serializer=LeaveRequestFormSerializer(leave_requests,many=True)
    #         return Response(serializer.data,status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    def get(self,request,emp_id):
        try:
            leave_requests=LeaveRequestForm.objects.filter(employee__EmployeeId=emp_id)
            # serializer=LeaveRequestFormSerializer(leave_requests,many=True)
            leaves_history=[]
            for leave_req in leave_requests:
                serializer=LeaveRequestFormSerializer(leave_req).data
                duration_days=EmployeesLeavesmodel.objects.filter(leave_request__pk=leave_req.pk)
                duration_serializer=EmployeeLeavesStoringSerializer(duration_days,many=True).data
                serializer.update({"leave_clasification":duration_serializer})
                leaves_history.append(serializer)
            return Response(leaves_history,status=status.HTTP_200_OK)
            # return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

class ReportingTeamLeavesHistory(APIView):
    def get(self,request,emp_id):
        try:
            emp_obj=EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()
            is_reporting_manager=EmployeeDataModel.objects.filter(Reporting_To__EmployeeId=emp_id).exists()
            if emp_obj.Designation in ["HR","Admin"]:
                leave_requests=LeaveRequestForm.objects.all()
                serializer=LeaveRequestFormSerializer(leave_requests,many=True)
            elif is_reporting_manager:
                leave_requests=LeaveRequestForm.objects.filter(report_to__EmployeeId=emp_id)
                serializer=LeaveRequestFormSerializer(leave_requests,many=True)
            else:
                serializer={}
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e))
        
from django.db.models import Q     
class WeeklyLeavesApprovalsList(APIView):
    def get(self, request, emp_id):
        try:
            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()
            is_reporting_manager=EmployeeDataModel.objects.filter(Reporting_To__EmployeeId=emp_id).exists()
            if emp_obj.Designation in ["HR", "Admin"]:
                current_date = timezone.localtime().date()
                future_date = current_date + timezone.timedelta(days=7)
                leave_requests = LeaveRequestForm.objects.filter(
                    Q(approved_status="approved") &
                    (
                        Q(from_date__range=[current_date, future_date]) |
                        Q(to_date__range=[current_date, future_date]) |
                        (Q(from_date__lte=current_date) & Q(to_date__gte=future_date))
                    )
                )
                serializer = LeaveRequestFormSerializer(leave_requests, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif is_reporting_manager:
                current_date = timezone.localtime().date()
                future_date = current_date + timezone.timedelta(days=7)
                leave_requests = LeaveRequestForm.objects.filter(
                    Q(approved_status="approved") &
                    (
                        Q(from_date__range=[current_date, future_date]) |
                        Q(to_date__range=[current_date, future_date]) |
                        (Q(from_date__lte=current_date) & Q(to_date__gte=future_date))
                    ) & 
                    Q (report_to__EmployeeId=emp_id)
                )
                serializer = LeaveRequestFormSerializer(leave_requests, many=True, context={'request': request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:        
                return Response({"detail": "Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class Employee_Leaves_Conversation(APIView):
    def get(self,request,leave_req_id):
        try:
            leave_request_obj = LeaveRequestForm.objects.filter(pk=leave_req_id, approved_status="pending").first()
            if not leave_request_obj:
                return Response("Leaves are not available", status=status.HTTP_200_OK)
            
            if (leave_request_obj.rm_status == None or leave_request_obj.rm_status == "approved") and (leave_request_obj.hr_status ==None or leave_request_obj.hr_status == "rejected"):
                
                leave_request_obj.hr_status=None
                leave_request_obj.is_approved_by_hr=False
                leave_request_obj.save()
                return Response("activated HR leaves approval action",status=status.HTTP_200_OK)
            
            # elif leave_request_obj.rm_status == "rejected" and leave_request_obj.hr_status == "approved":
            elif (leave_request_obj.rm_status == None or leave_request_obj.rm_status == "rejected") and (leave_request_obj.hr_status ==None or leave_request_obj.hr_status == "approved"):
                leave_request_obj.hr_status=None
                leave_request_obj.is_approved_by_hr=False
                leave_request_obj.save()
                return Response("activated HR leaves approval action",status=status.HTTP_200_OK)
            else:
                return Response("Acction not be done !",status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

   
class EmployeeLeavesPendingView(APIView):
    def get(self,request,login_user=None,report_emp=None):
        if login_user:
            try:
                pending_leaves=LeaveRequestForm.objects.filter(employee__EmployeeId=login_user,approved_status="pending")
                pending_leaves_serializers=LeaveRequestFormSerializer(pending_leaves,many=True,context={'request': request})
                return Response(pending_leaves_serializers.data,status=status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        else:
            
            try:
                emp_obj = EmployeeDataModel.objects.filter(EmployeeId=report_emp).first()
                pending_leaves = LeaveRequestForm.objects.filter(
                    Q(approved_status="pending", report_to__EmployeeId=report_emp,is_approved_by_rm=False) 
                )
                
                # Additional filtering if the employee is HR
                if emp_obj and emp_obj.Designation == "HR":
                    hr_additional_leaves = LeaveRequestForm.objects.filter(
                        Q(days__gt=2, approved_status="pending",is_approved_by_hr=False) |
                        Q(report_to__EmployeeId=report_emp, approved_status="pending")
                    )
                    pending_leaves = pending_leaves | hr_additional_leaves

                pending_leaves_serializers = LeaveRequestFormSerializer(
                    pending_leaves.distinct(),
                    many=True,
                    context={'request': request, 'report_emp': report_emp}
                )

                return Response(pending_leaves_serializers.data, status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
            
    def patch(self, request):
        try:
            id = request.data.get("id")
            request_data=request.data.copy()
            request_data["hr_approved_date"]=timezone.localtime()
            leave_request_obj = LeaveRequestForm.objects.filter(pk=id, approved_status="pending").first()
            
            if leave_request_obj:
                serializer = LeaveRequestFormSerializer(leave_request_obj, data=request_data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({"error": "Leave request not found or not pending"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)



class EmployeeCompanyHolidays(APIView):
    def get(self,request,login_user):
        try:
            current_year=timezone.localdate().year
            holidays=AvailableRestrictedLeaves.objects.filter(employee__EmployeeId=login_user,holiday__Date__year=current_year)
            holidays_serializer=AvailableRestrictedLeavesSerializer(holidays,many=True).data
            return Response(holidays_serializer,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
from calendar import month_name,day_name
import calendar

class CompanyHolidaysDataModelView(APIView):
    def get(self, request, year=None,display_by=None):
        try:
            if display_by == "Department":
                pass
            elif display_by == "reporting_To":# if the login employee is a rm means under his who are all employees is there that data will display
                pass
            elif display_by == "reporting_To_Team": # in this login employee reporting team employees calender can see
                pass
            else:
                pass

            login_emp = request.GET.get("login_emp")
            if not login_emp:
                return Response("Login employee and duration are mandatory", status=status.HTTP_400_BAD_REQUEST)

            # Fetch the employee object
            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=login_emp).first()
            if not emp_obj:
                return Response("Login employee does not exist", status=status.HTTP_400_BAD_REQUEST)
            
            emp_dep=emp_obj.Position.Department

            current_year = timezone.localdate().year
            year = year if year else current_year

            # Create a dictionary to store holidays and week-offs by month from calendar import month_name
            holidays_by_month = {month: {"holidays": [],"restricted_holidays": [], "weekoffs": []} for month in month_name if month}

            # Fetch holidays for the given year
            holidays = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave",Date__year=year)
            holiday_serializer = CompanyHolidaysDataModelSerializer(holidays, many=True)

            # Populate holidays in the dictionary
            for holiday in holiday_serializer.data:
                month = holiday['Date'].split('-')[1]  # Extract month from the date (YYYY-MM-DD) ["2024","09","07"]
                month_name_str = month_name[int(month)]
                holidays_by_month[month_name_str]["holidays"].append(holiday)

            emp_restricted_leaves=AvailableRestrictedLeaves.objects.filter(employee=emp_obj , Date__year=year)
            restricted_holiday_serializer = AvailableRestrictedLeavesSerializer(emp_restricted_leaves, many=True)

            for restric_leave in restricted_holiday_serializer.data:
                month=restric_leave['Date'].split('-')[1]
                month_name_str = month_name[int(month)]
                holidays_by_month[month_name_str]["restricted_holidays"].append(restric_leave)

            # Fetch week-offs for the employee for the given year
            employee_weekoffs = EmployeeWeekoffsModel.objects.filter(employee_id=emp_obj, year=year)

            # Iterate over the employee week-offs and populate the dictionary
            for weekoff in employee_weekoffs:
                month_name_str = month_name[weekoff.month]  # Get the name of the month
                weekoff_days = weekoff.weekoff_days.all()  # Get the related WeekOffDay objects
                
                # Find all dates for the given month 
                _, num_days = calendar.monthrange(weekoff.year, weekoff.month) 
                # print(f"this weekday {day_name[_]} and noof days is {num_days}") 
                # here calendar.monthrange function will return two values one is weekday and no.of days for that month  here we dont want the weekday

                # Iterate through each day of the month
                for day in range(1, num_days + 1):
                    date = datetime(year=weekoff.year, month=weekoff.month,day=day)
                    weekday_str = date.strftime('%A').lower()  # Get the day of the week (e.g., 'monday')
                    
                    # Check if this date is a week-off day
                    if weekoff_days.filter(day=weekday_str).exists():
                        holidays_by_month[month_name_str]["weekoffs"].append({
                            "date": date.strftime('%Y-%m-%d'),  # Add the date
                            "day": weekday_str.capitalize()  # Add the week-off day
                        })

            # Create the final list of dictionaries for the response
           
            response_data = [
                {"month_name": month, "holidays": data["holidays"], "restricted_holidays": data["restricted_holidays"], "weekoffs": data["weekoffs"]}
                for month, data in holidays_by_month.items()
            ]

            return Response(response_data)

        except Exception as e:
            return Response({"error": str(e)}, status=500)

    def post(self,request):
        data = request.data.copy()
        added_emp=EmployeeDataModel.objects.get(EmployeeId=data["added_By"])
        data["added_By"]=added_emp.pk

        serializer =  CompanyHolidaysDataModelSerializer(data=data)
        if serializer.is_valid():
            
            instance = serializer.save()
            if instance.Religion:
                EPIO = EmployeePersonalInformation.objects.filter(religion__pk=instance.Religion.pk)
                for emp in EPIO:
                    emp_obj=EmployeeDataModel.objects.filter(employeeProfile__pk=emp.EMP_Information.pk).first()
                    if emp_obj:
                        AvailableRestrictedLeaves.objects.create(
                        holiday = instance,
                        employee = emp_obj,
                        )
            return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            print(serializer.errors)
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self,request):
        data = request.data.copy()
        try:
            com_leave_obj=CompanyHolidaysDataModel.objects.get(pk=data["id"])
            serializer =  CompanyHolidaysDataModelSerializer(com_leave_obj,data=data,partial=True)

            if serializer.is_valid():
                arl_obj=AvailableRestrictedLeaves.objects.filter(holiday__pk=com_leave_obj.pk).first()
                instance = serializer.save()
                return Response("Holiday got Updated !",status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        

class AvailableRestrictedLeavesRequestView(APIView):
    def post(self,request):
        try:
            request_data=request.data.copy()
            empid=EmployeeDataModel.objects.get(EmployeeId=request_data["employee"])
            request_data['employee']=empid.pk
            request_data['report_to']=empid.Reporting_To.pk
            request_data['approved_status']="pending"
            leave_request_serializer=LeaveRequestFormSerializer(data=request_data,context={'request': request})
            if leave_request_serializer.is_valid():
                emp_id=leave_request_serializer.validated_data["employee"]
                if LeaveRequestForm.objects.filter(employee=emp_id,approved_status="pending").exists():
                    return Response("Last Leave Request still on Pending",status=status.HTTP_400_BAD_REQUEST)
                else:
                    instance=leave_request_serializer.save()
                    Holiday_obj=AvailableRestrictedLeaves.objects.filter(pk=instance.restricted_leave_type.pk).first()  
                    Holiday_obj.is_applied=True
                    Holiday_obj.save()
                    return Response(leave_request_serializer.data,status=status.HTTP_200_OK)
            else:
                print(leave_request_serializer.errors)
                return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
# weekoff creating to Employees

class WeekOffDayViewSet(viewsets.ModelViewSet):
    queryset = WeekOffDay.objects.all()
    serializer_class = WeekOffDaySerializer

class EmployeeWeekoffsModelViewSet(viewsets.ModelViewSet):
    queryset = EmployeeWeekoffsModel.objects.all()
    serializer_class = EmployeeWeekoffsModelSerializer

# class EmployeeLeaveRequestView(APIView):
    # def patch(self, request):
    #     try:
    #         id = request.data.get("id")
    #         leave_request_obj = LeaveRequestForm.objects.filter(pk=id, approved_status="pending").first()
    #         if leave_request_obj:
    #             data = request.data.copy()
    #             approvedby = data["approved_by"]
    #             emp_obj = EmployeeDataModel.objects.filter(employeeProfile__pk=approvedby).first()

    #             if emp_obj:
    #                 data["approved_by"] = emp_obj.pk

    #             data['employee'] = leave_request_obj.employee.pk
    #             days = leave_request_obj.days
    #             data["approved_date"] = timezone.localtime()
    #             leave_request_serializer = LeaveRequestFormSerializer(leave_request_obj, data=data, partial=True, context={'request': request})

    #             if leave_request_serializer.is_valid():
    #                 if leave_request_serializer.validated_data["approved_status"] == "approved":
    #                     leave_req = LeaveRequestForm.objects.filter(pk=id).first()
    #                     if leave_req.LeaveType:
    #                         leave_eligible_obj = EmployeeLeaveTypesEligiblity.objects.filter(employee=leave_request_obj.employee.pk, pk=leave_request_obj.LeaveType.pk).first()
    #                         monthly_leave_eligible_obj = MonthWiseLeavesModel.objects.filter(emp_Applicable_LT_Inst=leave_eligible_obj.pk, month=timezone.localdate().month, year=timezone.localdate().year).first()

    #                         if leave_request_obj.LeaveType.LeaveType.carry_forward and leave_request_obj.LeaveType.LeaveType.earned_leave:
    #                             if int(days) <= leave_eligible_obj.Available_leaves:
    #                                 leave_eligible_obj.Available_leaves = leave_eligible_obj.no_of_leaves - int(days)
    #                                 leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves - leave_eligible_obj.Available_leaves
    #                                 leave_eligible_obj.save()

    #                                 leaves_function(leave_req.from_date, leave_req.to_date, leave_req, leave_req.LeaveType.LeaveType.leave_name)

    #                             else:
    #                                 extra_days = days - leave_eligible_obj.Available_leaves
    #                                 leave_eligible_obj.Available_leaves = 0
    #                                 leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves
    #                                 leave_eligible_obj.save()

    #                                 leaves_function(leave_req.from_date, leave_req.from_date + timezone.timedelta(days=leave_eligible_obj.Available_leaves - 1), leave_req, leave_req.LeaveType.LeaveType.leave_name)
    #                                 Loss_Off_Pay_Function(extra_days, leave_req)

    #                         elif leave_request_obj.LeaveType.LeaveType.earned_leave:
    #                             if int(days) <= monthly_leave_eligible_obj.leaves_count_per_month:
    #                                 monthly_leave_eligible_obj.leaves_count_per_month = 0
    #                                 monthly_leave_eligible_obj.save()
    #                                 leave_eligible_obj.Available_leaves = leave_eligible_obj.no_of_leaves - int(days)
    #                                 leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves - leave_eligible_obj.Available_leaves
    #                                 leave_eligible_obj.save()

    #                                 leaves_function(leave_req.from_date, leave_req.to_date, leave_req, leave_req.LeaveType.LeaveType.leave_name)
    #                             else:
    #                                 extra_days = days - monthly_leave_eligible_obj.leaves_count_per_month
    #                                 available_leaves = leave_eligible_obj.no_of_leaves - monthly_leave_eligible_obj.leaves_count_per_month
    #                                 leave_eligible_obj.Available_leaves = available_leaves
    #                                 leave_eligible_obj.utilised_leaves = leave_eligible_obj.no_of_leaves - available_leaves
    #                                 leave_eligible_obj.save()
    #                                 monthly_leave_eligible_obj.leaves_count_per_month = 0
    #                                 monthly_leave_eligible_obj.save()

    #                                 leaves_function(leave_req.from_date, leave_req.from_date + timezone.timedelta(days=monthly_leave_eligible_obj.leaves_count_per_month - 1), leave_req, leave_req.LeaveType.LeaveType.leave_name)
    #                                 Loss_Off_Pay_Function(extra_days, leave_req)

    #                         else:
    #                             extra_days = days
    #                             Loss_Off_Pay_Function(extra_days, leave_req)

    #                         # Store each leave date in EmployeesLeavesmodel
    #                         leaves_function(leave_req.from_date, leave_req.to_date, leave_req, leave_req.LeaveType.LeaveType.leave_name)

    #                     else:
    #                         employee_id = leave_request_obj.employee.pk
    #                         holiday_id = leave_request_obj.restricted_leave_type.holiday.pk
    #                         restrictes_leave_obj = AvailableRestrictedLeaves.objects.filter(employee__pk=employee_id, holiday__pk=holiday_id).first()

    #                         if restrictes_leave_obj:
    #                             restrictes_leave_obj.is_utilised = True
    #                             restrictes_leave_obj.utilised_date = timezone.localtime()
    #                             restrictes_leave_obj.save()

    #                     instance = leave_request_serializer.save()
    #                     return Response("Leave Approved successfully", status=status.HTTP_200_OK)
    #                 else:
    #                     instance = leave_request_serializer.save()
    #                     leave_obj = LeaveRequestForm.objects.filter(pk=instance.pk).first()
    #                     if leave_obj.restricted_leave_type:
    #                         leave_obj.restricted_leave_type.is_applied = False
    #                         leave_obj.restricted_leave_type.save()
    #                     return Response("Leave Cancled successfully", status=status.HTTP_200_OK)
    #             else:
    #                 return Response(leave_request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    #         else:
    #             return Response("Leaves are not available", status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    



# ///////////////////////////////////////////////****************////////////////////////////////////


#displayying types of leaves  available for each employee

class EmployeesAvailableLeavesView(APIView):
    def get(self,request,emp_id):
        try:
            available_leaves=EmployeeLeaveTypesEligiblity.objects.filter(employee__EmployeeId=emp_id)
            available_leaves_serializer=EmployeeLeaveTypesEligiblitySerializer(available_leaves,many=True)
            return Response(available_leaves_serializer.data,status=status.HTTP_200_OK)
            # available_leaves_details={}
            # for leave_type in available_leaves:
            #     leave_obj=LeavesTypeDetailModel.objects.get(id=leave_type.LeaveType.pk)
            #     leave_serializer=LeaveTypeDetailSerializer(leave_obj).data
            #     available_leaves_details.update({leave_obj.leave_type.leave_name:leave_serializer})
            # return Response(available_leaves_details,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        

# def patch(self,request):
    #     try:
    #         employee_id=request.data.get("employee")
    #         leave_request_obj=LeaveRequestForm.objects.filter(employee__EmployeeId=employee_id,approved_status="pending").first()
    #         if leave_request_obj:
    #             data = request.data.copy()
    #             data['employee'] =  EmployeeDataModel.objects.get(EmployeeId=employee_id).pk
    #             leave_request_serializer=LeaveRequestFormSerializer(leave_request_obj,data=data,partial=True,context={'request': request})
    #             if leave_request_serializer.is_valid():
    #                 if leave_request_serializer.validated_data["approved_status"]=="approved":
    #                     instance=leave_request_serializer.save()

    #                     leave_eligible_obj=EmployeeLeaveTypesEligiblity.objects.filter(pk=instance.LeaveType.pk,employee=instance.employee).first()
    #                     days=request.data.get("days")
    #                     monthly_leave_eligible_obj=MonthWiseLeavesModel.objects.get(emp_Applicable_LT_Inst=leave_eligible_obj.pk,month=timezone.localdate().month,year__year=timezone.localdate().year)
    #                     if int(days)<=monthly_leave_eligible_obj.leaves_count_per_month:
    #                         monthly_leave_eligible_obj.leaves_count_per_month=0
    #                         monthly_leave_eligible_obj.save()
    #                         leave_eligible_obj.Available_leaves=leave_eligible_obj.no_of_leaves-int(days)
    #                         leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves-leave_eligible_obj.Available_leaves
    #                         leave_eligible_obj.save()
    #                         return Response("Leave Approved Successfully",status=status.HTTP_200_OK)
    #                     else:
    #                         # leave_eligible_obj.Available_leaves=0
    #                         monthly_leave_eligible_obj.leaves_count_per_month=0
    #                         monthly_leave_eligible_obj.save()

    #                         leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves
    #                         leave_eligible_obj.save()

    #                         if EmployeeLeaveTypesEligiblity.objects.filter(LeaveType__leave_type__leave_name="Unpaid_Leave").exists():
    #                             unpaid_Leave_obj=EmployeeLeaveTypesEligiblity.objects.filter(LeaveType__leave_type__leave_name="Unpaid_Leave").first()
    #                             unpaid_Leave_obj.utilised_leaves=unpaid_Leave_obj.utilised_leaves+int(days)
    #                             unpaid_Leave_obj.save()
    #                             return Response("Unpaid Leave Approved Successfully",status=status.HTTP_200_OK)
    #                         else:
    #                             LT_Obj=LeaveTypesModel.objects.create(leave_name="Unpaid_Leave")
    #                             LTD_Obj=LeavesTypeDetailModel.objects.create(leave_type=LT_Obj)
    #                             emp_obj=EmployeeDataModel.objects.get(EmployeeId=instance.employee.EmployeeId)
    #                             Emp_Eligible_obj=EmployeeLeaveTypesEligiblity.objects.create(employee=emp_obj,LeaveType=LTD_Obj)

    #                             Emp_Eligible_obj.utilised_leaves=leave_eligible_obj.utilised_leaves-int(days)
    #                             Emp_Eligible_obj.save()
                                
    #                             msg_dict={"message1":"Leave Approved Successfully",
    #                                     "message2":f"utilised all {leave_eligible_obj.LeaveType.leave_type.leave_name} from now this leave fall under Unpaid Leaves Category." }
    #                             return Response(msg_dict,status=status.HTTP_200_OK)
    #                 return Response("Leave Canclled Successfully",status=status.HTTP_200_OK)
    #             return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
    #         return Response("Leave Request is not Pending",status=status.HTTP_400_BAD_REQUEST)
                                
    #     except Exception as e:
    #         print(e)
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

 # def patch(self,request):
    #     try:
    #         employee_id=request.data.get("employee")
    #         leave_request_obj=LeaveRequestForm.objects.filter(employee__EmployeeId=employee_id,approved_status="pending").first()
            
    #         data = request.data.copy()
    #         data['employee'] =  EmployeeDataModel.objects.get(EmployeeId=employee_id).pk
    #         leave_request_serializer=LeaveRequestFormSerializer(leave_request_obj,data=data,partial=True)
            
    #         if leave_request_serializer.is_valid():
    #             if leave_request_serializer.validated_data["approved_status"]=="approved":
    #                 instance=leave_request_serializer.save()
    #                 leave_eligible_obj=EmployeeLeaveTypesEligiblity.objects.filter(employee=instance.employee,LeaveType=instance.LeaveType.pk).first()
                    
    #                 days=request.data.get("days")
    #                 if int(days)<=leave_eligible_obj.Available_leaves:
    #                     leave_eligible_obj.Available_leaves=leave_eligible_obj.no_of_leaves-int(days)
    #                     leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves-leave_eligible_obj.Available_leaves
    #                     leave_eligible_obj.save()
    #                     return Response("Leave Approved Successfully",status=status.HTTP_200_OK)
    #                 else:
    #                     leave_eligible_obj.Available_leaves=0
    #                     leave_eligible_obj.utilised_leaves=leave_eligible_obj.no_of_leaves
    #                     leave_eligible_obj.save()
                
    #                     if EmployeeLeaveTypesEligiblity.objects.filter(LeaveType__leave_type__leave_name="Unpaid_Leave").exists():
    #                         unpaid_Leave_obj=EmployeeLeaveTypesEligiblity.objects.filter(LeaveType__leave_type__leave_name="Unpaid_Leave").first()
    #                         unpaid_Leave_obj.utilised_leaves=unpaid_Leave_obj.utilised_leaves+int(days)
    #                         unpaid_Leave_obj.save()
    #                         return Response("Unpaid Leave Approved Successfully",status=status.HTTP_200_OK)
    #                     else:
    #                         LT_Obj=LeaveTypesModel.objects.create(leave_name="Unpaid_Leave")
    #                         LTD_Obj=LeavesTypeDetailModel.objects.create(leave_type=LT_Obj)
    #                         emp_obj=EmployeeDataModel.objects.get(EmployeeId=instance.employee.EmployeeId)
    #                         Emp_Eligible_obj=EmployeeLeaveTypesEligiblity.objects.create(employee=emp_obj,LeaveType=LTD_Obj)
    #                         Emp_Eligible_obj.utilised_leaves=leave_eligible_obj.utilised_leaves-int(days)
    #                         Emp_Eligible_obj.save()
                            
    #                         msg_dict={"message1":"Leave Approved Successfully",
    #                                   "message2":f"utilised all{leave_eligible_obj.LeaveType.leave_type.leave_name}\n From Now this leave fall under Unpaid Leaves Category." }
    #                         return Response(msg_dict,status=status.HTTP_200_OK)
    #             return Response("Leave Canclled Successfully",status=status.HTTP_200_OK)
    #         return Response(leave_request_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
                            
    #     except Exception as e:
    #         print(e)
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)



#6/01/2026
class Job_Description_View(APIView):
    def post(self, request):
        serializer = Job_Description_Serializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk=None):
        if pk:
            try:
                if str(pk).isdigit():
                    job = Job_Description_Model.objects.get(pk=pk)
                else:
                    job = Job_Description_Model.objects.get(slug=pk)
                serializer = Job_Description_Serializer(job)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Job_Description_Model.DoesNotExist:
                return Response("Job Not Found", status=status.HTTP_404_NOT_FOUND)
        
        active_only = request.query_params.get('active_only')
        if active_only == 'true':
            jobs = Job_Description_Model.objects.filter(is_active=True).order_by('-posted_on')
        else:
            jobs = Job_Description_Model.objects.all().order_by('-posted_on')
            
        serializer = Job_Description_Serializer(jobs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        try:
            if str(pk).isdigit():
                job = Job_Description_Model.objects.get(pk=pk)
            else:
                job = Job_Description_Model.objects.get(slug=pk)
            serializer = Job_Description_Serializer(job, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Job_Description_Model.DoesNotExist:
            return Response("Job Not Found", status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            if str(pk).isdigit():
                job = Job_Description_Model.objects.get(pk=pk)
            else:
                job = Job_Description_Model.objects.get(slug=pk)
            job.delete()
            return Response("Deleted Successfully", status=status.HTTP_200_OK)
        except Job_Description_Model.DoesNotExist:
            return Response("Job Not Found", status=status.HTTP_404_NOT_FOUND)