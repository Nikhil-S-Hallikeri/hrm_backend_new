from django.db import models
# Create your models here.
# from HRM_App.models import CandidateApplicationModel,EmployeeDataModel,InterviewSchedulModel,Review
import os
import uuid
from django.utils import timezone
# Client Model

def client_id():
    return "MTM"+str(uuid.uuid4().hex)[:7].upper()

class OurClients(models.Model):
    
    CLIENT_TYPE_CHOICES = [
        ("paid", 'Paid'),
        ("unpaid", 'Unpaid')
    ]
    client_id = models.CharField(max_length=255,default=client_id,unique=True)
    client_name = models.CharField(max_length=255,blank=True, null=True)
    client_email = models.EmailField(blank=True, null=True)
    alternative_emails = models.EmailField(blank=True, null=True)
    client_phone = models.CharField(max_length=15,blank=True, null=True)
    alternative_phone = models.CharField(max_length=15, blank=True, null=True)
    company_name=models.CharField(max_length=150, blank=True, null=True)
    gst_number = models.CharField(max_length=50,blank=True, null=True)
    company_address = models.TextField(blank=True, null=True)
    client_type = models.CharField(max_length=10, choices=CLIENT_TYPE_CHOICES)
    terms_and_conditions = models.BooleanField(default=False)
    registered_on = models.DateTimeField(auto_now_add=True)
    verified_on = models.DateTimeField(blank=True, null=True)
    client_status = models.BooleanField(default=False)

    def __str__(self):
        return self.client_name
    
class ClientsDocumentsModel(models.Model):
    client=models.ForeignKey(OurClients,on_delete=models.CASCADE,blank=True,null=True)
    document_proof=models.FileField(upload_to="client_documents",blank=True, null=True)
    upload_date = models.DateTimeField(default=timezone.localtime)

    def save(self,*args,**kwargs):
        if self.pk:
            old_file=ClientsDocumentsModel.objects.get(pk=self.pk).document_proof
            if old_file and old_file != self.document_proof:
                if os.path.isfile(old_file.path):
                    os.remove(old_file)

        super(ClientsDocumentsModel,self).save(*args,**kwargs)

# Requirement Model
class Requirement(models.Model):
    client = models.ForeignKey(OurClients, on_delete=models.CASCADE)
    job_title = models.CharField(max_length=255,blank=True, null=True)
    job_description = models.TextField(blank=True, null=True)
    open_positions = models.IntegerField(default=0,blank=True, null=True)
    hiring_start_date = models.DateField(blank=True, null=True)
    hiring_end_date = models.DateField(blank=True, null=True)
    package_min = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    package_max = models.DecimalField(max_digits=10, decimal_places=2,blank=True, null=True)
    experience_min = models.IntegerField(blank=True, null=True)
    experience_max = models.IntegerField(blank=True, null=True)
    required_skills = models.TextField(blank=True, null=True)
    qualification = models.TextField(blank=True, null=True)
    job_location = models.CharField(max_length=255,blank=True, null=True)
    added_on=models.DateTimeField(default=timezone.localtime)
    added_by=models.CharField(max_length=100,blank=True,null=True)
    
    def __str__(self):
        return self.job_title

# Requirement Assign Model

# class RequirementAssign(models.Model):
#     client = models.ForeignKey(OurClients, on_delete=models.CASCADE,blank=True, null=True)
#     requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE,blank=True, null=True)
#     assigned_to_recruiter = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='assigned_recruiter',blank=True, null=True)
#     assigned_by_employee = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='assigned_by',blank=True, null=True)
#     assigned_on = models.DateTimeField(default=timezone.localtime)
#     position_count = models.IntegerField(default=0,blank=True, null=True)


#     def __str__(self):
#         return f"Assignment for {self.requirement.job_title}" 
    
# # Interview Schedule Model
# class InterviewSchedule(models.Model):
#     requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
#     candidate = models.ForeignKey(CandidateApplicationModel, on_delete=models.CASCADE)
#     assigned_to_client = models.ForeignKey(OurClients, on_delete=models.CASCADE)
#     assigned_by_employee = models.ForeignKey(User, on_delete=models.CASCADE)
#     assigned_on = models.DateTimeField(auto_now_add=True)

#     def __str__(self):
#         return f"Interview for {self.candidate}"

