from .models import AppraisalInvitationModel
from .serializers import *
from EMS_App. models import *
from EMS_App. serializers import *



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

#29/12/2025
class AppraisalInvitationSendView(APIView):
    def get(self,request):
        try:
            employee_id = request.GET.get('employee_id')
            inviter_id = request.GET.get('inviter_id')
            
            emp_obj=EmployeeDataModel.objects.filter(EmployeeId=inviter_id).first()
            if emp_obj.Designation in ["Admin","HR"]:
                AIO = AppraisalInvitationModel.objects.filter(active_status= True)
                serializer = AppraisalInvitationModelSerializer(AIO,context={'request':request},many=True).data
                return Response(serializer,status=status.HTTP_200_OK)
            else:
                AIO = AppraisalInvitationModel.objects.filter(Q(invited_by__EmployeeId=inviter_id),active_status= True)
                serializer = AppraisalInvitationModelSerializer(AIO,context={'request':request},many=True).data
                return Response(serializer,status=status.HTTP_200_OK)
            
            
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

    def post(self,request):
        print(request.data)
        try:
            global self_evalution
            data = request.data.copy()

            emp_id=data.get("Emp_id")
            Emp_obj=EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()

            invited_by=data.get("invited_by")
            inviter=EmployeeDataModel.objects.filter(EmployeeId=invited_by).first()

            data["EmployeeId"]=Emp_obj.pk
            data["invited_by"]=inviter.pk 
            mail_content=data["mail"]

            emp_form_link=data["emp_form_link"]
        
            reporting_mail_content = data['reporting_mail_content']
            rm_form_link=data["rm_form_link"]

            data["invited_on"]=timezone.localtime()

            serializer = AppraisalInvitationModelSerializer(data=data)
            if serializer.is_valid():
                instance=serializer.save()
                
                # Debugging: Print emails to console to verify recipients
                print(f"--- DEBUG EMAIL SENDING ---")
                print(f"Sender: {settings.EMAIL_HOST_USER}")
                print(f"Employee Email (Recipient 1): {Emp_obj.employeeProfile.email}")
                if Emp_obj.Reporting_To and Emp_obj.Reporting_To.employeeProfile:
                     print(f"Manager Email (Recipient 2): {Emp_obj.Reporting_To.employeeProfile.email}")
                else:
                     print(f"Manager Email (Recipient 2): No Reporting Manager or Profile found")
                print(f"---------------------------")
                try:
                    if instance:
                        self_evalution=EmployeeSelfEvaluation.objects.create(invitation_id=instance)
                except Exception as e:
                    return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    if mail_content :
                            print("--- DEBUG: Sending Employee Mail... ---")
                            subject = "Merida Tech Minds Appraisal Invitation"
                            Message= f'{mail_content}\n{emp_form_link}{self_evalution.pk}/'
                            sent_count = send_mail(
                                subject, Message,
                                settings.EMAIL_HOST_USER,
                                [Emp_obj.employeeProfile.email],
                                fail_silently=False,
                            )
                            print(f"--- DEBUG: Employee Mail Sent Count: {sent_count} ---")
                    else:
                        print("--- DEBUG: No mail_content provided, skipping Employee Mail ---")
                except Exception as e:
                    return Response(f"Error sending email: {str(e)}", status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    if self_evalution:
                        # appraisal_review_obj=EmployeeSelfEvaluationReviewModel.objects.create(EmployeeSelfEvaluation=self_evalution,assigning_person=inviter)
                        # Database has NOT NULL constraint on these fields despite model saying null=True.
                        # We must initialize them with 0 to allow record creation.
                        appraisal_review_obj = EmployeeSelfEvaluationReviewModel.objects.create(
                            EmployeeSelfEvaluation=self_evalution,
                            assigning_person=inviter,
                            works_to_full_potential=0,
                            quality_of_work=0,
                            work_consistency=0,
                            communication=0,
                            independent_work=0,
                            takes_initiative=0,
                            group_work=0,
                            productivity=0,
                            creativity=0,
                            honesty=0,
                            integrity=0,
                            coworker_relations=0,
                            client_relations=0,
                            technical_skills=0,
                            dependability=0,
                            punctuality=0,
                            attendance=0,
                            overall=0
                        )
                        print(f"--- DEBUG: Created Appraisal Review Object: {appraisal_review_obj.pk} ---")
                except Exception as e:
                     print(f"--- DEBUG ERROR: Failed to create Appraisal Review Object: {str(e)} ---")
                     return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    print("--- DEBUG: Starting Manager Mail Process... ---")
                    
                    reporting_manager = Emp_obj.Reporting_To
                    reporting_manager_email = None
                    
                    if reporting_manager and reporting_manager.employeeProfile:
                        reporting_manager_email = reporting_manager.employeeProfile.email
                    else:
                        print("--- DEBUG ERROR: No Reporting Manager or Profile found in DB ---")

                    if reporting_manager_email:
                        subject = "Merida Tech Minds Employee Appraisal Review Invitation"
                        # Ensure appraisal_review_obj exists
                        if 'appraisal_review_obj' in locals() and appraisal_review_obj:
                             Message= f'{reporting_mail_content}\n{rm_form_link}{appraisal_review_obj.pk}/'

                             sent_count_rm = send_mail(
                                    subject, Message,
                                    settings.EMAIL_HOST_USER,
                                    [reporting_manager_email],
                                    fail_silently=False,
                                    )
                             print(f"--- DEBUG: Manager Mail Sent Count: {sent_count_rm} to {reporting_manager_email} ---")
                        else:
                             print("--- DEBUG ERROR: appraisal_review_obj is missing! ---")
                    else:
                         print(f"--- DEBUG ERROR: Skipping Manager mail. Email is None. Manager: {reporting_manager} ---")
                    
                except Exception as e:
                    print(f"--- DEBUG MANAGER EMAIL ERROR: {str(e)} ---")
                    # Do not fail the request if just the second email fails, but log it.
                    # return Response(str(e)) # Optional: decide if you want to fail hard here.

                    
                    
                except Exception as e:
                    print(e)
                    return  Response(e)
                return Response("send successfully",status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)


class EmployeeSelfEvaluationReviewModelView(viewsets.ModelViewSet):
    queryset = EmployeeSelfEvaluationReviewModel.objects.all()
    serializer_class = EmployeeSelfEvaluationReviewModelSerializer

class GetSelfAppraisalData(APIView):
    def get(self,request):
        try:
            self_app_id = request.GET.get('self_app_id')
            
            # Better error handling with detailed messages
            if not self_app_id:
                return Response({
                    "error": "Missing required parameter 'self_app_id'",
                    "details": "Please provide a valid self_app_id in the query parameters"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            self_app_obj=EmployeeSelfEvaluation.objects.filter(pk=self_app_id).first()
            result_dict={}
            if self_app_obj:
                # Defensive checks for null references
                try:
                    # Check if invitation_id exists
                    if not self_app_obj.invitation_id:
                        return Response({
                            "error": "Data integrity issue",
                            "details": f"EmployeeSelfEvaluation {self_app_id} has no associated AppraisalInvitation",
                            "help": "This record may be corrupted. Please contact system administrator."
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                    AIO = AppraisalInvitationModel.objects.filter(pk=self_app_obj.invitation_id.pk).first()
                    
                    if not AIO:
                        return Response({
                            "error": "Data integrity issue",
                            "details": f"AppraisalInvitation record not found for invitation_id: {self_app_obj.invitation_id.pk}",
                            "help": "Referenced invitation may have been deleted. Please create a new appraisal invitation."
                        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                    # Try serializing
                    AIO_serializer = AppraisalInvitationModelSerializer(AIO,context={'request':request}).data
                    self_app_serializer=EmployeeSelfEvaluationSerializer(self_app_obj,context={'request':request}).data

                    result_dict.update({"AppraisalInvitation":AIO_serializer})
                    result_dict.update({"SelfApprailsal":self_app_serializer})
                    return Response(result_dict,status=status.HTTP_200_OK)
                    
                except AttributeError as ae:
                    # Handle null reference errors
                    print(f"AttributeError in GetSelfAppraisalData GET: {str(ae)}")
                    return Response({
                        "error": "Data access error",
                        "details": f"Error accessing related data: {str(ae)}",
                        "help": "Some required data may be missing. Please check the database records."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                    
                except Exception as ser_error:
                    # Handle serialization errors
                    print(f"Serialization error in GetSelfAppraisalData GET: {str(ser_error)}")
                    return Response({
                        "error": "Serialization error", 
                        "details": str(ser_error),
                        "help": "Error converting database records to JSON. Please contact administrator."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # return Response("EmployeeSelfEvaluation got None",status=status.HTTP_400_BAD_REQUEST)
            
            # Check what records exist
            all_ids = list(EmployeeSelfEvaluation.objects.values_list('pk', flat=True))
            return Response({
                "error": "Employee Self Evaluation not found",
                "details": f"No EmployeeSelfEvaluation record found with ID: {self_app_id}",
                "available_ids": all_ids[:10] if all_ids else [],  # Show first 10 available IDs
                "total_records": len(all_ids),
                "help": "Please check if the appraisal invitation was created properly or use a valid ID from available_ids"
            }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            # Better exception handling
            print(f"Error in GetSelfAppraisalData GET: {str(e)}")
            import traceback
            traceback.print_exc()  # Print full stack trace to console
            return Response({
                "error": "Internal server error",
                "details": str(e),
                "type": type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self, request):
        try:
            data = request.data.copy()  # Make a mutable copy
            id = data.get("id")

            if not id:
                return Response({"error": "ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            self_app_obj = EmployeeSelfEvaluation.objects.filter(pk=id).first()

            if not self_app_obj:
                return Response({"error": "Employee Self Evaluation not found."}, status=status.HTTP_404_NOT_FOUND)

            # Handle DATE_OF_REVIEW format conversion
            if 'DATE_OF_REVIEW' in data and data['DATE_OF_REVIEW']:
                date_value = data['DATE_OF_REVIEW']
                try:
                    # Try to parse various date formats and convert to YYYY-MM-DD
                    from datetime import datetime
                    
                    # Try different date format patterns
                    date_formats = [
                        '%Y-%m-%d',      # 2025-12-29
                        '%d/%m/%Y',      # 29/12/2025
                        '%m/%d/%Y',      # 12/29/2025
                        '%d-%m-%Y',      # 29-12-2025
                        '%Y/%m/%d',      # 2025/12/29
                    ]
                    
                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(str(date_value), fmt)
                            break
                        except ValueError:
                            continue
                    
                    if parsed_date:
                        # Convert to YYYY-MM-DD format
                        data['DATE_OF_REVIEW'] = parsed_date.strftime('%Y-%m-%d')
                    else:
                        # If we can't parse it, remove it to avoid validation error
                        print(f"Could not parse DATE_OF_REVIEW: {date_value}")
                        del data['DATE_OF_REVIEW']
                        
                except Exception as e:
                    print(f"Error parsing DATE_OF_REVIEW: {str(e)}")
                    # Remove the field if we can't parse it
                    del data['DATE_OF_REVIEW']
            
            # Handle employee_signature - remove if not provided or empty
            if 'employee_signature' in data:
                if not data['employee_signature'] or data['employee_signature'] == '':
                    del data['employee_signature']

            serializer = EmployeeSelfEvaluationSerializer(
                self_app_obj, data=data, partial=True, context={'request': request}
            )

            if serializer.is_valid():
                instance = serializer.save()
                
                # Assuming invitation_id is a foreign key or related field in EmployeeSelfEvaluation
                AIO = instance.invitation_id
                if AIO:
                    AIO.is_filled = True
                    AIO.filled_on = timezone.localtime()
                    AIO.save()
                else:
                    return Response({"error": "Appraisal Invitation ID not found."}, status=status.HTTP_400_BAD_REQUEST)
                
                return Response({"message": "Saved successfully"}, status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except EmployeeSelfEvaluation.DoesNotExist:
            return Response({"error": "Employee Self Evaluation not found."}, status=status.HTTP_404_NOT_FOUND)
        except AppraisalInvitationModel.DoesNotExist:
            return Response({"error": "Appraisal Invitation not found."}, status=status.HTTP_404_NOT_FOUND)
        except KeyError as e:
            return Response({"error": f"Missing field: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Error in GetSelfAppraisalData PATCH: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class GetReportingManagerAppraisalData(APIView):
    def get(self,request):
        try:
            rm_app_id = request.GET.get('rm_app_id')
    
            self_rm_app_obj=EmployeeSelfEvaluationReviewModel.objects.filter(pk=rm_app_id).first()

            result_dict={}
            if self_rm_app_obj:
                SAIO = AppraisalInvitationModel.objects.filter(pk=self_rm_app_obj.EmployeeSelfEvaluation.invitation_id.pk).first()
                AIO_serializer = AppraisalInvitationModelSerializer(SAIO,context={'request':request}).data
                self_app_serializer=EmployeeSelfEvaluationReviewModelSerializer(self_rm_app_obj,context={'request':request}).data
                result_dict.update({"AppraisalInvitation":AIO_serializer})
                result_dict.update({"RMSelfApprailsal":self_app_serializer})
                return Response(result_dict,status=status.HTTP_200_OK)
            return Response("EmployeeSelfEvaluation got None",status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self, request):
        try:
            print("--- DEBUG PATCH REPORTING MANAGER ---")
            # print(f"Data received: {request.data}") 
            
            data = request.data
            id = data.get("id")

            if not id:
                return Response({"error": "ID is required."}, status=status.HTTP_400_BAD_REQUEST)

            self_rm_app_obj=EmployeeSelfEvaluationReviewModel.objects.filter(pk=id).first()

            if not self_rm_app_obj:
                return Response({"error": "Employee Self Evaluation not found."}, status=status.HTTP_404_NOT_FOUND)

            # Clean empty strings from data
            cleaned_data = {}
            for key, value in data.items():
                if value is not None and value != "":
                   cleaned_data[key] = value

            serializer = EmployeeSelfEvaluationReviewModelSerializer(
                self_rm_app_obj, data=cleaned_data, partial=True, context={'request': request}
            )

            if serializer.is_valid():
                instance = serializer.save()
                
                # Safely update the invitation status
                try:
                    if instance.EmployeeSelfEvaluation and instance.EmployeeSelfEvaluation.invitation_id:
                        AIO = instance.EmployeeSelfEvaluation.invitation_id
                        AIO.is_rm_filled = True
                        AIO.rm_filled_on = timezone.localtime()
                        AIO.save()
                        print(f"--- DEBUG: Updated Invitation {AIO.pk} status ---")
                    else:
                        print("--- DEBUG WARNING: Could not update AIO status. Missing EmployeeSelfEvaluation or invitation_id. ---")
                except Exception as e:
                     print(f"--- DEBUG ERROR Updating Invitation: {str(e)} ---")

                return Response({"message": "Saved successfully"}, status=status.HTTP_200_OK)
            else:
                print(f"--- DEBUG SERIALIZER ERRORS: {serializer.errors} ---")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # except EmployeeSelfEvaluation.DoesNotExist:
        #     return Response({"error": "Employee Self Evaluation not found."}, status=status.HTTP_404_NOT_FOUND)
        # except AppraisalInvitationModel.DoesNotExist:
        #     return Response({"error": "Appraisal Invitation not found."}, status=status.HTTP_404_NOT_FOUND)
        # except KeyError as e:
        #     return Response({"error": f"Missing field: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"--- DEBUG EXCEPTION IN PATCH: {str(e)} ---")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    

class PerformanceMetricsView(APIView):
    def get(self,request):
        self_app_id=request.GET.get('self_app_id')
        try:
            PM=Performance_Metrics_Model.objects.filter(EmployeeSelfEvaluation__pk=self_app_id).first()
            print(PM)
            meeting_review_serializer = Performance_Metrics_Model_Serializer(PM).data
            return Response(meeting_review_serializer,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def post(self, request):
        print(request.data)
        data = request.data.copy()
        mail_content = data.get("mail_content", "")
        # Validate the incoming data
        meeting_review_serializer = Performance_Metrics_Model_Serializer(data=data)
        if meeting_review_serializer.is_valid():
            try:
                # Save the data and send email if successful
                meeting_instance = meeting_review_serializer.save()
                invitation=meeting_instance.EmployeeSelfEvaluation.invitation_id
                invitation.meeting_mail_sent_status=True
                invitation.save()
                
                if meeting_instance:
                    subject = "Merida Tech Minds Appraisal Meeting Schedule"
                    # Safely retrieve the email, ensuring all necessary objects exist
                    try:
                        mail = meeting_instance.EmployeeSelfEvaluation.invitation_id.EmployeeId.employeeProfile.email
                    except AttributeError as e:
                        return Response({"error": "Error retrieving email address: " + str(e)}, status=status.HTTP_400_BAD_REQUEST)

                    # Send the email
                    try:
                        send_mail(
                            subject, mail_content,
                            settings.EMAIL_HOST_USER,
                            [mail],
                            fail_silently=False,
                        )

                        return Response("Mail sent Successfully", status=status.HTTP_200_OK)
                    except Exception as e:
                        # Handle email sending errors
                        return Response({"error": "Failed to send email: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except Exception as e:
                # Handle unexpected errors during saving or processing
                return Response({"error": "An error occurred while processing the request: " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            # Handle validation errors
            return Response(meeting_review_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self,request):
        try:
            print(request.data)
            data=request.data.copy()
            pm_obj=Performance_Metrics_Model.objects.filter(pk=data["id"]).first()
            pm_serializer=Performance_Metrics_Model_Serializer(pm_obj,data=data,partial=True)
            if pm_serializer.is_valid():
                pm_serializer.save()
                return Response("review done",status=status.HTTP_200_OK)
            else:
                print(pm_serializer.errors)
                return Response("review fail",status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            return Response("review error",status=status.HTTP_400_BAD_REQUEST)
        


class EmployeementPositionChanges(APIView):

    def get(self, request):
        self_app__id = request.GET.get("self_app__id")
        try:
            EPH = CompanyEmployeesPositionHistory.objects.filter(Appraisal_instance__pk=self_app__id).first()
            EPH_serializer = CompanyEmployeesPositionHistorySerializer(EPH).data
            return Response(EPH_serializer, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        data = request.data.copy()
        print("ffrrrfrf",data)
        id = data.get("emp_info_id")
        salary = data.get("assigned_salary")
        applicable_date = data.get("applicable_date")
        self_app__id=data.get("self_app__id")
        # Fetch the employee profile
        emp_create = EmployeeDataModel.objects.filter(employeeProfile__pk=id).first()

        if not emp_create:
            return Response({"detail": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
        try:
            # Create a new entry in the position history
            EPH = CompanyEmployeesPositionHistory.objects.create(employee=emp_create)
            # Save the position history
            if EPH:
                EPH.Appraisal_instance=self_app__id
                EPH.designation = emp_create.Position
                EPH.assigned_salary = salary if salary else None
                EPH.start_date = applicable_date if applicable_date else None
                EPH.rm_manager = emp_create.Reporting_To if emp_create.Reporting_To else None
                EPH.Employeement_Type = emp_create.employeeProfile.Employeement_Type if emp_create.employeeProfile.Employeement_Type else None
                EPH.internship_Duration_From=emp_create.employeeProfile.internship_Duration_From if emp_create.employeeProfile.internship_Duration_From else None
                EPH.internship_Duration_To=emp_create.employeeProfile.internship_Duration_To if emp_create.employeeProfile.internship_Duration_To else None
                EPH.probation_status = emp_create.employeeProfile.probation_status if emp_create.employeeProfile.probation_status else None
                EPH.probation_Duration_From=emp_create.employeeProfile.probation_Duration_From if emp_create.employeeProfile.probation_Duration_From else None
                EPH.probation_Duration_To=emp_create.employeeProfile.probation_Duration_To if emp_create.employeeProfile.probation_Duration_To else None
            EPH.save()

            return Response({"detail": "Position history updated successfully"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
    def patch(self,request):
        id=request.data.get("id")
        EPH = CompanyEmployeesPositionHistory.objects.filter(pk=id).first()
        if EPH:
            EPH_serializer = CompanyEmployeesPositionHistorySerializer(EPH,data=request.data,partial=True)
            if EPH_serializer.is_valid():
                instance=EPH_serializer.save()
                return Response("done!", status=status.HTTP_200_OK)
            else:
                return Response(EPH_serializer.errors, status=status.HTTP_200_OK)
        else:
            return Response("CompanyEmployeesPositionHistory is none!",status=status.HTTP_400_BAD_REQUEST)

        


        

        

        