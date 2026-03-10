from django.db import models
from HRM_App.models import*
from EMS_App.models import ReligionModels

from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

class WeekOffDay(models.Model):
    WEEKDAYS = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]

    day = models.CharField(max_length=10, choices=WEEKDAYS, unique=True)

    def __str__(self):
        return self.day.capitalize()

class EmployeeWeekoffsModel(models.Model):
    employee_id = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='weekoffs')
    weekoff_days = models.ManyToManyField(WeekOffDay, related_name='employees')
    month = models.PositiveIntegerField(default=1)
    year = models.PositiveIntegerField(default=2024)

    def __str__(self) -> str:
        return self.employee_id.employeeProfile.full_name
    
    class Meta: 
        unique_together = ('employee_id','month','year')
    
class CompanyHolidaysDataModel(models.Model):
    OccasionName=models.CharField(max_length=100,blank=True,null=True)
    Religion=models.ForeignKey(ReligionModels,on_delete=models.CASCADE,blank=True,null=True)
    ch=(("Public_Leave","Public_Leave"),("Restricted_Leave","Restricted_Leave"))
    leave_type=models.CharField(max_length=100,null=True,blank=True,choices=ch)
    Date=models.DateField(blank=True,null=True)
    Day=models.CharField(max_length=100,blank=True,null=True)
    state=models.CharField(max_length=100,blank=True,null=True)
    added_By=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    added_on=models.DateTimeField(default=timezone.localtime)
    related_image=models.ImageField(upload_to='holidaysrelated/',blank=True,null=True)

class AvailableRestrictedLeaves(models.Model):
    holiday=models.ForeignKey(CompanyHolidaysDataModel,on_delete=models.CASCADE,blank=True,null=True)
    employee=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    Date=models.DateField(default=timezone.localdate)
    is_expired=models.BooleanField(default=False)
    is_utilised=models.BooleanField(default=False)
    utilised_date=models.DateTimeField(blank=True,null=True)
    is_applied=models.BooleanField(default=False)

    def save(self,*args, **kwargs):
        if self.holiday.pk and self.holiday.Date < timezone.localdate():
            self.is_expired = True
        super().save(*args, **kwargs)

#12/02/2026 - Automatic Attendance Preparation for Payslip Generation
class AttendanceDataPreparationLog(models.Model):
    """
    Tracks which months have had attendance data prepared.
    Prevents redundant preparation runs when generating payslips.
    """
    month = models.IntegerField()
    year = models.IntegerField()
    prepared_at = models.DateTimeField(auto_now_add=True)
    prepared_by = models.CharField(max_length=100, blank=True, null=True, default='auto_payslip_generation')
    record_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ('month', 'year')
        verbose_name = "Attendance Preparation Log"
        verbose_name_plural = "Attendance Preparation Logs"
    
    def __str__(self):
        return f"{self.month}/{self.year} - Prepared on {self.prepared_at.strftime('%Y-%m-%d %H:%M')}"


class LeaveTypesModel(models.Model):
    leave_name=models.CharField(max_length=100,unique=True,blank=True,null=True)
    description=models.TextField(blank=True,null=True)
    added_By=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    added_on=models.DateTimeField(default=timezone.localtime)
    applicable_year=models.DateField(blank=True,null=True)
    def __str__(self):
        return self.leave_name

class LeavesTypeDetailModel(models.Model):
    leave_type=models.ForeignKey(LeaveTypesModel,on_delete=models.CASCADE,blank=True,null=True)
    No_Of_leaves = models.IntegerField(blank=True,null=True)
    carry_forward=models.BooleanField(default=False)
    max_carry_forward=models.IntegerField(blank=True,null=True)
    earned_leave=models.BooleanField(default=False)
    is_restricted=models.BooleanField(default=False)
    emp_type_choices=(("probationer","Probationer"),("confirmed","Confirmed"),("both","Both"))
    applicable_to=models.CharField(max_length=100,choices=emp_type_choices,blank=True,null=True)
    applicable_year=models.DateField(blank=True,null=True)
    is_active=models.BooleanField(default=True)
    def __str__(self):
        return self.leave_type.leave_name
    
@receiver(post_save, sender=LeaveTypesModel)
def create_leave_type_detail(sender, instance, created, **kwargs):
    if created:
        LeavesTypeDetailModel.objects.create(leave_type=instance,applicable_year=timezone.localdate())
    
