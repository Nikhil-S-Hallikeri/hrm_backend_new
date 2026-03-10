from HRM_App.models import *
from HRM_App.imports import *
from EMS_App.models import *
from .models import *
from .serializers import *
from rest_framework import viewsets
import time
from django.db.models import Min, Max
from datetime import time, datetime, timedelta
from rest_framework import status
import pandas as pd
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.shortcuts import get_object_or_404

class EmployeeShiftsAPIView(APIView):
    def post(self, request):
        emps_list = request.data.get("emps_list")
        shift_id = request.data.get("shift_obj")
        # Validate that both `emps_list` and `shift_id` are provided
        if emps_list and shift_id:
             # Validate `emps_list` is a list
            if not isinstance(emps_list, list):
                return Response(
                    {"error": "emps_list must be a list."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Fetch the shift object
            shift_obj = EmployeeShifts_Model.objects.filter(pk=shift_id).first()
            if not shift_obj:
                return Response(
                    {"error": "Shift does not exist."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Iterate over employee IDs and assign the shift
            for emp_id in emps_list:
                emp_obj = EmployeeInformation.objects.filter(employee_Id=emp_id).first()
                if emp_obj:
                    emp_obj.EmployeeShifts = shift_obj
                    emp_obj.save()
                else:
                    return Response(
                        {"error": f"Employee with ID {emp_id} does not exist."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            return Response({"message": "Shift assigned successfully."}, status=status.HTTP_200_OK)

        # If `emps_list` or `shift_obj` is not provided, handle shift creation
        else:
            serializer = EmployeeShiftsSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    def get(self, request, pk=None):
        if pk:
            # Detail view
            shift = get_object_or_404(EmployeeShifts_Model, pk=pk)
            serializer = EmployeeShiftsSerializer(shift)
            return Response(serializer.data)
        else:
            # List view
            shifts = EmployeeShifts_Model.objects.all()
            serializer = EmployeeShiftsSerializer(shifts, many=True)
            return Response(serializer.data)

    def patch(self, request, pk):
        shift = get_object_or_404(EmployeeShifts_Model, pk=pk)
        serializer = EmployeeShiftsSerializer(shift, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# EmployeeShifts_Model

class EmployeeShiftAddingView():
    def post(self,request):
        emps_list=request.data.get("emps_list")
        shift_id=request.data.get("shift_obj")
        shift_obj=EmployeeShifts_Model.objects.filter(pk=shift_id).first()
        if not shift_obj:
            return Response("Shift not Exist",status=status.HTTP_400_BAD_REQUEST)

        for emp in emps_list:
            emp_obj=EmployeeInformation.objects.filter(employeeId=emp).first()
            if emp_obj:
                emp_obj.EmployeeShifts=shift_obj.pk
                emp_obj.save()
        return Response("Success",status=status.HTTP_200_OK)
                

     

# to add the data 
# class AttendatnceAddingView(APIView):
#     def post(self, request):
#         try:
#             request_data = request.data.copy()
#             # Emp_obj = EmployeeDataModel.objects.get(EmployeeId=request_data["Emp_Id"])
#             Emp_obj = EmployeeDataModel.objects.get(employeeProfile__employee_attendance_id=request_data["Emp_Id"])
#             request_data["PayCode"] = Emp_obj.pk
            
#             Com_Attendance_Serializer = CompanyAttendanceDataSerializer(data=request_data)
#             if Com_Attendance_Serializer.is_valid():

#                 punch_timings = request_data["Punch_Time"]
#                 dt = datetime.strptime(punch_timings, '%b %d %Y %I:%M%p')
#                 date = dt.date()
#                 time = dt.time()
#                 # current_data=request_data["date"]
#                 current_data=dt.date()
#                 obj=CompanyAttendanceDataModel.objects.filter(Emp_Id=Emp_obj.pk,date=current_data).first()
#                 if obj:
#                     instance=obj
#                 else:
#                     instance = Com_Attendance_Serializer.save()
#                 # sc_list = json.loads(dt.time())#request_data["scanned_list"]
#                 sc_list = request_data.get("Punch_Time", [])
#                 if not sc_list:
#                     return Response({"error": "Punch_Time list is missing"}, status=status.HTTP_400_BAD_REQUEST)

#                 dt = datetime.now()
#                 date = dt.date()
#                 time = dt.time()
#                 current_data = dt.date()

#                 for data in sc_list:
#                     data["Attendance"] = instance.pk
#                     Attendance_Serializer = AttendanceSerializer(data=data)
#                     if Attendance_Serializer.is_valid():
#                         Attendance_Serializer.save()
#                     else:
#                         return Response({"error": "Scanning Data adding error", "details": Attendance_Serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
#                 att_entry_instance = CompanyAttendanceDataModel.objects.get(pk=instance.pk)
#                 attendance_entries = att_entry_instance.companyattendance_set.all()

#                 if attendance_entries.exists():
#                     first_entry = attendance_entries.order_by('Created_Date').first()
#                     last_entry = attendance_entries.order_by('Created_Date').last()
                    
#                     att_entry_instance.InTime = first_entry.ScanTimings
#                     att_entry_instance.OutTime = last_entry.ScanTimings

#                     start_time = time(9, 30)
#                     end_time = time(18, 30)
#                     if att_entry_instance.InTime and att_entry_instance.InTime > start_time:
#                         late_arrival = (datetime.combine(datetime.min, att_entry_instance.InTime) - datetime.combine(datetime.min, start_time))
#                         att_entry_instance.Late_Arrivals = (datetime.min + late_arrival).time()
#                     else:
#                         att_entry_instance.Late_Arrivals = None
                    
                    
#                     if att_entry_instance.OutTime and att_entry_instance.OutTime < end_time:
#                         early_departure = (datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, att_entry_instance.OutTime))
#                         att_entry_instance.Early_Depature = (datetime.min + early_departure).time()
#                     else:
#                         att_entry_instance.Early_Depature = None
                    
#                     if att_entry_instance.InTime and att_entry_instance.OutTime:
#                         hours_worked = (datetime.combine(datetime.min, att_entry_instance.OutTime) - datetime.combine(datetime.min, att_entry_instance.InTime))
#                         att_entry_instance.Hours_Worked = (datetime.min + hours_worked).time()
#                     else:
#                         att_entry_instance.Hours_Worked = None

#                     if start_time and end_time:
#                         hours_worked = (datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time))
#                         att_entry_instance.TotalWorkingHours = (datetime.min + hours_worked).time()

#                     if att_entry_instance.Hours_Worked:
#                         if att_entry_instance.Hours_Worked >= time(8,00):
#                             att_entry_instance.Status="present"
#                         else:
#                             att_entry_instance.Status="absent"
                    
#                     att_entry_instance.save()

#                 return Response({"message": "Uploaded Successfully"}, status=status.HTTP_200_OK)
            
#             return Response({"errors": Com_Attendance_Serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
# =================================================================================================================
# Outtime issues solved code 




# Orignal from Server 

# class AttendatnceAddingView(APIView):
#     def post(self, request):
#         try:
#             request_data = request.data.copy()
#             # Emp_obj = EmployeeDataModel.objects.get(EmployeeId=request_data["Emp_Id"])
#             Emp_obj = EmployeeDataModel.objects.get(employeeProfile__employee_attendance_id=request_data["Emp_Id"])
#             request_data["PayCode"] = Emp_obj.pk
            
#             Com_Attendance_Serializer = CompanyAttendanceDataSerializer(data=request_data)
#             if Com_Attendance_Serializer.is_valid():

#                 punch_timings = request_data["Punch_Time"]
#                 dt = datetime.strptime(punch_timings, '%b %d %Y %I:%M%p')
#                 date = dt.date()
#                 time = dt.time()
#                 # current_data=request_data["date"]
#                 current_data=dt.date()
#                 obj=CompanyAttendanceDataModel.objects.filter(Emp_Id=Emp_obj.pk,date=current_data).first()
#                 if obj:
#                     instance=obj
#                 else:
#                     instance = Com_Attendance_Serializer.save()
#                 sc_list = json.loads(dt.time())#request_data["scanned_list"]

#                 for data in sc_list:
#                     data["Attendance"] = instance.pk
#                     Attendance_Serializer = AttendanceSerializer(data=data)
#                     if Attendance_Serializer.is_valid():
#                         Attendance_Serializer.save()
#                     else:
#                         return Response({"error": "Scanning Data adding error", "details": Attendance_Serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
#                 att_entry_instance = CompanyAttendanceDataModel.objects.get(pk=instance.pk)
#                 attendance_entries = att_entry_instance.companyattendance_set.all()

#                 if attendance_entries.exists():
#                     first_entry = attendance_entries.order_by('Created_Date').first()
#                     last_entry = attendance_entries.order_by('Created_Date').last()
                    
#                     att_entry_instance.InTime = first_entry.ScanTimings
#                     att_entry_instance.OutTime = last_entry.ScanTimings

#                     start_time = time(9, 30)
#                     end_time = time(18, 30)
#                     if att_entry_instance.InTime and att_entry_instance.InTime > start_time:
#                         late_arrival = (datetime.combine(datetime.min, att_entry_instance.InTime) - datetime.combine(datetime.min, start_time))
#                         att_entry_instance.Late_Arrivals = (datetime.min + late_arrival).time()
#                     else:
#                         att_entry_instance.Late_Arrivals = None
                    
                    
#                     if att_entry_instance.OutTime and att_entry_instance.OutTime < end_time:
#                         early_departure = (datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, att_entry_instance.OutTime))
#                         att_entry_instance.Early_Depature = (datetime.min + early_departure).time()
#                     else:
#                         att_entry_instance.Early_Depature = None
                    
#                     if att_entry_instance.InTime and att_entry_instance.OutTime:
#                         hours_worked = (datetime.combine(datetime.min, att_entry_instance.OutTime) - datetime.combine(datetime.min, att_entry_instance.InTime))
#                         att_entry_instance.Hours_Worked = (datetime.min + hours_worked).time()
#                     else:
#                         att_entry_instance.Hours_Worked = None

#                     if start_time and end_time:
#                         hours_worked = (datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time))
#                         att_entry_instance.TotalWorkingHours = (datetime.min + hours_worked).time()

#                     if att_entry_instance.Hours_Worked:
#                         if att_entry_instance.Hours_Worked >= time(8,00):
#                             att_entry_instance.Status="present"
#                         else:
#                             att_entry_instance.Status="absent"
                    
#                     att_entry_instance.save()

#                 return Response({"message": "Uploaded Successfully"}, status=status.HTTP_200_OK)
            
#             return Response({"errors": Com_Attendance_Serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)







class AttendatnceAddingView(APIView):
    def post(self, request):
        try:
            request_data = request.data.copy()

            Emp_obj = EmployeeDataModel.objects.get(employeeProfile__employee_attendance_id=request_data["Emp_Id"])
            request_data["PayCode"] = Emp_obj.pk

            punch_list = request_data.get("Punch_Time", [])
            if not punch_list:
                return Response({"error": "Punch_Time list is missing or empty"}, status=status.HTTP_400_BAD_REQUEST)

            # Take date from first punch
            dt = datetime.strptime(punch_list[0]["ScanTimings"], "%H:%M:%S")
            current_date = datetime.now().date()

            attendance_obj, created = CompanyAttendanceDataModel.objects.get_or_create(
                Emp_Id=Emp_obj, date=current_date
            )

            for punch in punch_list:
                punch["Attendance"] = attendance_obj.pk
                attendance_serializer = AttendanceSerializer(data=punch)
                if attendance_serializer.is_valid():
                    attendance_serializer.save()
                else:
                    return Response({
                        "error": "Invalid punch data",
                        "details": attendance_serializer.errors
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # # Calculate timings
            # punches = attendance_obj.companyattendance_set.all().order_by("Created_Date")
            # if punches.exists():
            #     first = punches.first()
            #     last = punches.last()

            # Calculate timings and update status using centralized Model logic
            attendance_obj.save(force_recalculate=True)


            # attendance_obj.InTime = first.ScanTimings
            # attendance_obj.OutTime = last.ScanTimings
            # start_shift = time(9, 30)
            # end_shift = time(18, 30)
            # # Late Arrival
            # if attendance_obj.InTime and attendance_obj.InTime > start_shift:
            #     diff = datetime.combine(date.min, attendance_obj.InTime) - datetime.combine(date.min, start_shift)
            #     attendance_obj.Late_Arrivals = (datetime.min + diff).time()
            # else:
            #     attendance_obj.Late_Arrivals = None
            # # Early Departure
            # if attendance_obj.OutTime and attendance_obj.OutTime < end_shift:
            #     diff = datetime.combine(date.min, end_shift) - datetime.combine(date.min, attendance_obj.OutTime)
            #     attendance_obj.Early_Depature = (datetime.min + diff).time()
            # else:
            #     attendance_obj.Early_Depature = None
            # # Hours Worked
            # if attendance_obj.InTime and attendance_obj.OutTime:
            #     worked = datetime.combine(date.min, attendance_obj.OutTime) - datetime.combine(date.min, attendance_obj.InTime)
            #     attendance_obj.Hours_Worked = (datetime.min + worked).time()
            # # Fixed shift working hours
            # attendance_obj.TotalWorkingHours = (datetime.combine(date.min, end_shift) - datetime.combine(date.min, start_shift)).time()
            # # Status
            # if attendance_obj.Hours_Worked and attendance_obj.Hours_Worked >= time(8, 0):
            #     attendance_obj.Status = "present"
            # else:
            #     attendance_obj.Status = "absent"
            # attendance_obj.save()



            return Response({"message": "Uploaded Successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)




class DailyAttendanceRecordCreateView(APIView):
    def post(self, request):
        try:
            emp_id = request.GET.get("emp_id")
            if not emp_id:
                return Response({"message": "employee id is required"}, status=status.HTTP_400_BAD_REQUEST)

            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=emp_id, employeeProfile__employee_status="active").first()
            if not emp_obj:
                return Response({"message": "employee not found or blocked"}, status=status.HTTP_400_BAD_REQUEST)

            current_date = timezone.localdate()
            attendance_obj = CompanyAttendanceDataModel.objects.filter(Emp_Id=emp_obj, date=current_date).first()

            if not attendance_obj:
                # create today's login
                attendance_obj = CompanyAttendanceDataModel.objects.create(Emp_Id=emp_obj)
                attendance_obj.date = current_date
                attendance_obj.Day = current_date.strftime("%A")
                attendance_obj.Shift = emp_obj.employeeProfile.EmployeeShifts
                attendance_obj.save()

            # Create attendance instance for scanning time
            instance = CompanyAttendance.objects.create(Attendance=attendance_obj, ScanTimings=timezone.localtime().time())

            if attendance_obj and not attendance_obj.InTime:

                # start_time = time(9, 30)
                # end_time = time(18, 30)

                emp_shifts = emp_obj.employeeProfile.EmployeeShifts
                start_time = emp_shifts.start_shift if emp_shifts else time(9, 30)
                end_time = emp_shifts.end_shift if emp_shifts else time(18, 30)

                # Fetch first entry of scan timing (assuming 'instance' is saved)
                first_entry = CompanyAttendance.objects.filter(Attendance=attendance_obj).order_by('Created_Date').first()
                attendance_obj.InTime = first_entry.ScanTimings if first_entry else None
                attendance_obj.save()

                if attendance_obj.InTime and attendance_obj.InTime > start_time:
                    late_arrival = (datetime.combine(datetime.min, attendance_obj.InTime) - datetime.combine(datetime.min, start_time))
                    attendance_obj.Late_Arrivals = (datetime.min + late_arrival).time()
                else:
                    attendance_obj.Late_Arrivals = None

                attendance_obj.save()
            
            return Response({"message": f"Attendance Created on {current_date}"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        


from django.db import transaction
import logging
from datetime import datetime, time, timedelta

logger = logging.getLogger(__name__)

def EmployeesAttendanceStatusUpdating(current_date):
    from datetime import date

    print("yest/////////////////", current_date)
    
    # Validate current_date to avoid 'date out of range' errors
    try:
        if not isinstance(current_date, date):
            raise ValueError(f"Invalid date provided: {current_date}")
    except ValueError as e:
        logger.error(f"Date validation error: {e}")
        return  # Log the error but avoid processing if the date is invalid.

    active_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

    if not active_employees.exists():
        logger.info("No active employees found.")
        return

    for emp_obj in active_employees:
        try:
            with transaction.atomic():
                attendance_obj = CompanyAttendanceDataModel.objects.filter(Emp_Id=emp_obj, date=current_date).first()
                emp_shifts = emp_obj.employeeProfile.EmployeeShifts

                if attendance_obj:
                    if not attendance_obj.Status:
                        punches_obj = CompanyAttendance.objects.filter(Attendance=attendance_obj).order_by('Created_Date')

                        if punches_obj.count() == 1:
                            attendance_obj.Status = "absent"
                            attendance_obj.leave_information = "Unauthorized_Absent"
                            attendance_obj.save()
                            continue
                        
                        last_out_punch = punches_obj.filter(ScanType=False).order_by('-id').first()
                        attendance_obj.OutTime = last_out_punch.ScanTimings if last_out_punch else None
                        attendance_obj.save()

                        start_time = emp_shifts.start_shift if emp_shifts else time(9, 30)
                        end_time = emp_shifts.end_shift if emp_shifts else time(18, 30)

                        if attendance_obj.OutTime and attendance_obj.OutTime < end_time:
                            early_departure = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, attendance_obj.OutTime)
                            attendance_obj.Early_Depature = (datetime.min + early_departure).time()
                        else:
                            attendance_obj.Early_Depature = None

                        if attendance_obj.InTime and attendance_obj.OutTime:
                            # Adjust start and end times within shift hours
                            adjusted_start = max(attendance_obj.InTime, start_time)
                            adjusted_end = min(attendance_obj.OutTime, end_time)

                            if adjusted_start < adjusted_end:  # Ensure valid time range
                                total_work_hours = datetime.combine(datetime.min, adjusted_end) - datetime.combine(datetime.min, adjusted_start)

                                # Fetch all scans excluding the first (InTime) and last (OutTime)
                                break_scans = list(
                                    CompanyAttendance.objects.filter(Attendance=attendance_obj)
                                    .order_by("id")
                                )[1:-1]  

                                if len(break_scans) % 2 != 0:
                                    del break_scans[-1]

                                break_time = timedelta()
                                pending_break_start = None  # Track when break starts

                                for scan in break_scans:
                                    # Ignore break records before shift start or after shift end
                                    if scan.ScanTimings < start_time or scan.ScanTimings > end_time:
                                        continue  

                                    if scan.ScanType is False:  # Break starts (OUT)
                                        pending_break_start = scan.ScanTimings
                                    elif scan.ScanType is True and pending_break_start:  # Break ends (IN)
                                        break_duration = datetime.combine(datetime.min, scan.ScanTimings) - datetime.combine(datetime.min, pending_break_start)
                                        break_time += break_duration
                                        pending_break_start = None  # Reset break tracker

                                # Subtract total break time from work hours
                                final_hours_worked = total_work_hours - break_time
                                attendance_obj.break_timings = (datetime.min + break_time).time()
                                attendance_obj.Hours_Worked = (datetime.min + final_hours_worked).time()

                            else:
                                attendance_obj.Hours_Worked = None  # Invalid case where start >= end
                        else:
                            attendance_obj.Hours_Worked = None

                        total_working_hours = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time)
                        attendance_obj.TotalWorkingHours = (datetime.min + total_working_hours).time()

                        # Check for week-off/holiday even if attendance record exists
                        is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=current_date).exists()
                        leave_exists = EmployeesLeavesmodel.objects.filter(leave_request__employee=emp_obj, leave_date=current_date).exists()
                        
                        weekoff_qs = EmployeeWeekoffsModel.objects.filter(
                            employee_id=emp_obj,
                            month=current_date.month,
                            year=current_date.year
                        )
                        if weekoff_qs.exists():
                            weekoff_days = weekoff_qs.values_list('weekoff_days__day', flat=True)
                        else:
                            latest_weekoff = EmployeeWeekoffsModel.objects.filter(employee_id=emp_obj).order_by('-year', '-month').first()
                            weekoff_days = latest_weekoff.weekoff_days.values_list('day', flat=True) if latest_weekoff else []
                        
                        weekoff_days = [day.lower() for day in weekoff_days if isinstance(day, str) and day]
                        is_week_off = current_date.strftime('%A').lower() in weekoff_days

                        if attendance_obj.Hours_Worked:
                            if attendance_obj.Hours_Worked >= time(8, 0):
                                attendance_obj.leave_information = "No_attention_required"
                                attendance_obj.Status = "present"
                            elif attendance_obj.Hours_Worked >= time(4, 0):
                                attendance_obj.leave_information = "Attention_required"
                                attendance_obj.Status = "half_day"
                            else:
                                if is_week_off:
                                    attendance_obj.Status = "week_off"
                                    attendance_obj.leave_information = "No_attention_required"
                                elif is_public_holiday:
                                    attendance_obj.Status = "public_leave"
                                    attendance_obj.leave_information = "No_attention_required"
                                else:
                                    attendance_obj.leave_information = "Attention_required"
                                    attendance_obj.Status = "less_than_half_day"
                        else:
                            if leave_exists:
                                attendance_obj.Status = "absent"
                                attendance_obj.leave_information = "Authorized_Absent"
                            elif is_public_holiday:
                                attendance_obj.Status = "public_leave"
                                attendance_obj.leave_information = "No_attention_required"
                            elif is_week_off:
                                attendance_obj.Status = "week_off"
                                attendance_obj.leave_information = "No_attention_required"
                            else:
                                attendance_obj.Status = "absent"
                                attendance_obj.leave_information = "Unauthorized_Absent"

                        attendance_obj.save()
                else:
                    today_attendance_obj = CompanyAttendanceDataModel.objects.create(
                        Emp_Id=emp_obj, date=current_date, Day=current_date.strftime("%A")
                    )
                    is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=current_date).exists()
                    leave_exists = EmployeesLeavesmodel.objects.filter(leave_request__employee=emp_obj, leave_date=current_date).exists()
                    current_year = current_date.year
                    current_month = current_date.month

                    # Check if the employee has a week-off entry for the current month
                    weekoff_qs = EmployeeWeekoffsModel.objects.filter(
                        employee_id=emp_obj,
                        month=current_month,
                        year=current_year
                    )

                    if weekoff_qs.exists():
                        # If week-off exists for the current month, get the latest one
                        weekoff_days = weekoff_qs.values_list('weekoff_days__day', flat=True)
                    else:
                        # If no week-off exists for the current month, fetch the latest available week-off
                        latest_weekoff = EmployeeWeekoffsModel.objects.filter(
                            employee_id=emp_obj
                        ).order_by('-year', '-month').first()

                        if latest_weekoff:
                            # Copy the week-off days from the latest available record
                            latest_weekoff_days = list(latest_weekoff.weekoff_days.values_list('id', flat=True))

                            # Create a new week-off entry for the current month
                            new_weekoff = EmployeeWeekoffsModel.objects.create(
                                employee_id=emp_obj,
                                month=current_month,
                                year=current_year
                            )

                            # Assign the week-off days to the new entry
                            new_weekoff.weekoff_days.set(latest_weekoff_days)
                            new_weekoff.save()

                            # Fetch the newly created week-off days
                            weekoff_days = new_weekoff.weekoff_days.values_list('day', flat=True)
                        else:
                            weekoff_days = []  # No previous week-off records found, and nothing to copy

                    # Convert days to lowercase
                    weekoff_days = [day.lower() for day in weekoff_days if isinstance(day, str) and day]

                    status = "absent"
                    leave_information = "Unauthorized_Absent"

                    if leave_exists:
                        status = "absent"
                        leave_information = "Authorized_Absent"
                    elif AvailableRestrictedLeaves.objects.filter(
                        employee=emp_obj, holiday__Date=current_date, is_utilised=True
                    ).exists():
                        status = "restricted_leave"
                        leave_information = "Authorized_Absent"
                    elif is_public_holiday:
                        status = "public_leave"
                        leave_information = "No_attention_required"
                    elif current_date.strftime('%A').lower() in weekoff_days:
                        status = "week_off"
                        leave_information = "No_attention_required"

                    today_attendance_obj.Status = status
                    today_attendance_obj.leave_information = leave_information
                    today_attendance_obj.Shift = emp_shifts
                    today_attendance_obj.save()

        except Exception as e:
            # Log the exception and continue with the next employee
            logger.error(f"Error processing Employee {emp_obj.EmployeeId} on {current_date}: {e}")
            continue


from datetime import datetime, timedelta

class UpdateEmployeeAttendanceAPIView(APIView):
    def get(self,request):
        emp_id=request.GET.get("emp_id")
        # date=request.GET.get("date")
        # attendance_obj = CompanyAttendanceDataModel.objects.filter(Emp_Id__EmployeeId=emp_id, date=date).first()
        #17/02/2026
        date_str=request.GET.get("date")
        
        if date_str:
            try:
                # Parse the date string into a date object
                date_obj = datetime.fromisoformat(date_str).date()
            except ValueError:
                # Fallback to current local date if parsing fails
                date_obj = timezone.localdate()
        else:
            date_obj = timezone.localdate()

        attendance_obj = CompanyAttendanceDataModel.objects.filter(Emp_Id__EmployeeId=emp_id, date=date_obj).first()
        #09/02/2026
        # if attendance_obj:
        #     serializer=CompanyAttendanceDataSerializer(attendance_obj).data

        #     if not attendance_obj.Status:
        #         punches_obj = CompanyAttendance.objects.filter(Attendance=attendance_obj).last()

        #     serializer["current_punch"]=punches_obj.ScanType
        #     return Response(serializer)
        if attendance_obj:
            # serializer = CompanyAttendanceDataSerializer(attendance_obj).data
            
            # punches_obj = CompanyAttendance.objects.filter(Attendance=attendance_obj).last()
            
            # if punches_obj:
            #     serializer["current_punch"] = punches_obj.ScanType
            # else:
            #     serializer["current_punch"] = None
            
            # return Response(serializer)
            # Avoid heavy serializer for a simple toggle check.
            last_punch = CompanyAttendance.objects.filter(Attendance=attendance_obj).order_by('-id').first()
            
            response_data = {
                "id": attendance_obj.id,
                "current_punch": last_punch.ScanType if last_punch else None,
                "InTime": attendance_obj.InTime.strftime("%H:%M:%S") if attendance_obj.InTime else None,
                "OutTime": attendance_obj.OutTime.strftime("%H:%M:%S") if attendance_obj.OutTime else None,
                "Status": attendance_obj.Status
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Record not found"}, status=status.HTTP_404_NOT_FOUND)
    
    def patch(self,request):
        att_id=request.GET.get("id")
        attendance_obj = CompanyAttendanceDataModel.objects.filter(id=int(att_id)).first()
        serializer=CompanyAttendanceDataSerializer(attendance_obj,data=request.data,partial=True)
        if serializer.is_valid():
            serializer.save()
        else:
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        return Response("done",status=status.HTTP_200_OK)
    def post(self, request, *args, **kwargs):
        try:
            from_date = datetime.strptime(request.data.get("from_date"), "%Y-%m-%d").date()
            to_date = datetime.strptime(request.data.get("to_date"), "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=400)

        if from_date > to_date:
            return Response({"error": "from_date cannot be greater than to_date."}, status=400)

        active_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

        if not active_employees.exists():
            return Response({"message": "No active employees found."}, status=200)

        # Loop over the date range (including the same date if from_date == to_date)
        for date in (from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)):
            for emp_obj in active_employees:
                try:
                    with transaction.atomic():
                        attendance_obj = CompanyAttendanceDataModel.objects.filter(Emp_Id=emp_obj, date=date).first()
                        emp_shifts = emp_obj.employeeProfile.EmployeeShifts

                        if attendance_obj:
                            if not attendance_obj.Status:
                                punches_obj = CompanyAttendance.objects.filter(Attendance=attendance_obj).order_by('Created_Date')
                                if punches_obj.count() == 1:
                                    attendance_obj.Status = "absent"
                                    attendance_obj.leave_information = "Unauthorized_Absent"
                                    attendance_obj.save()
                                    continue
                                
                                #attendance_obj.OutTime = punches_obj.last().ScanTimings if punches_obj.last() else None
                                #attendance_obj.save()
                                
                                last_out_punch = punches_obj.filter(ScanType=False).order_by('-id').first()
                                attendance_obj.OutTime = last_out_punch.ScanTimings if last_out_punch else None
                                attendance_obj.save()
                                
                                start_time = emp_shifts.start_shift if emp_shifts else time(9, 30)
                                end_time = emp_shifts.end_shift if emp_shifts else time(18, 30)

                                if attendance_obj.OutTime and attendance_obj.OutTime < end_time:
                                    early_departure = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, attendance_obj.OutTime)
                                    attendance_obj.Early_Depature = (datetime.min + early_departure).time()
                                else:
                                    attendance_obj.Early_Depature = None

                                if attendance_obj.InTime and attendance_obj.OutTime:
                                    # Adjust start and end times within shift hours
                                    adjusted_start = max(attendance_obj.InTime, start_time)
                                    adjusted_end = min(attendance_obj.OutTime, end_time)

                                    if adjusted_start < adjusted_end:  # Ensure valid time range
                                        total_work_hours = datetime.combine(datetime.min, adjusted_end) - datetime.combine(datetime.min, adjusted_start)

                                        # Fetch all scans excluding the first (InTime) and last (OutTime)
                                        break_scans = list(
                                            CompanyAttendance.objects.filter(Attendance=attendance_obj)
                                            .order_by("id")
                                        )[1:-1]  

                                        if len(break_scans)%2 != 0:
                                            del break_scans[-1]

                                        break_time = timedelta()
                                        pending_break_start = None  # Track when break starts

                                        for scan in break_scans:
                                            # Ignore break records before shift start or after shift end
                                            if scan.ScanTimings < start_time or scan.ScanTimings > end_time:
                                                continue  

                                            if scan.ScanType is False:  # Break starts (OUT)
                                                pending_break_start = scan.ScanTimings
                                            elif scan.ScanType is True and pending_break_start:  # Break ends (IN)
                                                break_duration = datetime.combine(datetime.min, scan.ScanTimings) - datetime.combine(datetime.min, pending_break_start)
                                                break_time += break_duration
                                                pending_break_start = None  # Reset break tracker

                                        # Subtract total break time from work hours
                                        final_hours_worked = total_work_hours - break_time
                                        attendance_obj.break_timings = (datetime.min + break_time).time()
                                        attendance_obj.Hours_Worked = (datetime.min + final_hours_worked).time()

                                    else:
                                        attendance_obj.Hours_Worked = None  # Invalid case where start >= end
                                else:
                                    attendance_obj.Hours_Worked = None

                                total_working_hours = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time)
                                attendance_obj.TotalWorkingHours = (datetime.min + total_working_hours).time()
                                
                                if attendance_obj.Hours_Worked:
                                    if attendance_obj.Hours_Worked >= time(8, 0):
                                        attendance_obj.leave_information = "No_attention_required"
                                        attendance_obj.Status = "present"
                                    elif attendance_obj.Hours_Worked >= time(4, 0):
                                        attendance_obj.leave_information = "Attention_required"
                                        attendance_obj.Status = "half_day"
                                    else:
                                        attendance_obj.leave_information = "Attention_required"
                                        attendance_obj.Status = "less_than_half_day"
                                    
                                else:
                                    attendance_obj.Status = "absent"
                                    attendance_obj.leave_information = "Unauthorized_Absent"
                                attendance_obj.save()
                        else:
                            today_attendance_obj = CompanyAttendanceDataModel.objects.create(
                                Emp_Id=emp_obj, date=date, Day=date.strftime("%A")
                            )
                            is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=date).exists()
                            leave_exists = EmployeesLeavesmodel.objects.filter(leave_request__employee=emp_obj, leave_date=date).exists()
                            current_year = date.year
                            current_month = date.month

                            # Check if the employee has a week-off entry for the current month
                            weekoff_qs = EmployeeWeekoffsModel.objects.filter(
                                employee_id=emp_obj,
                                month=current_month,
                                year=current_year
                            )

                            if weekoff_qs.exists():
                                # If week-off exists for the current month, get the latest one
                                weekoff_days = weekoff_qs.values_list('weekoff_days__day', flat=True)
                            else:
                                # If no week-off exists for the current month, fetch the latest available week-off
                                latest_weekoff = EmployeeWeekoffsModel.objects.filter(
                                    employee_id=emp_obj
                                ).order_by('-year', '-month').first()

                                if latest_weekoff:
                                    # Copy the week-off days from the latest available record
                                    latest_weekoff_days = list(latest_weekoff.weekoff_days.values_list('id', flat=True))

                                    # Create a new week-off entry for the current month
                                    new_weekoff = EmployeeWeekoffsModel.objects.create(
                                        employee_id=emp_obj,
                                        month=current_month,
                                        year=current_year
                                    )

                                    # Assign the week-off days to the new entry
                                    new_weekoff.weekoff_days.set(latest_weekoff_days)
                                    new_weekoff.save()

                                    # Fetch the newly created week-off days
                                    weekoff_days = new_weekoff.weekoff_days.values_list('day', flat=True)
                                else:
                                    weekoff_days = []  # No previous week-off records found, and nothing to copy

                            # Convert days to lowercase
                            weekoff_days = [day.lower() for day in weekoff_days if isinstance(day, str) and day]


                            status = "absent"
                            leave_information = "Unauthorized_Absent"

                            if leave_exists:
                                status = "absent"
                                leave_information = "Authorized_Absent"
                            elif AvailableRestrictedLeaves.objects.filter(
                                employee=emp_obj, holiday__Date=date, is_utilised=True
                            ).exists():
                                status = "restricted_leave"
                                leave_information = "Authorized_Absent"
                            elif is_public_holiday:
                                status = "public_leave"
                                leave_information = "No_attention_required"
                            elif date.strftime('%A').lower() in weekoff_days:
                                status = "week_off"
                                leave_information = "No_attention_required"

                            today_attendance_obj.Status = status
                            today_attendance_obj.leave_information = leave_information
                            today_attendance_obj.Shift = emp_shifts
                            today_attendance_obj.save()
                except Exception as e:
                    logger.error(f"Error for Employee {emp_obj.EmployeeId} on {date}: {e}")
                    return Response(f"Error for Employee {emp_obj.EmployeeId} on {date}: {e}")
                    continue

        return Response({"message": "Employee attendance updated successfully."}, status=200)



from datetime import datetime, timedelta, time
from django.db import transaction
from django.db.models import Q
import logging

logger = logging.getLogger(__name__)

def process_attendance(from_date: str, to_date: str):
    """
    Processes attendance for active employees between from_date and to_date.
    
    Args:
        from_date (str): Start date in "YYYY-MM-DD" format.
        to_date (str): End date in "YYYY-MM-DD" format.
    
    Returns:
        dict: A dictionary containing processed attendance information.
    """
    try:
        from_date = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date = datetime.strptime(to_date, "%Y-%m-%d").date()
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    if from_date > to_date:
        return {"error": "from_date cannot be greater than to_date."}

    active_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

    if not active_employees.exists():
        return {"message": "No active employees found."}

    processed_attendance = []  # Store processed data for reference

    for date in (from_date + timedelta(days=i) for i in range((to_date - from_date).days + 1)):
        for emp_obj in active_employees:
            try:
                with transaction.atomic():
                    attendance_obj = CompanyAttendanceDataModel.objects.filter(Emp_Id=emp_obj, date=date).first()
                    emp_shifts = emp_obj.employeeProfile.EmployeeShifts

                    if attendance_obj:
                        if not attendance_obj.Status:
                            punches_obj = CompanyAttendance.objects.filter(Attendance=attendance_obj).order_by('Created_Date')
                            if punches_obj.count() == 1:
                                attendance_obj.Status = "absent"
                                attendance_obj.leave_information = "Unauthorized_Absent"
                                attendance_obj.save()
                                continue

                            last_out_punch = punches_obj.filter(ScanType=False).order_by('-id').first()
                            attendance_obj.OutTime = last_out_punch.ScanTimings if last_out_punch else None
                            attendance_obj.save()

                            start_time = emp_shifts.start_shift if emp_shifts else time(9, 30)
                            end_time = emp_shifts.end_shift if emp_shifts else time(18, 30)

                            if attendance_obj.OutTime and attendance_obj.OutTime < end_time:
                                early_departure = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, attendance_obj.OutTime)
                                attendance_obj.Early_Depature = (datetime.min + early_departure).time()
                            else:
                                attendance_obj.Early_Depature = None

                            if attendance_obj.InTime and attendance_obj.OutTime:
                                adjusted_start = max(attendance_obj.InTime, start_time)
                                adjusted_end = min(attendance_obj.OutTime, end_time)

                                if adjusted_start < adjusted_end:
                                    total_work_hours = datetime.combine(datetime.min, adjusted_end) - datetime.combine(datetime.min, adjusted_start)

                                    break_scans = list(
                                        CompanyAttendance.objects.filter(Attendance=attendance_obj)
                                        .order_by("id")
                                    )[1:-1]  

                                    if len(break_scans) % 2 != 0:
                                        del break_scans[-1]

                                    break_time = timedelta()
                                    pending_break_start = None  

                                    for scan in break_scans:
                                        if scan.ScanTimings < start_time or scan.ScanTimings > end_time:
                                            continue  

                                        if scan.ScanType is False:  
                                            pending_break_start = scan.ScanTimings
                                        elif scan.ScanType is True and pending_break_start:  
                                            break_duration = datetime.combine(datetime.min, scan.ScanTimings) - datetime.combine(datetime.min, pending_break_start)
                                            break_time += break_duration
                                            pending_break_start = None  

                                    final_hours_worked = total_work_hours - break_time
                                    attendance_obj.break_timings = (datetime.min + break_time).time()
                                    attendance_obj.Hours_Worked = (datetime.min + final_hours_worked).time()
                                else:
                                    attendance_obj.Hours_Worked = None
                            else:
                                attendance_obj.Hours_Worked = None

                            total_working_hours = datetime.combine(datetime.min, end_time) - datetime.combine(datetime.min, start_time)
                            attendance_obj.TotalWorkingHours = (datetime.min + total_working_hours).time()
                            
                            if attendance_obj.Hours_Worked:
                                if attendance_obj.Hours_Worked >= time(8, 0):
                                    attendance_obj.leave_information = "No_attention_required"
                                    attendance_obj.Status = "present"
                                elif attendance_obj.Hours_Worked >= time(4, 0):
                                    attendance_obj.leave_information = "Attention_required"
                                    attendance_obj.Status = "half_day"
                                else:
                                    attendance_obj.leave_information = "Attention_required"
                                    attendance_obj.Status = "less_than_half_day"
                            else:
                                attendance_obj.Status = "absent"
                                attendance_obj.leave_information = "Unauthorized_Absent"

                            attendance_obj.save()

                    else:
                        today_attendance_obj = CompanyAttendanceDataModel.objects.create(
                            Emp_Id=emp_obj, date=date, Day=date.strftime("%A")
                        )

                        is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=date).exists()
                        leave_exists = EmployeesLeavesmodel.objects.filter(leave_request__employee=emp_obj, leave_date=date).exists()
                        current_year = date.year
                        current_month = date.month

                        weekoff_qs = EmployeeWeekoffsModel.objects.filter(
                            employee_id=emp_obj,
                            month=current_month,
                            year=current_year
                        )

                        if weekoff_qs.exists():
                            weekoff_days = weekoff_qs.values_list('weekoff_days__day', flat=True)
                        else:
                            latest_weekoff = EmployeeWeekoffsModel.objects.filter(
                                employee_id=emp_obj
                            ).order_by('-year', '-month').first()

                            if latest_weekoff:
                                latest_weekoff_days = list(latest_weekoff.weekoff_days.values_list('id', flat=True))
                                new_weekoff = EmployeeWeekoffsModel.objects.create(
                                    employee_id=emp_obj,
                                    month=current_month,
                                    year=current_year
                                )
                                new_weekoff.weekoff_days.set(latest_weekoff_days)
                                new_weekoff.save()
                                weekoff_days = new_weekoff.weekoff_days.values_list('day', flat=True)
                            else:
                                weekoff_days = []

                        weekoff_days = [day.lower() for day in weekoff_days if isinstance(day, str) and day]

                        status = "absent"
                        leave_information = "Unauthorized_Absent"

                        if leave_exists:
                            status = "absent"
                            leave_information = "Authorized_Absent"
                        elif AvailableRestrictedLeaves.objects.filter(
                            employee=emp_obj, holiday__Date=date, is_utilised=True
                        ).exists():
                            status = "restricted_leave"
                            leave_information = "Authorized_Absent"
                        elif is_public_holiday:
                            status = "public_leave"
                            leave_information = "No_attention_required"
                        elif date.strftime('%A').lower() in weekoff_days:
                            status = "week_off"
                            leave_information = "No_attention_required"

                        today_attendance_obj.Status = status
                        today_attendance_obj.leave_information = leave_information
                        today_attendance_obj.Shift = emp_shifts
                        today_attendance_obj.save()

                #processed_attendance.append({"emp_id": emp_obj.EmployeeId, "date": date, "status": status})

            except Exception as e:
                logger.error(f"Error for Employee {emp_obj.EmployeeId} on {date}: {e}")

    return {"message": "Attendance processing completed"}





       
     
# to upload the bulk data.

# class ImportAttendanceData(APIView):

#     def post(self, request, *args, **kwargs):
#         file_path = request.data.get('file_path')
       
#         if not file_path:
#             return Response({"error": "File path not provided."})
#         try:
#             # Read the Excel file
#             df = pd.read_excel(file_path)
#             print(df)

#             # Filter out rows with any empty or null values
#             # df.dropna(inplace=True)

#             # print(df)

#             # Ensure proper date parsing
#             try:
#                 df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d').dt.date  # Adjust date format as needed
#             except Exception as e:
#                 print(f"Error parsing dates: {e}")
#                 return Response({"error": "Error parsing dates from the Excel file."}, status=status.HTTP_400_BAD_REQUEST)
            
#             df['ScanTimings'] = pd.to_datetime(df['ScanTimings'], format='%H:%M:%S').dt.time  # Ensure ScanTimings are in time format

#             # Get all active employees
#             active_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

#             # Get the date range from the imported data
#             min_date = df['date'].min()
#             max_date = df['date'].max()
#             all_dates = pd.date_range(min_date, max_date).date

#             with transaction.atomic():
#                 # Iterate over each date in the date range
#                 for date in all_dates:
#                     date_data = df[df['date'] == date]
#                     # Check for public holiday
#                     is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=date).exists()
# # changessssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssssss
#                     # Iterate over each active employee
#                     for employee in active_employees:
#                         # emp_id=employee.EmployeeId
#                         date_data['Emp_Id'] = date_data['Emp_Id'].astype(str).str.strip()
#                         # Make sure 'employee_attendance_id' is a string or integer (whichever matches your DataFrame)
#                         emp_id = str(employee.employeeProfile.employee_attendance_id).strip()
#                         # Now try to match Emp_Id in the DataFrame with employee_attendance_id
#                         emp_data = date_data[date_data['Emp_Id'] == emp_id]
#                         # Check if emp_data is not empty
#                         # Default status
#                         Status = "absent"

#                         # Determine attendance status
#                         if not emp_data.empty:
#                             Status = "present"
#                         elif is_public_holiday:
#                             Status = "public_leave"
#                         else:
#                             weekoff_days = EmployeeWeekoffsModel.objects.filter(
#                                 employee_id=employee.pk,
#                                 month=date.month,
#                                 year=date.year
#                             ).values_list('weekoff_days__day', flat=True)
#                             weekoff_days = [day.lower() for day in weekoff_days]

#                             if date.strftime('%A').lower() in weekoff_days:
#                                 Status = "week_off"
#                             elif AvailableRestrictedLeaves.objects.filter(employee=employee, holiday__Date=date, is_utilised=True).exists():
#                                 Status = "restricted_leave"

#                         # Retrieve employee shift timings
#                         employee_shift = employee.employeeProfile.EmployeeShifts
#                         start_time = employee_shift.start_shift if employee_shift else time(9, 30)
#                         end_time = employee_shift.end_shift if employee_shift else time(18, 30)


#                         # leave_information = "uninformed" if status == "absent" else "present"

#                         obj=EmployeesLeavesmodel.objects.filter(leave_request__employee=employee, leave_date=date).exists()
#                         if obj:
#                             leave_information = "Authorized_Absent"
                        
#                         elif (not obj) and Status == "absent":
#                             leave_information = "Unauthorized_Absent"

#                         elif Status == "present" or Status == "week_off":
#                             leave_information = "No_attention_required"
                        

#                         # Save or update CompanyAttendanceDataModel
#                         attendance_data, created = CompanyAttendanceDataModel.objects.get_or_create(
#                             Emp_Id=employee,
#                             date=date,
#                             defaults={'leave_information': leave_information,'Status': Status, 'Shift': employee_shift}  # Save the shift
#                         )
#                         # Update status and shift if not created
#                         if not created:
#                             attendance_data.leave_information = leave_information
#                             attendance_data.Status = Status
#                             attendance_data.Shift = employee_shift
#                             attendance_data.save()

#                         # Process scan timings
#                         if not emp_data.empty:
#                             scan_times = emp_data['ScanTimings']
#                             attendance_entries = [
#                                 CompanyAttendance(ScanTimings=scan_time, Attendance=attendance_data)
#                                 for scan_time in scan_times
#                             ]
#                             CompanyAttendance.objects.bulk_create(attendance_entries)
#                         # Update CompanyAttendanceDataModel with scan timings
#                         attendance_entries = attendance_data.companyattendance_set.all()
#                         if attendance_entries.exists():
#                             # Filter entries related to the current attendance_data instance
#                             attendance_entries = attendance_entries.filter(Attendance=attendance_data.pk)

#                             # Get earliest and latest scan times
#                             first_entry = attendance_entries.order_by('ScanTimings').first()
#                             last_entry = attendance_entries.order_by('-ScanTimings').first()                

#                             # Update InTime and OutTime based on the earliest and latest scan times
#                             if first_entry:
#                                 attendance_data.InTime = first_entry.ScanTimings
#                             else:
#                                 attendance_data.InTime = None

#                             if last_entry:
#                                 attendance_data.OutTime = last_entry.ScanTimings
#                             else:
#                                 attendance_data.OutTime = None

#                             # Calculate other metrics
#                             if attendance_data.InTime and attendance_data.OutTime:
#                                 # Calculate late arrival, early departure, hours worked, etc.
#                                 in_datetime = datetime.combine(date, attendance_data.InTime)
#                                 out_datetime = datetime.combine(date, attendance_data.OutTime)

#                                 # Calculate late arrivals
#                                 if in_datetime > datetime.combine(date, start_time):
#                                     late_arrival = in_datetime - datetime.combine(date, start_time)
#                                     attendance_data.Late_Arrivals = (datetime.min + late_arrival).time()
#                                 else:
#                                     attendance_data.Late_Arrivals = None

#                                 # Calculate early departure
#                                 if out_datetime < datetime.combine(date, end_time):
#                                     early_departure = datetime.combine(date, end_time) - out_datetime
#                                     attendance_data.Early_Depature = (datetime.min + early_departure).time()
#                                 else:
#                                     attendance_data.Early_Depature = None

#                                 # Calculate hours worked
#                                 hours_worked = out_datetime - in_datetime
#                                 attendance_data.Hours_Worked = (datetime.min + hours_worked).time()

#                                 # Calculate total working hours
#                                 total_working_hours = datetime.combine(date, end_time) - datetime.combine(date, start_time)
#                                 attendance_data.TotalWorkingHours = (datetime.min + total_working_hours).time()

#                                 # Calculate overtime if applicable
#                                 # if hours_worked > total_working_hours:
#                                 #     over_time = hours_worked - total_working_hours
#                                 #     attendance_data.Over_Time = (datetime.min + over_time).time()
#                                 # Determine attendance status based on hours worked
#                                 if time(5, 30) <= attendance_data.Hours_Worked <= time(8, 30):
#                                     attendance_data.Status = "half_day"
#                                 elif attendance_data.Hours_Worked < time(5, 30):
#                                     attendance_data.Status = "absent"
#                                 elif attendance_data.Hours_Worked > time(8, 30):
#                                     attendance_data.Status = "present"
#                             else:
#                                 attendance_data.Status = "absent"

#                             attendance_data.Day = date.strftime('%A')
#                             attendance_data.save()

#                 return Response({"message": "Attendance data imported successfully."})

#         except Exception as e:
#             print(e)
#             return Response({"error": f"Error processing attendance data: {str(e)}"},status=status.HTTP_400_BAD_REQUEST )
        


# ...........................................bulk attendance function 2..................................................

# class ImportAttendanceData(APIView):

#     def post(self, request, *args, **kwargs):
#         file_path = request.data.get('file_path')
       
#         if not file_path:
#             return Response({"error": "File path not provided."})

#         try:
#             # Read the Excel file
#             df = pd.read_excel(file_path)
#             print(df)

#             # Ensure proper date parsing
#             try:
#                 df['date'] = pd.to_datetime(df['date'], format='%Y-%m-%d').dt.date  # Adjust date format as needed
#             except Exception as e:
#                 print(f"Error parsing dates: {e}")
#                 return Response({"error": "Error parsing dates from the Excel file."}, status=status.HTTP_400_BAD_REQUEST)
            
#             df['ScanTimings'] = pd.to_datetime(df['ScanTimings'], format='%H:%M:%S').dt.time  # Ensure ScanTimings are in time format

#             # Get all active employees
#             active_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

#             # Get the date range from the imported data
#             min_date = df['date'].min()
#             max_date = df['date'].max()
#             all_dates = pd.date_range(min_date, max_date).date

#             with transaction.atomic():
#                 # Iterate over each date in the date range
#                 for date in all_dates:
#                     date_data = df[df['date'] == date]
#                     # Check for public holiday
#                     is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=date).exists()
                    
#                     # Iterate over each active employee
#                     for employee in active_employees:
#                         date_data['Emp_Id'] = date_data['Emp_Id'].astype(str).str.strip()
#                         emp_id = str(employee.employeeProfile.employee_attendance_id).strip()
#                         emp_data = date_data[date_data['Emp_Id'] == emp_id]
                        
#                         # Default status
#                         Status = "absent"

#                         if not emp_data.empty:
#                             Status = "present"
#                         elif is_public_holiday:
#                             Status = "public_leave"
#                         else:
#                             weekoff_days = EmployeeWeekoffsModel.objects.filter(
#                                 employee_id=employee.pk,
#                                 month=date.month,
#                                 year=date.year
#                             ).values_list('weekoff_days__day', flat=True)
#                             weekoff_days = [day.lower() for day in weekoff_days]

#                             if date.strftime('%A').lower() in weekoff_days:
#                                 Status = "week_off"
#                             elif AvailableRestrictedLeaves.objects.filter(employee=employee, holiday__Date=date, is_utilised=True).exists():
#                                 Status = "restricted_leave"

#                         # Retrieve employee shift timings
#                         employee_shift = employee.employeeProfile.EmployeeShifts
#                         start_time = employee_shift.start_shift if employee_shift else time(9, 30)
#                         end_time = employee_shift.end_shift if employee_shift else time(18, 30)

#                         # Leave information determination
#                         obj = EmployeesLeavesmodel.objects.filter(leave_request__employee=employee, leave_date=date).exists()
#                         if obj:
#                             leave_information = "Authorized_Absent"
#                         elif not obj and Status == "absent":
#                             leave_information = "Unauthorized_Absent"
#                         elif Status == "present" or Status == "week_off":
#                             leave_information = "No_attention_required"

#                         # Save or update CompanyAttendanceDataModel
#                         attendance_data, created = CompanyAttendanceDataModel.objects.get_or_create(
#                             Emp_Id=employee,
#                             date=date,
#                             defaults={'leave_information': leave_information, 'Status': Status, 'Shift': employee_shift}
#                         )
#                         if not created:
#                             attendance_data.leave_information = leave_information
#                             attendance_data.Status = Status
#                             attendance_data.Shift = employee_shift
#                             attendance_data.save()

#                         # Process scan timings
#                         if not emp_data.empty:
#                             scan_times = emp_data['ScanTimings'].tolist()
                            
#                             if len(scan_times) == 1:
#                                 # Only one scan time, use as InTime
#                                 in_time = scan_times[0]
#                                 attendance_data.InTime = in_time
#                                 attendance_data.OutTime = None
                                
#                                 # Calculate late arrival based on the employee's shift starting time
#                                 in_datetime = datetime.combine(date, in_time)
#                                 start_datetime = datetime.combine(date, start_time)
#                                 if in_datetime > start_datetime:
#                                     late_arrival = in_datetime - start_datetime
#                                     attendance_data.Late_Arrivals = (datetime.min + late_arrival).time()
#                                 else:
#                                     attendance_data.Late_Arrivals = None
                                
#                                 # Set working hours and status
#                                 attendance_data.Hours_Worked = None
#                                 attendance_data.TotalWorkingHours = None
#                                 attendance_data.Status = "Present" 
#                                 if attendance_data.Late_Arrivals :

#                                     subject=f"Late Login Notification on {attendance_data.date}"
#                                     message=f"We noticed that you logged in late on {attendance_data.date}. Your recorded late arrival time is {attendance_data.Late_Arrivals}.\nPlease ensure to adhere to your shift timings to avoid any further issues.\n\nThank you,\n Merida Tech Minds."

#                                     send_mail(
#                                         subject,
#                                         message,
#                                         settings.DEFAULT_FROM_EMAIL,
#                                         [attendance_data.Emp_Id.employeeProfile.email],
#                                     )
                                   
#                             elif len(scan_times) > 1:
#                                 # More than one scan time, process both InTime and OutTime
#                                 attendance_entries = [
#                                     CompanyAttendance(ScanTimings=scan_time, Attendance=attendance_data)
#                                     for scan_time in scan_times
#                                 ]
#                                 CompanyAttendance.objects.bulk_create(attendance_entries)
                                
#                                 # Update CompanyAttendanceDataModel with scan timings
#                                 attendance_entries = attendance_data.companyattendance_set.all()
#                                 if attendance_entries.exists():
#                                     first_entry = attendance_entries.order_by('ScanTimings').first()
#                                     last_entry = attendance_entries.order_by('-ScanTimings').first()

#                                     if first_entry:
#                                         attendance_data.InTime = first_entry.ScanTimings
#                                     else:
#                                         attendance_data.InTime = None

#                                     if last_entry:
#                                         attendance_data.OutTime = last_entry.ScanTimings
#                                     else:
#                                         attendance_data.OutTime = None

#                                     if attendance_data.InTime and attendance_data.OutTime:
#                                         in_datetime = datetime.combine(date, attendance_data.InTime)
#                                         out_datetime = datetime.combine(date, attendance_data.OutTime)
                                        
#                                         if in_datetime > datetime.combine(date, start_time):
#                                             late_arrival = in_datetime - datetime.combine(date, start_time)
#                                             attendance_data.Late_Arrivals = (datetime.min + late_arrival).time()
#                                         else:
#                                             attendance_data.Late_Arrivals = None

#                                         if out_datetime < datetime.combine(date, end_time):
#                                             early_departure = datetime.combine(date, end_time) - out_datetime
#                                             attendance_data.Early_Depature = (datetime.min + early_departure).time()
#                                         else:
#                                             attendance_data.Early_Depature = None

#                                         hours_worked = out_datetime - in_datetime
#                                         attendance_data.Hours_Worked = (datetime.min + hours_worked).time()

#                                         total_working_hours = datetime.combine(date, end_time) - datetime.combine(date, start_time)
#                                         attendance_data.TotalWorkingHours = (datetime.min + total_working_hours).time()

#                                         if time(5, 30) <= attendance_data.Hours_Worked <= time(8, 30):
#                                             attendance_data.Status = "half_day"
#                                         elif attendance_data.Hours_Worked < time(5, 30):
#                                             attendance_data.Status = "absent"
#                                         elif attendance_data.Hours_Worked > time(8, 30):
#                                             attendance_data.Status = "present"
#                                     else:
#                                         attendance_data.Status = "absent"
                                    
#                                     attendance_data.Day = date.strftime('%A')
#                             attendance_data.save()

#                 return Response({"message": "Attendance data imported successfully."})

#         except Exception as e:
#             print(e)
#             return Response({"error": f"Error processing attendance data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

# ..........................................bulk upload function 3...................................................

import logging
# logger = logging.getLogger(__name__)


# class ImportAttendanceData(APIView):

#     def post(self, request, *args, **kwargs):
#         file_path = request.data.get('file_path')
       
#         if not file_path:
#             return Response({"error": "File path not provided."})

#         try:
#             # Read the Excel file
#             df = pd.read_excel(file_path)
#             # Ensure proper date parsing
#             try:
#                 df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y').dt.date  # Adjust date format as needed
#             except Exception as e:
#                 print(f"Error parsing dates: {e}")
#                 return Response({"error": "Error parsing dates from the Excel file."}, status=status.HTTP_400_BAD_REQUEST)

#             try:
        
#                 # Convert intime and outtime to time format
#                 df['intime'] = pd.to_datetime(df['intime'], format='%H:%M:%S').dt.time
#                 df['outtime'] = pd.to_datetime(df['outtime'], format='%H:%M:%S').dt.time

#             except Exception as e:
#                 print("llllll",e)
              
#             # Get all active employees
#             active_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

#             # Get the date range from the imported data
#             min_date = df['date'].min()
#             max_date = df['date'].max()
#             all_dates = pd.date_range(min_date, max_date).date

#             with transaction.atomic():
#                 # Iterate over each date in the date range
#                 for date in all_dates:
#                     date_data = df[df['date'] == date]
#                     # Check for public holiday
#                     is_public_holiday = CompanyHolidaysDataModel.objects.filter(leave_type="Public_Leave", Date=date).exists()
                    
#                     # Iterate over each active employee
#                     for employee in active_employees:
#                         date_data['Emp_Id'] = date_data['Emp_Id'].astype(str).str.strip()
#                         emp_id = str(employee.employeeProfile.employee_attendance_id).strip()
#                         emp_data = date_data[date_data['Emp_Id'] == emp_id]
                        
#                         # Default status
#                         Status = "absent"

#                         if not emp_data.empty:
#                             Status = "present"
#                         elif is_public_holiday:
#                             Status = "public_leave"
#                         else:
#                             weekoff_days = EmployeeWeekoffsModel.objects.filter(
#                                 employee_id=employee.pk,
#                                 month=date.month,
#                                 year=date.year
#                             ).values_list('weekoff_days__day', flat=True)
#                             weekoff_days = [day.lower() for day in weekoff_days]

#                             if date.strftime('%A').lower() in weekoff_days:
#                                 Status = "week_off"
#                             elif AvailableRestrictedLeaves.objects.filter(employee=employee, holiday__Date=date, is_utilised=True).exists():
#                                 Status = "restricted_leave"

#                         # Retrieve employee shift timings
#                         employee_shift = employee.employeeProfile.EmployeeShifts
#                         start_time = employee_shift.start_shift if employee_shift else time(9, 30)
#                         end_time = employee_shift.end_shift if employee_shift else time(18, 30)

#                         # Leave information determination
#                         obj = EmployeesLeavesmodel.objects.filter(leave_request__employee=employee, leave_date=date).exists()
#                         if obj:
#                             leave_information = "Authorized_Absent"
#                         elif not obj and Status == "absent":
#                             leave_information = "Unauthorized_Absent"
#                         elif Status == "present" or Status == "week_off":
#                             leave_information = "No_attention_required"

#                         # Process intime and outtime
#                         if not emp_data.empty:
                            
#                             # intime = emp_data['intime'].values[0]
#                             # outtime = emp_data.loc[emp_data['outtime']!='']
#                             # print(outtime)
#                             # # outtime  = outtime.columns['outtime'] if outtime.columns['outtime'] == 'NaT' else None
#                             # print(outtime)

#                             emp_data = pd.DataFrame(emp_data)

#                             # Extract the 'intime' and 'outtime'
#                             intime = emp_data['intime'].values[0]
#                             outtime = emp_data['outtime'].values[0]
#                             if pd.isna(outtime):
#                                 outtime = None

#                             # else:
#                             #     outtime = pd.to_datetime(outtime).time()

#                             # outtime = emp_data['outtime'].values[0] if 'outtime' in emp_data.columns else None
#                             # emp_data['columns']

#                             if pd.isna(intime):
#                                 intime = None

#                             # Check for existing attendance data
#                             attendance_data, created = CompanyAttendanceDataModel.objects.get_or_create(
#                                 Emp_Id=employee,
#                                 date=date,
#                                 defaults={
#                                     'leave_information': leave_information, 
#                                     'Status': Status, 
#                                     'Shift': employee_shift,
#                                     'InTime': intime,
#                                     'OutTime': outtime 
#                                 }
#                             )

#                             in_datetime = datetime.combine(date, intime) if intime else None
#                             out_datetime = datetime.combine(date, outtime) if outtime else None

#                             # Calculate late arrival based on the employee's shift starting time
#                             late_arrival = None
            
#                             if in_datetime > datetime.combine(date, start_time):
#                                 late_arrival = in_datetime - datetime.combine(date, start_time)
#                                 # Limit late arrival to 1 minute
#                                 # if late_arrival > timedelta(minutes=1):
#                                 #     late_arrival = timedelta(minutes=1)
#                                 attendance_data.Late_Arrivals = (datetime.min + late_arrival).time()
#                             else:
#                                 attendance_data.Late_Arrivals = None

#                             if not created:
#                                 # Check if InTime is different
#                                 if attendance_data.InTime != intime and attendance_data.Late_Arrivals is not None:
#                                     # Send email notification
#                                     self.send_email_notification(employee, intime, date,attendance_data)

#                                 # Update the attendance record
#                                 attendance_data.InTime = intime
#                                 attendance_data.OutTime = outtime
#                                 attendance_data.leave_information = leave_information
#                                 attendance_data.Status = Status
#                                 attendance_data.Shift = employee_shift
#                                 attendance_data.save()
#                             else:
#                                 # Save new attendance record
#                                 attendance_data.InTime = intime
#                                 attendance_data.OutTime = outtime
#                                 attendance_data.save()

#                             # Calculate early departure based on the employee's shift ending time
#                             if out_datetime and out_datetime < datetime.combine(date, end_time):
#                                 early_departure = datetime.combine(date, end_time) - out_datetime
#                                 attendance_data.Early_Depature = (datetime.min + early_departure).time()
#                             else:
#                                 attendance_data.Early_Depature = None

#                             # Calculate hours worked and update status accordingly
#                             if intime and outtime:
#                                 hours_worked = out_datetime - in_datetime
#                                 attendance_data.Hours_Worked = (datetime.min + hours_worked).time()

#                                 total_working_hours = datetime.combine(date, end_time) - datetime.combine(date, start_time)
#                                 attendance_data.TotalWorkingHours = (datetime.min + total_working_hours).time()

#                                 if time(5, 30) <= attendance_data.Hours_Worked <= time(8, 29):
#                                     attendance_data.Status = "half_day"
#                                 elif attendance_data.Hours_Worked < time(5, 30):
#                                     attendance_data.Status = "absent"
#                                 elif attendance_data.Hours_Worked > time(8, 30):
#                                     attendance_data.Status = "present"
#                             else:
#                                 attendance_data.Status = "absent"
#                                 if attendance_data.OutTime is None:
#                                     attendance_data.Status = "present"

                                    
#                             attendance_data.Day = date.strftime('%A')
#                             attendance_data.save()

#                 return Response({"message": "Attendance data imported successfully."})

#         except Exception as e:
#             print(e)
#             return Response({"error": f"Error processing attendance data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

#     def send_email_notification(self, employee, new_intime, date,attendance_data):
#         subject=f"Late Login Notification on {date}"
#         message=f"We noticed that you logged in late on {date}. Your recorded late arrival time is {attendance_data.Late_Arrivals}.\nPlease ensure to adhere to your shift timings to avoid any further issues.\n\nThank you,\n Merida Tech Minds."
#         email_from = settings.EMAIL_HOST_USER
#         recipient_list = [employee.employeeProfile.email]
#         send_mail(subject, message, email_from, recipient_list)

# ..........................................bulk upload function 4..........................................................

# import logging
# from django.core.mail import send_mail
# from django.conf import settings

# logger = logging.getLogger(__name__)

# class ImportAttendanceData(APIView):

#     def post(self, request, *args, **kwargs):
#         file_path = request.data.get('file_path')

#         if not file_path:
#             return Response({"error": "File path not provided."})

#         try:
#             # Read the Excel file
#             df = pd.read_excel(file_path)
            
#             # Ensure proper date parsing
#             df['date'] = pd.to_datetime(df['date'], format='%d-%m-%Y').dt.date
            
#             # Convert intime and outtime to time format
#             df['intime'] = pd.to_datetime(df['intime'], format='%H:%M:%S').dt.time
#             df['outtime'] = pd.to_datetime(df['outtime'], format='%H:%M:%S').dt.time

            

#             # Get the date range from the imported data
#             min_date = df['date'].min()
#             max_date = df['date'].max()
#             all_dates = pd.date_range(min_date, max_date).date

#             with transaction.atomic():
                
#                 for date in all_dates:
#                     date_data = df[df['date'] == date]

#                     is_public_holiday = CompanyHolidaysDataModel.objects.filter(
#                         leave_type="Public_Leave", Date=date
#                     ).exists()

#                     emp_attendance_id = date_data['Emp_Id'].astype(str).str.strip()
                    
    
#                     active_employee = EmployeeDataModel.objects.filter(
#                         employeeProfile__employee_attendance_id__in=emp_attendance_id
#                     ).first()

                    

#                     if active_employee and active_employee.employeeProfile.employee_status == "active":

#                         emp_id = str(active_employee.employeeProfile.employee_attendance_id).strip()
#                         emp_data = date_data[date_data['Emp_Id'].astype(str).str.strip() == emp_id]

#                         Status = "absent"
#                         leave_information = "Unauthorized_Absent"  # Default value

#                         # Check if the employee is on leave
#                         leave_exists = EmployeesLeavesmodel.objects.filter(
#                             leave_request__employee=active_employee, leave_date=date
#                         ).exists()

#                         print(leave_exists)

#                         weekoff_days = EmployeeWeekoffsModel.objects.filter(
#                                 employee_id=active_employee.pk,
#                                 month=date.month,
#                                 year=date.year
#                             ).values_list('weekoff_days__day', flat=True)

#                         weekoff_days = [day.lower() for day in weekoff_days]

#                         if leave_exists:
#                             Status = "absent"
#                             leave_information = "Authorized_Absent"
#                         elif AvailableRestrictedLeaves.objects.filter(employee=active_employee, holiday__Date=date, is_utilised=True).exists():
#                             Status = "restricted_leave"
#                             leave_information = "No_attention_required"
#                         elif is_public_holiday:
#                             Status = "public_leave"
#                             leave_information = "No_attention_required"
#                         elif weekoff_days:
    
#                             if date.strftime('%A').lower() in weekoff_days:
#                                 Status = "week_off"
#                                 leave_information = "No_attention_required"
#                             # elif not emp_data.empty:
#                             #     print("hellooo")
#                             #     Status = "present"
#                             #     leave_information = "No_attention_required"

#                         employee_shift = active_employee.employeeProfile.EmployeeShifts
#                         start_time = employee_shift.start_shift if employee_shift else time(9, 30)
#                         end_time = employee_shift.end_shift if employee_shift else time(18, 30)

#                         intime = emp_data['intime'].values[0] if not emp_data.empty and pd.notna(emp_data['intime'].values[0]) else None
#                         outtime = emp_data['outtime'].values[0] if not emp_data.empty and pd.notna(emp_data['outtime'].values[0]) else None

#                         attendance_data, created = CompanyAttendanceDataModel.objects.get_or_create(
#                             Emp_Id=active_employee,
#                             date=date,
#                             defaults={
#                                 'leave_information': leave_information, 
#                                 'Status': Status, 
#                                 'Shift': employee_shift,
#                                 'InTime': intime,
#                                 'OutTime': outtime 
#                             }
#                         )

#                         # Calculate late arrival
#                         if intime:
#                             in_datetime = datetime.combine(date, intime)
#                             late_arrival = None
#                             if in_datetime > datetime.combine(date, start_time):
#                                 late_arrival = in_datetime - datetime.combine(date, start_time)
#                                 attendance_data.Late_Arrivals = (datetime.min + late_arrival).time()
#                             else:
#                                 attendance_data.Late_Arrivals = None

#                         # Calculate early departure
#                         if outtime:
#                             out_datetime = datetime.combine(date, outtime)
#                             if out_datetime < datetime.combine(date, end_time):
#                                 early_departure = datetime.combine(date, end_time) - out_datetime
#                                 attendance_data.Early_Depature = (datetime.min + early_departure).time()
#                             else:
#                                 attendance_data.Early_Depature = None

#                         # Calculate hours worked
#                         if intime and outtime:
#                             if intime < start_time:
#                                 intime = start_time

#                             if outtime > end_time:
#                                 outtime = end_time

#                             in_datetime = datetime.combine(date, intime)
#                             out_datetime = datetime.combine(date, outtime)
#                             hours_worked = out_datetime - in_datetime
#                             attendance_data.Hours_Worked = (datetime.min + hours_worked).time()

#                             total_working_hours = datetime.combine(date, end_time) - datetime.combine(date, start_time)
#                             attendance_data.TotalWorkingHours = (datetime.min + total_working_hours).time()

#                             if time(4, 00) <= attendance_data.Hours_Worked <= time(8, 00):
#                                 Status = "half_day"
#                             elif attendance_data.Hours_Worked < time(4, 00):
#                                 Status = "less_than_half_day"
#                             elif attendance_data.Hours_Worked > time(8, 00):
#                                 Status = "present"
#                                 leave_information = "No_attention_required"
                            
#                         attendance_data.Day = date.strftime('%A')
#                         attendance_data.leave_information = leave_information
#                         attendance_data.Status = Status if Status  else None
                        
#                         attendance_data.save()

#                         # Send email notification if required
#                         if attendance_data.Late_Arrivals is not None:
#                             if created:
#                                 pass
#                                 # If the attendance record was just created, send the email without checking the intime
#                                 # print("need to send", attendance_data.date)
#                                 # self.send_email_notification(active_employee, intime, date, attendance_data)
#                             elif attendance_data.InTime != intime:
#                                 pass
#                                 # If the attendance record was not created (i.e., it already existed) and intime has changed, send the email
#                                 # print("need to send", attendance_data.date)
#                                 # self.send_email_notification(active_employee, intime, date, attendance_data)

#                     else:
#                         continue
#                 return Response({"message": "Attendance data imported successfully."})

#         except Exception as e:
#             logger.error(f"Error processing attendance data: {str(e)}")
#             return Response({"error": f"Error processing attendance data: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

#     def send_email_notification(self, employee, new_intime, date, attendance_data):
#         subject = f"Late Login Notification on {date}"
#         message = (
#             f"We noticed that you logged in late on {date}. "
#             f"Your recorded late arrival time is {attendance_data.Late_Arrivals}.\n"
#             "Please ensure to adhere to your shift timings to avoid any further issues.\n\n"
#             "Thank you,\nMerida Tech Minds."
#         )
#         email_from = settings.EMAIL_HOST_USER
#         recipient_list = [employee.employeeProfile.email]
#         send_mail(subject, message, email_from, recipient_list)

# ..........................................bulk upload function 5..........................................................

import os
import io
import pandas as pd
import logging
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from datetime import datetime, time

logger = logging.getLogger(__name__)

class ImportAttendanceData(APIView):

    def post(self, request, *args, **kwargs):
        file_path = request.data.get('file_path')
        
        if not file_path:
            return Response({"error": "File path not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if the file exists
            # if not os.path.exists(file_path):
            #     return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

            # Load the Excel file into a DataFrame
            df = pd.read_excel(file_path)

            # Process Excel: Combine 'Date', 'Month', and 'Year' columns into a single 'date' column
            df['date'] = pd.to_datetime(df[['Date', 'Month', 'Year']].astype(str).agg('-'.join, axis=1), format='%d-%b-%Y').dt.normalize()

            # Create 'intime' and 'outtime' columns based on the first and last punch time of the day
            df['intime'] = df.groupby(['PayCode', 'date'])['Time'].transform('first')
            df['outtime'] = df.groupby(['PayCode', 'date'])['Time'].transform('last')

            # Replace NaN with None for 'intime' and 'outtime'
            df['intime'] = df['intime'].where(df['intime'].notna(), None)
            df['outtime'] = df['outtime'].where(df['outtime'].notna(), None)

            # Drop duplicates to retain only one record per employee per day
            df = df.drop_duplicates(subset=['PayCode', 'date']).drop(['Month', 'Date', 'Year'], axis=1)

            # Rename columns to match your expected output
            df = df.rename(columns={'PayCode': 'Emp_Id', 'Name': 'Names'})

            # Reorder columns as required
            df = df[['Names', 'Emp_Id', 'date', 'intime', 'outtime']]

            # Process Attendance Data (as done in ImportAttendanceData class)
            a=self.process_attendance_data(df)

            # Create a BytesIO buffer to write the processed Excel file to
            # buffer = io.BytesIO()
            # with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            #     df.to_excel(writer, index=False, sheet_name='Sheet1')

            # buffer.seek(0)  # Ensure buffer is not closed before being sent in the response

            # # Return processed Excel data as response
            # response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            # response['Content-Disposition'] = 'attachment; filename="processed_data.xlsx"'
            
            if a:
                return a
            else:
                return Response("Data not uploded")

        except Exception as e:
            logger.error(f"Error processing data: {str(e)}")
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # def process_attendance_data(self, df):
    #     """
    #     Logic to process attendance data and insert into the database.
    #     """
    #     try:
    #         df['date'] = pd.to_datetime(df['date']).dt.date
    #         min_date = df['date'].min()
    #         max_date = df['date'].max()
    #         all_dates = pd.date_range(min_date, max_date).date

    #         with transaction.atomic():
    #             for date in all_dates:
    #                 date_data = df[df['date'] == date]
                    
    #                 if date_data.empty:
    #                     print(f"No data for date {date}")
    #                     continue

    #                 emp_attendance_id = date_data['Emp_Id'].astype(str).str.strip()

    #                 for emp_id in emp_attendance_id:
                       
    #                     # Fetch the employee based on Emp_Id
    #                     active_employee = EmployeeDataModel.objects.filter(
    #                         employeeProfile__employee_attendance_id=emp_id
    #                     ).first()

    #                     if active_employee:
    #                         if active_employee.employeeProfile.employee_status == "active":
                               
    #                             # Filter employee data
    #                             emp_data = date_data[date_data['Emp_Id'].astype(str).str.strip() == emp_id]
                               
    #                             # Processing intime, outtime
    #                             intime = emp_data['intime'].values[0] if not emp_data.empty and pd.notna(emp_data['intime'].values[0]) else None
    #                             outtime = emp_data['outtime'].values[0] if not emp_data.empty and pd.notna(emp_data['outtime'].values[0]) else None
    #                             print(f"Intime: {intime}, Outtime: {outtime}")

    #                             # Call the function to save attendance
    #                             try:
    #                                 Status, leave_information = self.calculate_status(
    #                                     active_employee, emp_data, False, False, [], date
    #                                 )
    #                                 self.create_or_update_attendance_record(
    #                                     active_employee, date, Status, leave_information, intime, outtime
    #                                 )
    #                                 print(f"Attendance saved for {emp_id}")
    #                             except Exception as save_err:
    #                                 print(f"Error saving attendance for {emp_id}: {save_err}")
    #                         else:
    #                             print(f"Employee {emp_id} is not active.")
    #                     else:
    #                         print(f"Employee with Emp_Id {emp_id} not found in the database.")

    #     except Exception as e:
    #         print(f"Error: {e}")
    #         logger.error(f"Error processing attendance data: {str(e)}")

    # def calculate_status(self, employee, emp_data, is_public_holiday, leave_exists, weekoff_days, date):
    #     """
    #     Helper function to calculate status and leave information.
    #     """
    #     Status = "absent"
    #     leave_information = "Unauthorized_Absent"

    #     if leave_exists:
    #         Status = "absent"
    #         leave_information = "Authorized_Absent"
    #     elif AvailableRestrictedLeaves.objects.filter(employee=employee, holiday__Date=date, is_utilised=True).exists():
    #         Status = "restricted_leave"
    #         leave_information = "No_attention_required"
    #     elif is_public_holiday:
    #         Status = "public_leave"
    #         leave_information = "No_attention_required"
    #     elif date.strftime('%A').lower() in weekoff_days:
    #         Status = "week_off"
    #         leave_information = "No_attention_required"

    #     return Status, leave_information

    # def create_or_update_attendance_record(self, employee, date, Status, leave_information, intime, outtime):
    #     """
    #     Helper function to create or update attendance record.
    #     """
    #     employee_shift = employee.employeeProfile.EmployeeShifts
    #     start_time = employee_shift.start_shift if employee_shift else time(9, 30)
    #     end_time = employee_shift.end_shift if employee_shift else time(18, 30)

    #     attendance_data, created = CompanyAttendanceDataModel.objects.get_or_create(
    #         Emp_Id=employee,
    #         date=date,
    #         defaults={'leave_information': leave_information, 'Status': Status, 'Shift': employee_shift}
    #     )

    #     if intime:
    #         attendance_data.InTime = intime
    #     if outtime:
    #         attendance_data.OutTime = outtime
    #     # Late arrival, early departure, and working hours calculation can be added here as required.
    #     attendance_data.save()


    def process_attendance_data(self, df):
        """
        Logic to process attendance data and insert into the database.
        """
        try:

            df['date'] = pd.to_datetime(df['date']).dt.date
            min_date = df['date'].min()
            max_date = df['date'].max()
            all_dates = pd.date_range(min_date, max_date).date

            with transaction.atomic():
                for date in all_dates:
                    date_data = df[df['date'] == date]
                    
                    if date_data.empty:
                        print(f"No data for date {date}")
                        continue

                    emp_attendance_id = date_data['Emp_Id'].astype(str).str.strip()

                    for emp_id in emp_attendance_id:
                       
                        # Fetch the employee based on Emp_Id
                        active_employee = EmployeeDataModel.objects.filter(
                            employeeProfile__employee_attendance_id=emp_id
                        ).first()

                        if active_employee:
                            if active_employee.employeeProfile.employee_status == "active":
                               
                                # Filter employee data
                                emp_data = date_data[date_data['Emp_Id'].astype(str).str.strip() == emp_id]
                               
                                # Processing intime, outtime
                                intime = emp_data['intime'].values[0] if not emp_data.empty and pd.notna(emp_data['intime'].values[0]) else None
                                outtime = emp_data['outtime'].values[0] if not emp_data.empty and pd.notna(emp_data['outtime'].values[0]) else None
                                print(f"Intime: {intime}, Outtime: {outtime}")

                                # Check for public holiday, leave, weekoff, etc.
                                is_public_holiday = CompanyHolidaysDataModel.objects.filter(
                                    leave_type="Public_Leave", Date=date
                                ).exists()

                                leave_exists = EmployeesLeavesmodel.objects.filter(
                                    leave_request__employee=active_employee, leave_date=date
                                ).exists()

                                weekoff_days = EmployeeWeekoffsModel.objects.filter(
                                    employee_id=active_employee.pk,
                                    month=date.month,
                                    year=date.year
                                ).values_list('weekoff_days__day', flat=True)
                                weekoff_days = [day.lower() for day in weekoff_days]

                                Status, leave_information = self.calculate_status(
                                    active_employee, emp_data, is_public_holiday, leave_exists, weekoff_days, date
                                )

                                # Call the function to save attendance
                                try:
                                    self.create_or_update_attendance_record(
                                        active_employee, date, Status, leave_information, intime, outtime
                                    )
                                    print(f"Attendance saved for {emp_id}")
                                except Exception as save_err:
                                    print(f"Error saving attendance for {emp_id}: {save_err}")
                            else:
                                print(f"Employee {emp_id} is not active.")
                        else:
                            print(f"Employee with Emp_Id {emp_id} not found in the database.")

        except Exception as e:
            print(f"Error: {e}")
            logger.error(f"Error processing attendance data: {str(e)}")

    def calculate_status(self, employee, emp_data, is_public_holiday, leave_exists, weekoff_days, date):
        """
        Helper function to calculate status and leave information.
        """
        Status = "absent"
        leave_information = "Unauthorized_Absent"

        if leave_exists:
            Status = "absent"
            leave_information = "Authorized_Absent"
        elif AvailableRestrictedLeaves.objects.filter(employee=employee, holiday__Date=date, is_utilised=True).exists():
            Status = "restricted_leave"
            leave_information = "No_attention_required"
        elif is_public_holiday:
            Status = "public_leave"
            leave_information = "No_attention_required"
        elif date.strftime('%A').lower() in weekoff_days:
            Status = "week_off"
            leave_information = "No_attention_required"

        return Status, leave_information

    def create_or_update_attendance_record(self, employee, date, Status, leave_information, intime, outtime):
        """
        Helper function to create or update attendance record.
        """
        employee_shift = employee.employeeProfile.EmployeeShifts
        start_time = employee_shift.start_shift if employee_shift else time(9, 30)
        end_time = employee_shift.end_shift if employee_shift else time(18, 30)

        attendance_data, created = CompanyAttendanceDataModel.objects.get_or_create(
            Emp_Id=employee,
            date=date,
            defaults={
                'leave_information': leave_information, 
                'Status': Status, 
                'Shift': employee_shift
            }
        )

        if intime:
            attendance_data.InTime = intime
        if outtime:
            attendance_data.OutTime = outtime

        # Calculate late arrival
        # if intime:
        #     in_datetime = datetime.combine(date, intime)
        #     late_arrival = None
        #     if in_datetime > datetime.combine(date, start_time):
        #         late_arrival = in_datetime - datetime.combine(date, start_time)
        #         attendance_data.Late_Arrivals = (datetime.min + late_arrival).time()
        #     else:
        #         attendance_data.Late_Arrivals = None

        # # Calculate early departure
        # if outtime:
        #     out_datetime = datetime.combine(date, outtime)
        #     if out_datetime < datetime.combine(date, end_time):
        #         early_departure = datetime.combine(date, end_time) - out_datetime
        #         attendance_data.Early_Depature = (datetime.min + early_departure).time()
        #     else:
        #         attendance_data.Early_Depature = None

        # # Calculate hours worked
        # if intime and outtime:
        #     if intime < start_time:
        #         intime = start_time
        #     if outtime > end_time:
        #         outtime = end_time

        #     in_datetime = datetime.combine(date, intime)
        #     out_datetime = datetime.combine(date, outtime)
        #     hours_worked = out_datetime - in_datetime
        #     attendance_data.Hours_Worked = (datetime.min + hours_worked).time()

        #     total_working_hours = datetime.combine(date, end_time) - datetime.combine(date, start_time)
        #     attendance_data.TotalWorkingHours = (datetime.min + total_working_hours).time()

        #     # Update status based on hours worked, but respect week-off/holiday
        #     if attendance_data.Hours_Worked >= time(8, 00):
        #         Status = "present"
        #         leave_information = "No_attention_required"
        #     elif attendance_data.Hours_Worked >= time(4, 00):
        #         Status = "half_day"
        #     else:
        #         # If they worked less than 4 hours, keep the original Status if it was week_off or public_leave
        #         if Status not in ["week_off", "public_leave"]:
        #             Status = "less_than_half_day"

        # attendance_data.Day = date.strftime('%A')
        # attendance_data.leave_information = leave_information
        # attendance_data.Status = Status if Status else None
        # attendance_data.save()

        #17/02/2026
        # Calculate late arrival, early departure, worked hours, and status using centralized Model logic
        # Force recalculation to ensure consistency
        attendance_data.save(force_recalculate=True)

        # Send email notification if late arrival is present (re-fetch after save)
        if attendance_data.Late_Arrivals is not None:
            if created or attendance_data.InTime != intime:
                self.send_email_notification(employee, intime, date, attendance_data)

    def send_email_notification(self, employee, new_intime, date, attendance_data):
        print(employee)
        """
        Helper function to send late login email notifications.
        """
        # subject = f"Late Login Notification on {date}"
        # message = (
        #     f"We noticed that you logged in late on {date}. "
        #     f"Your recorded late arrival time is {attendance_data.Late_Arrivals}.\n"
        #     "Please ensure to adhere to your shift timings to avoid any further issues.\n\n"
        #     "Thank you,\nMerida Tech Minds."
        # )

        # email_from = settings.EMAIL_HOST_USER
        # recipient_list = [employee.employeeProfile.email]
        # send_mail(subject, message, email_from, recipient_list)



#//////////////////////.............functionality..............//////////////////////////////////////
class EmployeesAttendanceDataList(APIView):
    def get(self,request,emp_id=None,duration=None):
        emp_obj=EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()

        current_date=timezone.localdate()
        current_year=current_date.year
        current_month=current_date.month

        # duration_wise_attendance_data
        year_wise_attendance_data=CompanyAttendanceDataModel.objects.filter(date__year=current_date)
        month_wise_attendance_data=year_wise_attendance_data.filter(date__month=current_month)

        if duration=="month":
            pass


class AttendanceByYearMonthView(APIView):
    def get(self, request, start_date=None, end_date=None):

        if start_date:
            start_date = parse_date(start_date)
            if end_date:
                end_date = parse_date(end_date)
            else:
                end_date= start_date
                
            # attendance_data = CompanyAttendanceDataModel.objects.filter(date__range=[start_date, end_date]).order_by('-date','-Emp_Id__Name')
            # Optimization: Batch load all related data to prevent N+1 queries in the serializer.
            # Fix: Only return attendance for ACTIVE employees.
            attendance_data = CompanyAttendanceDataModel.objects.filter(
                date__range=[start_date, end_date],
                Emp_Id__employeeProfile__employee_status="active"
            ).select_related(
                'Shift', 'Emp_Id', 'Emp_Id__Position', 
                'Emp_Id__Position__Department', 'Emp_Id__Reporting_To',
                'Emp_Id__employeeProfile' #19/02/2026
            ).prefetch_related(
                'companyattendance_set'
            ).order_by('-date','-Emp_Id__Name')
            
            serializer = CompanyAttendanceDataSerializer(attendance_data, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        else:
            return Response([],status=status.HTTP_200_OK)

class AttendanceByYearMonthWeekView(APIView):
    def get(self, request, year, month, week):
        first_day_of_week = (week - 1) * 7 + 1
        last_day_of_week = first_day_of_week + 6
        attendance_data = CompanyAttendanceDataModel.objects.filter(
            date__year=year,
            date__month=month,
            date__day__range=(first_day_of_week, last_day_of_week)
        )
        serializer = CompanyAttendanceDataSerializer(attendance_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from django.utils.dateparse import parse_date

class EmployeeAttendanceView(APIView):
    # Original version (Unoptimized / No prefetching):
    # def get(self, request, employee_id,start_date,end_date):
    #     employee = get_object_or_404(EmployeeDataModel, EmployeeId=employee_id)
    #     
    #     # Parse the dates
    #     if start_date:
    #         start_date = parse_date(start_date)
    #     if end_date:
    #         end_date = parse_date(end_date)
    #     
    #     # Filter attendance data based on employee and date range
    #     if start_date and end_date:
    #         attendance_records = CompanyAttendanceDataModel.objects.filter(
    #             Emp_Id=employee, 
    #             date__range=[start_date, end_date]
    #         ).order_by("date")
    #     else:
    #         attendance_records = CompanyAttendanceDataModel.objects.filter(Emp_Id=employee).order_by("date")
    #     
    #     # Serialize the data
    #     employee_serializer = EmployeeAttendanceSerializer(employee)
    #     attendance_serializer = CompanyAttendanceDataSerializer(attendance_records, many=True)
    #     
    #     # Combine serialized data
    #     response_data = employee_serializer.data
    #     response_data['attendance_data'] = attendance_serializer.data
    #     
    #     return Response(response_data, status=status.HTTP_200_OK)

    def get(self, request, employee_id, start_date, end_date):
        employee = get_object_or_404(EmployeeDataModel, EmployeeId=employee_id)
        
        # Parse the dates
        if start_date:
            start_date = parse_date(start_date)
        if end_date:
            end_date = parse_date(end_date)
        
        # Filter attendance data based on employee and date range
        # Use select_related and prefetch_related to avoid N+1 queries
        attendance_queryset = CompanyAttendanceDataModel.objects.filter(Emp_Id=employee).select_related('Shift', 'Emp_Id', 'Emp_Id__Position', 'Emp_Id__Position__Department', 'Emp_Id__Reporting_To').prefetch_related('companyattendance_set')
        
        if start_date and end_date:
            # attendance_records = CompanyAttendanceDataModel.objects.filter(
            #     Emp_Id=employee, 
            attendance_records = attendance_queryset.filter(
                date__range=[start_date, end_date]
            ).order_by("date")
        else:
            # attendance_records = CompanyAttendanceDataModel.objects.filter(Emp_Id=employee).order_by("date")
            attendance_records = attendance_queryset.order_by("date")
        
        # Serialize the data
        # employee_serializer = EmployeeAttendanceSerializer(employee)
        # Use a simpler serializer for the employee to avoid the heavy attendance_data field
        from HRM_App.serializers import EmployeeDataSerializer
        employee_data = EmployeeDataSerializer(employee).data
        attendance_serializer = CompanyAttendanceDataSerializer(attendance_records, many=True)
        
        # Combine serialized data
        # response_data = employee_serializer.data
        response_data = employee_data
        response_data['attendance_data'] = attendance_serializer.data
        
        return Response(response_data, status=status.HTTP_200_OK)

class ReportingEmployeeAttendanceView(APIView):
    def get(self, request, reporting_manager_id):
        reporting_manager = get_object_or_404(EmployeeDataModel, EmployeeId=reporting_manager_id)
        # reporting_employees = EmployeeDataModel.objects.filter(Reporting_To=reporting_manager)
        
        # 1. LIMIT historical data to the last 30 days. Loading all-time data is a disaster for performance.
        # 2. Use prefetching to avoid N+1 queries in the serializer.
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        reporting_employees = EmployeeDataModel.objects.filter(
            Reporting_To=reporting_manager
        ).prefetch_related(
            Prefetch(
                'companyattendancedatamodel_set',
                queryset=CompanyAttendanceDataModel.objects.filter(
                    date__gte=thirty_days_ago
                ).select_related(
                    'Shift', 'Emp_Id', 'Emp_Id__Position', 
                    'Emp_Id__Position__Department'
                ).prefetch_related('companyattendance_set').order_by('-date')
            )
        )
        
        serializer = EmployeeAttendanceSerializer(reporting_employees, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from datetime import datetime, timedelta

class EmployeesDailyAttendanceData(APIView):
    def get(self, request):
        try:
            date_str = request.GET.get("date")
            login_user = request.GET.get("login_emp")
            print(date_str,login_user)

            if not date_str:
                return Response({"error": "Missing 'date' parameter."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Parse the date string into a datetime object
                date = datetime.fromisoformat(date_str).date()
            except ValueError as e:
                return Response({"error": f"Invalid date format: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

            #5/1/2026
            # Get the employee object for the logged-in user
            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=login_user).first()

            # if emp_obj and emp_obj.Designation in ["Admin", 'HR']:
            if emp_obj and emp_obj.Designation in ["Admin", 'HR', 'Manager']:
                # # Fetch attendance data for the specified date
                # # attendance_data = CompanyAttendanceDataModel.objects.filter(date=date).exclude(Q(Late_Arrivals=None) , Q(Early_Depature=None))
                # attendance_data = CompanyAttendanceDataModel.objects.filter(date=date)

                # print("attendance_data",attendance_data)

                # list_data=[]
                # if attendance_data.exists():
                  
                #     def time_to_timedelta(time_obj):
                #         return timedelta(hours=time_obj.hour, minutes=time_obj.minute, seconds=time_obj.second)

                #     # Filter for high late logins (greater than or equal to 15 minutes)
                #     high_late_logins = attendance_data.filter(Late_Arrivals__gte=(datetime.min + timedelta(minutes=15)).time())
                #     high_late_logins_serializer = CompanyAttendanceDataSerializer(high_late_logins, many=True)

                #     # Filter for low late logins (less than 15 minutes and greater than or equal to 1 minute)
                #     low_late_logins = attendance_data.filter(
                #         Late_Arrivals__lt=(datetime.min + timedelta(minutes=15)).time(),
                #         Late_Arrivals__gte=(datetime.min + timedelta(minutes=1)).time()
                #     )
                #     low_late_logins_serializer = CompanyAttendanceDataSerializer(low_late_logins, many=True)
            
                #     list_data+=high_late_logins_serializer.data
                #     list_data+=low_late_logins_serializer.data

                #     logins_data.append({"high_late_logins":high_late_logins_serializer.data})
                #     logins_data.append({"low_late_logins":low_late_logins_serializer.data})
                #     logins_data["low_late_logins"] = low_late_logins_serializer.date

                #     attendance_data_serializer= CompanyAttendanceDataSerializer(attendance_data, many=True)
                #     list_data+=attendance_data_serializer.data

                # if list_data==[]:
                #     logins_data=None

                # return Response(list_data, status=status.HTTP_200_OK)
                
                # Use prefetching and serialize ONCE.
                attendance_data = CompanyAttendanceDataModel.objects.filter(date=date).select_related(
                    'Shift', 'Emp_Id', 'Emp_Id__Position', 
                    'Emp_Id__Position__Department', 'Emp_Id__Reporting_To'
                ).prefetch_related('companyattendance_set')

                if not attendance_data.exists():
                    return Response([], status=status.HTTP_200_OK)

                # Serialize the entire set once
                all_data = CompanyAttendanceDataSerializer(attendance_data, many=True).data
                return Response(all_data, status=status.HTTP_200_OK)
            else:
                # Fetch attendance data for the specific employee on the specified date
                attendance_data = CompanyAttendanceDataModel.objects.filter(Emp_Id__EmployeeId=login_user, date=date).first()

                if attendance_data:
                    attendance_serializer = CompanyAttendanceDataSerializer(attendance_data)
                    return Response(attendance_serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response(None, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

class DailyEmployeeAttendanceView(APIView):

    def get(self, request, employee_id, *args, **kwargs):
        try:
            # Get the employee instance
            employee = EmployeeDataModel.objects.get(EmployeeId=employee_id)
            # Get the current date
            today = timezone.now().date()
            # Calculate the start of the last week (7 days from today)
            start_of_last_week = today - timedelta(days=7)
            # Calculate the start and end of the last month
            start_of_last_month = today.replace(day=1) - timedelta(days=1)
            start_of_last_month = start_of_last_month.replace(day=1)
            end_of_last_month = today.replace(day=1) - timedelta(days=1)

            # Get attendance data for the last week with late arrivals or early departures
            last_week_data = CompanyAttendanceDataModel.objects.filter(
                Emp_Id=employee,
                date__range=[start_of_last_week, today],
                Late_Arrivals__isnull=False
            ).order_by('-date') | CompanyAttendanceDataModel.objects.filter(
                Emp_Id=employee,
                date__range=[start_of_last_week, today],
                Early_Depature__isnull=False
            ).order_by('-date')

            # Get attendance data for the last month with late arrivals or early departures
            last_month_data = CompanyAttendanceDataModel.objects.filter(
                Emp_Id=employee,
                date__range=[start_of_last_month, end_of_last_month],
                Late_Arrivals__isnull=False
            ).order_by('date') | CompanyAttendanceDataModel.objects.filter(
                Emp_Id=employee,
                date__range=[start_of_last_month, end_of_last_month],
                Early_Depature__isnull=False
            ).order_by('date')

            # Serialize the data
            last_week_serializer = CompanyAttendanceDataSerializer(last_week_data.distinct(), many=True)
            last_month_serializer = CompanyAttendanceDataSerializer(last_month_data.distinct(), many=True)

            # Prepare response data
            response_data = {
                "last_week_attendance": last_week_serializer.data,
                "last_month_attendance": last_month_serializer.data
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        
class LateloginsEmailsSend(APIView):
    def get(self, request):
        attendance_id = request.GET.get("att_id")
        late_in_early_out = request.GET.get("att_id_list")
        duration_from = request.GET.get("from")
        duration_to = request.GET.get("to")

        # Handle individual attendance ID
        if attendance_id:
            attendance_obj = CompanyAttendanceDataModel.objects.filter(pk=attendance_id).first()
            if attendance_obj:
                try:
                    send_email_notification(attendance_obj)
                    return Response("Mail sent successfully", status=status.HTTP_200_OK)
                except Exception as e:
                    print(e)
                    return Response("Email not sent. Error: {}".format(str(e)), status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response("Attendance ID does not exist", status=status.HTTP_400_BAD_REQUEST)

        # Handle list of attendance IDs
        elif late_in_early_out:
            late_in_early_out_list = late_in_early_out.split(",")  # Assuming the IDs are passed as a comma-separated string
            
            # Prepare date range filter
            if duration_from and duration_to:
                try:
                    # Convert strings to date objects
                    duration_from_date = timezone.datetime.fromisoformat(duration_from)
                    duration_to_date = timezone.datetime.fromisoformat(duration_to)
                    
                    for att_id in late_in_early_out_list:
                        attendance_obj = CompanyAttendanceDataModel.objects.filter(pk=att_id, date__range=(duration_from_date, duration_to_date)).first()
                        if attendance_obj:
                            send_email_notification(attendance_obj)
                except Exception as e:
                    print(e)
                    return Response("Error processing date range or sending email: {}".format(str(e)), status=status.HTTP_400_BAD_REQUEST)
                
                return Response("Mail sent successfully for the specified date range", status=status.HTTP_200_OK)

            # If no duration_from and duration_to provided, send emails for today
            else:
                for att_id in late_in_early_out_list:
                    attendance_obj = CompanyAttendanceDataModel.objects.filter(pk=att_id, date=timezone.localdate()).first()
                    if attendance_obj:
                        try:
                            send_email_notification(attendance_obj)
                        except Exception as e:
                            print(e)
                            return Response("Error sending email for attendance ID {}: {}".format(att_id, str(e)), status=status.HTTP_400_BAD_REQUEST)

                return Response("Mail sent successfully for today's attendance", status=status.HTTP_200_OK)

        return Response("No attendance ID provided", status=status.HTTP_400_BAD_REQUEST)
    
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

def send_email_notification(attendance_data):
    date = attendance_data.date
    subject = f"Late Login Alert on {date}"

    if attendance_data.Early_Depature:
        reason = f"Your recorded early departure time is {attendance_data.Early_Depature}."
    elif attendance_data.Late_Arrivals:
        reason = f"Your recorded late arrival time is {attendance_data.Late_Arrivals}."
    else:
        reason = ""

    # HTML email content
    html_content = f"""
    <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; width: 80%; margin: auto;">
        <div style="text-align: left;">
            <img src='https://hrmbackendapi.meridahr.com/media/Profile_Images/merida_logo_bOT3Dnk.jpg' alt="Company Logo" style="width: 100px;"/>
        </div>
        <h2 style="color: #333;">Late Login Alert</h2>
        <p>Dear {attendance_data.Emp_Id.Name},</p>
        <p>We noticed that you logged in late on <strong>{date}/{attendance_data.Day}</strong>.</p>
        {f"<p>{reason}</p>" if reason else ""}
        <p>Please ensure to adhere to your shift timings <strong>{attendance_data.Shift.Shift_Name}</strong>.</p>
        <p><strong>From:</strong> {attendance_data.Shift.start_shift} <strong>To:</strong> {attendance_data.Shift.end_shift}</p>
        <p>To avoid any further issues, kindly follow your assigned shift timings.</p>
        <p>Thank you,<br/>Merida Tech Minds</p>
    </div>
    """

    # Plain text fallback for email clients that don't support HTML
    text_content = f"""
    Late Login Alert

    Dear {attendance_data.Emp_Id.Name},

    We noticed that you logged in late on {date}/{attendance_data.Day}.

    {reason}

    Please ensure to adhere to your shift timings {attendance_data.Shift.Shift_Name}.
    From: {attendance_data.Shift.start_shift} To: {attendance_data.Shift.end_shift}

    To avoid any further issues, kindly follow your assigned shift timings.

    Thank you,
    Merida Tech Minds
    """

    email_from = settings.EMAIL_HOST_USER
    recipient_list = [attendance_data.Emp_Id.employeeProfile.email]

    # Create email message
    email = EmailMultiAlternatives(subject, text_content, email_from, recipient_list)
    email.attach_alternative(html_content, "text/html")

    try:
        email.send()
    except Exception as e:
        print(f"Error sending email: {e}")



        
#  Employee Attendance Leaves Calculation function
from django.db.models import Q
class EmployeesAttendanceCalculation(APIView):
    def get(self,request,emp_id,month,year):
        try:
            cad_obj=CompanyAttendanceDataModel.objects.filter(Emp_Id__EmployeeId=emp_id,date__month=month,date__year=year)
            for i in cad_obj:
                print(i.Status)
            cld_obj=EmployeesLeavesmodel.objects.filter(leave_request__employee__EmployeeId=emp_id,leave_date__month=month,leave_date__year=year)

            paid_leaves=cld_obj.filter(fall_under="Paid_Leave").count()

            work_days=cad_obj.filter(Q(Status="present") | Q(Status="week_off") | Q(Status="public_leave")).count()
            half_days=cad_obj.filter(Status="half_day").count()/2

            unpaid_leaves=cld_obj.filter(fall_under="Unpaid_Leave").count()
            un_info_obj=cad_obj.filter(leave_information="Unauthorized_Absent").count()

            total_working_days=cad_obj.exclude(Status="public_leave").count()
            total_paid_leaves= paid_leaves
            total_unpaid_leaves= unpaid_leaves + un_info_obj

            att_dict={"total_working_days":total_working_days,
                      "work_days":work_days+half_days,
                      "total_paid_leaves":total_paid_leaves,
                      "total_unpaid_leaves":total_unpaid_leaves+half_days}
            
            return Response(att_dict,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        






# ....................................testing ...........................................................................

import pandas as pd
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
#from .serializers import ExcelUploadSerializer
from django.http import HttpResponse
import io

class ProcessExcelView(APIView):

    def get(self, request, *args, **kwargs):
        file_path = request.query_params.get('file_path')
    # def post(self, request, *args, **kwargs):
    #     file_path = request.data.get('file_path')
        
        if not file_path:
            return Response({"error": "File path not provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Check if the file exists
            if not os.path.exists(file_path):
                return Response({"error": "File not found."}, status=status.HTTP_404_NOT_FOUND)

            # Load the Excel file into a DataFrame
            df = pd.read_excel(file_path)

            # Combine 'Date', 'Month', and 'Year' columns into a single 'date' column
            # df['date'] = pd.to_datetime(df[['Date', 'Month', 'Year']].astype(str).agg('-'.join, axis=1), format='%d-%b-%Y').dt.date
            df['date'] = pd.to_datetime(df[['Date', 'Month', 'Year']].astype(str).agg('-'.join, axis=1), format='%d-%b-%Y').dt.normalize()

            # Create 'intime' and 'outtime' columns based on the first and last punch time of the day
            df['intime'] = df.groupby(['PayCode', 'date'])['Time'].transform('first')
            df['outtime'] = df.groupby(['PayCode', 'date'])['Time'].transform('last')

            # Drop duplicates to retain only one record per employee per day
            df = df.drop_duplicates(subset=['PayCode', 'date']).drop(['Month', 'Date', 'Year'], axis=1)

            # Rename columns to match your expected output
            df = df.rename(columns={'PayCode': 'Emp_Id', 'Name': 'Names'})

            # Reorder columns as required
            df = df[['Names', 'Emp_Id', 'date', 'intime', 'outtime']]

            # Create a BytesIO buffer to write the Excel file to
            buffer = io.BytesIO()

            # Write the DataFrame to an Excel file
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')

            # Ensure buffer is not closed before being sent in the response
            buffer.seek(0)

            # Create a response with the Excel file
            response = HttpResponse(buffer, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename="processed_data.xlsx"'

            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

# Add employee Week offs 
from dateutil.relativedelta import relativedelta
class WeekoffsView(APIView):
    def get(self,request):
        weekoff_emp=request.GET.get("weekoff_emp")
        weekoff_id=request.GET.get("weekoff_id")
        year = request.GET.get("year")   
        month = request.GET.get("month")

        try:
            if not year and not month:
                year=timezone.localdate().year
                month=timezone.localdate().month

            if weekoff_emp:
                emp_weekoff_obj=EmployeeWeekoffsModel.objects.filter(employee_id__EmployeeId=weekoff_emp,month=month,year=year)
                if not emp_weekoff_obj:
                    return Response("employee is not active or week of not exist!", status=status.HTTP_400_BAD_REQUEST)
                emp_weeoff_list=[]
                for i in emp_weekoff_obj:
                    emp_weeoff_serializer=EmployeeWeekoffsSerializer(i).data
                    print("emp_weeoff_serializer",emp_weeoff_serializer)
                    days=WeekOffDay.objects.filter(pk__in=i.weekoff_days.all())
                    emp_weeoff_serializer["weekoff_days"]=WeekOffDaySerializer(days, many=True).data
                    # emp_weeoff_serializer["weekoff_days"]=[ j.day for j in days]
                    # emp_weeoff_serializer["weekoff_days"]=[ j.id for j in days]
                    emp_weeoff_list.append(emp_weeoff_serializer)
                
                return Response(emp_weeoff_list,status=status.HTTP_200_OK)
            elif weekoff_id:
                emp_weekoff_obj=EmployeeWeekoffsModel.objects.filter(pk=weekoff_id).first()
                if not emp_weekoff_obj:
                    return Response("Only active employees are allowed", status=status.HTTP_400_BAD_REQUEST)
                emp_weeoff_serializer=EmployeeWeekoffsSerializer(emp_weekoff_obj)
                return Response(emp_weeoff_serializer.data,status=status.HTTP_200_OK)
   
            else:
                weekoffs=WeekOffDay.objects.all()
                WeekOffSerializer=WeekOffDaySerializer(weekoffs,many=True)
                return Response(WeekOffSerializer.data,status=status.HTTP_200_OK)
                
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
        
    def post(self, request):
        
        #return Response(request.data)
        
        employee_id = request.data.get("employee_id")
        same_for_comming_3m = request.data.get("three_months")
        same_for_comming_6m = request.data.get("six_months")
        same_for_comming_12m = request.data.get("onetwo_months")

        year = request.data.get("year")  # e.g., 2024
        month = request.data.get("month")  # e.g., 6 for June

    
        # Get the employee object, exclude inactive employees
        print("employee_id",employee_id)
        emp_obj = EmployeeDataModel.objects.filter(EmployeeId=employee_id,employeeProfile__employee_status="active").first()
        if not emp_obj:
            return Response(f"Only active employees are allowed{employee_id}", status=status.HTTP_400_BAD_REQUEST)

        # Create instances for the specified number of months
        if same_for_comming_3m:
            return self.create_weekoff_instances(emp_obj, year, month, 3, request.data)
        elif same_for_comming_6m:
            return self.create_weekoff_instances(emp_obj, year, month, 6, request.data)
        elif same_for_comming_12m:
            return self.create_weekoff_instances(emp_obj, year, month, 12, request.data)
        else:
            return self.create_weekoff_instances(emp_obj, year, month, 1, request.data)


    def create_weekoff_instances(self, employee, start_year, start_month, months_to_add, data):
        """Create weekoff instances starting from a given year and month, adding months based on the request."""
        instances_to_create = []

        # Convert year and month to a valid datetime object
        try:
            start_date = timezone.datetime(year=int(start_year), month=int(start_month), day=1)
        except ValueError as e:
            return Response(f"Invalid date: {str(e)}", status=status.HTTP_400_BAD_REQUEST)

        # Loop through the months to create instances
        for month_offset in range(months_to_add):
            # Add the appropriate number of months
            new_date = start_date + relativedelta(months=month_offset)
            new_year = new_date.year
            new_month = new_date.month

            # Check if an entry already exists to avoid duplicates
            if not EmployeeWeekoffsModel.objects.filter(employee_id=employee, month=new_month, year=new_year).exists():
                # Prepare data for the new instance
                ewo_data = {
                    'employee_id': employee.id,  # ForeignKey to EmployeeDataModel
                    'month': new_month,  # New month
                    'year': new_year,  # New year
                    'weekoff_days': data.get('weekoff_days')  # List of WeekOffDay IDs
                }

                # Create the instance with the serializer
                ewo_serializer = EmployeeWeekoffsSerializer(data=ewo_data)
                if ewo_serializer.is_valid():
                    instances_to_create.append(ewo_serializer)
                else:
                    return Response(ewo_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Save all valid instances
        for serializer in instances_to_create:
            serializer.save()

        return Response(f"Weekoff instances created for {months_to_add} months successfully.", status=status.HTTP_201_CREATED)
    
    def patch(self,request):
        try:

            weekoff_id=request.GET.get("weekoff_id")
            if not weekoff_id:
                return Response("weekoff id is required",status=status.HTTP_400_BAD_REQUEST)
            
            emp_weekoff_obj=EmployeeWeekoffsModel.objects.filter(pk=weekoff_id).first()
            if not emp_weekoff_obj:
                return Response("Only active employees are allowed", status=status.HTTP_400_BAD_REQUEST)
            
            emp_weeoff_serializer=EmployeeWeekoffsSerializer(emp_weekoff_obj,data=request.data,partial=True)

            if emp_weeoff_serializer.is_valid():
                emp_weeoff_serializer.save()
                return Response("updated successfully",status=status.HTTP_200_OK)
            else:
                return Response(emp_weeoff_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self,request):
        weekoff_id=request.GET.get("weekoff_id")
        if not weekoff_id:
            return Response("weekoff id is required",status=status.HTTP_400_BAD_REQUEST)
        EmployeeWeekoffsModel.objects.filter(pk=weekoff_id).first().delete()
        return Response("data deleted successfully",status=status.HTTP_200_OK)
    



# def is_within_permitted_location(current_location, permitted_location, radius=0.1):
#     """
#     Check if the current location is within the permitted radius (in km) of the permitted location.
#     """
#     distance = geodesic(current_location, permitted_location).kilometers
#     return distance <= radius



# def verify_face(captured_face_path, reference_face_path):
#     """
#     Verifies the captured face against the reference face.
#     """
#     captured_image = face_recognition.load_image_file(captured_face_path)
#     reference_image = face_recognition.load_image_file(reference_face_path)

#     # Encode faces
#     captured_encoding = face_recognition.face_encodings(captured_image)[0]
#     reference_encoding = face_recognition.face_encodings(reference_image)[0]

#     # Compare faces
#     results = face_recognition.compare_faces([reference_encoding], captured_encoding)
#     return results[0]  # True if faces match, False otherwise

# from datetime import datetime

# def log_attendance_with_face_recognition(current_location, permitted_location, reference_face_path,emp_id):
#     """
#     Logs attendance if the employee is within the permitted location and their face matches the reference.
#     """
#     if not is_within_permitted_location(current_location, permitted_location):
#         print("Access denied: Outside permitted location.")
#         return False

#     captured_face_path = capture_face(emp_id)
#     if not captured_face_path:
#         print("Failed to capture face.")
#         return False

#     is_face_verified = verify_face(captured_face_path, reference_face_path)
#     if is_face_verified:
#         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#         print(f"Attendance logged successfully at {timestamp}")
#         return True
#     else:
#         print("Access denied: Face verification failed.")
#         return False

# # Example Usage
# import requests
# def get_current_location():
#     # Use ipinfo.io to get the current location of the device
#     response = requests.get('https://ipinfo.io')
#     data = response.json()
#     location = data['loc'].split(',')
#     lat, lon = float(location[0]), float(location[1])
#     return lat, lon

# current_employee_location = get_current_location()
# current_location = current_employee_location  # GPS coordinates
# permitted_location = (12.971598, 77.594566)
# emp_id='MTM24EMP97'
# emp_obj=EmployeeDataModel.objects.filter(EmployeeId=emp_id).first()
# reference_face_path = emp_obj.employeeProfile.emp_img if emp_obj and emp_obj.employeeProfile.emp_img else None
# if not reference_face_path:
#     print("please give reference")
# else:
#     pass
#     # log_attendance_with_face_recognition(current_location, permitted_location, reference_face_path,emp_id)


           

