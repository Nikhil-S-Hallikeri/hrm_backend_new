from django.contrib import admin

# Register your models here.

from .models import *

# Register your models here

admin.site.register(ResignationModel)
admin.site.register(ExitDetailsModel)


@admin.register(EmployeeInformation)
class EmployeeInformationAdmin(admin.ModelAdmin):
    list_filter = (
        ('ProfileVerification', admin.EmptyFieldListFilter), 
    )
    search_fields = ["Candidate_id__pk",]  # Searching by Candidate primary key
    autocomplete_fields = ['Candidate_id']  # Enable searchable dropdown for ForeignKey
    

@admin.register(EmployeeEducation)
class EmployeeEducationAdmin(admin.ModelAdmin):
    pass

@admin.register(FamilyDetails)
class FamilyDetailsAdmin(admin.ModelAdmin):
    pass

@admin.register(EmergencyDetails)
class EmergencyDetailsAdmin(admin.ModelAdmin):
    pass

@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    pass

@admin.register(CandidateReference)
class CandidateReferenceAdmin(admin.ModelAdmin):
    pass

@admin.register(ExceperienceModel)
class ExceperienceModelAdmin(admin.ModelAdmin):
    pass

@admin.register(Last_Position_Held)
class Last_Position_HeldAdmin(admin.ModelAdmin):
    pass

@admin.register(EmployeePersonalInformation)
class EmployeePersonalInformationAdmin(admin.ModelAdmin):
    pass

@admin.register(EmployeeIdentity)
class EmployeeIdentityAdmin(admin.ModelAdmin):
    pass

@admin.register(BankAccountDetails)
class BankAccountDetailsAdmin(admin.ModelAdmin):
    pass

@admin.register(PFDetails)
class PFDetailsAdmin(admin.ModelAdmin):
    pass

@admin.register(AditionalInformationModel)
class AditionalInformationModelAdmin(admin.ModelAdmin):
    pass

@admin.register(AttachmentsModel)
class AttachmentsModelAdmin(admin.ModelAdmin):
    pass

@admin.register(Declaration)
class DeclarationAdmin(admin.ModelAdmin):
    pass

admin.site.register(ReligionModels)
admin.site.register(PaySlip)
admin.site.register(CompanyEmployeesPositionHistory)