from datetime import datetime
class EmployeeLeaveTypesEligiblity(models.Model):
    employee = models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,related_name="employee")
    LeaveType=models.ForeignKey(LeavesTypeDetailModel,on_delete=models.CASCADE,blank=True,null=True)
    no_of_leaves= models.IntegerField(blank=True,null=True)
    no_of_leaves_per_month= models.IntegerField(blank=True,null=True)
    Available_leaves=models.IntegerField(blank=True,null=True)
    utilised_leaves=models.IntegerField(default=0,blank=True,null=True)
    added_By=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="addedby")
    added_on=models.DateTimeField(default=timezone.localtime)
    is_active=models.BooleanField(default=True)
    is_details_added=models.BooleanField(default=False)
    is_utilised_in_this_month=models.BooleanField(default=False)

    # restricted_leaves_count = models.IntegerField(blank=True,null=True)

    def save(self, *args, **kwargs):
        if not self.is_details_added and self.LeaveType:
            LTD = LeavesTypeDetailModel.objects.get(id=self.LeaveType.pk)
            if LTD.earned_leave:
                self.no_of_leaves = LTD.No_Of_leaves
                self.no_of_leaves_per_month = int(LTD.No_Of_leaves / 12)
                self.Available_leaves = LTD.No_Of_leaves
                self.is_details_added=True
                self.added_on=timezone.localtime()
        super().save(*args, **kwargs)

        month_objects=MonthWiseLeavesModel.objects.filter(emp_Applicable_LT_Inst__pk=self.pk).exists()

        if not month_objects and self.LeaveType.earned_leave and not self.LeaveType.carry_forward:
            self.create_monthwise_leaves()

    def create_monthwise_leaves(self):
        current_date=timezone.localdate()
        current_year = current_date.year
        current_month = current_date.month

        if self.employee.employeeProfile.hired_date == self.added_on.date():
            start_month = current_month + 1
        else:
            start_month = current_month

        for month in range(start_month, 13):
            MonthWiseLeavesModel.objects.create(
                emp_Applicable_LT_Inst=self,
                month=month,
                year=current_date,
                leaves_count_per_month=self.no_of_leaves_per_month,
                created_at=timezone.localtime()
            )

    def __str__(self):
        return f"{self.employee.EmployeeId} - {self.LeaveType.leave_type.leave_name} - {self.LeaveType.applicable_year}"

class MonthWiseLeavesModel(models.Model):
    emp_Applicable_LT_Inst=models.ForeignKey(EmployeeLeaveTypesEligiblity,on_delete=models.CASCADE,blank=True,null=True)
    month=models.IntegerField()
    year=models.DateField(blank=True,null=True)
    leaves_count_per_month=models.IntegerField(blank=True,null=True)
    created_at=models.DateField(default=timezone.localtime,blank=True,null=True)

    def save(self, *args, **kwargs):

        current_date = timezone.localdate()
        month = current_date.month
        year = current_date.year

        hire_date = self.emp_Applicable_LT_Inst.employee.employeeProfile.hired_date
        hire_month = hire_date.month
        hire_year = hire_date.year
      
        # Check if the current year and month is within the first month after hiring
        if self.year.year == year and self.month == hire_month and (current_date - hire_date).days <= 30:
            self.leaves_count_per_month = 0
        #     pass  # Don't set leaves_count_per_month to 0
        # elif self.month < month and self.year.year == year:
        #     self.leaves_count_per_month = 0

        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.emp_Applicable_LT_Inst.pk} month-{self.month}/{self.year.year}'



