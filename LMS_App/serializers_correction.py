from rest_framework import serializers
from .models_correction import AttendanceCorrectionRequest
from .models import CompanyAttendanceDataModel
from HRM_App.models import EmployeeDataModel

class AttendanceCorrectionRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source='requested_by.Name', read_only=True)
    attendance_date = serializers.DateField(source='attendance_record.date', read_only=True)
    employee_name = serializers.CharField(source='attendance_record.Emp_Id.Name', read_only=True)
    employee_id = serializers.CharField(source='attendance_record.Emp_Id.EmployeeId', read_only=True)
    
    class Meta:
        model = AttendanceCorrectionRequest
        fields = [
            'id', 
            'attendance_record', 
            'requested_by', 'requested_by_name',
            'previous_status', 
            'requested_status', 
            'reason', 
            'request_status', 
            'approved_by', 
            'approval_reason', 
            'approval_date', 
            'created_at',
            'attendance_date',
            'employee_name',
            'employee_id'
        ]
        read_only_fields = ['request_status', 'approved_by', 'approval_date', 'approval_reason', 'created_at']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Add more readable formats if needed
        return representation
