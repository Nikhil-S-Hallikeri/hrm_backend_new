
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from EMS_App.views import *
from EMS_App.resignation import *
from rest_framework.routers import DefaultRouter
from.filters import EmployeesFilters,EmployeesSort

router = DefaultRouter()
router.register(r'Departments', DepartmentViewSet,basename='dep')
router.register(r'Designation/(?P<Dep_id>\d+)', DesignationViewSet,basename='designation')
router.register(r'Designations', DesignationViewSet,basename='all_designation')
router.register(r'Religions', ReligionViewSet,basename='employee_Religions')
from django.urls import re_path

urlpatterns = [
    path('', include(router.urls)),
    
    path("EmployeesFilters",EmployeesFilters.as_view()),
    path("EmployeesSort/<str:login_user>",EmployeesSort.as_view()),

    path('employee_information/<int:can_id>/', EmployeeInformationView.as_view(), name='employee-information'),#post the emplo_info details
    path('updating_employee_information/<int:emp_info_id>/', EmployeeInformationView.as_view()),#get or update or del the emplo_info details
    path('candidate_employee_information/<int:can_obj>/', CandidateEmployeeInformation.as_view(), name='candidate-employee-information'),

    path('employee-education/<int:emp_info_id>/', EmployeeEducationView.as_view(), name='employee-education'),#get or post the emplo_edu details
    path('update-employee-education/<int:id>/', EmployeeEducationView.as_view()),#update or del the emplo_edu details

    path('family-details/<int:emp_info_id>/', FamilyDetailsView.as_view(), name='family-details'),#get or post the emplo_family details
    path('update-family-details/<int:id>/', FamilyDetailsView.as_view()),#del or update or del the emplo_family details

    path('emergency-details/<int:emp_info_id>/', EmergencyDetailsView.as_view(), name='emergency-details'),
    path('update-emergency-details/<int:id>/', EmergencyDetailsView.as_view()),

    path('emergency-contact/<int:emp_info_id>/', EmergencyContactView.as_view(), name='emergency-contact'),
    path('update-emergency-contact/<int:id>/', EmergencyContactView.as_view()),

    path('candidate-reference/<int:emp_info_id>/', CandidateReferenceView.as_view(), name='candidate-reference'),
    path('update-candidate-reference/<int:id>/', CandidateReferenceView.as_view()),

    path('experience/<int:emp_info_id>/', ExceperienceModelView.as_view(), name='experience'),
    path('update-experience/<int:id>/', ExceperienceModelView.as_view()),

    path('last-position-held/<int:emp_info_id>/', LastPositionHeldView.as_view(), name='last-position-held'),
    path('update-last-position-held/<int:id>/', LastPositionHeldView.as_view()),

    path('employee-personal-information/<int:emp_info_id>/', EmployeePersonalInformationView.as_view(), name='employee-personal-information'),
    path('update-employee-personal-information/<int:id>/', EmployeePersonalInformationView.as_view()),

    path('employee-identity/<int:emp_info_id>/', EmployeeIdentityView.as_view(), name='employee-identity'),
    path('update-employee-identity/<int:id>/', EmployeeIdentityView.as_view()),

    path('bank-account-details/<int:emp_info_id>/', BankAccountDetailsView.as_view(), name='bank-account-details'),
    path('update-bank-account-details/<int:id>/', BankAccountDetailsView.as_view()),

    path('pf-details/<int:emp_info_id>/', PFDetailsView.as_view(), name='pf-details'),
    path('update-pf-details/<int:id>/', PFDetailsView.as_view()),

    path('additional-information/<int:emp_info_id>/', AditionalInformationView.as_view(), name='additional-information'),
    path('update-additional-information/<int:id>/', AditionalInformationView.as_view()),

    path("attachments/<int:emp_info_id>/",AttachmentModelView.as_view(), name='attachments'),
    path("update-attachments/<int:id>/",AttachmentModelView.as_view()),

    path("Documents/<int:emp_info_id>/",Documents_SubmitedView.as_view(), name='attachments'),
    path("update-Documents/<int:id>/",Documents_SubmitedView.as_view()),

    path('declaration/<int:emp_info_id>/', DeclarationView.as_view(), name='declaration'),
    path('update-declaration/<int:id>/', DeclarationView.as_view()),

    path("EmployeeCreation/<int:emp_info_id>/",EmployeeCreation.as_view()),
    path("JoiningFormalityesSubmitedList",JoiningFormalityesSubmitedList.as_view()),
    path("JoiningFormalityesSubmitedList/<int:emp_info_id>/",JoiningFormalityesSubmitedList.as_view()),
    #path("ProfileVerification/<int:emp_info_id>/",ProfileVerification.as_view()),
    
    path("Get-Employee/<int:id>/",NewEmployeesAdding.as_view()),
    path("Get_Employee_by_Emp/<str:emp_id>/",NewEmployeesAdding.as_view()),

    path("NewEmployeesAdding/",NewEmployeesAdding.as_view()),
    path("Employee-Update/<int:id>/",NewEmployeesAdding.as_view()),
    path("Employee-Delete/<int:id>/",NewEmployeesAdding.as_view()),

    path("AllEmployeesList/<str:login_user>/",HRDashboardEmployees.as_view()),
    path("LoginEmployeeProfile/<str:loginuser>/",LoginEmployeeProfileView.as_view()),


    path("EmployeeProfile/<str:emp_info_id>/",EmployeeProfileView.as_view()),

    path("Employee_search/<str:search_value>/",Employee_search.as_view()),
    path("HiredFilter/<str:From_Date>/<To_Date>/",Employee_search.as_view()),

    path("DepartmentList/<str:login_user>/",DepartmentsList.as_view()),
    path("SingleDesignation/List/<int:dep_id>/",DepartmentsList.as_view()),#new onedes_id
    path("SingleDesignation/Employee/List/<int:des_id>/",DepartmentsList.as_view()),#new one
    path("DesignationList/<str:login_user>/",DesignationListView.as_view()),

    path("EmployeeHistoryCreating/<int:emp_info_id>/",EmployeeHistoryCreating.as_view()),
    path("UpdateEmployeeHistory/<int:id>/",EmployeeHistoryCreating.as_view()),

# ..................................................................................
    path("SingleDepartmentEmployee/<str:login_user>/<str:Department_id>/",HRDashboardEmployees.as_view()),
    path("SingleDesignationEmployee/<str:login_user>/<str:Designation_id>/",HRDashboardEmployees.as_view()),
    
    path("MassMails",MassMailsView.as_view()),
    re_path(r'Department_Mail/(?P<dep_value>.+)/$', MassMailsView.as_view(), name='department_mail'),
    #path("Department_Mail/<str:dep_value>/",MassMailsView.as_view()),
    re_path(r'Designation_Mail/(?P<deg_value>.+)/$', MassMailsView.as_view(), name='designation_mail'),
    #path("Designation_Mail/<str:deg_value>/",MassMailsView.as_view()),
    path("EmployeeId/Mail/<str:search_value>/",MassMailsView.as_view()),
    path("SendMassMails",SendEmailAPIView.as_view()),

    

    path("CompanyPolicies/<str:applicable>/",CompanyPolicies.as_view()),
    path("CompanyPolicies/",CompanyPolicies.as_view()),

    path("HRList",HRList.as_view()),
    path("ReportingTeam/<str:loginuser>/",ReportingTeamView.as_view()),

    path("ResignationRequest",ResignationRequestView.as_view()),
    path("RM_ResignationVerification",RMResignationVerification.as_view()),
    path("HR_ResignationVerification",HRResignationVerification.as_view()),#post

    path("HR_ResignationVerification_List/<str:login_user>/",HRResignationVerification.as_view()),#get all
    path("HR_ResignationVerification/<int:resign_id>/",HRResignationVerification.as_view()),#get single

    path("EmployeeExitInterview",ExitInterview.as_view()),#post
    # path("ExitEmployeeList/<str:login_user>/",ExitInterview.as_view()),
    # path("ExitEmployeeList/<int:resign_id>/",ExitInterview.as_view()),
    path("ExitEmployeeList/<str:login_user>/",ExitInterview.as_view()),
    path("ExitEmployeeList/<int:resign_id>/",ExitInterview.as_view()),
    path("Handovers",HandoverDetails.as_view()),
    path("Handovers/<int:handover_id>/",HandoverDetails.as_view()),
    path("HandoverAcknowledgement",HandoverAcknowledgement.as_view()),

    path("Clearence",ClearenceFormView.as_view()),
    path("EmpLeftOrganization",EmpLeftOrganizationView.as_view()),


    # path("ResignationRequest",ResignationRequestView.as_view()),

    # path("RM_ResignationVerification",RMResignationVerification.as_view()),
    # path("HR_ResignationVerification",HRResignationVerification.as_view()),#post

    # path("HR_ResignationVerification_List/<str:login_user>/",HRResignationVerification.as_view()),#get all
    # path("HR_ResignationVerification/<int:resign_id>/",HRResignationVerification.as_view()),#get single

    # path("EmployeeExitInterview",ExitInterview.as_view()),#post
    # path("ExitEmployeeList/<str:login_user>/",ExitInterview.as_view()),
    # path("ExitEmployeeList/<int:resign_id>/",ExitInterview.as_view()),
    
    # path("EmpLeftOrganization",EmpLeftOrganizationView.as_view()),
    


]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