class LeaveRequestForm(models.Model):
    SESSION_CHOICES = [('AM', 'AM'),('PM', 'PM'),('FULL', 'Full Day')]
    employee =models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE)
    LeaveType=models.ForeignKey(EmployeeLeaveTypesEligiblity,on_delete=models.CASCADE,blank=True,null=True)

    restricted_leave_type=models.ForeignKey(AvailableRestrictedLeaves,on_delete=models.CASCADE,blank=True,null=True)

    from_date = models.DateField(blank=True,null=True)
    from_session = models.CharField(max_length=10, choices=SESSION_CHOICES,blank=True, null=True)
    to_date = models.DateField(blank=True,null=True)
    to_session = models.CharField(max_length=10, choices=SESSION_CHOICES,blank=True, null=True)
    days = models.IntegerField(blank=True,null=True)
    report_to=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True, null=True,related_name="reporting_manager")
    reason = models.TextField(blank=True, null=True)
    Document=models.FileField(upload_to='Leave_Profs/',blank=True,null=True)

    Leave_Withdrawn=models.BooleanField(default=False)
    Withdrawn_Date=models.DateTimeField(blank=True,null=True)
    Approved_Status=(("approved","Approved"),("rejected","Rejected"))
    is_approved_by_rm=models.BooleanField(default=False)
    rm_status=models.CharField(max_length=10, blank=True,null=True,choices=Approved_Status)
    rm_approved_date=models.DateTimeField(blank=True,null=True)

    is_approved_by_hr=models.BooleanField(default=False)
    hr_status=models.CharField(max_length=10, blank=True,null=True,choices=Approved_Status)
    hr_approved_date=models.DateTimeField(blank=True,null=True)

    Approved_Status=(("approved","Approved"),("rejected","Rejected"),("canceled","Canceled"),("pending","Pending"))
    approved_status=models.CharField(max_length=10, blank=True,null=True,choices=Approved_Status)
    hr_reason=models.TextField(blank=True,null=True)
    rm_reason = models.TextField(blank=True, null=True)
    approved_date=models.DateTimeField(blank=True, null=True)
    approved_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="Approver")
    applied_date=models.DateTimeField(default=timezone.localtime,blank=True, null=True)

    def __str__(self):
        return f"{self.employee.EmployeeId}"
    
class EmployeesLeavesmodel(models.Model):
    leave_request=models.ForeignKey(LeaveRequestForm,on_delete=models.CASCADE,null=True,blank=True)
    eligible_leave_obj=models.ForeignKey(EmployeeLeaveTypesEligiblity,on_delete=models.CASCADE,null=True,blank=True)
    leave_date=models.DateField(null=True,blank=True)
    leave_type=models.CharField(max_length=100,null=True,blank=True)
    fall_under=models.CharField(max_length=100,null=True,blank=True)
   

#////////////////////////////////////**************************////////////////////////////////////////
#///////////////////////////////////........Attendance........///////////////////////////////////////

