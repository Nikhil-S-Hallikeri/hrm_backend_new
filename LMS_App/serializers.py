
# import time
from datetime import datetime, timedelta, time

from HRM_App.imports import *
from .models import *
from rest_framework import serializers
from datetime import datetime, timedelta
from .models import CompanyAttendance, CompanyAttendanceDataModel, EmployeeDataModel
from .serializers import EmployeeDataSerializer

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model=LeaveTypesModel
        fields="__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.added_By:
            representation['added_By'] = instance.added_By.id
        return representation
    
class LeaveTypeDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model=LeavesTypeDetailModel
        fields="__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if representation['leave_type'] != None:
            representation['leave_type'] = instance.leave_type.id
            return representation
        else:
            representation 
    
class EmployeeLeaveTypesEligiblitySerializer(serializers.ModelSerializer):
    class Meta:
        model=EmployeeLeaveTypesEligiblity
        fields="__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['employee'] = instance.employee.EmployeeId
        representation['LeaveType'] = instance.LeaveType.leave_type.leave_name 
        representation['LeaveType_Id'] = instance.LeaveType.leave_type.pk

        # representation['added_By'] = instance.added_By.EmployeeId
        # called_Time= instance.called_date.time().replace(microsecond=0)
        # applied_time_with_offset = (datetime.combine(date.min, called_Time) + timedelta(hours=5, minutes=30)).time()
        # representation['called_Time'] = applied_time_with_offset
        # representation['called_date'] = instance.called_date.date()
        return representation

class MonthWiseLeavesSerializer(serializers.ModelSerializer):
    class Meta:
        model=MonthWiseLeavesModel
        fields="__all__"


# class LeaveRequestFormSerializer(serializers.ModelSerializer):
#     is_hr_permission_required = serializers.SerializerMethodField()
#     class Meta:
#         model=LeaveRequestForm
#         fields="__all__"

#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         representation['employee'] = instance.employee.EmployeeId
#         representation['employee_name'] = instance.employee.Name
#         if instance.approved_by:
#             representation['approved_by'] = instance.approved_by.EmployeeId
#             representation['approved_name'] = instance.approved_by.Name
        
#         if instance.LeaveType:
#             representation['LeaveType'] = instance.LeaveType.LeaveType.leave_type.leave_name
#         if instance.restricted_leave_type:
#             representation['LeaveType'] = instance.restricted_leave_type.holiday.OccasionName
#         representation['report_to'] = instance.report_to.EmployeeId if instance.report_to else None
        
#         applied_date= instance.applied_date.time().replace(microsecond=0)
#         applied_time_with_offset = (datetime.combine(date.min, applied_date) + timedelta(hours=5, minutes=30)).time()
#         representation['applied_Time'] = applied_time_with_offset
#         representation['applied_date'] = instance.applied_date.date()

#         return representation

#     def get_is_hr_permission_required(self, obj):
#         request = self.context.get('request')
#         if request:
#             login_user = request.query_params.get('login_user')
#             report_emp = self.context.get('report_emp')
#             emp_obj = EmployeeDataModel.objects.filter(EmployeeId=report_emp).first()
#             if emp_obj and emp_obj.Designation == "HR" and obj.report_to.EmployeeId == report_emp:
#                 return False
            
#             # Calculate the number of leave days
#             start_date = obj.from_date  # Replace with your actual field
#             end_date = obj.to_date     # Replace with your actual field
#             leave_days = (end_date - start_date).days + 1  # Including both start and end dates
            
#             # Check the condition
#             if emp_obj and emp_obj.Designation == "HR" or (obj.report_to.EmployeeId == report_emp and leave_days > 2):
#                 return True
                
#         return False

