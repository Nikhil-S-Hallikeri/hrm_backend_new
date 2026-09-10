from django.db import models
from django.utils import timezone
# Removed: from HRM_App.models import EmployeeDataModel

class AttendanceCorrectionRequest(models.Model):
    # Use string references for ALL ForeignKeys to avoid circular imports
    attendance_record = models.ForeignKey('LMS_App.CompanyAttendanceDataModel', on_delete=models.CASCADE, related_name="correction_requests")
    requested_by = models.ForeignKey('HRM_App.EmployeeDataModel', on_delete=models.CASCADE, related_name="correction_requests_made")
    
    # The change being requested
    PREVIOUS_STATUS_CHOICES = (
        ("present","Present"),
        ("absent","Absent"),
        ("half_day","Half Day"),
        ("week_off"," Week off"),
        ('restricted_leave','Restricted Leave'),
        ("public_leave","Public Leave"),
        ("less_than_half_day", "Less Than Half Day") 
    )
    
    previous_status = models.CharField(max_length=50, blank=True, null=True, choices=PREVIOUS_STATUS_CHOICES)
    requested_status = models.CharField(max_length=50, choices=PREVIOUS_STATUS_CHOICES)
    
    reason = models.TextField()
    
    # Approval Flow
    STATUS_CHOICES = (("Pending", "Pending"), ("Approved", "Approved"), ("Rejected", "Rejected"))
    request_status = models.CharField(max_length=20, default="Pending", choices=STATUS_CHOICES)
    
    approved_by = models.ForeignKey('HRM_App.EmployeeDataModel', on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_corrections")
    approval_reason = models.TextField(blank=True, null=True) # Admin's comment
    approval_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(default=timezone.localtime)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Note: str() might fail if accessing related fields that aren't loaded, 
        # but for now we trust Django to handle the lazy loading or we'll simplify str later.
        # Ideally we shouldn't access related fields in __str__ if it risks db hits, 
        # but here we need it for admin visibility.
        return f"Correction for {self.attendance_record_id} - {self.request_status}"