class CompanyAttendanceDataModel(models.Model):
    Emp_Id=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE)
    date=models.DateField(blank=True,null=True)
    Day=models.CharField(max_length=100,blank=True,null=True)
    Shift=models.ForeignKey(EmployeeShifts_Model,on_delete=models.CASCADE,blank=True,null=True)
    InTime=models.TimeField(blank=True,null=True)
    LunchIn=models.TimeField(blank=True,null=True)
    LunchOut=models.TimeField(blank=True,null=True)
    OutTime=models.TimeField(blank=True,null=True)
    Hours_Worked=models.TimeField(blank=True,null=True)
    # Over_Time=models.TimeField(blank=True,null=True)
    TotalWorkingHours=models.TimeField(blank=True,null=True)
    Late_Arrivals=models.TimeField(blank=True,null=True)
    Early_Depature=models.TimeField(blank=True,null=True)

    leave_info=(("No_attention_required","No_attention_required"),("Attention_required","Attention_required"),("Authorized_Absent","Authorized_Absent"),("Unauthorized_Absent","Unauthorized_Absent"))
    leave_information=models.CharField(max_length=100,blank=True,null=True,choices=leave_info)
    
    break_timings=models.TimeField(blank=True,null=True)
    remarks=models.TextField(blank=True,null=True)
    ch=(("present","Present"),("absent","Absent"),("half_day","Half Day"),("week_off"," Week off"),('restricted_leave','Restricted Leave'),("public_leave","Public Leave"))
    Status=models.CharField(max_length=100,blank=True,null=True,choices=ch)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['Emp_Id', 'date'], name='unique_employee_attendance')
        ]
    
    def save(self, *args, **kwargs):
        #09/02/2026
        # Extract force_recalculate flag before passing to super().save()
        force_recalculate = kwargs.pop('force_recalculate', False)
        
        # Only calculate if Status is NULL (not yet calculated) OR force_recalculate is True
        if self.Status is None or force_recalculate:
            self.calculate_attendance_fields()
            
        if not self.remarks:
            self.remarks = self.leave_information or ""
        super().save(*args, **kwargs)



    # #09/02/2026
    # def calculate_attendance_fields(self):
    #     """Calculate all derived attendance fields from punch records"""
    #     from datetime import datetime, timedelta, time as dt_time
    #     import calendar
        
    #     # Skip calculation if record hasn't been saved yet (no primary key)
    #     # This prevents "instance needs to have a primary key" error
    #     if not self.pk:
    #         return
        
    #     # Get all punch records for this attendance
    #     punches = list(self.companyattendance_set.all().order_by('ScanTimings'))
        
    #     if not punches:
    #         # No punches - determine status without punch data
    #         self.determine_status_without_punches()
    #         return
        
    #     # 1. Calculate InTime and OutTime
    #     self.InTime = punches[0].ScanTimings  # First punch
    #     self.OutTime = punches[-1].ScanTimings  # Last punch
        
    #     # 2. Calculate total duration and breaks
    #     total_duration = timedelta()
    #     break_duration = timedelta()
        
    #     # Calculate working hours (pair IN-OUT punches)
    #     for i in range(1, len(punches), 2):
    #         try:
    #             in_time = punches[i - 1].ScanTimings
    #             out_time = punches[i].ScanTimings
                
    #             dt_in = datetime.combine(datetime.today(), in_time)
    #             dt_out = datetime.combine(datetime.today(), out_time)
                
    #             # Handle overnight shifts
    #             if dt_out < dt_in:
    #                 dt_out += timedelta(days=1)
                
    #             total_duration += dt_out - dt_in
    #         except (IndexError, AttributeError):
    #             continue
        
    #     # Calculate breaks (OUT to next IN) and identify lunch break
    #     breaks_list = []  # Store (break_duration, out_time, in_time) tuples
        
    #     for i in range(1, len(punches) - 1, 2):
    #         try:
    #             out_time = punches[i].ScanTimings
    #             next_in_time = punches[i + 1].ScanTimings
                
    #             dt_out = datetime.combine(datetime.today(), out_time)
    #             dt_in = datetime.combine(datetime.today(), next_in_time)
                
    #             if dt_in < dt_out:
    #                 dt_in += timedelta(days=1)
                
    #             current_break = dt_in - dt_out
    #             break_duration += current_break
                
    #             # Store break info for lunch identification
    #             breaks_list.append((current_break, out_time, next_in_time))
    #         except (IndexError, AttributeError):
    #             continue
        
    #     # 2.5. Identify LunchOut and LunchIn (longest break is assumed to be lunch)
    #     if breaks_list:
    #         # Find the longest break
    #         longest_break = max(breaks_list, key=lambda x: x[0])
    #         self.LunchOut = longest_break[1]  # Time when lunch started
    #         self.LunchIn = longest_break[2]   # Time when returned from lunch
        
    #     # 3. Set Hours_Worked and break_timings as TimeField
    #     # Convert timedelta to time (hours:minutes:seconds)
    #     total_seconds = int(total_duration.total_seconds())
    #     hours_worked_time = (datetime.min + timedelta(seconds=total_seconds)).time()
    #     self.Hours_Worked = hours_worked_time
        
    #     break_seconds = int(break_duration.total_seconds())
    #     if break_seconds > 0:
    #         break_time = (datetime.min + timedelta(seconds=break_seconds)).time()
    #         self.break_timings = break_time
        
    #     # 4. Calculate TotalWorkingHours (InTime to OutTime)
    #     if self.InTime and self.OutTime:
    #         dt_in = datetime.combine(datetime.today(), self.InTime)
    #         dt_out = datetime.combine(datetime.today(), self.OutTime)
    #         if dt_out < dt_in:
    #             dt_out += timedelta(days=1)
    #         total_time = dt_out - dt_in
    #         total_time_seconds = int(total_time.total_seconds())
    #         self.TotalWorkingHours = (datetime.min + timedelta(seconds=total_time_seconds)).time()
        
    #     # 5. Determine Status based on working hours
    #     hours_worked = total_duration.total_seconds() / 3600  # Convert to hours
        
    #     if hours_worked >= 8:  # Full day threshold
    #         self.Status = "present"
    #     elif hours_worked >= 4:  # Half day threshold
    #         self.Status = "half_day"
    #     elif hours_worked > 0:
    #         self.Status = "less_than_half_day"
    #     else:
    #         self.Status = "absent"
        
    #     # 6. Calculate Late Arrivals
    #     if self.Shift and self.Shift.start_shift and self.InTime:
    #         shift_start = datetime.combine(datetime.today(), self.Shift.start_shift)
    #         actual_in = datetime.combine(datetime.today(), self.InTime)
            
    #         if actual_in > shift_start:
    #             late_duration = actual_in - shift_start
    #             late_seconds = int(late_duration.total_seconds())
    #             self.Late_Arrivals = (datetime.min + timedelta(seconds=late_seconds)).time()
        
    #     # 7. Calculate Early Departure
    #     if self.Shift and self.Shift.end_shift and self.OutTime:
    #         shift_end = datetime.combine(datetime.today(), self.Shift.end_shift)
    #         actual_out = datetime.combine(datetime.today(), self.OutTime)
            
    #         if actual_out < shift_end:
    #             early_duration = shift_end - actual_out
    #             early_seconds = int(early_duration.total_seconds())
    #             self.Early_Depature = (datetime.min + timedelta(seconds=early_seconds)).time()
        
    #     # 8. Set Day name if not already set
    #     if not self.Day and self.date:
    #         self.Day = self.date.strftime("%A")

    
    #09/02/2026
    def calculate_attendance_fields(self):
        """Calculate all derived attendance fields from punch records"""
        from datetime import datetime, timedelta, time as dt_time
        import calendar
        
        # Skip calculation if record hasn't been saved yet (no primary key)
        # This prevents "instance needs to have a primary key" error
        if not self.pk:
            return
        
        # Get all punch records for this attendance
        punches = list(self.companyattendance_set.all().order_by('ScanTimings'))
        
        if not punches:
            # No punches - determine status without punch data
            self.determine_status_without_punches()
            return
        
        # 1. Calculate InTime and OutTime
        self.InTime = punches[0].ScanTimings  # First punch
        
        # If there is only one punch, OutTime should be None.
        # This prevents "Early Departure" from calculating 8+ hours when someone just arrived.
        if len(punches) > 1:
            self.OutTime = punches[-1].ScanTimings
        else:
            self.OutTime = None
        
        # 2. Calculate total duration and breaks
        total_duration = timedelta()
        break_duration = timedelta()
        
        # Calculate working hours (pair IN-OUT punches)
        for i in range(1, len(punches), 2):
            try:
                in_time = punches[i - 1].ScanTimings
                out_time = punches[i].ScanTimings
                
                dt_in = datetime.combine(datetime.today(), in_time)
                dt_out = datetime.combine(datetime.today(), out_time)
                
                # Handle overnight shifts
                if dt_out < dt_in:
                    dt_out += timedelta(days=1)
                
                total_duration += dt_out - dt_in
            except (IndexError, AttributeError):
                continue
        
        # Calculate breaks (OUT to next IN) and identify lunch break
        breaks_list = []  # Store (break_duration, out_time, in_time) tuples
        
        for i in range(1, len(punches) - 1, 2):
            try:
                out_time = punches[i].ScanTimings
                next_in_time = punches[i + 1].ScanTimings
                
                dt_out = datetime.combine(datetime.today(), out_time)
                dt_in = datetime.combine(datetime.today(), next_in_time)
                
                if dt_in < dt_out:
                    dt_in += timedelta(days=1)
                
                current_break = dt_in - dt_out
                break_duration += current_break
                
                # Store break info for lunch identification
                breaks_list.append((current_break, out_time, next_in_time))
            except (IndexError, AttributeError):
                continue
        
        # 2.5. Identify LunchOut and LunchIn (longest break is assumed to be lunch)
        if breaks_list:
            # Find the longest break
            longest_break = max(breaks_list, key=lambda x: x[0])
            self.LunchOut = longest_break[1]  # Time when lunch started
            self.LunchIn = longest_break[2]   # Time when returned from lunch
        
        # 3. Set Hours_Worked and break_timings as TimeField
        # Convert timedelta to time (hours:minutes:seconds)
        total_seconds = int(total_duration.total_seconds())
        hours_worked_time = (datetime.min + timedelta(seconds=total_seconds)).time()
        self.Hours_Worked = hours_worked_time
        
        break_seconds = int(break_duration.total_seconds())
        if break_seconds > 0:
            break_time = (datetime.min + timedelta(seconds=break_seconds)).time()
            self.break_timings = break_time
        
        # 4. Calculate TotalWorkingHours (InTime to OutTime)
        if self.InTime and self.OutTime:
            dt_in = datetime.combine(datetime.today(), self.InTime)
            dt_out = datetime.combine(datetime.today(), self.OutTime)
            if dt_out < dt_in:
                dt_out += timedelta(days=1)
            total_time = dt_out - dt_in
            total_time_seconds = int(total_time.total_seconds())
            self.TotalWorkingHours = (datetime.min + timedelta(seconds=total_time_seconds)).time()
        
        # 5. Determine Status based on working hours
        hours_worked = total_duration.total_seconds() / 3600  # Convert to hours
        
        if hours_worked >= 8:  # Full day threshold (Changed from 6 to 8 as per traditional logic)
            self.Status = "present"
        elif hours_worked >= 4:  # Half day threshold
            self.Status = "half_day"
        elif hours_worked > 0:
            self.Status = "less_than_half_day"
        else:
            self.Status = "absent"
        
        # 6. Calculate Late Arrivals
        self.Late_Arrivals = None
        if self.Shift and self.Shift.start_shift and self.InTime:
            # shift_start = datetime.combine(datetime.today(), self.Shift.start_shift)
            # actual_in = datetime.combine(datetime.today(), self.InTime)
            # Senior Dev Fix: Use self.date instead of datetime.today() for consistency
            shift_start = datetime.combine(self.date, self.Shift.start_shift)
            actual_in = datetime.combine(self.date, self.InTime)
            
            if actual_in > shift_start:
                late_duration = actual_in - shift_start
                late_seconds = int(late_duration.total_seconds())
                self.Late_Arrivals = (datetime.min + timedelta(seconds=late_seconds)).time()
        
        # 7. Calculate Early Departure
        self.Early_Depature = None
        if self.Shift and self.Shift.end_shift and self.OutTime:
            # shift_end = datetime.combine(datetime.today(), self.Shift.end_shift)
            # actual_out = datetime.combine(datetime.today(), self.OutTime)
            # Use self.date for reference. 
            # For overnight shifts, we'd need more complex logic, but this is safer than today().
            shift_end = datetime.combine(self.date, self.Shift.end_shift)
            actual_out = datetime.combine(self.date, self.OutTime)
            
            # Handle overnight end_shift (if end < start, it's next day)
            if self.Shift.start_shift and self.Shift.end_shift < self.Shift.start_shift:
                shift_end += timedelta(days=1)
                
            # If actual_out is also potentially next day (if < InTime), handled by model save logic usually
            # But here let's be safe:
            if self.InTime and actual_out.time() < self.InTime:
                actual_out += timedelta(days=1)

            # Don't flag early departure for TODAY until the shift has actually ended.
            # This prevents premature "Early Departure" tags while someone is just on a lunch break.
            is_past_date = self.date < timezone.localdate()
            shift_has_ended = timezone.localtime() > timezone.make_aware(shift_end)

            # if actual_out < shift_end:
            if actual_out < shift_end and (is_past_date or shift_has_ended):
                early_duration = shift_end - actual_out
                early_seconds = int(early_duration.total_seconds())
                self.Early_Depature = (datetime.min + timedelta(seconds=early_seconds)).time()
        
        # 8. Set Day name if not already set
        if not self.Day and self.date:
            self.Day = self.date.strftime("%A")
    
    def determine_status_without_punches(self):
        """Determine status when no punch records exist"""
        import calendar
        
        if not self.date:
            return
        
        # Set Day name
        if not self.Day:
            self.Day = self.date.strftime("%A")
        
        # Check if it's a week off day
        try:
            emp_weekoff_config = EmployeeWeekoffsModel.objects.filter(
                employee_id=self.Emp_Id,
                month=self.date.month,
                year=self.date.year
            ).first()
            
            weekoff_days = []
            if emp_weekoff_config:
                weekoff_days = [d.day.lower() for d in emp_weekoff_config.weekoff_days.all()]
            else:
                weekoff_days = ['sunday']  # Default
            
            day_name = self.date.strftime("%A").lower()
            if day_name in weekoff_days:
                self.Status = "week_off"
                return
        except Exception:
            pass
        
        # Check if it's a public holiday
        try:
            holiday = CompanyHolidaysDataModel.objects.filter(
                Date=self.date,
                leave_type="Public_Leave"
            ).first()
            
            if holiday:
                self.Status = "public_leave"
                return
        except Exception:
            pass
        
        # Otherwise, mark as absent
        self.Status = "absent"
        self.leave_information = ""
    
    def __str__(self):
        return f"{self.Emp_Id.EmployeeId} --> {self.date}"

