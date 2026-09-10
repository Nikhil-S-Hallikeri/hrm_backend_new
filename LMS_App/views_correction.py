from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from .models_correction import AttendanceCorrectionRequest
from .serializers_correction import AttendanceCorrectionRequestSerializer
from .models import CompanyAttendanceDataModel
from HRM_App.models import EmployeeDataModel

class AttendanceCorrectionRequestView(generics.ListCreateAPIView):
    queryset = AttendanceCorrectionRequest.objects.all().order_by('-created_at')
    serializer_class = AttendanceCorrectionRequestSerializer

    def create(self, request, *args, **kwargs):
        # Expect 'attendance_record_id' and 'requested_status'
        attendance_id = request.data.get('attendance_record_id')
        requested_status = request.data.get('requested_status')
        reason = request.data.get('reason')
        requester_id = request.data.get('employee_id') # The one requesting (logged in user)
        target_emp_id = request.data.get('target_employee_id') # The employee whose attendance is being fixed
        date_str = request.data.get('attendance_date')

        try:
            # 1. Resolve Attendance Record
            if attendance_id:
                attendance_obj = CompanyAttendanceDataModel.objects.get(id=attendance_id)
            elif target_emp_id and date_str:
                # Find or Create a placeholder record
                # We need the Employee Object for the TARGET
                target_emp_obj = EmployeeDataModel.objects.get(EmployeeId=target_emp_id)
                
                attendance_obj, created = CompanyAttendanceDataModel.objects.get_or_create(
                    Emp_Id=target_emp_obj,
                    date=date_str,
                    defaults={
                        'Status': 'absent', # Default to absent if missing
                        'Day': timezone.datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
                    }
                )
            else:
                 return Response({"error": "Missing attendance ID or Date/TargetEmployee"}, status=status.HTTP_400_BAD_REQUEST)

            # 2. Resolve Requester
            # If requester_id not provided, maybe fallback to target (self-correction)? 
            # But normally frontend should send it.
            if requester_id:
                employee_obj = EmployeeDataModel.objects.get(EmployeeId=requester_id)
            else:
                # Fallback purely for safety, though frontend should send it
                 employee_obj = attendance_obj.Emp_Id 

            # Create request
            correction = AttendanceCorrectionRequest.objects.create(
                attendance_record=attendance_obj,
                requested_by=employee_obj,
                previous_status=attendance_obj.Status,
                requested_status=requested_status,
                reason=reason
            )
            
            serializer = self.get_serializer(correction)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ApproveAttendanceCorrectionView(APIView):
    def post(self, request, pk):
        try:
            correction = AttendanceCorrectionRequest.objects.get(pk=pk)
            action = request.data.get('action') # 'Approved' or 'Rejected'
            approver_id = request.data.get('approver_id')
            approval_reason = request.data.get('approval_reason', '')
            
            approver = EmployeeDataModel.objects.get(EmployeeId=approver_id)
            
            if action == 'Approved':
                # Update the actual attendance record
                attendance_record = correction.attendance_record
                attendance_record.Status = correction.requested_status
                # If changing to Present, logic for working hours? 
                # For now just force the status as that's what Payslip uses.
                attendance_record.save()
                
                correction.request_status = 'Approved'
                
                # --- Auto-Regenerate Payslip ---
                try:
                    from payroll_app.views import getEmployeesAttendanceCalculation, generatePaySlip
                    # emp_id = correction.requested_by.EmployeeId
                    # month = correction.attendance_record.date.month
                    # year = correction.attendance_record.date.year
                    
                    # print(f"Auto-regenerating payslip for {emp_id} - {month}/{year}")
                    target_emp_id = attendance_record.Emp_Id.EmployeeId
                    month = attendance_record.date.month
                    year = attendance_record.date.year
                    
                    # 1. Recalculate stats
                    # output = getEmployeesAttendanceCalculation(emp_id, month, year)
                    # output["employee"] = emp_id
                    output = getEmployeesAttendanceCalculation(target_emp_id, month, year)
                    if output:
                        output["employee"] = target_emp_id
                        output["month"] = month
                        output["year"] = year
                        
                        # 2. Update/Create Payslip
                        generatePaySlip(**output)
                    
                except Exception as e:
                    print(f"Error auto-regenerating payslip: {e}")
                # -------------------------------
            elif action == 'Rejected':
                correction.request_status = 'Rejected'
            else:
                 return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)
                
            correction.approved_by = approver
            correction.approval_reason = approval_reason
            correction.approval_date = timezone.localtime()
            correction.save()
            
            return Response({"message": f"Request {action} successfully"}, status=status.HTTP_200_OK)
            
        except AttendanceCorrectionRequest.DoesNotExist:
             return Response({"error": "Request not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
