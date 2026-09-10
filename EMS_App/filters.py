from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from HRM_App.models import *
from .models import *
from HRM_App.serializers import *
from .serializers import *
from payroll_app.models import EmployeeSalaryBreakUp
from payroll_app.serializer import EmployeeSalaryBreakUpSerializer
from django.db.models.functions import Lower

today = timezone.now().date()
from datetime import datetime

def currentexperience(exp_data,exp_type,cur_years_exp=0,cur_months_exp=0):

    if exp_type == "cur_exp":
        
        hired_date=exp_data.employeeProfile.hired_date

        years_of_experience = today.year - hired_date.year
        months_of_experience = today.month - hired_date.month
                    # If the months are negative, adjust the year and month calculations
        if months_of_experience < 0:
            years_of_experience -= 1
            months_of_experience += 12

        if years_of_experience > 1 :
            if months_of_experience>1:
                current_exp=f"{years_of_experience}Years {months_of_experience}Months"
            else:
                current_exp=f"{years_of_experience}Years {months_of_experience}Month"
        else:
            if months_of_experience > 1:
                current_exp=f"{years_of_experience}Year {months_of_experience}Months"
            else:
                current_exp=f"{years_of_experience}Year {months_of_experience}Month"
    
        return {"current_exp":current_exp,"years":years_of_experience,"months":months_of_experience}
    
    else:
        

        Total_Experience_Years= int(cur_years_exp)
        Total_Experience_Months = int(cur_months_exp)

        for exp in exp_data:
                # Convert string dates to datetime.date objects
                fd = datetime.strptime(exp["from_date"], "%Y-%m-%d").date()  # Assuming the format is 'YYYY-MM-DD'
                td = datetime.strptime(exp["to_date"], "%Y-%m-%d").date()    # Same assumption for 'to_date'
                
                years = td.year - fd.year
                months = td.month - fd.month

                if months < 0:
                    years -= 1
                    months += 12

                # Accumulate total years and months
                Total_Experience_Years += years
                Total_Experience_Months += months

            # Handle overflow of months (convert to years if months >= 12)
        Total_Experience_Years += Total_Experience_Months // 12
        Total_Experience_Months = Total_Experience_Months % 12

        if Total_Experience_Years > 1 :
            if Total_Experience_Months > 1:
                Total_Experience=f"{Total_Experience_Years}Years {Total_Experience_Months}Months"
            else:
                Total_Experience=f"{Total_Experience_Years}Years {Total_Experience_Months}Month"
        else:
            if Total_Experience_Months > 1:
                Total_Experience=f"{Total_Experience_Years}Year {Total_Experience_Months}Months"
            else:
                Total_Experience=f"{Total_Experience_Years}Year {Total_Experience_Months}Month"
                
        return Total_Experience


