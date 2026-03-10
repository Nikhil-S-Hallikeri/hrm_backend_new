from django.urls import path,include
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from .attendance_view import *
from rest_framework.routers import DefaultRouter
from . import appraisalview
router = DefaultRouter()
router.register(r'LeaveTypes',LeaveTypeAddingView,basename='Leave')
router.register(r'LeaveTypeDetails/(?P<Leave_id>\d+)',LeaveTypeDetailsView,basename='LeaveData')
router.register(r'LeaveTypeDetails',LeaveTypeDetailsView,basename='LeaveDataList')
router.register(r'weekoffdays', WeekOffDayViewSet,basename="weekoffs")
router.register(r'employeeweekoffs', EmployeeWeekoffsModelViewSet,basename="EmployeeWeekoffs")
from .views_correction import AttendanceCorrectionRequestView, ApproveAttendanceCorrectionView
urlpatterns = [
    path('', include(router.urls)),
    
    path("UpdateEmployeeAttendanceManually/",UpdateEmployeeAttendanceAPIView.as_view()),
    
    path("Weekoffs",WeekoffsView.as_view()),
    path("AttendanceRecordCreate", DailyAttendanceRecordCreateView.as_view()),
    path("LeaveTypeDetailsCreating/",LeavesTypesDetailsCreating.as_view()),
    path("Available_Leaves/<str:emp_id>/",LeavesTypesDetailsCreating.as_view()),
    path('CompanyHolidaysDataAdding/',CompanyHolidaysDataModelView.as_view()),# to post
    path('CompanyHolidaysData/',CompanyHolidaysDataModelView.as_view()),# ot get all get method
    path('CompanyHolidaysData/<str:year>/',CompanyHolidaysDataModelView.as_view()),
    path('EmployeeHolidays/<str:login_user>/',EmployeeCompanyHolidays.as_view()),# ot get all get method
    path("EmployeeLeavesPending/<str:login_user>/",EmployeeLeavesPendingView.as_view()),
    path("Reporting/Employee/PendingLeaves/<str:report_emp>/",EmployeeLeavesPendingView.as_view()),
    path("EmployeeLeaves/accepting/By_hr/",EmployeeLeavesPendingView.as_view()),
    path("LeaveWithdraw/<int:leave_req_id>/<str:withdraw>/",LeaveWithDrawnViewFunction.as_view()),
    path("Leaves/History/<str:emp_id>/",LeaveWithDrawnViewFunction.as_view()),
    path("ReportingTeam/Leaves/History/<str:emp_id>/",ReportingTeamLeavesHistory.as_view()),
    path("EmployeeLeaveEligibilityView",EmployeeLeaveEligibilityView.as_view()),
    path("EmployeeLeaveEligibility/list/<str:login_user>/",EmployeeLeaveEligibilityView.as_view()),
    
    path("EmployeesAvailableLeaves/<str:emp_id>/",EmployeesAvailableLeavesView.as_view()),
    path("Approve_Employee_Leave_Request/",EmployeeLeaveRequestView.as_view()),
    path("Employee_Leave_Conversation/<int:leave_req_id>/",Employee_Leaves_Conversation.as_view()),
    
    path("LeavesRequest/Handling/ByAdmin/",LeavesRequestHandlingByAdmin.as_view()),
    path("WeeklyLeaves/Approvals/<str:emp_id>/",WeeklyLeavesApprovalsList.as_view()),
# attendance apis
    path('shifts/', EmployeeShiftsAPIView.as_view()),  # For list and post
    path('shifts/<int:pk>/', EmployeeShiftsAPIView.as_view()),  # For detail and update
    path("AttendatnceAddingView/",AttendatnceAddingView.as_view()),#to post
    path("Bulk_Attendance_Data/",ImportAttendanceData.as_view()),# to upload bulk data 
    path('attendance/<str:start_date>/<str:end_date>/', AttendanceByYearMonthView.as_view(), name='attendance_by_year_month'),
    path('attendance/year/<int:year>/month/<int:month>/week/<int:week>/', AttendanceByYearMonthWeekView.as_view(), name='attendance_by_year_month_week'),
    path('attendance/employee/<str:employee_id>/', EmployeeAttendanceView.as_view(), name='employee_attendance'),
    path("employee-attendance/<str:employee_id>/<start_date>/<end_date>/",EmployeeAttendanceView.as_view()),
    path('attendance/reporting_manager/<str:reporting_manager_id>/', ReportingEmployeeAttendanceView.as_view(), name='reporting_employee_attendance'),
 
    path("EmployeeSalaryDistrubution/<str:emp_id>/month/<int:month>/year/<int:year>/",EmployeesAttendanceCalculation.as_view()),
    #5/1/2026
    path("Employees/Daily/Attendance",EmployeesDailyAttendanceData.as_view()),
    
    # performance appraisals
    
    path('AppraisalInvitation/',appraisalview.AppraisalInvitationSendView.as_view()),
    path('PerformanceMetrics/',appraisalview.PerformanceMetricsView.as_view()),
    
    # 29/12/2025
    path("GetSelfAppraisal/",appraisalview.GetSelfAppraisalData.as_view()),
    path("GetReportingManagerAppraisal/",appraisalview.GetReportingManagerAppraisalData.as_view()),
    
    path("EmployeementHistoryManagement",appraisalview.EmployeementPositionChanges.as_view()),
    
    path("attendance/correction/", AttendanceCorrectionRequestView.as_view()),
    path("attendance/correction/<int:pk>/approve/", ApproveAttendanceCorrectionView.as_view()),
    
    ]