class LeaveRequestFormSerializer(serializers.ModelSerializer):
    is_hr_permission_required = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequestForm
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Handle employee fields safely
        if hasattr(instance, 'employee') and instance.employee:
            representation['employee'] = instance.employee.EmployeeId
            representation['employee_name'] = instance.employee.Name
        else:
            representation['employee'] = None
            representation['employee_name'] = None
        
        # Handle approved_by fields safely
        if hasattr(instance, 'approved_by') and instance.approved_by:
            representation['approved_by'] = instance.approved_by.EmployeeId
            representation['approved_name'] = instance.approved_by.Name
        else:
            representation['approved_by'] = None
            representation['approved_name'] = None

        # Handle LeaveType and restricted_leave_type fields safely
        if hasattr(instance, 'LeaveType') and instance.LeaveType:
            representation['LeaveType'] = instance.LeaveType.LeaveType.leave_type.leave_name
        elif hasattr(instance, 'restricted_leave_type') and instance.restricted_leave_type:
            representation['LeaveType'] = instance.restricted_leave_type.holiday.OccasionName
        else:
            representation['LeaveType'] = None

        # Handle report_to field safely
        if hasattr(instance, 'report_to') and instance.report_to:
            representation['report_to'] = instance.report_to.EmployeeId
        else:
            representation['report_to'] = None

        # Handle applied_date and applied_time_with_offset safely
        if hasattr(instance, 'applied_date') and instance.applied_date:
            applied_date = instance.applied_date
            applied_time_with_offset = (applied_date + timedelta(hours=5, minutes=30)).time()
            representation['applied_Time'] = applied_time_with_offset
            representation['applied_date'] = applied_date.date()
        else:
            representation['applied_Time'] = None
            representation['applied_date'] = None

        return representation

    def get_is_hr_permission_required(self, obj):
        request = self.context.get('request')
        if request:
            login_user = request.query_params.get('login_user')
            report_emp = self.context.get('report_emp')
            
            # Ensure report_emp is present
            if not report_emp:
                return False
            
            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=report_emp).first()
            
            if emp_obj and emp_obj.Designation == "HR" and obj.report_to and obj.report_to.EmployeeId == report_emp:
                return False
            
            # Calculate the number of leave days
            if hasattr(obj, 'from_date') and hasattr(obj, 'to_date') and obj.from_date and obj.to_date:
                start_date = obj.from_date
                end_date = obj.to_date
                leave_days = (end_date - start_date).days + 1  # Including both start and end dates
                
                # Check the condition for HR permission requirement
                if (emp_obj and emp_obj.Designation == "HR") or (obj.report_to and obj.report_to.EmployeeId == report_emp and leave_days > 2):
                    return True
                
        return False

class EmployeeLeavesStoringSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeesLeavesmodel
        fields  = '__all__'

class CompanyHolidaysDataModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyHolidaysDataModel
        fields  = '__all__'

class AvailableRestrictedLeavesSerializer(serializers.ModelSerializer):
    holiday = CompanyHolidaysDataModelSerializer(read_only=True)
    class Meta:
        model = AvailableRestrictedLeaves
        fields  = '__all__'

class EmployeeShiftsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShifts_Model
        fields = "__all__"


################################################################################################
#orignal code from server 

from datetime import datetime, time, timedelta
from django.utils.timezone import localtime, now

# class AttendanceSerializer(serializers.ModelSerializer):
#     duration_type = serializers.SerializerMethodField()

#     class Meta:
#         model = CompanyAttendance
#         fields = ["id", "duration_type", "ScanTimings","ScanType", "Created_Date", "Attendance"]

#     def get_duration_type(self, obj):
#         """
#         Determine whether the current punch type is 'InTime' or 'OutTime'.
#         """
#         punches = list(
#             CompanyAttendance.objects.filter(Attendance=obj.Attendance).order_by('ScanTimings')
#         )
#         try:
#             index = punches.index(obj)  # Get the index of the current punch
#             return "InTime" if index % 2 == 0 else "OutTime"
#         except ValueError:
#             return None  # If obj is not found in punches


# class CompanyAttendanceDataSerializer(serializers.ModelSerializer):
#     Emp_Id = EmployeeDataSerializer(read_only=True)
#     attendance_records = AttendanceSerializer(many=True, read_only=True, source='companyattendance_set')
#     total_duration = serializers.SerializerMethodField()

#     class Meta:
#         model = CompanyAttendanceDataModel
#         fields = "__all__"

#     def get_total_duration(self, instance):
#         """
#         Calculate the total duration for all attendance records related to this instance
#         based on OutTime to the next InTime.
#         """
#         punches = list(
#             CompanyAttendance.objects.filter(Attendance=instance).order_by('ScanTimings')
#         )
#         total_duration = timedelta()

#         for i in range(1, len(punches), 2):  # Start from index 1 (OutTime) and step by 2
#             try:
#                 out_time = punches[i].ScanTimings  # Current OutTime
#                 in_time = punches[i + 1].ScanTimings  # Next InTime

