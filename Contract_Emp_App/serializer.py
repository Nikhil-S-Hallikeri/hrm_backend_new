from .models import *
from HRM_App.models import RequirementAssign
from HRM_App.serializers import *
from rest_framework import serializers

class ClientDocumentsSerializer(serializers.ModelSerializer):
    class Meta:
        model=ClientsDocumentsModel
        fields="__all__"
    
class OurClientSerializer(serializers.ModelSerializer):
    Documents = serializers.SerializerMethodField(read_only= True)
    class Meta:
        model=OurClients
        fields="__all__"

    def get_Documents(self,obj):
        CO = ClientsDocumentsModel.objects.filter(client=obj)
        if CO.exists():
            serializer =  ClientDocumentsSerializer(CO,many=True,context={"request": self.context.get("request")})
            return serializer.data
        else:
            return []

#22/04/2026
class Requirementserializer(serializers.ModelSerializer):
    client_details = serializers.SerializerMethodField(read_only=True)
    total_position_allocated = serializers.SerializerMethodField(read_only=True)
    total_candidate_assigned = serializers.SerializerMethodField(read_only=True)
    total_position_closed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Requirement
        fields = "__all__"

    def get_client_details(self, obj):
        if obj and hasattr(obj, 'client'):
            return OurClientSerializer(obj.client).data
        return None

    def get_total_position_allocated(self, obj):
        from django.db.models import Sum
        allocated = RequirementAssign.objects.filter(requirement=obj).aggregate(total=Sum('position_count'))['total']
        return allocated or 0

    def get_total_candidate_assigned(self, obj):
        from HRM_App.models import NewDailyAchivesModel
        # Counting all 'interview_calls' activities for this requirement across all recruiters
        return NewDailyAchivesModel.objects.filter(assigned_requirement__requirement=obj).count()

    def get_total_position_closed(self, obj):
        from HRM_App.models import NewDailyAchivesModel
        # Counting only 'joined' statuses (case-insensitive)
        return NewDailyAchivesModel.objects.filter(assigned_requirement__requirement=obj, interview_status__iexact='joined').count()

class ClientRequirementAssignSerializer(serializers.ModelSerializer):
    assigned_by = serializers.SerializerMethodField(read_only=True)
    recruiter = serializers.SerializerMethodField(read_only=True)
    candidate_assigned = serializers.SerializerMethodField(read_only=True)
    position_closed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RequirementAssign
        fields = ["id", "requirement", "assigned_by_employee", "assigned_to_recruiter", "position_count", "assigned_on", "assigned_by", "recruiter", "candidate_assigned", "position_closed"]

    def get_candidate_assigned(self, obj):
        from HRM_App.models import NewDailyAchivesModel
        return NewDailyAchivesModel.objects.filter(assigned_requirement=obj).count()

    def get_position_closed(self, obj):
        from HRM_App.models import NewDailyAchivesModel
        return NewDailyAchivesModel.objects.filter(assigned_requirement=obj, interview_status__iexact='joined').count()
    
    def get_assigned_by(self,obj):
        if obj and hasattr(obj, 'assigned_by_employee'):  # Check if the object has the related client
            
            serialized_data = EmployeeDataSerializer(obj.assigned_by_employee).data
            position_obj=obj.assigned_by_employee.Position
            rep_emp_obj=obj.assigned_by_employee.Reporting_To

            serialized_data["Position"]=position_obj.Name if position_obj else None
            serialized_data["Department"]=position_obj.Department.Dep_Name if position_obj.Department else None
            serialized_data["Reporting_To"]= rep_emp_obj.Reporting_To.Name if rep_emp_obj.Reporting_To else None
            serialized_data["Reporting_Emp_Id"]= rep_emp_obj.Reporting_To.EmployeeId if rep_emp_obj.Reporting_To else None

            return serialized_data  # Serialize the related client data
        return None  
    
    def get_recruiter(self,obj):
        if obj and hasattr(obj,'assigned_to_recruiter'):
            serialized_data = EmployeeDataSerializer(obj.assigned_to_recruiter).data
            position_obj=obj.assigned_to_recruiter.Position
            rep_emp_obj=obj.assigned_to_recruiter.Reporting_To

            serialized_data["Position"]=position_obj.Name if position_obj else None
            serialized_data["Department"]=position_obj.Department.Dep_Name if position_obj.Department else None
            serialized_data["Reporting_To"]= rep_emp_obj.Reporting_To.Name if rep_emp_obj.Reporting_To else None
            serialized_data["Reporting_Emp_Id"]= rep_emp_obj.Reporting_To.EmployeeId if rep_emp_obj.Reporting_To else None

            return serialized_data  # Serialize the related client data
        return None  
      
        
    
#18/03/2026
# Phase 2: Client Billing Serializer

class ClientBillingCycleSerializer(serializers.ModelSerializer):
    """
    Serializer for ClientBillingCycle.
    Exposes all billing cycle fields + useful read-only lookup fields
    (candidate name, requirement title, client info) for frontend display.
    """
    candidate_name = serializers.SerializerMethodField(read_only=True)
    requirement_title = serializers.SerializerMethodField(read_only=True)
    client_name = serializers.SerializerMethodField(read_only=True)
    billing_mode = serializers.SerializerMethodField(read_only=True)

    #1/04/2026
    # --- Phase 2: Contract Fields ---
    is_contract_basis = serializers.SerializerMethodField(read_only=True)
    candidate_salary_per_month = serializers.SerializerMethodField(read_only=True)
    net_profit = serializers.ReadOnlyField() # Property from model
    # ---------------------------------

    class Meta:
        model = ClientBillingCycle
        fields = "__all__"

    #1/04/2026
    def get_is_contract_basis(self, obj):
        try:
            return obj.joining_details.is_contract_basis
        except Exception:
            return False

    def get_candidate_salary_per_month(self, obj):
        try:
            return obj.joining_details.candidate_salary
        except Exception:
            return 0

    def get_candidate_name(self, obj):
        try:
            candidate = obj.joining_details.candidate
            if candidate:
                last = candidate.LastName or ""
                return f"{candidate.FirstName} {last}".strip()
        except Exception:
            pass
        return None

    def get_requirement_title(self, obj):
        try:
            return obj.joining_details.requirement.job_title
        except Exception:
            return None

    def get_client_name(self, obj):
        try:
            return obj.joining_details.requirement.client.client_name
        except Exception:
            return None

    def get_billing_mode(self, obj):
        try:
            return obj.joining_details.requirement.billing_model
        except Exception:
            return None
