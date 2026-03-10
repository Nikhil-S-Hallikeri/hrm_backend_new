from django.contrib import admin
# Register your models here.
from LMS_App.models import *

admin.site.register(LeaveTypesModel)
admin.site.register(LeavesTypeDetailModel)
admin.site.register(EmployeeLeaveTypesEligiblity)
admin.site.register(LeaveRequestForm)
admin.site.register(EmployeesLeavesmodel)
admin.site.register(MonthWiseLeavesModel)
admin.site.register(CompanyAttendance)
#admin.site.register(CompanyAttendanceDataModel)

class CompanyAttendanceDataAdmin(admin.ModelAdmin):
    # Fields to display as filters in the admin panel
    list_filter = ['date',]

admin.site.register(CompanyAttendanceDataModel, CompanyAttendanceDataAdmin)

admin.site.register(AvailableRestrictedLeaves)
admin.site.register(CompanyHolidaysDataModel)

admin.site.register(WeekOffDay)
admin.site.register(EmployeeWeekoffsModel)


admin.site.register(AppraisalInvitationModel)

admin.site.register(EmployeeSelfEvaluation)
admin.site.register(EmployeeSelfEvaluationReviewModel)
admin.site.register(Performance_Metrics_Model)