class EmployeesFilters(APIView):
    def get(self, request, login_user=None):
        filter_params = request.GET.dict()  # Capture all filter parameters from the request
        filter_conditions = Q()  # Initialize an empty Q object to dynamically build filter conditions
        
        # Loop through each filter key-value pair in the request
        for key, value in filter_params.items():
            if value:  # If the value is present, proceed with filtering
                # Convert the query value to lowercase for case-insensitive comparison
                value = value.lower()
                
                # Check if the filter is related to EmployeeInformation fields
                if hasattr(EmployeeInformation, key):
                    filter_conditions &= Q(**{f"{key}__icontains": value})  # Add case-insensitive filter condition
                
                # Department filter
                elif key == "Department":
                    filter_conditions &= Q(employeedatamodel__Position__Department__Dep_Name__icontains=value)
                
                # Designation filter
                elif key == "Designation":
                    filter_conditions &= Q(employeedatamodel__Position__Name__icontains=value)
                
                # Reporting To filters
                elif key == "Reporting_To":
                    filter_conditions &= Q(employeedatamodel__Reporting_To__EmployeeId__icontains=value)
                
                elif key == "Reporting_To_Name":
                    filter_conditions &= Q(employeedatamodel__Reporting_To__Name__icontains=value)
                
                # Filters related to employee education
                elif hasattr(EmployeeEducation, key):
                    filter_conditions &= Q(**{f'employeeeducation__{key}__icontains': value})
                
                # Filters related to family details
                elif hasattr(FamilyDetails, key):
                    filter_conditions &= Q(**{f'familydetails__{key}__icontains': value})
                
                # Filters related to emergency contact details
                elif hasattr(EmergencyDetails, key):
                    filter_conditions &= Q(**{f'emergencydetails__{key}__icontains': value})
                
                # Additional filters for other related models
                elif hasattr(EmployeePersonalInformation, key):
                    filter_conditions &= Q(**{f'employeepersonalinformation__{key}__icontains': value})
                
                elif hasattr(BankAccountDetails, key):
                    filter_conditions &= Q(**{f'bankaccountdetails__{key}__icontains': value})

                elif hasattr(EmployeeIdentity, key):
                    filter_conditions |= Q(**{f'employeeidentity__{key}__icontains': value})
                
                elif hasattr(PFDetails, key):
                    filter_conditions &= Q(**{f'pfdetails__{key}__icontains': value})
                
                elif hasattr(AditionalInformationModel, key):
                    filter_conditions &= Q(**{f'aditionalinformationmodel__{key}__icontains': value})
                
                elif hasattr(AttachmentsModel, key):
                    filter_conditions &= Q(**{f'attachmentsmodel__{key}__icontains': value})
                    
        # Apply the filter conditions to the EmployeeInformation model
        employee_information_list = EmployeeInformation.objects.filter(filter_conditions)

        response_data_list = []

        # Process and serialize the filtered results
        # for employee_information in employee_information_list.filter(employee_status="active"):
        emp_status = filter_params.get("employee_status", "active")
        for employee_information in employee_information_list.filter(employee_status=emp_status):
            info = EmployeeDataModel.objects.filter(employeeProfile=employee_information).first()
            employee_info = EmployeeInformationSerializer(employee_information, context={"request": request}).data

            try:
                employee_info["Designation"] = info.Position.Name.lower() if info.Position else None
                employee_info["Dashboard"] = info.Designation.lower() if info.Designation else None
                employee_info["Department"] = info.Position.Department.Dep_Name.lower() if info.Position else None
                employee_info["Reporting_To"] = info.Reporting_To.EmployeeId.lower() if info.Reporting_To else None
                employee_info["Reporting_To_Name"] = info.Reporting_To.Name.lower() if info.Reporting_To else None

                current_experience = currentexperience(exp_data=info, exp_type="cur_exp")
                employee_info["Current_Experience"] = current_experience["current_exp"]

            except AttributeError:
                pass

            offer_details = OfferLetterModel.objects.filter(CandidateId=employee_information.Candidate_id).first()
            if offer_details:
                EOD_serializer = DOJ_OfferLetterserializer(offer_details, context={'request': request}).data

                employee_info.update(EOD_serializer)
            
            # Add salary and salary template information
            try:
                ESH = CompanyEmployeesPositionHistory.objects.filter(employee=info, is_applicable=True).first()
                employee_info["salary"] = ESH.assigned_salary if ESH else None
            except:
                pass

            try:
                ESB = EmployeeSalaryBreakUp.objects.filter(employee_id=info).first()
                serializer_data = EmployeeSalaryBreakUpSerializer(ESB).data
                employee_info["salary_Template"] = serializer_data
            except:
                pass

            # Serialize related fields (education, family, emergency contact, etc.)
            education_serializer = EmployeeEducationSerializer(employee_information.employeeeducation_set.all(), many=True, context={"request": request})
            family_serializer = FamilyDetailsSerializer(employee_information.familydetails_set.all(), many=True, context={"request": request})
            emergency_details_serializer = EmergencyDetailsSerializer(employee_information.emergencydetails_set.all(), many=True, context={"request": request})
            emergency_contact_serializer = EmergencyContactSerializer(employee_information.emergencycontact_set.all(), many=True, context={"request": request})
            candidate_reference_serializer = CandidateReferenceSerializer(employee_information.candidatereference_set.all(), many=True, context={"request": request})
            experience_serializer = ExceperienceModelSerializer(employee_information.exceperiencemodel_set.all(), many=True, context={"request": request})
            last_position_held_serializer = Last_Position_HeldSerializer(employee_information.last_position_held_set.all(), many=True, context={"request": request})
            personal_info_serializer = EmployeePersonalInformationSerializer(employee_information.employeepersonalinformation_set.all(), many=True, context={"request": request})
            employee_identity_serializer = EmployeeIdentitySerializer(employee_information.employeeidentity_set.all(), many=True, context={"request": request})
            bank_account_serializer = BankAccountDetailsSerializer(employee_information.bankaccountdetails_set.all(), many=True, context={"request": request})
            pf_details_serializer = PFDetailsSerializer(employee_information.pfdetails_set.all(), many=True, context={"request": request})
            additional_info_serializer = AditionalInformationSerializer(employee_information.aditionalinformationmodel_set.all(), many=True, context={"request": request})
            attachments_serializer = AttachmentsModelSerializer(employee_information.attachmentsmodel_set.all(), many=True, context={"request": request})
            declaration_serializer = DeclarationSerializer(employee_information.declaration_set.all(), many=True, context={"request": request})

            # Combine serialized data into the response
            employee_info.update({
                "EducationDetails": education_serializer.data,
                "FamilyDetails": family_serializer.data,
                "EmergencyDetails": emergency_details_serializer.data,
                "EmergencyContactDetails": emergency_contact_serializer.data,
                "CandidateReferenceDetails": candidate_reference_serializer.data,
                "LastPositionHeldDetails": last_position_held_serializer.data,
                "ExperienceDetails": experience_serializer.data,
                "PersonalInformation": personal_info_serializer.data,
                "EmployeeIdentity": employee_identity_serializer.data,
                "BankAccountDetails": bank_account_serializer.data,
                "AdditionalInformation": additional_info_serializer.data,
                "PFDetails": pf_details_serializer.data,
                "Attachments": attachments_serializer.data,
                "Declaration": declaration_serializer.data
            })

            # Add total experience based on current experience data
            employee_info["Total_Experience"] = currentexperience(
                exp_data=experience_serializer.data,
                exp_type="total_exp",
                cur_years_exp=current_experience["years"],
                cur_months_exp=current_experience["months"]
            )
            response_data_list.append(employee_info)
        return Response(response_data_list)
    