#                 base_date = datetime.now().date()
#                 out_datetime = datetime.combine(base_date, out_time)
#                 in_datetime = datetime.combine(base_date, in_time)

#                 # Handle overnight cases where InTime is earlier than OutTime
#                 if in_time < out_time:
#                     in_datetime += timedelta(days=1)

#                 # Add duration
#                 total_duration += (in_datetime - out_datetime)
#             except IndexError:
#                 # If there's no matching InTime after OutTime, break the loop
#                 break

#         # Convert total duration to hours and minutes
#         hours, remainder = divmod(total_duration.total_seconds(), 3600)
#         minutes, _ = divmod(remainder, 60)
#         return f"{int(hours)}h {int(minutes)}m"

#     # def to_representation(self, instance):
#     #     representation = super().to_representation(instance)

#     #     # Shift Details
#     #     shift = instance.Shift
#     #     representation['Shift_Name'] = shift.Shift_Name if shift else "Regular Shift"
#     #     representation['start_shift'] = shift.start_shift if shift else "09:30:00"
#     #     representation['end_shift'] = shift.end_shift if shift else "18:30:00"

#     #     # Position and Department
#     #     emp_position = instance.Emp_Id.Position if instance.Emp_Id else None
#     #     representation['position_name'] = emp_position.Name if emp_position else None
#     #     representation['Department_name'] = emp_position.Department.Dep_Name if emp_position and emp_position.Department else None

#     #     # Reporting and Status
#     #     representation['Reporting_to_name'] = (
#     #         instance.Emp_Id.Reporting_To.Name if instance.Emp_Id and instance.Emp_Id.Reporting_To else None
#     #     )
#     #     representation['Status'] = instance.Status.title() if instance.Status else None
#     #     representation['leave_information'] = instance.leave_information.title() if instance.leave_information else None

#     #     return representation


#     def to_representation(self, instance):
#         representation = super().to_representation(instance)

#         # Shift Details
#         shift = instance.Shift
#         representation['Shift_Name'] = shift.Shift_Name if shift else "Regular Shift"
#         representation['start_shift'] = shift.start_shift if shift else "09:30:00"
#         representation['end_shift'] = shift.end_shift if shift else "18:30:00"

#         # Position and Department
#         emp_position = instance.Emp_Id.Position if instance.Emp_Id else None
#         representation['position_name'] = emp_position.Name if emp_position else None
#         representation['Department_name'] = emp_position.Department.Dep_Name if emp_position and emp_position.Department else None

#         # Reporting and Status
#         representation['Reporting_to_name'] = (
#             instance.Emp_Id.Reporting_To.Name if instance.Emp_Id and instance.Emp_Id.Reporting_To else None
#         )
#         representation['Status'] = instance.Status.title() if instance.Status else None
#         representation['leave_information'] = instance.leave_information.title() if instance.leave_information else None

#         # OutTime visibility logic (only for today's attendance)
#         try:
#             is_today = instance.date == localtime(now()).date()
#             end_shift_time = shift.end_shift if shift and shift.end_shift else time(18, 30)
#             cutoff_time = datetime.combine(localtime(now()).date(), end_shift_time) + timedelta(hours=3.5)
#             current_time = localtime(now())

#             if not is_today or (instance.OutTime and current_time >= cutoff_time):
#                 representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None
#             else:
#                 representation['OutTime'] = None
#         except Exception as e:
#             # Fallback in case of any unexpected error
#             representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None

#         return representation




########################################################################################################

from datetime import datetime, time, timedelta
from django.utils.timezone import localtime, now

class AttendanceSerializer(serializers.ModelSerializer):
    duration_type = serializers.SerializerMethodField()

    class Meta:
        model = CompanyAttendance
        fields = ["id", "duration_type", "ScanTimings", "ScanType", "Created_Date", "Attendance"]

    def get_duration_type(self, obj):
        # Senior Dev Optimization: Instead of querying the DB for EVERY punch, 
        # we try to use the prefetched parent's collection if available.
        # This reduces queries significantly when serializing list of punches.
        parent = obj.Attendance
        if hasattr(parent, '_prefetched_objects_cache') and 'companyattendance_set' in parent._prefetched_objects_cache:
            punches = list(parent.companyattendance_set.all())
        else:
            # Fallback if not prefetched, but we should ensure views prefetch!
            punches = list(CompanyAttendance.objects.filter(Attendance=parent).order_by('ScanTimings'))
        
        punches.sort(key=lambda x: x.ScanTimings)
        
        if not punches:
            return None
        try:
            for index, punch in enumerate(punches):
                if punch.id == obj.id:
                    return "InTime" if index % 2 == 0 else "OutTime"
        except Exception:
            return None

