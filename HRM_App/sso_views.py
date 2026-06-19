"""
SSO Views for HRM-DAS Integration
Handles JWT token generation and employee status checking for SSO
"""

from django.shortcuts import redirect
from django.http import JsonResponse
from django.views import View
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from .models import EmployeeInformation
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class RedirectToDASView(View):
    """
    Generates JWT token with employee details and redirects to DAS SSO login
    
    URL: /redirect-to-das/<employee_id>/
    Method: GET
    
    Flow:
    1. Get employee by employee_id
    2. Generate JWT token with employee details
    3. Redirect to DAS SSO login endpoint with token
    """
    
    def get(self, request, employee_id):
        try:
            # Fetch employee information with related data
            employee = EmployeeInformation.objects.select_related(
                'Candidate_id'
            ).filter(employee_Id=employee_id).first()
            
            if not employee:
                return JsonResponse({
                    'error': 'Employee not found'
                }, status=404)
            
            # Check if employee is active
            is_active = employee.employee_status == 'active'
            
            # Get EmployeeDataModel for designation and reporting info
            employee_data = None
            try:
                from .models import EmployeeDataModel
                employee_data = EmployeeDataModel.objects.select_related(
                    'Position', 'Reporting_To', 'Position__Department'
                ).filter(EmployeeId=employee_id).first()
            except Exception as e:
                logger.warning(f"Could not fetch EmployeeDataModel: {str(e)}")
            
            # Create lightweight JWT token with essential auth data only
            refresh = RefreshToken()
            
            # Essential Authentication Data (minimal payload)
            refresh['email'] = employee.email or ''
            refresh['name'] = employee.full_name or ''
            refresh['employee_id'] = employee.employee_Id or ''
            refresh['is_active'] = is_active
            
            # Role mapping data
            if employee_data:
                refresh['designation'] = employee_data.Designation or ''
                refresh['hrm_role'] = employee_data.Designation or ''
            else:
                refresh['designation'] = ''
                refresh['hrm_role'] = employee.Employeement_Type or ''
            
            # Data freshness indicator (for smart sync)
            # DAS will use this to decide if full sync is needed
            from django.utils import timezone
            refresh['last_modified'] = timezone.now().isoformat()
            
            # Signal that full employee data is available via API
            refresh['sync_required'] = True  # DAS will fetch full data if needed
            
            # Get access token
            access_token = str(refresh.access_token)
            
            # Build DAS SSO URL
            das_sso_url = f"https://das.meridahr.com/api/sso-login/?token={access_token}"
            
            logger.info(f"Redirecting employee {employee_id} to DAS with SSO token")
            
            # Redirect to DAS
            return redirect(das_sso_url)
            
        except Exception as e:
            logger.error(f"Error in RedirectToDASView: {str(e)}")
            return JsonResponse({
                'error': 'Internal server error',
                'details': str(e)
            }, status=500)


class CheckEmployeeStatusAPI(APIView):
    """
    API endpoint to check employee active status and get full employee data
    Used by DAS to verify employee status and sync complete employee information
    
    URL: /api/check-employee-status/<email>/
    Method: GET
    Query Parameters: full_details=true (optional, to get complete employee data)
    
    Response:
    {
        "is_active": true/false,
        "email": "employee@example.com",
        "name": "John Doe",
        "employee_id": "EMP001",
        "employee_details": {...}  // If full_details=true
    }
    """
    
    def get(self, request, email):
        try:
            # Fetch employee by email
            employee = EmployeeInformation.objects.select_related(
                'Candidate_id'
            ).filter(email=email).first()
            
            if not employee:
                return Response({
                    'is_active': False,
                    'error': 'Employee not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Check if employee is active
            is_active = employee.employee_status == 'active'
            
            # Basic response (always returned)
            response_data = {
                'is_active': is_active,
                'email': employee.email,
                'name': employee.full_name,
                'employee_id': employee.employee_Id,
                'employee_status': employee.employee_status,
            }
            
            # Check if full employee details are requested
            full_details = request.query_params.get('full_details', 'false').lower() == 'true'
            
            if full_details:
                # Fetch EmployeeDataModel for additional info
                from .models import EmployeeDataModel
                employee_data = EmployeeDataModel.objects.select_related(
                    'Position', 'Reporting_To', 'Position__Department'
                ).filter(EmployeeId=employee.employee_Id).first()
                
                # Build complete employee details
                employee_details = {
                    # Basic Info
                    'employee_id': employee.employee_Id,
                    'name': employee.full_name,
                    'email': employee.email,
                    'phone': employee.mobile or '',
                    'secondary_phone': employee.secondary_mobile_number or '',
                    'secondary_email': employee.secondary_email or '',
                    
                    # Address
                    'address': employee.permanent_address or '',
                    'city': employee.permanent_City or '',
                    'state': employee.permanent_state or '',
                    'pincode': employee.permanent_pincode or '',
                    
                    # Employment
                    'employment_type': employee.Employeement_Type or '',
                    'department': employee.work_location or '',
                    'work_location': employee.work_location or '',
                    
                    # Dates
                    'date_of_joining': employee.hired_date.isoformat() if employee.hired_date else '',
                    'date_of_birth': employee.date_of_birth.isoformat() if employee.date_of_birth else '',
                    
                    # Probation/Internship
                    'probation_status': employee.probation_status or '',
                    'probation_from': employee.probation_Duration_From.isoformat() if employee.probation_Duration_From else '',
                    'probation_to': employee.probation_Duration_To.isoformat() if employee.probation_Duration_To else '',
                    'internship_from': employee.internship_Duration_From.isoformat() if employee.internship_Duration_From else '',
                    'internship_to': employee.internship_Duration_To.isoformat() if employee.internship_Duration_To else '',
                    
                    # Status
                    'employee_status': employee.employee_status or 'active',
                    'profile_verification': employee.ProfileVerification or '',
                }
                
                # Add EmployeeDataModel info if available
                if employee_data:
                    employee_details['designation'] = employee_data.Designation or ''
                    employee_details['position'] = employee_data.Position.Name if employee_data.Position else ''
                    employee_details['hrm_role'] = employee_data.Designation or ''
                    employee_details['department'] = employee_data.Position.Department.Dep_Name if (employee_data.Position and employee_data.Position.Department) else employee.work_location or ''
                    
                    if employee_data.Reporting_To:
                        employee_details['reporting_manager_id'] = employee_data.Reporting_To.EmployeeId or ''
                        employee_details['reporting_manager_name'] = employee_data.Reporting_To.Name or ''
                    else:
                        employee_details['reporting_manager_id'] = ''
                        employee_details['reporting_manager_name'] = ''
                else:
                    employee_details['designation'] = ''
                    employee_details['position'] = ''
                    employee_details['hrm_role'] = employee.Employeement_Type or ''
                    employee_details['reporting_manager_id'] = ''
                    employee_details['reporting_manager_name'] = ''
                
                response_data['employee_details'] = employee_details
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Error in CheckEmployeeStatusAPI: {str(e)}")
            return Response({
                'error': 'Internal server error',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)