class CompanyAttendance(models.Model):
    Attendance=models.ForeignKey(CompanyAttendanceDataModel,on_delete=models.CASCADE)
    ScanTimings=models.TimeField()
    ScanType=models.BooleanField(blank=True,null=True)
    Created_Date=models.DateTimeField(default=timezone.localtime,blank=True,null=True)
	
    def save(self, *args, **kwargs):
        if self.ScanType is None:  # Only apply logic if ScanType is not manually set
            last_entry = CompanyAttendance.objects.filter(
                Attendance=self.Attendance
            ).order_by('-id').first()

            if last_entry:
                self.ScanType = not last_entry.ScanType  # Toggle the last ScanType
            else:
                self.ScanType = True  # First entry should be True

        super().save(*args, **kwargs)
        
#09/02/2026
# Signal to recalculate attendance fields when punch records are added
@receiver(post_save, sender=CompanyAttendance)
def recalculate_attendance_on_punch_save(sender, instance, created, **kwargs):
    """
    Recalculate parent attendance fields when a new punch is added.
    This handles the case where attendance record is created before punches.
    """
    if created:  # Only on new punch creation, not updates
        try:
            attendance = instance.Attendance
            # Force recalculation since new punch was added
            attendance.save(force_recalculate=True)
        except Exception as e:
            # Log error but don't break the save operation
            logger = logging.getLogger(__name__)
            logger.error(f"Error recalculating attendance on punch save: {e}")

