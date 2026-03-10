from django.contrib import admin
from .models import *

# Register your models here.

admin.site.register(RegistrationModel)
admin.site.register(EmployeeDataModel)
admin.site.register(EmployeeShifts_Model)
# admin.site.register(EmployeeWeekoffs_Model)
admin.site.register(InterviewSchedulModel)
admin.site.register(ScreeningAssigningModel)

class ReviewAdmin(admin.ModelAdmin):
    search_fields=["CandidateId__CandidateId",'ReviewedDate','ReviewedBy','Screening_Status']
    list_filter = ('ReviewedDate','ReviewedBy',)  # Adds a filter for ReviewedDate in the sidebar
admin.site.register(Review, ReviewAdmin)

admin.site.register(Documents_Upload_Model)
admin.site.register(Documents_Model)
admin.site.register(InterviewScheduleStatusModel)
admin.site.register(Notification)
admin.site.register(BG_VerificationModel)
admin.site.register(OfferLetterModel)
admin.site.register(LetterTemplatesModel)
admin.site.register(DesignationModel)
admin.site.register(Deparments)
#admin.site.register(HRFinalStatusModel)
admin.site.register(CalledCandidatesModel)
admin.site.register(WishNotifications)
admin.site.register(EmployeeIDTracker)

class HRFinalStatusAdmin(admin.ModelAdmin):
    search_fields=["ReviewedOn","ReviewedBy","Final_Result"]
admin.site.register(HRFinalStatusModel,HRFinalStatusAdmin)


class CandidateApplicationAdmin(admin.ModelAdmin):
    search_fields=["CandidateId","FirstName","pk",'Email']
    list_display=["CandidateId"]
    list_filter = ('Email',)

admin.site.register(CandidateApplicationModel,CandidateApplicationAdmin)

admin.site.register(Activity)
admin.site.register(DailyAchives)
admin.site.register(InterviewSchedule)
admin.site.register(DailyAchivesInterviewSchedule)
admin.site.register(WalkIns)
admin.site.register(OfferedPosition)


# new activitys
admin.site.register(ActivityListModel)
admin.site.register(NewActivityModel)
admin.site.register(MonthAchivesListModel)
admin.site.register(NewDailyAchivesModel)


