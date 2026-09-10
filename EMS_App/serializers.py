
from rest_framework import serializers
from EMS_App.models import *

from rest_framework import serializers
from .models import *


    # def create(self, validated_data):
    #     employees_data = validated_data.pop('employees')
    #     employees = [EmployeeInformation.objects.create(**item) for item in employees_data]
    #     return employees    

class EmployeeEducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeEducation
        fields = '__all__'

class FamilyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FamilyDetails
        fields = '__all__'


class EmergencyDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyDetails
        fields = '__all__'

class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = '__all__'

class CandidateReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateReference
        fields = '__all__'

class ExceperienceModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExceperienceModel
        fields = '__all__'

class Last_Position_HeldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Last_Position_Held
        fields = '__all__'

class ReligionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReligionModels
        fields = '__all__'

class EmployeePersonalInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeePersonalInformation
        fields = '__all__'

class EmployeeIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeIdentity
        fields = '__all__'

class BankAccountDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccountDetails
        fields = '__all__'

class PFDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PFDetails
        fields = '__all__'

class AditionalInformationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AditionalInformationModel
        fields = '__all__'

class AttachmentsModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttachmentsModel
        fields = '__all__'


class Documents_SubmitedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documents_Submited
        fields = '__all__'

class DeclarationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Declaration
        fields = '__all__'

# .....................................................

class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDataModel
        fields = ["id","designation","EmployeeId"]


class CompanyEmployeesPositionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyEmployeesPositionHistory
        fields = "__all__"

class CompanyPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyPolicy
        fields = "__all__"


class CompanyMassMailsSendedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyMassMailsSendedModel
        fields = "__all__"
        
class ResignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResignationModel 
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # OLD: crashed with AttributeError if any FK was null
        # representation['employee_id'] = instance.employee_id.EmployeeId
        # representation['reporting_manager_name'] = instance.reporting_manager_name.EmployeeId
        # representation['HR_manager_name'] = instance.HR_manager_name.EmployeeId

        # NEW: safely handle null FK fields
        representation['employee_id'] = instance.employee_id.EmployeeId if instance.employee_id else None
        representation['reporting_manager_name'] = instance.reporting_manager_name.EmployeeId if instance.reporting_manager_name else None
        representation['HR_manager_name'] = instance.HR_manager_name.EmployeeId if instance.HR_manager_name else None

        # Expose Interviewer as EmployeeId (string) so frontend dropdown can match by EmployeeId
        # OLD: returned numeric PK (e.g. 95) which didn't match any dropdown option value
        representation['Interviewer'] = instance.Interviewer.EmployeeId if instance.Interviewer else None

        return representation


class ReportingToResignationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResignationModel 
        fields = ["id","name","position","reason","resigned_letter_file","employee_id","reporting_manager_name","emp_id"]

    employee_id=serializers.SerializerMethodField()
    emp_id=serializers.SerializerMethodField()
    reporting_manager_name =serializers.SerializerMethodField()

    def get_employee_id(self,obj):
        return obj.employee_id.EmployeeId if obj.employee_id else None
    
    def get_reporting_manager_name(self,obj):
        return obj.reporting_manager_name.EmployeeId if obj.reporting_manager_name else None
    
    def get_emp_id(self,obj):
        return obj.employee_id.pk

    
class ExitDetailsSerializer(serializers.ModelSerializer):
    resignation=ResignationSerializer()
    class Meta:
        model = ExitDetailsModel
        fields = "__all__"

class ClearenceSerializer(serializers.ModelSerializer):
    # resignation=ResignationSerializer()
    class Meta:
        model = AssetsClearance
        fields = "__all__"

class HandOverSerializer(serializers.ModelSerializer):
    class Meta:
        model = HandoversDetails
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Expose names for FK fields
        if instance.handover_to:
            representation['handover_to_name'] = instance.handover_to.Name
            representation['handover_to_emp_id'] = instance.handover_to.EmployeeId
        else:
            representation['handover_to_name'] = "Not Assigned"
            representation['handover_to_emp_id'] = None
            
        return representation