#10/02/2026
# Signal to recalculate attendance when public holidays are added
@receiver(post_save, sender=CompanyHolidaysDataModel)
def recalculate_attendance_on_holiday_save(sender, instance, created, **kwargs):
    """
    Automatically recalculate attendance records when admin declares a new public holiday.
    This ensures all employees get Status = "public_leave" for the holiday date.
    """
    if created and instance.leave_type == "Public_Leave":
        try:
            # Find all attendance records for this holiday date
            records = CompanyAttendanceDataModel.objects.filter(date=instance.Date)
            
            if records.exists():
                logger = logging.getLogger(__name__)
                logger.info(f"Recalculating {records.count()} attendance records for holiday: {instance.Date}")
                
                for record in records:
                    # Force recalculation to update status to "public_leave"
                    record.save(force_recalculate=True)
                
                logger.info(f"Successfully updated attendance for holiday: {instance.Date}")
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error recalculating attendance on holiday save: {e}")
        
#.........................Performance Management.............................#

from django.core.validators import MaxValueValidator, MinValueValidator

def AppraisalInvitation_Id():
    return "ABC"+str(uuid.uuid4().hex)[:7].upper()

class AppraisalInvitationModel(models.Model):
    EmployeeId=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE)
    InvitationId=models.CharField(max_length=100,default=AppraisalInvitation_Id)
    invitation_reason=models.TextField(blank=True,null=True)
    strat_date=models.DateField(blank=True,null=True)
    end_date=models.DateField(blank=True,null=True)
    is_filled=models.BooleanField(default=False)
    filled_on=models.DateTimeField(blank=True,null=True)
    is_rm_filled=models.BooleanField(default=False)
    rm_filled_on=models.DateTimeField(blank=True,null=True)
    invited_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,related_name="invitation")
    invited_on=models.DateTimeField(blank=True,null=True)
    active_status = models.BooleanField(default=True)
    meeting_mail_sent_status=models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.localtime)
    