from datetime import datetime, time, timedelta
from django.utils.timezone import localtime, now

class CompanyAttendanceDataSerializer(serializers.ModelSerializer):
    Emp_Id = EmployeeDataSerializer(read_only=True)
    attendance_records = AttendanceSerializer(many=True, read_only=True, source='companyattendance_set')
    total_duration = serializers.SerializerMethodField()

    class Meta:
        model = CompanyAttendanceDataModel
        fields = "__all__"
    

    # def get_break_timings(self, obj):
    #     attendance_records = obj.companyattendance_set.order_by("Created_Date")
    #     total_break = timedelta()
    #     last_out_time = None

    #     for record in attendance_records:
    #         if record.ScanType is False:  # OUT scan
    #             last_out_time = record.ScanTimings
    #         elif record.ScanType is True and last_out_time:  # IN scan after break
    #             break_duration = datetime.combine(datetime.today(), record.ScanTimings) - datetime.combine(datetime.today(), last_out_time)
    #             total_break += break_duration
    #             last_out_time = None

    #     return str(total_break) if total_break.total_seconds() > 0 else None


    # Original version (N+1 query problem):
    # def get_break_timings(self, obj):
    #     punches = list(
    #         CompanyAttendance.objects.filter(Attendance=obj).order_by('ScanTimings')
    #     )
    #
    #     total_break = timedelta()
    #     for i in range(1, len(punches) - 1, 2):  # OUT followed by next IN
    #         try:
    #             out_time = punches[i].ScanTimings
    #             next_in_time = punches[i + 1].ScanTimings
    #
    #             dt_out = datetime.combine(datetime.today(), out_time)
    #             dt_in = datetime.combine(datetime.today(), next_in_time)
    #
    #             if dt_in < dt_out:
    #                 dt_in += timedelta(days=1)
    #
    #             total_break += dt_in - dt_out
    #         except:
    #             continue
    #
    #     return str(total_break) if total_break.total_seconds() > 0 else None

    def get_break_timings(self, obj):
        # punches = list(
        #     CompanyAttendance.objects.filter(Attendance=obj).order_by('ScanTimings')
        # )
        # Use prefetched objects if available
        punches = list(obj.companyattendance_set.all())
        # Sort if not already ordered in prefetch
        punches.sort(key=lambda x: x.ScanTimings)

        total_break = timedelta()
        for i in range(1, len(punches) - 1, 2):  # OUT followed by next IN
            try:
                out_time = punches[i].ScanTimings
                next_in_time = punches[i + 1].ScanTimings

                dt_out = datetime.combine(datetime.today(), out_time)
                dt_in = datetime.combine(datetime.today(), next_in_time)

                if dt_in < dt_out:
                    dt_in += timedelta(days=1)

                total_break += dt_in - dt_out
            except:
                continue

        return str(total_break) if total_break.total_seconds() > 0 else None


    # def get_total_duration(self, instance):
    #     # from datetime import datetime, timedelta, time  # ✅ Just in case
    #     punches = list(
    #         CompanyAttendance.objects.filter(Attendance=instance).order_by('ScanTimings')
    #     )

    #     total_duration = timedelta()
    #     in_time = None
    #     out_time = None

    #     if punches:
    #         in_time = punches[0].ScanTimings
    #         out_time = punches[-1].ScanTimings

    #     instance.InTime = in_time
    #     instance.OutTime = out_time

    #     for i in range(1, len(punches), 2):
    #         try:
    #             t1 = punches[i - 1].ScanTimings
    #             t2 = punches[i].ScanTimings

    #             if not (isinstance(t1, time) and isinstance(t2, time)):
    #                 continue

    #             dt1 = datetime.combine(datetime.today(), t1)
    #             dt2 = datetime.combine(datetime.today(), t2)

    #             if dt2 < dt1:  # overnight shift
    #                 dt2 += timedelta(days=1)

    #             total_duration += dt2 - dt1

    #         except Exception as e:
    #             continue

    #     hours, remainder = divmod(total_duration.total_seconds(), 3600)
    #     minutes, _ = divmod(remainder, 60)
    #     return f"{int(hours)}h {int(minutes)}m"




    # Original version (N+1 query problem):
    # def get_total_duration(self, instance):
    #     punches = list(
    #         CompanyAttendance.objects.filter(Attendance=instance).order_by('Created_Date')
    #     )
    #
    #     total_duration = timedelta()
    #
    #     if punches:
    #         # First odd-indexed (starting from 0) punch → InTime
    #         in_time = punches[0].ScanTimings if len(punches) >= 1 else None
    #         # Last even-indexed punch (e.g. 1, 3, 5...) → OutTime
    #         out_time = None
    #         if len(punches) % 2 == 0:
    #             out_time = punches[-1].ScanTimings
    #         elif len(punches) >= 2:
    #             out_time = punches[-2].ScanTimings
    #
    #         instance.InTime = in_time
    #         instance.OutTime = out_time
    #
    #         for i in range(1, len(punches), 2):
    #             try:
    #                 t1 = punches[i - 1].ScanTimings
    #                 t2 = punches[i].ScanTimings
    #
    #                 if not (isinstance(t1, time) and isinstance(t2, time)):
    #                     continue
    #
    #                 dt1 = datetime.combine(datetime.today(), t1)
    #                 dt2 = datetime.combine(datetime.today(), t2)
    #
    #                 if dt2 < dt1:
    #                     dt2 += timedelta(days=1)
    #
    #                 total_duration += dt2 - dt1
    #             except Exception:
    #                 continue
    #
    #     hours, remainder = divmod(total_duration.total_seconds(), 3600)
    #     minutes, _ = divmod(remainder, 60)
    #     return f"{int(hours)}h {int(minutes)}m"

    def get_total_duration(self, instance):
    #     punches = list(
    #         CompanyAttendance.objects.filter(Attendance=instance).order_by('Created_Date')
    # )
        punches = list(instance.companyattendance_set.all())
        punches.sort(key=lambda x: x.Created_Date)

        total_duration = timedelta()

        if punches:
            # First odd-indexed (starting from 0) punch → InTime
            in_time = punches[0].ScanTimings if len(punches) >= 1 else None
            # Last even-indexed punch (e.g. 1, 3, 5...) → OutTime
            out_time = None
            if len(punches) % 2 == 0:
                out_time = punches[-1].ScanTimings
            elif len(punches) >= 2:
                out_time = punches[-2].ScanTimings

            instance.InTime = in_time
            instance.OutTime = out_time

            for i in range(1, len(punches), 2):
                try:
                    t1 = punches[i - 1].ScanTimings
                    t2 = punches[i].ScanTimings

                    if not (isinstance(t1, time) and isinstance(t2, time)):
                        continue

                    dt1 = datetime.combine(datetime.today(), t1)
                    dt2 = datetime.combine(datetime.today(), t2)

                    if dt2 < dt1:
                        dt2 += timedelta(days=1)

                    total_duration += dt2 - dt1
                except Exception:
                    continue

        hours, remainder = divmod(total_duration.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m"

    # Original version (N+1 query problem):
    # def get_hours_worked(self, obj):
    #     punches = list(
    #         CompanyAttendance.objects.filter(Attendance=obj).order_by('ScanTimings')
    #     )
    #     total_work_duration = timedelta()
    #
    #     for i in range(1, len(punches), 2):  # pair In-Out
    #         try:
    #             in_time = punches[i - 1].ScanTimings
    #             out_time = punches[i].ScanTimings
    #
    #             dt_in = datetime.combine(datetime.today(), in_time)
    #             dt_out = datetime.combine(datetime.today(), out_time)
    #
    #             if dt_out < dt_in:
    #                 dt_out += timedelta(days=1)
    #
    #             total_work_duration += dt_out - dt_in
    #         except:
    #             continue
    #
    #     return str(total_work_duration) if total_work_duration.total_seconds() > 0 else None

    def get_hours_worked(self, obj):
        # punches = list(
            # CompanyAttendance.objects.filter(Attendance=obj).order_by('ScanTimings')
        # )
        punches = list(obj.companyattendance_set.all())
        punches.sort(key=lambda x: x.ScanTimings)
        
        total_work_duration = timedelta()

        for i in range(1, len(punches), 2):  # pair In-Out
            try:
                in_time = punches[i - 1].ScanTimings
                out_time = punches[i].ScanTimings

                dt_in = datetime.combine(datetime.today(), in_time)
                dt_out = datetime.combine(datetime.today(), out_time)

                if dt_out < dt_in:
                    dt_out += timedelta(days=1)

                total_work_duration += dt_out - dt_in
            except:
                continue

        return str(total_work_duration) if total_work_duration.total_seconds() > 0 else None


    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['InTime'] = instance.InTime.strftime("%H:%M:%S") if instance.InTime else None
    #     representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None

    #     # break_timings = serializers.SerializerMethodField()

    #     # def get_break_timings(self, obj):
    #     representation["break_timings"] = self.get_break_timings(instance)
    #     representation["Hours_Worked"] = self.get_hours_worked(instance)
    

    #     shift = instance.Shift
    #     representation['Shift_Name'] = shift.Shift_Name if shift else "Regular Shift"
    #     representation['start_shift'] = shift.start_shift if shift else "09:30:00"
    #     representation['end_shift'] = shift.end_shift if shift else "18:30:00"

    #     emp_position = instance.Emp_Id.Position if instance.Emp_Id else None
    #     representation['position_name'] = emp_position.Name if emp_position else None
    #     representation['Department_name'] = emp_position.Department.Dep_Name if emp_position and emp_position.Department else None

    #     representation['Reporting_to_name'] = (
    #         instance.Emp_Id.Reporting_To.Name if instance.Emp_Id and instance.Emp_Id.Reporting_To else None
    #     )
    #     representation['Status'] = instance.Status.title() if instance.Status else None
    #     representation['leave_information'] = instance.leave_information.title() if instance.leave_information else None

    #     return representation
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)

    #     # Shift Details
    #     shift = instance.Shift
    #     representation['Shift_Name'] = shift.Shift_Name if shift else "Regular Shift"
    #     representation['start_shift'] = shift.start_shift if shift else "09:30:00"
    #     representation['end_shift'] = shift.end_shift if shift else "18:30:00"

    #     # Position and Department
    #     emp_position = instance.Emp_Id.Position if instance.Emp_Id else None
    #     representation['position_name'] = emp_position.Name if emp_position else None
    #     representation['Department_name'] = emp_position.Department.Dep_Name if emp_position and emp_position.Department else None

    #     # Reporting and Status
    #     representation['Reporting_to_name'] = (
    #         instance.Emp_Id.Reporting_To.Name if instance.Emp_Id and instance.Emp_Id.Reporting_To else None
    #     )
    #     representation['Status'] = instance.Status.title() if instance.Status else None
    #     representation['leave_information'] = instance.leave_information.title() if instance.leave_information else None

    #     # OutTime visibility logic (only for today's attendance)
    #     try:
    #         is_today = instance.date == localtime(now()).date()
    #         end_shift_time = shift.end_shift if shift and shift.end_shift else time(18, 30)
    #         cutoff_time = datetime.combine(localtime(now()).date(), end_shift_time) + timedelta(hours=3.5)
    #         current_time = localtime(now())

    #         if not is_today or (instance.OutTime and current_time >= cutoff_time):
    #             representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None
    #         else:
    #             representation['OutTime'] = None
    #     except Exception as e:
    #         # Fallback in case of any unexpected error
    #         representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None

    #     return representation
    def to_representation(self, instance):
        # Ensure times are calculated if they are missing on the instance
        # if instance.InTime is None or instance.OutTime is None:
        #     self.get_total_duration(instance)
        # Senior Dev Optimization: Trust the database values. 
        # The model's save() already handles calculation when data is imported.
        representation = super().to_representation(instance)

        # Use pre-fetched related objects to avoid N+1 queries
        shift = instance.Shift
        representation['Shift_Name'] = shift.Shift_Name if shift else "Regular Shift"
        # representation['start_shift'] = shift.start_shift if shift else "09:30:00"
        # representation['end_shift'] = shift.end_shift if shift else "18:30:00"
        representation['start_shift'] = shift.start_shift.strftime("%H:%M:%S") if shift and shift.start_shift else "09:30:00"
        representation['end_shift'] = shift.end_shift.strftime("%H:%M:%S") if shift and shift.end_shift else "18:30:00"

        # Position and Department
        # emp_position = instance.Emp_Id.Position if instance.Emp_Id else None
        emp = instance.Emp_Id
        emp_position = emp.Position if emp else None
        representation['position_name'] = emp_position.Name if emp_position else None
        representation['Department_name'] = emp_position.Department.Dep_Name if emp_position and emp_position.Department else None

        # Reporting and Status
        # representation['Reporting_to_name'] = (
        #     instance.Emp_Id.Reporting_To.Name if instance.Emp_Id and instance.Emp_Id.Reporting_To else None
        # )
        representation['Reporting_to_name'] = emp.Reporting_To.Name if emp and emp.Reporting_To else None
        representation['Status'] = instance.Status.title() if instance.Status else None
        representation['leave_information'] = instance.leave_information.title() if instance.leave_information else None

        # Day
        if not instance.Day and instance.date:
            representation['Day'] = instance.date.strftime("%A")
        else:
            representation['Day'] = instance.Day

        # # InTime
        # representation['InTime'] = instance.InTime.strftime("%H:%M:%S") if instance.InTime else Nonelse None
        # # BUT for correction modal, we might want to see it regardless if it exists.
        # # Let's keep the logic but fallback to strftime if it exists.
        # try:
        #     is_today = instance.date == localtime(now()).date()
        #     end_shift_time = shift.end_shift if shift and shift.end_shift else time(18, 30)
        #     cutoff_time = datetime.combine(localtime(now()).date(), end_shift_time) + timedelta(hours=3.5)
        #     current_time = localtime(now())

        #     if not is_today or (instance.OutTime and current_time >= cutoff_time):
        # else:
                # representation['OutTime'] = None
                # If it's today and not yet cutoff, but we HAVE an OutTime, maybe show it?
                # Actually, the user wants it to display for "Present" days.
                # If it's a past record, it should show.
        #         representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None
        # except Exception:

        
        #     representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None

        # Custom logic for working and break duration

        # InTime and OutTime (formatted)
        representation['InTime'] = instance.InTime.strftime("%H:%M:%S") if instance.InTime else None
        representation['OutTime'] = instance.OutTime.strftime("%H:%M:%S") if instance.OutTime else None

        # Working and break duration (These now use prefetched data)
        representation["break_timings"] = self.get_break_timings(instance)
        representation["Hours_Worked"] = self.get_hours_worked(instance)

        return representation


