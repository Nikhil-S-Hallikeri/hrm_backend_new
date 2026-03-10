from django.urls import path
from .views import *
from .location import *
from .downloads import *
from .notifications import *
from.search import *
from .activity import *
from .wish_notification import *
from .admin_view import *
from django.conf import settings
from django.conf.urls.static import static
from HRM_App.wish_notification import *
from rest_framework.routers import DefaultRouter
from django.urls import include


# Router for internal HR management endpoints
manage_router = DefaultRouter()
manage_router.register(r'companies', CompanyManagementViewSet, basename='manage-company')
manage_router.register(r'skills', SkillManagementViewSet, basename='manage-skill')
manage_router.register(r'jobs', JobManagementViewSet, basename='manage-job')


# Router for the public, service-to-service API
public_router = DefaultRouter()
public_router.register(r'jobs', PublicJobListingViewSet, basename='public-job')



urlpatterns = [
    path("job_description/",Job_Post.as_view()),
    path('log-ip/', log_ip_view, name='log_ip'),
    path("signin",RegistrationView.as_view(),name="registration"),
    path('verify',OTPVerificationView.as_view()),
    path('login',LoginView.as_view()),
    path("logout/<str:empid>/",LogoutView.as_view()),
    path('forgotpassword',ForgotPasswordView.as_view()),
    path("forgotpasswordverify",forgotPassOTPVerificationView.as_view()),
    path("setpassword",SetPasswordView.as_view()),
    path("changepassword",ChangePasswordView.as_view()),
    path("UserProfileUpload/<str:userid>/",UserProfileUpdate.as_view()),
    path("loginuser/<str:login_user>/",loginuserview.as_view()),

    path('applicationform/<str:param>/',CandidateApplicationView.as_view()),#post
    path("Districts/<str:state_name>",Location.as_view()),
    path("States",States.as_view()),
    path('appliedcandidate/<str:can_id>/',CandidateApplicationView.as_view()),#get single
    path('appliedcandidateslist',CandidateApplicationSearchView.as_view()),#get all
    path("employee-team-munbers/<str:login_user>/",employeeReportingTeam.as_view()),

    path("interviewschedule",InterviewSchedulView.as_view()),
    path("ScreeningAssigning/",ScreeningAssigningView.as_view()),
    path("ScreeningAssignedCandidate/<str:can_id>/",ScreeningAssigningView.as_view()),

    path("ScreeningReviewData",ScreeningReviewListView.as_view()),
    path("InterviewReviewData",InterviewReviewListView.as_view()),
    path("InterviewScheduledCandidate/<int:interview_id>/",InterviewScheduledCandidatesData.as_view()),


    path('upload-excel/', ExcelUploadView.as_view(), name='upload_excel'),
    path("upload-employees-excel-data/",EmployeeExcelUploadView.as_view()),
    path('download-excel/', AppliedCandidatesDownload.as_view(), name='download_excel'),
    path("employee-download-excel/",EmployeeDataDownload.as_view()),

    path("Employees-Upload-Formate/<str:file>/",Download_doc_Sheet.as_view()),
    path("Candidates/Upload/Formate/<str:file>/",Download_doc_Sheet.as_view()),

    # candidates search
    path("AppliedCandidateSearch/<search_value>/",FinalCandidateSearchView.as_view()),

    # interview process
    path("New-Screening-assigned-list/<str:loginuser>/<str:scr_status>/",Screening_assigned_list.as_view()),
    path("New-Candidate-Screening-list/<str:loginuser>/<str:scr_status>/",Candidate_Screening_list.as_view()),
    path("New-Interview-assigned-list/<str:loginuser>/<str:scr_status>/",Interview_assigned_list.as_view()),
    path("New-Candidate-Interview-list/<str:loginuser>/<str:scr_status>/",Candidate_Interview_list.as_view()),

    path("New-Candidate-Screening-Completed-Details/<str:can_id>/",CandidateScreeningCompletedDetails.as_view()),
    path("New-Candidate-Interview-Completed-Details/<str:can_id>/",CandidateInterviewCompletedDetails.as_view()),
    

    #final data
    path("FinalList/<str:login_user>/",FinalDataView.as_view()),
    path("FinalStatusUpdate",UpdateFinalStatusView.as_view()),

    path("FinalCandidatesList/<str:FinalStatus>/",FinalCandidatesListViewView.as_view()),
    path("FinalCandidatesList/<str:FinalStatus>/<str:duration>/",FinalCandidatesListViewView.as_view()),

    path("FinalResultsCount",FinalResultsCount.as_view()),
    path("FinalResultsCount/<str:duration>/",FinalResultsCount.as_view()),

    path("FinalResultsCountFunction/<str:login_user>/<str:dis_value>/",FinalResultsCountFunction.as_view()),
    path("FinalResultsData/<str:login_user>/<str:FinalStatus>/",FinalResultsCountFunction.as_view()),
 
    #documents
    path("DocumentsUploadData/<str:can_id>/<str:mail_sended_by>", DocumentsUploadView.as_view()),
    path("DocumentsUploadedList/<str:can_id>/", DocumentsUploadView.as_view()),
    path("DocumentsUploadForm", DocumentsUploasForm.as_view()),
    path("Candidates_Applied_Filter/<str:duration>/",Candidates_Applied_Filter.as_view()),
    path("Filter_FROM_TO_Date/<str:FromDate>/<str:ToDate>/",FilterBasedFromToView.as_view()),

    path("CompleteFinalStatus/<str:can_id>/",CompleteFinalStatusView.as_view()),

    path("BG_Verification/",BG_VerificationView.as_view()),
    path("BGVerification/<int:doc_id>/",BG_VerificationView.as_view()),
    path("BG_Status/<int:doc_instance>/",BG_Status.as_view()),
    path("BG_VerificationMailSend/",BG_VerificationMailSendView.as_view()),
    path("Offerletter/<str:candidate_id>/",SendOfferLetterEmail.as_view()),#post and get 
    path("OfferLetterDetails/<int:offer_id>/",OfferLetterDetails.as_view()),#update or approvals patch
    path("OfferLetterApprovalList/<str:login_user>/",OfferLetterDetails.as_view()),
    path("CandidateOfferLetterSending/<int:offer_id>/",SendOfferLetterEmail.as_view()),#send offer letter patch
    
    #9/1/2026
    path('OfferAcceptStatus/<str:can_id>/', OfferAcceptStatus.as_view(),name="OfferAcceptStatus"),
    path("JoiningAppointmentMail",JoiningAppointmentMail.as_view()),
    path("PendingJoiningForms",PendingJoiningFormsView.as_view()),  # New endpoint for pending forms


    
    # notifications
    path("Candidatenotifications/<str:login_user>/",CandidateAppliedNotifications.as_view(), name='notifications_get'),
    path('AppliedNotifications/Delete/<int:id>/', CandidateAppliedNotifications.as_view(), name='notifications_get_delete'),
    path('Notifications/Delete', CandidateAppliedNotifications.as_view(), name='selected_notifications_get_delete'),

    # activity sheet urls
    path("add_activity/",ActivityView.as_view(),name='add-activity'),# activity post 
    path('activity/<str:login_user>/', ActivityView.as_view(), name='example-detail'),# employee activitys get 
    path("activity/updel/<int:instance>/",ActivityView.as_view()),# employee activitys delete and update
    path("daily_achives",DailyActivityView.as_view()),  # daily achives post
    path("daily_achives/<int:instance>/",DailyActivityView.as_view()),
    path("ActivityListDisplay/<str:login_user>/",ActivityListDisplay.as_view()),
    path("ActivityList/Display/<str:filter_value>/<str:employee>/",ActivityListDisplay.as_view()),
    path("EmployeeActivity/<str:employee>/",ActivityListDisplay.as_view()),

    path("Activity/Download/<str:start_date>/<str:end_date>/<str:employee>/",ActivityListDisplayDownload.as_view(), name='activity-download'),

    path("InterviewList/Display/<str:filter_value>/<str:employee>/",InterviewListDisplay.as_view()),
    path("InterviewListDisplay/<str:login_user>/",InterviewListDisplay.as_view()),
    path("Interview_Schedule_activity",InterviewScheduleView.as_view()),#post
    path("Interview_Schedule_activity/updel/<int:instance>/",InterviewScheduleView.as_view()),#update delete

    path("Interview_Schedule_activity/<str:login_user>/",InterviewScheduledAchived.as_view()),#get
    path("Daily_Interview_Schedule_Achives/<int:instance>/",InterviewScheduledAchived.as_view()),#update

    path("Walkin_activity/<str:login_user>/",WalkinView.as_view()),#get
    path("Daily_Walkins_Achives/<int:instance>/",WalkinView.as_view()),#update

    path("Offered_activity/<str:login_user>/",OfferedView.as_view()),#get
    path("Daily_Offers_Achives/<int:instance>/",OfferedView.as_view()),#update

    # New Activity Urls
    path("activity-list/<str:activity_status>/<str:employee_id>",DisplayActivityListView.as_view()),
    path("new-employees-activity/<str:login_user>",AddNewActivitys.as_view()),
    path("new-assigned-activity/<str:assigned_by>",AddNewActivitys.as_view()),

    path("create-daily-achieved-activity",CreateNewDailyAchievedActivitys.as_view()),
    path("create-daily-achieved-activity/<int:id>",CreateNewDailyAchievedActivitys.as_view()),
    # root/create-daily-achieved-activity?login_emp_id=MTM24E1002 -- post
    # root/create-daily-achieved-activity?activity_list_id=1&login_emp_id=MTM24E1002&date=2024-11-26 -- get

    path("display-interviewcalls-date",DisplayInterviewCallsDate.as_view()), # not working
    path("display--assigned-interviewcalls-date/<str:assigned_by>",DisplayInterviewCallsDate.as_view()),# not working

    path("DisplayEmployeeActivitys/<str:login_user>",DisplayEmployeeActivitys.as_view()),# to get all interview schedule and walkin schedule
    path("CreateInterviewAchievedActivitys",CreateInterviewAchievedActivitys.as_view()),
    #http://127.0.0.1:8000/root/CreateInterviewAchievedActivitys?activity_list_id=1&login_emp_id=MTM24E1002&activity_status=walkins&date=2024-11-27

    path("CreateInterviewAchievedActivitys420",CreateInterviewAchievedActivitys420.as_view()),
    path("DisplayEmployeeActivitys420/<str:login_user>",DisplayEmployeeActivitys420.as_view()),

    path("assign-services/<int:id>",AssignServices.as_view()), 

    # dashboard urls
    path('department-ratio/', DepartmentRatioAPIView.as_view(), name='department-ratios'),
    path('candidate-gender-diversity/', GenderDiversityAPIView.as_view(), name='gender-diversity'),
    path('employee-diversity/', EmployeeDiversityView.as_view(), name='employee-diversity'),
    path('job-portal-source-count/', JobPortalSourceCountAPIView.as_view(), name='job-portal-source-count'),
    path("JPS-Filter",JobPortalSourceFilter.as_view()),
    path("GetEmployeeCelebrations/",GetEmployeeCelebrations.as_view()), # wishes
    path("DisplayEmployeeCelebrations",DisplayEmployeeCelebrations.as_view()), #display wishes

    path("RecCandidateFillingApplication",RecCandidateFillingApplication.as_view()),
    path('called_candidates/', CalledCandidatesListCreate.as_view(), name='called_candidates_list_create'),
    path("Called_Candidates_Search/<str:search_value>/",CalledCandidatesSearch.as_view()),
    path("Called_Candidates_Duration/<str:duration>/",CalledCandidatesSearch.as_view()),
    path('called_candidates/upload_excel/', UploadCalledCandidatesExcel.as_view(), name='upload_excel'),
    path('called_candidates/download_excel/', DownloadCalledCandidatesExcel.as_view(), name='download_excel'),

    # ...............PANDAS DOWNLOAD.................
    path("PerticularAppliedCandidateDownload/<str:can_id>/",PerticularAppliedCandidateDownload.as_view()),
    path("ScreeningDownload/<str:loginuser>/<str:can_id>",ScreeningAssignedCandidateDownload.as_view()),
    path("CompleteDetailsDownload/<str:can_id>/",CompleteFinalStatusDownloadView.as_view()),

    # /////////////////// 
    path("ScreeningDownloadExcel",ScreeningDownloadExcel.as_view()),  
    path("InterviewDownloadExcel",InterviewDownloadExcel.as_view()),
    path("FinalDownloadExcel",FinalDownloadExcel.as_view()),
    path("SelectedFinalResultDownloadExcel/<str:selected_list>/",download.as_view()),

    path("hired_candidates/<str:duration>/",Candidates_Hired_Filter_View.as_view()),
    path("client_candidates/<str:duration>/",Candidates_Client_Filter_View.as_view()),
    path("rejected_candidates/<str:duration>/",Candidates_Rejected_Filter_View.as_view()),

    path("Applied_Candidate_Filter",Candidate_Model_Filter.as_view()),
    path("FinalCandidatelist",Final_Candidate_Model_Filter.as_view()),

    path("InterviewScheduledSearch/<str:search_value>/<str:employee>/",InterviewScheduleSearchView.as_view()),
    path("Interview_filter/<str:Status>/<str:duration>//<str:employee>/",InterviewScheduleSearchView.as_view()),
    path("ScreeningScheduleSearch/<str:search_value>/<str:src_status>/", ScreeningScheduleSearchView.as_view()),
    path("Screening_filter/<str:src_status>/<str:duration>/",ScreeningScheduleSearchView.as_view()),

    path("FinalStatusView",FinalStatusView.as_view()),

   
    path("Telephonic_Round_Status_List/<str:loginuser>/",Telephonic_Round_StatusView.as_view()),
    path("TRS_List_Separation/<str:Employee>/<str:scr_status>/",Telephonic_Round_StatusView.as_view()),
    path('Screening_Schedule_Data/<str:can_id>/<int:screener>/',Telephonic_Round_StatusView.as_view()),

    path("Interview_Schedule_List/<str:loginuser>/",Interview_Schedule_StatusView.as_view()),
    path("IS_List_Separation/<str:Employee>/",Interview_Schedule_StatusView.as_view()),
    path("Interview_Schedule_Data/<str:can_id>/",Interview_Schedule_StatusView.as_view()),
    #///////////////////////////////////////////
    # path("bulk-interview-call-upload", BulkInterviewCallUploadView.as_view(), name="bulk-interview-upload"),
    #changes
    path("bulk-activity-upload", BulkActivityUploadView.as_view(), name="bulk-activity-upload"),
    path("download-activity-template", DownloadActivityTemplateView.as_view(), name="download-activity-template"),

    
    path("notifications", NotificationListView.as_view(), name="notification-list"),
    path("notifications/mark-as-read", MarkNotificationsAsReadView.as_view(), name="notification-mark-read"),
    path("notifications/delete/<int:notification_id>", NotificationDeleteView.as_view(), name="notification-delete"),
    path("notifications/clear-all", ClearAllNotificationsView.as_view(), name="notification-clear-all"),

    path("activity-dashboard-analytics", ActivityDashboardAnalyticsView.as_view(), name="activity-dashboard-analytics"),
    path("activity-dashboard-details", ActivityDashboardDetailsView.as_view(), name="activity-dashboard-details"),

    #28-01-2026
    # Follow-up management endpoints
    path("activity/convert-to-followup", ConvertToFollowUpView.as_view(), name="convert-to-followup"),
    path("activity/pending-followups", PendingFollowUpsView.as_view(), name="pending-followups"),
    path("activity/completed-followups", CompletedFollowUpsView.as_view(), name="completed-followups"),
    path("activity/followup/<int:followup_id>/action", FollowUpActionView.as_view(), name="followup-action"),

    # Activity pagination endpoints (29-01-2026)
    path("activity/total-activities", TotalActivitiesView.as_view(), name="total-activities"),
    path("activity/successful-outcomes", SuccessfulOutcomesView.as_view(), name="successful-outcomes"),
    path("activity/rejected", RejectedLeadsView.as_view(), name="rejected-leads"),
    path("activity/closed", ClosedLeadsView.as_view(), name="closed-leads"),
    path("activity/interview-calls", InterviewCallsView.as_view(), name="interview-calls"),
    path("activity/client-calls", ClientCallsView.as_view(), name="client-calls"),
    path("activity/job-posts", JobPostsView.as_view(), name="job-posts"),
    path("activity/lead-log/<int:activity_id>", LeadActivityLogView.as_view(), name="lead-activity-log"),

    path("interview-dashboard-summary/<str:employee_id>", InterviewActivitySummaryView.as_view(), name="interview-dashboard-summary"),
    path("employee-interview-dashboard/<str:employee_id>", EmployeeInterviewDashboardView.as_view(), name="employee-interview-dashboard"),

    #changes2
    path("public/submit-candidate-form", PublicCandidateInterviewCallView.as_view(), name="public-candidate-form"),

##################################################################
    # URLs for HR Managers: e.g., /api/manage/jobs/
    path('manage/', include(manage_router.urls)),
    
    # URLs for the external CRM service: e.g., /api/public/jobs/
    path('public/', include(public_router.urls)),

    

    
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)






