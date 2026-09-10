from HRM_App.imports import *
from payroll_app.models import *

class AllowanceTypeSerializer(serializers.ModelSerializer):
    # types = serializers.SerializerMethodField()
    class Meta:
        model=AllowanceType
        fields="__all__"

    # def get_types(self,obj):
    #     return obj.type

class SalaryTemplatesSerializer(serializers.ModelSerializer):
    types = AllowanceTypeSerializer(many=True, read_only=True)
    class Meta:
        model=SalaryTemplate
        fields="__all__"

class EmployeeSalaryBreakUpSerializer(serializers.ModelSerializer):
    class Meta:
        model=EmployeeSalaryBreakUp
        fields="__all__"

class EmployeePaySlipsSerializer(serializers.ModelSerializer):
    salary_breakups = EmployeeSalaryBreakUpSerializer()
    class Meta:
        model=EmployeePaySlips
        fields="__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['employee_id'] = instance.employee.EmployeeId
        return representation
            
            
            
            
            
            
            
            
            
            
            
            
            