class EmployeeAttendanceSerializer(serializers.ModelSerializer):
    attendance_data = CompanyAttendanceDataSerializer(many=True, source='companyattendancedatamodel_set')

    class Meta:
        model = EmployeeDataModel
        fields = ['EmployeeId', 'Name', 'attendance_data']





#################################Appraisal serializer ##################
#29/12/2025
class AppraisalInvitationModelSerializer(serializers.ModelSerializer):
    self_app_id =  serializers.SerializerMethodField()
    rm_app_id =  serializers.SerializerMethodField()
    class Meta:
        model  = AppraisalInvitationModel
        fields =  '__all__'
    
    def get_self_app_id(self,obj):
        # OLD: Didn't check if ESEO is None before serializing
        # ESEO = EmployeeSelfEvaluation.objects.filter(invitation_id=obj).order_by('-id').last()
        # serializer = EmployeeSelfEvaluationSerializer(ESEO).data
        # self_app_id=serializer["id"]
        # return self_app_id
        
        # FIXED: Added null checks to prevent serialization errors
        try:
            ESEO = EmployeeSelfEvaluation.objects.filter(invitation_id=obj).order_by('-id').last()
            if ESEO:
                serializer = EmployeeSelfEvaluationSerializer(ESEO).data
                return serializer.get("id", None)
            return None
        except Exception as e:
            print(f"Error in get_self_app_id: {str(e)}")
            return None
    
    def get_rm_app_id(self,obj):
        # OLD:Didn't check if objects are None before serializing
        # ESEO = EmployeeSelfEvaluation.objects.filter(invitation_id=obj).order_by('-id').last()
        # ESEO  = EmployeeSelfEvaluationReviewModel.objects.filter(EmployeeSelfEvaluation=ESEO).order_by('-id').last()
        # serializer = EmployeeSelfEvaluationReviewModelSerializer(ESEO).data
        # rm_app_id=serializer["id"]
        # return rm_app_id
        
        # FIXED:Added null checks to prevent serialization errors
        try:
            ESEO = EmployeeSelfEvaluation.objects.filter(invitation_id=obj).order_by('-id').last()
            if ESEO:
                ESERM = EmployeeSelfEvaluationReviewModel.objects.filter(EmployeeSelfEvaluation=ESEO).order_by('-id').last()
                if ESERM:
                    serializer = EmployeeSelfEvaluationReviewModelSerializer(ESERM).data
                    return serializer.get("id", None)
            return None
        except Exception as e:
            print(f"Error in get_rm_app_id: {str(e)}")
            return None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['EmployeeId'] = instance.EmployeeId.EmployeeId
        representation['employee_name'] = instance.EmployeeId.Name
        if instance.EmployeeId.Position:
            representation['Designation'] = instance.EmployeeId.Position.Name
            representation['Department'] = instance.EmployeeId.Position.Department.Dep_Name
        representation['invited_by'] = instance.invited_by.EmployeeId
        representation['inviter_name'] = instance.invited_by.Name
        representation['ReportingEmployeeId'] = instance.EmployeeId.Reporting_To.EmployeeId
        representation['ReportingEmployeeName'] = instance.EmployeeId.Reporting_To.Name
        representation['RMDesignation'] = instance.EmployeeId.Reporting_To.Position.Name
        representation['RMDepartment'] = instance.EmployeeId.Reporting_To.Position.Department.Dep_Name
        
        return representation



class EmployeeSelfEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model =  EmployeeSelfEvaluation
        fields = '__all__'


class Performance_Metrics_Model_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Performance_Metrics_Model
        fields = '__all__'

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['Emp_info_Id'] = instance.EmployeeSelfEvaluation.invitation_id.EmployeeId.employeeProfile.pk

        return representation


class EmployeeSelfEvaluationReviewModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeSelfEvaluationReviewModel
        fields ='__all__'


class WeekOffDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = WeekOffDay
        fields = ['id', 'day']

class EmployeeWeekoffsSerializer(serializers.ModelSerializer):
    weekoff_days = serializers.PrimaryKeyRelatedField(many=True, queryset=WeekOffDay.objects.all())
    
    class Meta:
        model = EmployeeWeekoffsModel
        fields = "__all__"


class EmployeeWeekoffsModelSerializer(serializers.ModelSerializer):
    weekoff_days = WeekOffDaySerializer(many=True)
    employee_id = serializers.CharField()  # Use CharField for EmployeeId

    class Meta:
        model = EmployeeWeekoffsModel
        fields = ['id', 'employee_id', 'weekoff_days', 'month', 'year']

    def to_internal_value(self, data):
        # Override to handle string EmployeeId and convert it to a related EmployeeDataModel instance
        internal_data = super().to_internal_value(data)
        try:
            employee = EmployeeDataModel.objects.get(EmployeeId=data['employee_id'])
            internal_data['employee_id'] = employee
        except EmployeeDataModel.DoesNotExist:
            raise serializers.ValidationError({'employee_id': 'Employee with this ID does not exist.'})
        return internal_data

    def create(self, validated_data):
        weekoff_days_data = validated_data.pop('weekoff_days')
        employee_weekoffs = EmployeeWeekoffsModel.objects.create(**validated_data)
        for day_data in weekoff_days_data:
            day, created = WeekOffDay.objects.get_or_create(**day_data)
            employee_weekoffs.weekoff_days.add(day)
        return employee_weekoffs

    def update(self, instance, validated_data):
        weekoff_days_data = validated_data.pop('weekoff_days', [])
        instance.month = validated_data.get('month', instance.month)
        instance.year = validated_data.get('year', instance.year)
        instance.save()

        # Update weekoff_days
        if weekoff_days_data:
            instance.weekoff_days.clear()
            for day_data in weekoff_days_data:
                day, created = WeekOffDay.objects.get_or_create(**day_data)
                instance.weekoff_days.add(day)

        return instance
    


class EmployeeShiftsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeShifts_Model
        fields = '__all__'


class Job_Description_Serializer(serializers.ModelSerializer):
    class Meta:
        model = Job_Description_Model
        fields = "__all__"