# # Interview Review Model
# class InterviewReview(models.Model):
#     LINED_UP = 'lined_up'
#     SHORTLISTED = 'shortlisted'
#     REJECTED = 'rejected'
#     OFFERED = 'offered'
#     ACCEPTED = 'accepted'
#     REJECTED_OFFER = 'rejected_offer'
    
#     REVIEW_STATUS_CHOICES = [
#         (LINED_UP, 'Lined Up'),
#         (SHORTLISTED, 'Shortlisted'),
#         (REJECTED, 'Rejected'),
#         (OFFERED, 'Offered - Accept/Reject'),
#         (ACCEPTED, 'Accepted'),
#         (REJECTED_OFFER, 'Rejected Offer')
#     ]
#     interview = models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE)
#     review_status = models.CharField(max_length=20, choices=REVIEW_STATUS_CHOICES)
#     reviewed_on = models.DateField()
#     joining_date = models.DateField()
#     def __str__(self):
#         return f"Review for {self.interview}"

# # Joining History Model
# class JoiningHistory(models.Model):
#     candidate = models.ForeignKey(CandidateApplicationModel, on_delete=models.CASCADE)
#     review = models.ForeignKey(InterviewReview, on_delete=models.CASCADE)
#     date_of_join = models.DateField()
#     remarks = models.TextField(blank=True, null=True)
#     active = models.BooleanField(default=True)
    
#     def __str__(self):
#         return f"Joining of {self.candidate}"

# # Invoice Model
# class Invoice(models.Model):
#     our_company_profile = models.ForeignKey('CompanyProfile', on_delete=models.CASCADE, related_name='our_company')
#     client_company_profile = models.ForeignKey(OurClients, on_delete=models.CASCADE, related_name='client_company')
#     requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
#     candidate = models.ForeignKey(CandidateApplicationModel, on_delete=models.CASCADE)
#     gst_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     total_amount = models.DecimalField(max_digits=10, decimal_places=2)
#     generated_on = models.DateTimeField(auto_now_add=True)
#     generated_by = models.ForeignKey(User, on_delete=models.CASCADE)

#     def __str__(self):
#         return f"Invoice for {self.client_company_profile.client_name}"

# # Payment/Receipt Model
# class Payment(models.Model):
#     requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE)
#     joining_history = models.ForeignKey(JoiningHistory, on_delete=models.CASCADE)
#     total_payment = models.DecimalField(max_digits=10, decimal_places=2)
#     payment_status = models.CharField(max_length=20)
#     paid_on = models.DateField()

#     def __str__(self):
#         return f"Payment for {self.requirement.job_title}"

# # Candidate Model
# class Candidate(models.Model):
#     candidate_id = models.AutoField(primary_key=True)
#     full_name = models.CharField(max_length=255)
#     email = models.EmailField()
#     phone = models.CharField(max_length=15)
#     experience_years = models.IntegerField()
#     skills = models.TextField()

#     def __str__(self):
#         return self.full_name

# # Company Profile Model (for our company profile)
# class CompanyProfile(models.Model):
#     company_name = models.CharField(max_length=255)
#     company_address = models.TextField()
#     gst_number = models.CharField(max_length=50)

#     def __str__(self):
#         return self.company_name





















# from HRM_App.models import EmployeeDataModel,WishNotifications
# from django.db.models import Q
# import threading
# from datetime import datetime, date
# import time 
# from django.core.mail import send_mail
# from .imports import *
# from django.utils import timezone
# from rest_framework import response
# from LMS_App.models import CompanyHolidaysDataModel,LeaveRequestForm
# from LMS_App.serializers import CompanyHolidaysDataModelSerializer,LeaveRequestFormSerializer
# from EMS_App.serializers import ResignationSerializer
# from datetime import datetime, date
# import time 
# from datetime import timedelta
# from django.utils.timezone import make_aware, localdate, get_current_timezone
# from django.core.mail import EmailMultiAlternatives
# from django.utils import timezone
# from django.db.models import Q
        
# from django.db.models.functions import ExtractMonth, ExtractDay

# from EMS_App.models import EmployeePersonalInformation ,ResignationModel

# from django.core.mail import EmailMultiAlternatives


# from pytz import timezone as pytz_timezone
# from datetime import datetime, date
# import time 

# from django.utils import timezone
# from LMS_App.attendance_view import EmployeesAttendanceStatusUpdating


# from datetime import datetime, date
# import time 
# from django.utils.timezone import make_aware