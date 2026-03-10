from EMS_App.imports import *
from HRM_App.models import *
from HRM_App.serializers import *
from django.core.mail import EmailMessage
from django.core.exceptions import ObjectDoesNotExist

class ResignationRequestView(APIView):
    def post(self, request):
        try:
            print(request.data)
            # Step 1: Extract and validate required fields
            login_user_id = request.data.get("employee_id")
            reporting_manager_id = request.data.get("reporting_manager_name")
            hr_manager_id = request.data.get("HR_manager_name")
            separation_type=request.data.get("separation_type")
            # appling_by=request.data.get("login_user")

            if not login_user_id or not reporting_manager_id or not hr_manager_id:
                print({"error": "Missing required fields: 'employee_id', 'reporting_manager_name', 'HR_manager_name'."})
                return Response({"error": "Missing required fields: 'employee_id', 'reporting_manager_name', 'HR_manager_name'."},
                                status=status.HTTP_400_BAD_REQUEST)

            # Step 2: Retrieve employee and managers
            # OLD CODE (caused 500: unpacking a Response object as a tuple):
            # employee, reporting_manager, hr_manager = self.get_employee_and_managers(login_user_id, reporting_manager_id, hr_manager_id)
            # if isinstance(employee, Response):  # In case of an error in retrieving data
            #     return employee

            # NEW CODE: get_employee_and_managers now raises ValueError on not found
            try:
                employee, reporting_manager, hr_manager = self.get_employee_and_managers(login_user_id, reporting_manager_id, hr_manager_id)
            except (ValueError, ObjectDoesNotExist) as e:
                return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

            # Step 3: Check if there is an existing resignation under process
            if self.has_pending_resignation(employee):
                print({"message": "Your resignation is under process!"})
                return Response({"message": "Your resignation is under process!"}, status=status.HTTP_400_BAD_REQUEST)

            # Step 4: Prepare and validate serializer data
            
            request_data = self.prepare_serializer_data(request.data, employee, reporting_manager, hr_manager)
            request_data["department"]= employee.Position.Department.Dep_Name if employee.Position else None
            serializer = ResignationSerializer(data=request_data, context={'request': request})
          
            if serializer.is_valid():
                resignation_instance = serializer.save()  # Save resignation instance

                if resignation_instance.employee_id.Reporting_To.Designation=="HR" or resignation_instance.separation_type=="involuntary":
                    resign_obj=ResignationModel.objects.get(pk=resignation_instance.pk)
                    resign_obj.is_rm_verified=True
                    resign_obj.rm_remarks=None
                    resign_obj.rm_verified_On=timezone.localdate()
                    resign_obj.save()
               
                self.create_notifications(login_user_id, reporting_manager, hr_manager)  # Create notifications
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # OLD CODE (returned a Response object which caused unpacking crash):
    # def get_employee_and_managers(self, employee_id, reporting_manager_id, hr_manager_id):
    #     try:
    #         employee = EmployeeDataModel.objects.get(EmployeeId=employee_id)
    #         reporting_manager = EmployeeDataModel.objects.get(EmployeeId=reporting_manager_id)
    #         hr_manager = EmployeeDataModel.objects.get(EmployeeId=hr_manager_id)
    #         return employee, reporting_manager, hr_manager
    #     except ObjectDoesNotExist:
    #         return Response({"error": "employee/manager records not found."}, status=status.HTTP_404_NOT_FOUND)

    def get_employee_and_managers(self, employee_id, reporting_manager_id, hr_manager_id):
        """
        Helper method to retrieve the employee, reporting manager, and HR manager from the database.
        Raises ValueError if any record is not found (so the caller can handle it properly).
        """
        try:
            employee = EmployeeDataModel.objects.get(EmployeeId=employee_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Employee with ID '{employee_id}' not found.")
        try:
            reporting_manager = EmployeeDataModel.objects.get(EmployeeId=reporting_manager_id)
        except ObjectDoesNotExist:
            raise ValueError(f"Reporting manager with ID '{reporting_manager_id}' not found.")
        try:
            hr_manager = EmployeeDataModel.objects.get(EmployeeId=hr_manager_id)
        except ObjectDoesNotExist:
            raise ValueError(f"HR manager with ID '{hr_manager_id}' not found.")
        return employee, reporting_manager, hr_manager

    def has_pending_resignation(self, employee):
        """
        Check if there is a pending resignation for the given employee.
        """
        resign_obj = ResignationModel.objects.filter(employee_id=employee.pk, resignation_verification__in=["pending","approved","ongoing"])
        return resign_obj.exists()

    def prepare_serializer_data(self, data, employee, reporting_manager, hr_manager):
        """
        Prepare data for the resignation serializer.
        """
        request_data = data.copy()
        request_data["employee_id"] = employee.pk
        request_data["reporting_manager_name"] = reporting_manager.pk
        request_data["HR_manager_name"] = hr_manager.pk
        return request_data

    def create_notifications(self, employee_id, reporting_manager, hr_manager):
        """
        Create notifications for the reporting manager and HR manager.
        """
        login_user = RegistrationModel.objects.get(EmployeeId=employee_id)
        reg_obj = RegistrationModel.objects.get(EmployeeId=reporting_manager.EmployeeId)
        hr_reg_obj = RegistrationModel.objects.get(EmployeeId=hr_manager.EmployeeId)

        # Create notifications
        Notification.objects.create(sender=login_user, receiver=reg_obj, message=f"{login_user.EmployeeId} filed a resignation form.")
        Notification.objects.create(sender=login_user, receiver=hr_reg_obj, message=f"{login_user.EmployeeId} filed a resignation form.")

    def get(self,request):
        
        login_emp=request.GET.get("emp_id")
        separation_id=request.GET.get("sep_id")
        if login_emp:
        
            resign_obj = ResignationModel.objects.filter(employee_id__EmployeeId=login_emp,separation_type="voluntary")
            if resign_obj:
                serializer = ResignationSerializer(resign_obj, context={'request': request},many=True)
                
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                # OLD: returned 400 which the frontend treated as an error
                # return Response("No resignation request", status=status.HTTP_400_BAD_REQUEST)
                # NEW: return 200 with empty list (correct REST standard for "no data found")
                return Response([], status=status.HTTP_200_OK)
        else:
            resign_obj = ResignationModel.objects.filter(pk=separation_id).first()
            if resign_obj:
                serializer = ResignationSerializer(resign_obj, context={'request': request})
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                return Response("erroe",status=status.HTTP_400_BAD_REQUEST)


        
from django.utils import timezone
from django.db.models import Q

class RMResignationVerification(APIView):
    def get(self, request):
        emp_id = request.GET.get("emp_id")
        if not emp_id:
            return Response({"error": "Employee ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        emp_obj = EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()
        if not emp_obj:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        # Query resignations based on the employee's role

        if emp_obj.Designation == "HR":
            resignation_request = ResignationModel.objects.filter(Q(resignation_verification="pending") | Q(resignation_verification="approved")).exclude(is_rm_verified=False)
        else:
            resignation_request = ResignationModel.objects.filter(is_rm_verified=False, employee_id__Reporting_To=emp_obj)
        # Serialize resignation requests
        if resignation_request.exists():
            resignation_serializer = ResignationSerializer(resignation_request, many=True, context={'request': request})
            return Response(resignation_serializer.data, status=status.HTTP_200_OK)
        else:
            # OLD: return Response({"message": "No resignation requests found."}, status=status.HTTP_400_BAD_REQUEST)
            # Return 200 with empty list — 400 is for bad requests, not "no data"
            return Response([], status=status.HTTP_200_OK)
                    
    # def patch(self,request):
    #     try:
    #         login_user=request.data.get("emp_id")
    #         if not login_user:
    #             return Response({"error": "Employee ID is required."}, status=status.HTTP_400_BAD_REQUEST)
            
    #         emp_obj = EmployeeDataModel.objects.filter(EmployeeId=login_user).first()
    #         if not emp_obj:
    #             return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
    #         # Query resignations based on the employee's role
    #         if emp_obj.Designation == "HR":
    #             resignation_request = ResignationModel.objects.filter(resignation_verification=None)
    #         else:
    #             resignation_request = ResignationModel.objects.filter(is_rm_verified=False, employee_id__Reporting_To=emp_obj)
    #             # Serialize resignation requests
    #         print(request.data)
    #         id=request.data.get("id")
    #         resign_obj=ResignationModel.objects.get(pk=id)

    #         resign_obj.is_rm_verified=request.data.get("is_rm_verified")
    #         resign_obj.rm_remarks=request.data.get("rm_remarks")
    #         resign_obj.rm_verified_On=timezone.localdate()
    #         resign_obj.save()

    #         Sender=RegistrationModel.objects.get(EmployeeId=resign_obj.reporting_manager_name)
    #         Receiver=RegistrationModel.objects.get(EmployeeId=resign_obj.HR_manager_name)

    #         notification=Notification.objects.create(sender=Sender,receiver=Receiver,message=f"{Sender.EmployeeId} Reviewed {resign_obj.employee_id.EmployeeId} {resign_obj.employee_id.Name}.On {resign_obj.rm_verified_On}\n The Remarks are {resign_obj.rm_remarks}")

    #         return Response("Reviewed Successfull",status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def patch (self,request):
        try:
            print(request.data)
            separation_id=request.GET.get("sep_id")
            request_data=request.data.copy()

            if request.data.get("rm_verified_On"):
                request_data["rm_verified_On"]=timezone.localdate()
                del request_data["hr_verified_On"]
            
            if request.data.get("hr_verified_On"):
                request_data["hr_verified_On"]=timezone.localdate()
                del request_data["rm_verified_On"]
                
            if not separation_id:
                return Response({"error": "separation_id is required."}, status=status.HTTP_400_BAD_REQUEST)
    
            resignation_request = ResignationModel.objects.filter(pk=separation_id).first()

            if request_data.get("is_hr_verified"):
                # if request_data.get("Interviewer") and int(request_data.get("Interviewer")) == resignation_request.employee_id.pk:
                #     return Response("Interviewer Should not a Resigning Employee",status=status.HTTP_400_BAD_REQUEST)
                interviewer_val = request_data.get("Interviewer")
                if interviewer_val:
                    # Support both numeric PK (from modal dropdown) and EmployeeId string
                    try:
                        interviewer_match = int(interviewer_val) == resignation_request.employee_id.pk
                    except (ValueError, TypeError):
                        # EmployeeId string format — compare by EmployeeId
                        interviewer_match = str(interviewer_val) == resignation_request.employee_id.EmployeeId
                    if interviewer_match:
                        return Response("Interviewer Should not a Resigning Employee", status=status.HTTP_400_BAD_REQUEST)
                   
            if request_data.get("Interviewer") and not request_data.get("Date_Of_Interview"):
                # Only require Date_Of_Interview if Interviewer is being newly assigned (not already set)
                if not resignation_request.Date_Of_Interview:
                    return Response("Provide Interview Date along with Interviewer",status=status.HTTP_400_BAD_REQUEST)

            # Resolve Interviewer: if it's an EmployeeId string (e.g. "MTM25I1022"), convert to numeric PK
            # because DRF FK fields expect numeric PK for validation/saving
            interviewer_raw = request_data.get("Interviewer")
            if interviewer_raw:
                try:
                    int(interviewer_raw)  # already a numeric PK — no conversion needed
                except (ValueError, TypeError):
                    # It's an EmployeeId string — look up the numeric PK
                    from EMS_App.models import EmployeeDataModel
                    interviewer_obj = EmployeeDataModel.objects.filter(EmployeeId=interviewer_raw).first()
                    if interviewer_obj:
                        request_data["Interviewer"] = interviewer_obj.pk
                    else:
                        return Response({"error": f"Interviewer with EmployeeId '{interviewer_raw}' not found."}, status=status.HTTP_400_BAD_REQUEST)

            resignation_serializer = ResignationSerializer(resignation_request,data=request_data,partial=True)
            if resignation_serializer.is_valid():
                resign_instance=resignation_serializer.save()
                if resign_instance.is_hr_verified and resign_instance.Interviewer:
                    try:
                        subject = f"Invitation for Resignation Discussion"

                        Message = f"""
                        Dear Mr./Ms. {resign_instance.name},  
                        Employee ID: {resign_instance.employee_id.EmployeeId}

                        We would like to invite you to a formal meeting to discuss the resignation process. Please note that this discussion is scheduled for {resign_instance.Date_Of_Interview}.

                        If you have any questions or require further details before the meeting, feel free to contact us.

                        We appreciate your cooperation and look forward to meeting with you.

                        Best regards,  
                        {resign_instance.HR_manager_name.Name}  
                        HR Manager
                        """
                    
                        # email= resign_instance.employee_id.employeeProfile.email 
                    
                        # send_mail(
                        #         subject,Message,
                        #         'sender@example.com',  
                        #         [email],
                        #         fail_silently=False,
                        # )
                    except Exception as e:
                        return Response(f"Data saved Successfully! and {str(e)}",status=status.HTTP_400_BAD_REQUEST)
                   
                return Response(resignation_serializer.data, status=status.HTTP_200_OK)
            else:
                print(resignation_serializer.errors)
                return Response(resignation_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


        
class HRResignationVerification(APIView):
    def get(self,request,login_user=None,resign_id=None):
        try:
            if resign_id:
                resignation_request=ResignationModel.objects.get(pk=resign_id)
                resignation_serializer = ResignationSerializer(resignation_request,context={'request': request}).data if resignation_request else {}
                try: 
                    resignation_request.employee_id.employeeProfile.Candidate_id
                    can_id=resignation_request.employee_id.employeeProfile.Candidate_id
                    offer_instance=resignation_request.employee_id.employeeProfile.Offered_Instance.filter(CandidateId=can_id).first()
                    resignation_serializer=resignation_serializer
                    resignation_serializer["notice_period"]=offer_instance.notice_period
                    ctc= offer_instance.CTC if offer_instance.CTC else 0
                    resignation_serializer["notice_pay"]=int(offer_instance.notice_period)* ctc
                except:
                    pass
                return Response(resignation_serializer,status=status.HTTP_200_OK)
            else:
                emp_obj=EmployeeDataModel.objects.get(EmployeeId=login_user)
                # resignation_request=ResignationModel.objects.filter(HR_manager_name=emp_obj.pk,resignation_verification=None)
                # Broaden filter: include all except completed, so ongoing/approved show up
                resignation_request=ResignationModel.objects.filter(HR_manager_name=emp_obj.pk).exclude(resignation_verification="completed")

                resignation_serializer = ResignationSerializer(resignation_request,many=True,context={'request': request}).data if resignation_request else []
                
                return Response(resignation_serializer,status=status.HTTP_200_OK)
        except:
            return Response("Error",status=status.HTTP_400_BAD_REQUEST)
        
    def post(self,request):
        try:
            print(request.data)
            id=request.data.get("id")
            resign_obj=ResignationModel.objects.get(pk=id)

            resign_obj.is_hr_verified=request.data.get("is_hr_verified")
            resign_obj.hr_remarks=request.data.get("hr_remarks")
            resign_obj.hr_verified_On=timezone.localdate()

            date_str=request.data.get("Date_of_Interview")

            if date_str:
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    resign_obj.Date_Of_Interview = date_obj
                except ValueError:
                    print("Incorrect date format, should be YYYY-MM-DD")

            resign_obj.save()

            login_user=RegistrationModel.objects.get(EmployeeId=resign_obj.HR_manager_name.EmployeeId)
            receiver=RegistrationModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)
            
            notification=Notification.objects.create(sender=login_user,receiver=receiver,message=f"Mr/Mis{resign_obj.name}\n{login_user.EmployeeId} {login_user.UserName} Invited you to Resignation Process On {resign_obj.Date_Of_Interview}.\n Regards\n{resign_obj.HR_manager_name}.")

            subject= f"Resignation Duscussion"
            Message=f"Mr/Mis{resign_obj.name}\n{login_user.EmployeeId} {login_user.UserName} Invited you to Resignation Process On {resign_obj.Date_Of_Interview}.\n Regards\n{resign_obj.HR_manager_name}."
            employee_obj=EmployeeDataModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)

            send_mail(
                    subject,Message,
                    'sender@example.com',  
                    [employee_obj.employeeProfile.email],
                    fail_silently=False,
            )
            return Response("Reviewed Successfull")
        except Exception as e:
            return Response(str(e))
        
class ExitInterview(APIView):

    def get(self,request,login_user=None):
        try:
            sep_id=request.GET.get("sep_id")
            # emp_id=request.GET.get("emp_id")
            emp_id=login_user or request.GET.get("emp_id")  # Use login_user from path if available
            if sep_id:
                exit_data=ExitDetailsModel.objects.filter(resignation=sep_id).first()
                if exit_data:
                    exit_serializer=ExitDetailsSerializer(exit_data)
                    return Response(exit_serializer.data,status=status.HTTP_200_OK)
                else:
                # OLD: return Response("Exit Serializer Not Exit",status=status.HTTP_400_BAD_REQUEST)
                    return Response({}, status=status.HTTP_200_OK)
            else:
            # OLD: no filter — returned ALL exit interviews regardless of interviewer
            # exit_data=ExitDetailsModel.objects.all().exclude(resignation__resignation_verification="completed")

            # NEW: if emp_id passed, filter by the assigned Interviewer
                if emp_id:
                    exit_data = ExitDetailsModel.objects.filter(
                        resignation__Interviewer__EmployeeId=emp_id
                    ).exclude(resignation__resignation_verification="completed")
                else:
                    exit_data = ExitDetailsModel.objects.all().exclude(resignation__resignation_verification="completed")

                if exit_data.exists():
                    exit_serializer=ExitDetailsSerializer(exit_data,many=True)
                    return Response(exit_serializer.data,status=status.HTTP_200_OK)
                else:
                # OLD: return Response("Exit Serializer Not Exit",status=status.HTTP_400_BAD_REQUEST)
                    return Response([], status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
       
        
    def patch(self,request):
        try:
            print(request.data)
            request_data=request.data.copy()
            exit_id=request_data.get("id")
            exit_obj=ExitDetailsModel.objects.filter(pk=exit_id).first()
            # if not resignation_request.is_hr_verified:
            #     return Response("Resignation Should Verify from HR Manager, to Conduct the Exit Interview", status=status.HTTP_400_BAD_REQUEST)
            if exit_obj:
                exit_serializer=ExitDetailsSerializer(exit_obj,data=request_data,partial=True)
                if exit_serializer.is_valid():
                    exit_serializer.save()
                    return Response(exit_serializer.data,status=status.HTTP_200_OK)
                else:
                    print(exit_serializer.errors)
                    return Response(exit_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("Exit objects not found",status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    def post(self,request):
        try:
            print(request.data)
            request_data=request.data.copy()
            resignation_id=request_data.get("id")
            resignation_obj=ResignationModel.objects.filter(pk=resignation_id).first()
            
            if not resignation_obj:
                 return Response("Resignation object not found",status=status.HTTP_400_BAD_REQUEST)
            
            # Use get_or_create to handle both new creation and updates if called multiple times
            exit_obj, created = ExitDetailsModel.objects.get_or_create(resignation=resignation_obj)
            
            # Remove resignation from data to avoid validation issues with nested serializer
            request_data.pop("resignation", None)
            
            exit_serializer=ExitDetailsSerializer(exit_obj,data=request_data,partial=True)
            if exit_serializer.is_valid():
                exit_serializer.save()
                return Response(exit_serializer.data,status=status.HTTP_200_OK)
            else:
                print(exit_serializer.errors)
                return Response(exit_serializer.errors,status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
class ClearenceFormView(APIView): 

    def get(self,request):
        exit_id=request.GET.get("exit_id")
        clearence_obj=AssetsClearance.objects.filter(separation_information=exit_id).first()
        if clearence_obj:
            clearence_serializer=ClearenceSerializer(clearence_obj)
            return Response(clearence_serializer.data,status=status.HTTP_200_OK)
        else:
            # Return 200 with empty dict for consistency
            return Response({}, status=status.HTTP_200_OK)
        
    def post(self,request):
        try:
            request_data=request.data.copy()
            clearence_serializer=ClearenceSerializer(data=request_data)
            if clearence_serializer.is_valid():
                clearence_serializer.save()
                return Response(clearence_serializer.data,status=status.HTTP_200_OK)
            else:
                print(clearence_serializer.errors)
                return Response(clearence_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self,request):
        try:
            request_data=request.data.copy()
            ac_id=request_data.get("id")
            ac_obj=AssetsClearance.objects.filter(pk=ac_id).first()
            if ac_obj:
                clearence_serializer=ClearenceSerializer(ac_obj,data=request_data,partial=True)
                if clearence_serializer.is_valid():
                    clearence_serializer.save()
                    return Response(clearence_serializer.data,status=status.HTTP_200_OK)
                else:
                    print(clearence_serializer.errors)
                    return Response(clearence_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("object not found",status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class HandoverDetails(APIView):
    def get(self,request):
        try:
            resign_id=request.GET.get("resign_id")
            Handover_list=HandoversDetails.objects.filter(resignation=resign_id)
            
            if Handover_list.exists():
                handover_serializer=HandOverSerializer(Handover_list,many=True)
                return Response(handover_serializer.data,status=status.HTTP_200_OK)
            else:
                # Return 200 with empty list for consistency
                return Response([], status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        print(request.data)
        request_data=request.data.copy()
        handover_serializer=HandOverSerializer(data=request_data)

        if handover_serializer.is_valid():
            handover_serializer.save()
            return Response(handover_serializer.data,status=status.HTTP_200_OK)
        else:
            print(f"DEBUG: Handover save failed! Errors: {handover_serializer.errors}")
            return Response(handover_serializer.errors,status=status.HTTP_400_BAD_REQUEST)

    def patch(self,request):
        request_data=request.data.copy() 
        handover_id=request_data.get("id")
        handover_obj=HandoversDetails.objects.filter(pk=handover_id).first()
        if handover_obj:
            handover_serializer=HandOverSerializer(handover_obj,data=request_data,partial=True)
            if handover_serializer.is_valid():
                handover_serializer.save()
                return Response(handover_serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(handover_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response("not exist",status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request, handover_id):
        try:
            handover = HandoversDetails.objects.filter(id=handover_id).first()
            if handover:
                handover.delete()
                return Response({"message": "Handover deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({"message": "Failed to Delete"}, status=status.HTTP_400_BAD_REQUEST)
        except HandoversDetails.DoesNotExist:
            return Response({"error": "Handover not found"}, status=status.HTTP_404_NOT_FOUND)
        
class HandoverAcknowledgement(APIView):
    def get(self,request):
        try:
            login_emp=request.GET.get("emp_id")
            # handover_list=HandoversDetails.objects.filter(handover_to__EmployeeId=login_emp,assigned_handover_emp_accept_status="pending")
            if not login_emp:
                return Response({"error": "emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the employee object to check designation
            from EMS_App.models import EmployeeDataModel
            employee_obj = EmployeeDataModel.objects.filter(EmployeeId=login_emp).first()
            
            if not employee_obj:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

            print(f"DEBUG: login_emp={login_emp}, designation={employee_obj.Designation}")
            # Define filtering logic based on role
            if employee_obj.Designation in ['HR', 'Admin']:
                # HR/Admin sees all pending or in-progress handovers for transparency
                handover_list = HandoversDetails.objects.all().exclude(
                    assigned_handover_emp_accept_status="accepted",
                    handover_status="completed"
                )
                print(f"DEBUG: HR/Admin mode, count={handover_list.count()}")
            else:
                # Regular employees see:
                # 1. Tasks assigned TO them
                # 2. Tasks initiated BY them (if they are the resigning employee)
                from django.db.models import Q
                handover_list = HandoversDetails.objects.filter(
                    Q(handover_to__EmployeeId=login_emp) | 
                    Q(resignation__employee_id__EmployeeId=login_emp)
                ).distinct()
                print(f"DEBUG: Reg emp mode, count={handover_list.count()}")
                for h in handover_list:
                    print(f"DEBUG: Found handover: {h.id}, Title: {h.handover_title}, To: {h.handover_to}")

            if handover_list.exists():
                handover_serializer=HandOverSerializer(handover_list,many=True)
                return Response(handover_serializer.data,status=status.HTTP_200_OK)
            else:
                # OLD: return Response("data not exist",status=status.HTTP_400_BAD_REQUEST)
                # Return 200 with empty list — 400 is for bad requests, not "no data"
                # return Response([],status=status.HTTP_200_OK)
                total_db_count = HandoversDetails.objects.all().count()
                print(f"DEBUG: No handovers found for {login_emp}. Total in DB: {total_db_count}")
                # REVERTED: Return empty list to prevent frontend crash
                return Response([], status=status.HTTP_200_OK)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# corrections 
""" auto refresh verification status 
    clerence for change 
    not issue in the clerence form field choice has to add
    department
    exit interview form fields has to check 
    exit interview data should be hide it has to visible only how conducted and the HR

    neddd to show the Employee History and need to add the 

    separation type should not choice for self applying
"""
    

    # def post(self,request):
    #     try:
    #         ExitDetailsData=request.data.copy()
    #         employeeid=ExitDetailsData.get("employee_id")
    #         id=ExitDetailsData.get("id")
    
    #         resign_obj=ResignationModel.objects.filter(pk=id).first()
    #         ExitDetailsData["resignation"]=resign_obj.pk

    #         ExitDetails_serializer=ExitDetailsSerializer(data=ExitDetailsData,context={'request': request})
    #         if ExitDetails_serializer.is_valid():
    #             instance=ExitDetails_serializer.save()

    #             resign_obj.resignation_verification=request.data.get("resignation_verification")
    #             resign_obj.remarks=request.data.get("remarks")
    #             resign_obj.save()
    #         else:
    #             return Response(ExitDetails_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            
    #         Sender=RegistrationModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)
    #         reg_obj=RegistrationModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)

    #         notification=Notification.objects.create(sender=Sender,receiver=reg_obj,message=f"{resign_obj.HR_manager_name.Name} Reviewved On Your Resignation\n The Applied Resignation Was {resign_obj.resignation_verification}.")
            
    #         subject= f"Applied Resignation Status "
    #         Message=f"Your Resignation Was {resign_obj.resignation_verification} Reviewed By {resign_obj.reporting_manager_name}"
    #         employee_obj=EmployeeDataModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)

    #         send_mail(
    #                 subject,Message,
    #                 'sender@example.com',  
    #                 [employee_obj.employeeProfile.email],
    #                 fail_silently=False,
    #         )

    #         if resign_obj.resignation_verification=="approved":
    #             return Response(f"Resignation Approved Successful",status=status.HTTP_200_OK)
    #         else:
    #             return Response(f"Resignation declined Successful",status=status.HTTP_200_OK)
    #     except Exception as e:
    #         print(e)
    #         return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    # def get(self,request,resign_id=None,login_user=None):
    #     try:
    #         if resign_id:
    #             resignation_request=ResignationModel.objects.get(pk=resign_id)
    #             resignation_serializer = ResignationSerializer(resignation_request,context={'request': request}).data if resignation_request else {}
    #             try:
    #                 resignation_request.employee_id.employeeProfile.Candidate_id
    #                 can_id=resignation_request.employee_id.employeeProfile.Candidate_id
    #                 offer_instance=resignation_request.employee_id.employeeProfile.Offered_Instance.filter(CandidateId=can_id).first()
    #                 resignation_serializer=resignation_serializer
    #                 resignation_serializer["notice_period"]=offer_instance.notice_period
    #                 ctc= offer_instance.CTC if offer_instance.CTC else 0
    #                 resignation_serializer["notice_pay"]=int(offer_instance.notice_period)*ctc
    #             finally:
    #                 print("okkk")
    #             exit_data=ExitDetailsModel.objects.get(resignation=resign_id)
    #             resignation_serializer.update(exit_data)
    #             return Response(resignation_serializer,status=status.HTTP_200_OK)
    #         else:
    #             emp_obj=EmployeeDataModel.objects.get(EmployeeId=login_user)
    #             resignation_request=ResignationModel.objects.filter(employee_id__employeeProfile__employee_status="in_active")
    #             resignation_serializer = ResignationSerializer(resignation_request,many=True,context={'request': request}).data if resignation_request else []
    #             return Response(resignation_serializer,status=status.HTTP_200_OK)
    #     except:
    #         return Response("Error",status=status.HTTP_400_BAD_REQUEST)

        

class EmpLeftOrganizationView(APIView):
    def get(self,request):
        # resign_obj=ExitDetailsModel.objects.filter(resignation__resignation_verification="approved")
        # Broaden filter to include 'completed' and 'ongoing' so employees who missed the initial 
        # trigger or were manually updated can still be successfully offboarded.
        resign_obj=ExitDetailsModel.objects.filter(resignation__resignation_verification__in=["approved", "completed", "ongoing"])
        resign_list=[]
        for resign_item in resign_obj:
            # Use employment_end_date or last_working_day as Leaving_date
            leaving_date = resign_item.employment_end_date or resign_item.last_working_day or resign_item.submission_date
            
            # Safe access to fields - avoid 500 if data is inconsistent
            if not resign_item.resignation or not resign_item.resignation.employee_id:
                print(f"DEBUG: Skipping ExitDetails {resign_item.pk} due to missing resignation or employee_id")
                continue
                
            resign_dict={"instance":resign_item.pk,
                        # "Leaving_date":resign_item.Date_to_Leave,
                         "Leaving_date":leaving_date,
                         "resign_instance":resign_item.resignation.pk,
                         "EmployeeId":resign_item.resignation.employee_id.EmployeeId, # Used by auto-separation logic
                         "mail_sent":resign_item.mail_sent,
                         # Fields required by the Tab 3 Table in the frontend:
                         "name": resign_item.resignation.name,
                         "employee_id": resign_item.resignation.employee_id.EmployeeId,
                         "position": resign_item.resignation.position,
                         "Applied_On": resign_item.resignation.Applied_On,
                         "rm_verified_On": resign_item.resignation.rm_verified_On,
                         "hr_verified_On": resign_item.resignation.hr_verified_On,
                         "Date_Of_Interview": resign_item.resignation.Date_Of_Interview,
                         "id": resign_item.resignation.id # Used for onClick -> hello(e.id)
                         }
            resign_list.append(resign_dict)
        return Response(resign_list)
    def post(self,request):
        try:
            # exist_instance=request.data
            # if exist_instance:
            #     resign_obj=ExitDetailsModel.objects.filter(pk__in=exist_instance)
            input_data=request.data
            processed_count = 0
            # if exist_instance:
            #     # Handle both list and single ID
            #     if not isinstance(exist_instance, list):
            #         exist_instance = [exist_instance]
            if input_data:
                # Extract instance IDs from different possible input formats
                instance_ids = []
                if isinstance(input_data, list):
                    instance_ids = input_data
                elif isinstance(input_data, dict):
                    # Check for 'instance' key (common in formData)
                    # Support both single value and list (via getlist if it's a QueryDict)
                    if hasattr(input_data, 'getlist'):
                        instance_ids = input_data.getlist('instance')
                    elif 'instance' in input_data:
                        val = input_data['instance']
                        instance_ids = [val] if not isinstance(val, list) else val
                    else:
                        # Fallback: use all values if 'instance' key not found
                        instance_ids = list(input_data.values())
                else:
                    # Single ID case
                    instance_ids = [input_data]
                    
                # resign_obj=ExitDetailsModel.objects.filter(pk__in=exist_instance)
                resign_obj=ExitDetailsModel.objects.filter(pk__in=instance_ids)
                for resign_item in resign_obj:
                    resign_item.NoticedServed=True
                    resign_item.EmpLeftOrganization=True
                    resign_item.Date_of_Left_Organization=timezone.localdate()
                    resign_item.mail_sent=True
                    # resign_item.resignation.employee_id.employeeProfile.employee_status="in_active"
                    # resign_item.save()

                    # emp_obj=EmployeeInformation(employee_Id=resign_item.resignation.employee_id.EmployeeId)
                    # emp_obj.employee_status="in_active"
                    # emp_obj.save()
                    # print(emp_obj.employee_status)
                    
                    # Correctly update the profile status and save it
                    profile = resign_item.resignation.employee_id.employeeProfile
                    if profile:
                        profile.employee_status="in_active"
                        profile.save()
                        print(f"Status updated for {profile.employee_Id}")
                    
                    resign_item.save()

                    subject= f"Organisation Exit Day {resign_item.Date_of_Left_Organization}"
                    Message=f"Mr/Miss {resign_item.resignation.employee_id.Name} Today is Your Organisation Exit Day.\n Check all the Settlements Happen or not\n By filling the following form By EOD."
                    sender_email = 'sender@example.com'
                    # recipient_email = resign_item.resignation.employee_id.employeeProfile.email
                    recipient_email = profile.email if profile else None
                    
                    if recipient_email:
                        email = EmailMessage(subject, Message, sender_email, [recipient_email])
                        if resign_item.Required_letters:
                            try:
                                email.attach(f'{resign_item.resignation.employee_id.Name}_LeavingLetter.pdf', resign_item.Required_letters.read(), 'application/pdf')
                            except Exception as e:
                                print(f"File attachment error: {e}")
                        try:
                            email.send()
                        # return Response({'message': 'Email sent successfully'}, status=status.HTTP_200_OK)
                        except Exception as e:
                                                    # return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                            print(f"Email send fail for {recipient_email}: {e}")
                    
                    processed_count += 1
                
                return Response({'message': f'Successfully processed {processed_count} exit(s)'}, status=status.HTTP_200_OK)
            else:
                return Response("Data not provided",status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    



# class ResignationRequestView(APIView):
#     def post(self,request):
#         try:
#             login_user=request.data.get("employee_id")
#             reporting_manager_id=request.data.get("reporting_manager_name")
#             hr_manager_id=request.data.get("HR_manager_name")

#             employeeid=EmployeeDataModel.objects.get(EmployeeId=login_user)

#             rm_emp_obj=EmployeeDataModel.objects.get(EmployeeId=reporting_manager_id)
#             hr_emp_obj=EmployeeDataModel.objects.get(EmployeeId=hr_manager_id)

#             request_data=request.data.copy()
#             request_data["employee_id"]=employeeid.pk
#             request_data["reporting_manager_name"]=rm_emp_obj.pk
#             request_data["HR_manager_name"]=hr_emp_obj.pk

#             resign_obj=ResignationModel.objects.filter(employee_id=employeeid.pk,resignation_verification=None)
    
#             if resign_obj:
#                 for i in resign_obj:
#                     if i.resignation_verification:
#                         serializer=ResignationSerializer(data=request_data,context={'request': request})
#                         if serializer.is_valid():
#                             resign_instance=serializer.save()
                    
#                             # can_id=employeeid.employeeProfile.Candidate_id
#                             # offer_instance=employeeid.employeeProfile.Offered_Instance.get(CandidateId=can_id)
#                             # offer_obj=OfferLetterModel.objects.get(pk=offer_instance)
                            
#                             login_user=RegistrationModel.objects.filter(EmployeeId=login_user).first()
#                             reg_obj=RegistrationModel.objects.get(EmployeeId=rm_emp_obj.EmployeeId)
#                             hr_reg_obj=RegistrationModel.objects.get(EmployeeId=hr_emp_obj.EmployeeId)
                            
#                             notification=Notification.objects.create(sender=login_user,receiver=reg_obj,message=f"{login_user.EmployeeId} Filed  Resignation Form")
#                             notification=Notification.objects.create(sender=login_user,receiver=hr_reg_obj,message=f"{login_user.EmployeeId} Filed  Resignation Form")

#                             return Response(serializer.data,status=status.HTTP_200_OK)
#                         else:
#                             print(serializer.errors)
#                             return Response(serializer.errors,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#                     else:
#                         return Response("Your resignation Under Process!",status=status.HTTP_200_OK)
#             else:
#                 serializer=ResignationSerializer(data=request_data,context={'request': request})
#                 if serializer.is_valid():
#                     resign_instance=serializer.save()

#                     login_user=RegistrationModel.objects.filter(EmployeeId=login_user).first()
#                     reg_obj=RegistrationModel.objects.get(EmployeeId=rm_emp_obj.EmployeeId)
#                     hr_reg_obj=RegistrationModel.objects.get(EmployeeId=hr_emp_obj.EmployeeId)
                    
#                     notification=Notification.objects.create(sender=login_user,receiver=reg_obj,message=f"{login_user.EmployeeId} Filed  Resignation Form")
#                     notification=Notification.objects.create(sender=login_user,receiver=hr_reg_obj,message=f"{login_user.EmployeeId} Filed  Resignation Form")


#                     return Response(serializer.data,status=status.HTTP_200_OK)
#                 else:
#                     print(serializer.errors)
#                     return Response(serializer.errors,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#         except Exception as e:
#             print(e)  
#             return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
# from django.utils import timezone

# class RMResignationVerification(APIView):
#     def post(self,request):
#         try:
#             print(request.data)
#             id=request.data.get("id")
#             resign_obj=ResignationModel.objects.get(pk=id)

#             resign_obj.is_rm_verified=request.data.get("is_rm_verified")
#             resign_obj.rm_remarks=request.data.get("rm_remarks")
#             resign_obj.rm_verified_On=timezone.localdate()
#             resign_obj.save()

#             Sender=RegistrationModel.objects.get(EmployeeId=resign_obj.reporting_manager_name)
#             Receiver=RegistrationModel.objects.get(EmployeeId=resign_obj.HR_manager_name)

#             notification=Notification.objects.create(sender=Sender,receiver=Receiver,message=f"{Sender.EmployeeId} Reviewed {resign_obj.employee_id.EmployeeId} {resign_obj.employee_id.Name}.On {resign_obj.rm_verified_On}\n The Remarks are {resign_obj.rm_remarks}")

#             return Response("Reviewed Successfull")
#         except Exception as e:
#             return Response(str(e))
        
# class HRResignationVerification(APIView):
#     def get(self,request,login_user=None,resign_id=None):
#         try:
#             if resign_id:
#                 resignation_request=ResignationModel.objects.get(pk=resign_id)
#                 resignation_serializer = ResignationSerializer(resignation_request,context={'request': request}).data if resignation_request else {}
#                 try: 
#                     resignation_request.employee_id.employeeProfile.Candidate_id
#                     can_id=resignation_request.employee_id.employeeProfile.Candidate_id
#                     offer_instance=resignation_request.employee_id.employeeProfile.Offered_Instance.filter(CandidateId=can_id).first()
#                     resignation_serializer=resignation_serializer
#                     resignation_serializer["notice_period"]=offer_instance.notice_period
#                     ctc= offer_instance.CTC if offer_instance.CTC else 0
#                     resignation_serializer["notice_pay"]=int(offer_instance.notice_period)* ctc
#                 except:
#                     pass
#                 return Response(resignation_serializer,status=status.HTTP_200_OK)
#             else:
#                 emp_obj=EmployeeDataModel.objects.get(EmployeeId=login_user)
#                 resignation_request=ResignationModel.objects.filter(HR_manager_name=emp_obj.pk,resignation_verification=None)

#                 resignation_serializer = ResignationSerializer(resignation_request,many=True,context={'request': request}).data if resignation_request else []
#                 return Response(resignation_serializer,status=status.HTTP_200_OK)
#         except:
#             return Response("Error",status=status.HTTP_400_BAD_REQUEST)
        
#     def post(self,request):
#         try:
#             print(request.data)
#             id=request.data.get("id")
#             resign_obj=ResignationModel.objects.get(pk=id)

#             resign_obj.is_hr_verified=request.data.get("is_hr_verified")
#             resign_obj.hr_remarks=request.data.get("hr_remarks")
#             resign_obj.hr_verified_On=timezone.localdate()

#             date_str=request.data.get("Date_of_Interview")

#             if date_str:
#                 try:
#                     date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
#                     resign_obj.Date_Of_Interview = date_obj
#                 except ValueError:
#                     print("Incorrect date format, should be YYYY-MM-DD")

#             resign_obj.save()

#             login_user=RegistrationModel.objects.get(EmployeeId=resign_obj.HR_manager_name.EmployeeId)
#             receiver=RegistrationModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)
            
#             notification=Notification.objects.create(sender=login_user,receiver=receiver,message=f"Mr/Mis{resign_obj.name}\n{login_user.EmployeeId} {login_user.UserName} Invited you to Resignation Process On {resign_obj.Date_Of_Interview}.\n Regards\n{resign_obj.HR_manager_name}.")

#             subject= f"Resignation Duscussion"
#             Message=f"Mr/Mis{resign_obj.name}\n{login_user.EmployeeId} {login_user.UserName} Invited you to Resignation Process On {resign_obj.Date_Of_Interview}.\n Regards\n{resign_obj.HR_manager_name}."
#             employee_obj=EmployeeDataModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)

#             send_mail(
#                     subject,Message,
#                     'sender@example.com',  
#                     [employee_obj.employeeProfile.email],
#                     fail_silently=False,
#             )

#             return Response("Reviewed Successfull")
#         except Exception as e:
#             return Response(str(e))

# class ExitInterview(APIView):
#     def post(self,request):
#         try:
#             ExitDetailsData=request.data.copy()
#             employeeid=ExitDetailsData.get("employee_id")
#             id=ExitDetailsData.get("id")
    
#             resign_obj=ResignationModel.objects.filter(pk=id).first()
#             ExitDetailsData["resignation"]=resign_obj.pk

#             ExitDetails_serializer=ExitDetailsSerializer(data=ExitDetailsData,context={'request': request})
#             if ExitDetails_serializer.is_valid():
#                 instance=ExitDetails_serializer.save()

#                 resign_obj.resignation_verification=request.data.get("resignation_verification")
#                 resign_obj.remarks=request.data.get("remarks")
#                 resign_obj.save()
#             else:
#                 return Response(ExitDetails_serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            
#             Sender=RegistrationModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)
#             reg_obj=RegistrationModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)

#             notification=Notification.objects.create(sender=Sender,receiver=reg_obj,message=f"{resign_obj.HR_manager_name.Name} Reviewved On Your Resignation\n The Applied Resignation Was {resign_obj.resignation_verification}.")
            
#             subject= f"Applied Resignation Status "
#             Message=f"Your Resignation Was {resign_obj.resignation_verification} Reviewed By {resign_obj.reporting_manager_name}"
#             employee_obj=EmployeeDataModel.objects.get(EmployeeId=resign_obj.employee_id.EmployeeId)

#             send_mail(
#                     subject,Message,
#                     'sender@example.com',  
#                     [employee_obj.employeeProfile.email],
#                     fail_silently=False,
#             )

#             if resign_obj.resignation_verification=="approved":
#                 return Response(f"Resignation Approved Successful",status=status.HTTP_200_OK)
#             else:
#                 return Response(f"Resignation declined Successful",status=status.HTTP_200_OK)
#         except Exception as e:
#             print(e)
#             return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
#     def get(self,request,resign_id=None,login_user=None):
#         try:
#             if resign_id:
#                 resignation_request=ResignationModel.objects.get(pk=resign_id)
#                 resignation_serializer = ResignationSerializer(resignation_request,context={'request': request}).data if resignation_request else {}
#                 try:
#                     resignation_request.employee_id.employeeProfile.Candidate_id
#                     can_id=resignation_request.employee_id.employeeProfile.Candidate_id
#                     offer_instance=resignation_request.employee_id.employeeProfile.Offered_Instance.filter(CandidateId=can_id).first()
#                     resignation_serializer=resignation_serializer
#                     resignation_serializer["notice_period"]=offer_instance.notice_period
#                     ctc= offer_instance.CTC if offer_instance.CTC else 0
#                     resignation_serializer["notice_pay"]=int(offer_instance.notice_period)*ctc
#                 finally:
#                     print("okkk")
#                 exit_data=ExitDetailsModel.objects.get(resignation=resign_id)
#                 resignation_serializer.update(exit_data)
#                 return Response(resignation_serializer,status=status.HTTP_200_OK)
#             else:
#                 emp_obj=EmployeeDataModel.objects.get(EmployeeId=login_user)
#                 resignation_request=ResignationModel.objects.filter(employee_id__employeeProfile__employee_status="in_active")
#                 resignation_serializer = ResignationSerializer(resignation_request,many=True,context={'request': request}).data if resignation_request else []
#                 return Response(resignation_serializer,status=status.HTTP_200_OK)
#         except:
#             return Response("Error",status=status.HTTP_400_BAD_REQUEST)

        

# class EmpLeftOrganizationView(APIView):
#     def get(self,request):
#         resign_obj=ExitDetailsModel.objects.filter(resignation__resignation_verification="approved")
#         resign_list=[]
#         for resign_item in resign_obj:
#             resign_dict={"instance":resign_item.pk,
#                          "Leaving_date":resign_item.Date_to_Leave,
#                          "resign_instance":resign_item.resignation.pk,
#                          "EmployeeId":resign_item.resignation.employee_id.EmployeeId,
#                          "mail_sent":resign_item.mail_sent
#                          }
#             resign_list.append(resign_dict)
#         return Response(resign_list)
#     def post(self,request):
#         try:
#             exist_instance=request.data
#             if exist_instance:
#                 resign_obj=ExitDetailsModel.objects.filter(pk__in=exist_instance)
#                 for resign_item in resign_obj:
#                     resign_item.NoticedServed=True
#                     resign_item.EmpLeftOrganization=True
#                     resign_item.Date_of_Left_Organization=timezone.localdate()
#                     resign_item.mail_sent=True
#                     resign_item.resignation.employee_id.employeeProfile.employee_status="in_active"
#                     resign_item.save()

#                     emp_obj=EmployeeInformation(employee_Id=resign_item.resignation.employee_id.EmployeeId)
#                     emp_obj.employee_status="in_active"
#                     emp_obj.save()
#                     print(emp_obj.employee_status)

#                     subject= f"Organaisation Exit Day {resign_item.Date_of_Left_Organization}"
#                     Message=f"Mr/Miss {resign_item.resignation.employee_id.Name} Today is Your Organaisation Exit Day.\n Cheeck all the Setelments Happen or not\n By filling the following form  By EOD."
#                     sender_email = 'sender@example.com'
#                     recipient_email = resign_item.resignation.employee_id.employeeProfile.email
#                     email = EmailMessage(subject, Message, sender_email, [recipient_email])
#                     if resign_item.Required_letters:
#                         email.attach(f'{resign_item.resignation.employee_id.Name}_LeavingLetter.pdf', resign_item.Required_letters.read(), 'application/pdf')
#                     try:
#                         email.send()
#                         return Response({'message': 'Email sent successfully'}, status=status.HTTP_200_OK)
#                     except Exception as e:
#                         return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#             else:
#                 return Response("okkkk",status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             print(e)
#             return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
    