class EmployeeSelfEvaluation(models.Model):
    invitation_id=models.ForeignKey(AppraisalInvitationModel ,on_delete=models.CASCADE,blank=True,null=True)
    # Employee_ID=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE)
    REVIEW_PERIOD = models.CharField(max_length=255,blank=True,null=True)
    DATE_OF_REVIEW = models.DateField(blank=True,null=True)
    # Rating fields
    works_to_full_potential = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    quality_of_work = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    work_consistency = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    communication = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    independent_work = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    takes_initiative = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    group_work = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    productivity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    creativity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    honesty = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    integrity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    coworker_relations = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    client_relations = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    technical_skills = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    dependability = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    punctuality = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    attendance = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    overall=models.IntegerField(blank=True,null=True)
    # Current responsibilities
    key_responsibilities = models.TextField(blank=True,null=True)
    performance_assessment_responsibilities = models.TextField(blank=True,null=True)
    # Performance goals
    performance_and_work_objectives = models.TextField(blank=True,null=True)
    performance_assessment_objectives = models.TextField(blank=True,null=True)
    # Core values
    core_values_assessment = models.TextField(blank=True,null=True)
    # Employee signature
    employee_signature = models.ImageField(upload_to="EmployeeDocuments/appraisal_signature/",blank=True)
    created_at = models.DateTimeField(default=timezone.localtime)

    def __str__(self):
        return f"{self.invitation_id.EmployeeId} - {self.REVIEW_PERIOD}"
    
