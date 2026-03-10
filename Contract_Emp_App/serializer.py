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

class Requirementserializer(serializers.ModelSerializer):
    client_details=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model=Requirement
        fields="__all__"

    def get_client_details(self, obj):
        if obj and hasattr(obj, 'client'):  # Check if the object has the related client
            return OurClientSerializer(obj.client).data  # Serialize the related client data
        return None  # Return None if there is no related client
    
class ClientRequirementAssignSerializer(serializers.ModelSerializer):
    assigned_by=serializers.SerializerMethodField(read_only=True)
    recruiter=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model=RequirementAssign
        fields="__all__"
    
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
      
        
    