from django.db.models import F

class EmployeesSort(APIView):
    def get(self, request, login_user=None):
        sort_params = request.GET.dict()  # For GET requests

        # employee_information_list = EmployeeInformation.objects.filter(employee_status="active")
        emp_status = login_user if login_user in ["active", "in_active"] else "active"
        employee_information_list = EmployeeInformation.objects.filter(employee_status=emp_status)

        if sort_params:
            sort_order = []  # Store sorting fields
            for key, value in sort_params.items():
                sort_field = value
                # Determine if the field is in EmployeeInformation or related models
                if hasattr(EmployeeInformation, sort_field):
                    # Apply Lower function to sort by lowercase values
                    if key == "asc":
                        sort_order.append(Lower(sort_field))
                    else:
                        sort_order.append(Lower(sort_field).desc())

                elif hasattr(Deparments, sort_field) or sort_field == "Department":
                    if key == "asc":
                        employee_information_list = employee_information_list.order_by(Lower('employeedatamodel__Position__Department__Dep_Name'))
                    else:
                        employee_information_list = employee_information_list.order_by(Lower('employeedatamodel__Position__Department__Dep_Name').desc())

                elif hasattr(DesignationModel, sort_field) or sort_field == "Designation":
                    if key == "asc":
                        employee_information_list = employee_information_list.order_by(Lower('employeedatamodel__Position__Name'))
                    else:
                        employee_information_list = employee_information_list.order_by(Lower('employeedatamodel__Position__Name').desc())

                elif hasattr(EmployeeDataModel, sort_field) or sort_field == "Reporting_To" or sort_field == "Reporting_To_Name":
                    if key == "asc":
                        if sort_field == "Reporting_To":
                            employee_information_list = employee_information_list.order_by(Lower("employeedatamodel__Reporting_To__EmployeeId"))
                        else:
                            employee_information_list = employee_information_list.order_by(Lower("employeedatamodel__Reporting_To__Name"))
                    else:
                        if sort_field == "Reporting_To_Name":
                            employee_information_list = employee_information_list.order_by(Lower("employeedatamodel__Reporting_To__EmployeeId").desc())
                        else:
                            employee_information_list = employee_information_list.order_by(Lower("employeedatamodel__Reporting_To__Name").desc())

                elif hasattr(EmployeeEducation, sort_field):
                    sort_order.append(f'employeeeducation__{sort_field}' if key == "asc" else f'-employeeeducation__{sort_field}')
                elif hasattr(FamilyDetails, sort_field):
                    sort_order.append(f'familydetails__{sort_field}' if key == "asc" else f'-familydetails__{sort_field}')
                elif hasattr(EmergencyDetails, sort_field):
                    sort_order.append(f'emergencydetails__{sort_field}' if key == "asc" else f'-emergencydetails__{sort_field}')
                elif hasattr(EmergencyContact, sort_field):
                    sort_order.append(f'emergencycontact__{sort_field}' if key == "asc" else f'-emergencycontact__{sort_field}')
                elif hasattr(CandidateReference, sort_field):
                    sort_order.append(f'candidatereference__{sort_field}' if key == "asc" else f'-candidatereference__{sort_field}')
                elif hasattr(ExceperienceModel, sort_field):
                    sort_order.append(f'exceperiencemodel__{sort_field}' if key == "asc" else f'-exceperiencemodel__{sort_field}')
                elif hasattr(Last_Position_Held, sort_field):
                    sort_order.append(f'last_position_held__{sort_field}' if key == "asc" else f'-last_position_held__{sort_field}')
                elif hasattr(EmployeePersonalInformation, sort_field):
                    sort_order.append(f'employeepersonalinformation__{sort_field}' if key == "asc" else f'-employeepersonalinformation__{sort_field}')
                elif hasattr(EmployeeIdentity, sort_field):
                    sort_order.append(f'employeeidentity__{sort_field}' if key == "asc" else f'-employeeidentity__{sort_field}')
                elif hasattr(BankAccountDetails, sort_field):
                    sort_order.append(f'bankaccountdetails__{sort_field}' if key == "asc" else f'-bankaccountdetails__{sort_field}')
                elif hasattr(PFDetails, sort_field):
                    sort_order.append(f'pfdetails__{sort_field}' if key == "asc" else f'-pfdetails__{sort_field}')
                elif hasattr(AditionalInformationModel, sort_field):
                    sort_order.append(f'aditionalinformationmodel__{sort_field}' if key == "asc" else f'-aditionalinformationmodel__{sort_field}')
                elif hasattr(AttachmentsModel, sort_field):
                    sort_order.append(f'attachmentsmodel__{sort_field}' if key == "asc" else f'-attachmentsmodel__{sort_field}')
            
            # Apply the dynamic sort order (handling lowercase sorting)
            if sort_order:
                # employee_information_list = EmployeeInformation.objects.filter(employee_status="active").order_by(*sort_order)#.filter(employee_status="active")
                employee_information_list = EmployeeInformation.objects.filter(employee_status=emp_status).order_by(*sort_order)#.filter(employee_status="active")
            
        response_data_list = []

        for employee_information in employee_information_list:
            info = EmployeeDataModel.objects.filter(employeeProfile=employee_information).first()
        
            employee_info = EmployeeInformationSerializer(employee_information, context={"request": request}).data                   
      
            try:
                employee_info["Designation"] = info.Position.Name if info.Position else None
                employee_info["Dashboard"] = info.Designation if info.Designation else None
                employee_info["Department"] = info.Position.Department.Dep_Name if info.Position else None
                employee_info["Reporting_To"] = info.Reporting_To.EmployeeId if info.Reporting_To else None
                employee_info["Reporting_To_Name"] = info.Reporting_To.Name if info.Reporting_To else None

                current_experience = currentexperience(exp_data=info, exp_type="cur_exp")
                employee_info["Currrent_Experience"] = current_experience["current_exp"]

            except AttributeError:
                pass

            offer_details = OfferLetterModel.objects.filter(CandidateId=employee_information.Candidate_id).first()
            if offer_details:
                EOD_serializer = DOJ_OfferLetterserializer(offer_details, context={'request': request}).data
                employee_info.update(EOD_serializer)
            try:
                ESH = CompanyEmployeesPositionHistory.objects.filter(employee=info, is_applicable=True).first()
                if ESH:
                    employee_info["salary"] = ESH.assigned_salary
                else:
                    employee_info["salary"] = None
            except:
                pass
            try:
                ESB = EmployeeSalaryBreakUp.objects.filter(employee_id=info).first()
                serializer_data = EmployeeSalaryBreakUpSerializer(ESB).data
                employee_info["salary_Template"] = serializer_data
            except:
                pass

            education_serializer = EmployeeEducationSerializer(employee_information.employeeeducation_set.all(), many=True, context={"request": request})
            family_serializer = FamilyDetailsSerializer(employee_information.familydetails_set.all(), many=True, context={"request": request})
            emergency_details_serializer = EmergencyDetailsSerializer(employee_information.emergencydetails_set.all(), many=True, context={"request": request})
            emergency_contact_serializer = EmergencyContactSerializer(employee_information.emergencycontact_set.all(), many=True, context={"request": request})
            candidate_reference_serializer = CandidateReferenceSerializer(employee_information.candidatereference_set.all(), many=True, context={"request": request})
            experience_serializer = ExceperienceModelSerializer(employee_information.exceperiencemodel_set.all(), many=True, context={"request": request})
            last_position_held_serializer = Last_Position_HeldSerializer(employee_information.last_position_held_set.all(), many=True, context={"request": request})
            personal_info_serializer = EmployeePersonalInformationSerializer(employee_information.employeepersonalinformation_set.all(), many=True, context={"request": request})
            employee_identity_serializer = EmployeeIdentitySerializer(employee_information.employeeidentity_set.all(), many=True, context={"request": request})
            bank_account_serializer = BankAccountDetailsSerializer(employee_information.bankaccountdetails_set.all(), many=True, context={"request": request})
            pf_details_serializer = PFDetailsSerializer(employee_information.pfdetails_set.all(), many=True, context={"request": request})
            additional_info_serializer = AditionalInformationSerializer(employee_information.aditionalinformationmodel_set.all(), many=True, context={"request": request})
            attachments_serializer = AttachmentsModelSerializer(employee_information.attachmentsmodel_set.all(), many=True, context={"request": request})
            declaration_serializer = DeclarationSerializer(employee_information.declaration_set.all(), many=True, context={"request": request})

            employee_info.update({
                "EducationDetails": education_serializer.data,
                "FamilyDetails": family_serializer.data,
                "EmergencyDetails": emergency_details_serializer.data,
                "EmergencyContactDetails": emergency_contact_serializer.data,
                "CandidateReferenceDetails": candidate_reference_serializer.data,
                "LastPositionHeldDetails": last_position_held_serializer.data,
                "ExperienceDetails": experience_serializer.data,
                "PersonalInformation": personal_info_serializer.data,
                "EmployeeIdentity": employee_identity_serializer.data,
                "BankAccountDetails": bank_account_serializer.data,
                "AdditionalInformation": additional_info_serializer.data,
                "PFDetails": pf_details_serializer.data,
                "Attachments": attachments_serializer.data,
                "Declaration": declaration_serializer.data
            })
            
            employee_info["Total_Experience"] = currentexperience(exp_data=experience_serializer.data, exp_type="total_exp", cur_years_exp=current_experience["years"], cur_months_exp=current_experience["months"])

            response_data_list.append(employee_info)

        return Response(response_data_list)