class EmployeeSelfEvaluationReviewModel(models.Model):
    EmployeeSelfEvaluation=models.ForeignKey(EmployeeSelfEvaluation,on_delete=models.CASCADE,related_name='apprasial_review',blank=True,null=True)
    DateOfCurrentReview=models.DateField(blank=True,null=True)
    DateOfLastReview=models.DateField(blank=True,null=True)
    Reviewer_Name=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    Reviewer_Title=models.CharField(max_length=100,blank=True,null=True)
    assigning_person = models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,related_name='assigning_person',blank=True,null=True)
    # CHARACTERISTICS
    works_to_full_potential = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    quality_of_work = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    work_consistency = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    communication = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    independent_work = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    takes_initiative = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    group_work = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    productivity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    creativity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    honesty = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    integrity = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    coworker_relations = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    client_relations = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    technical_skills = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    dependability = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    punctuality = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    attendance = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(10)],blank=True,null=True)
    overall=models.IntegerField(blank=True,null=True)
    # GOALS
    # Were previously set goals achieved?
    Were_previously_set_goals_achieved=models.TextField(blank=True,null=True)
    Goals_for_next_review_period=models.TextField(blank=True,null=True)
    COMMENTS_AND_APPROVAL=models.TextField(blank=True,null=True)
    submitted_Date=models.DateTimeField(default=timezone.localtime)

class Performance_Metrics_Model(models.Model):
    ch = [("Excellent", "Excellent"), ("Verygood", "Verygood"),("Good", "Good"),("Fair", "Fair"),("Poor", "Poor")]
    EmployeeSelfEvaluation = models.ForeignKey(EmployeeSelfEvaluation, on_delete=models.CASCADE, blank=True, null=True)
    # Metric_Name = models.CharField(max_length=100, blank=True, null=True)
    # Description = models.TextField()
    # Target_Goal = models.TextField()
    Performance_Achived = models.CharField(max_length=100, blank=True, null=True, choices=ch)
    # Achived_Date = models.DateField(blank=True, null=True)
    Performance_Rating = models.IntegerField(blank=True, null=True)
    Comments_Feedback = models.TextField(blank=True, null=True)
    Goals_for_Next_Period = models.TextField(blank=True, null=True)
    Strengths = models.TextField(blank=True, null=True)  # Additional
    Areas_for_Improvement = models.TextField(blank=True, null=True)  # Additional
    Potential_Development_Opportunities = models.TextField(blank=True, null=True)  # Additional
    Responsible_Parties = models.CharField(max_length=100, blank=True, null=True)  # Additional
    # Review_and_Follow_Up = models.DateField(blank=True, null=True)  # Additional
    Meeting_Date=models.DateTimeField(blank=True,null=True)
    Meeting_reviewed_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    created_at = models.DateTimeField(default=timezone.localtime)



#6/01/2026
class Job_Description_Model(models.Model):
    Experience = models.CharField(max_length=100, blank=True, null=True)
    Job_Discription = models.TextField(blank=True, null=True)
    Qualification = models.CharField(max_length=255, blank=True, null=True)
    Title = models.CharField(max_length=255, blank=True, null=True)
    company_inrto = models.TextField(blank=True, null=True)
    department_id = models.CharField(max_length=100, blank=True, null=True)
    department_name = models.CharField(max_length=255, blank=True, null=True)
    designation_id = models.CharField(max_length=100, blank=True, null=True)
    designation_name = models.CharField(max_length=255, blank=True, null=True)
    expertise_points = models.JSONField(default=list, blank=True, null=True)
    job_location = models.CharField(max_length=255, blank=True, null=True)
    job_type = models.CharField(max_length=100, blank=True, null=True)
    key_skills = models.JSONField(default=list, blank=True, null=True)
    max_salary = models.CharField(max_length=100, blank=True, null=True)
    min_exp = models.CharField(max_length=100, blank=True, null=True)
    min_salary = models.CharField(max_length=100, blank=True, null=True)
    points = models.JSONField(default=list, blank=True, null=True)
    role = models.CharField(max_length=255, blank=True, null=True)
    salary_type = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    posted_on = models.DateTimeField(auto_now_add=True)
    slug = models.SlugField(max_length=500, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            date_str = timezone.localdate().strftime('%Y-%m-%d')
            # Fallback if fields are missing, though they shouldn't be
            role = self.role or "job"
            company = self.company_inrto or "company"
            base_slug = f"{role}-{company}-{date_str}"
            self.slug = slugify(base_slug)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.Title} - {self.designation_name}"
from .models_correction import *
