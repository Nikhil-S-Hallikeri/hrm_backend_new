from django.db import models
# .................................................................Employee management system .............................................................. 
from django.core.validators import RegexValidator, EmailValidator
from django.utils import timezone
import uuid
from HRM_App.models import *
from HRM_App.models import EmployeeInformation

class ReligionModels(models.Model):
    religion_name=models.CharField(max_length=100)

class EmployeeEducation(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    Qualification= models.CharField(max_length=100, blank=True)
    University= models.CharField(max_length=100, blank=True)
    year_of_passout=models.DateField(default=timezone.localdate,blank=True)
    Persentage=models.CharField(max_length=100, blank=True)
    Major_Subject=models.CharField(max_length=100, blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

# Family Details
class FamilyDetails(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    name = models.CharField(max_length=100,blank=True)
    relation = models.CharField(max_length=50,blank=True)
    dob = models.DateField(blank=True)
    age = models.PositiveSmallIntegerField(blank=True)
    blood_group = models.CharField(max_length=10,blank=True)
    gender = models.CharField(max_length=10,blank=True)
    profession = models.CharField(max_length=100,blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

# Emergency Details
class EmergencyDetails(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    blood_group = models.CharField(max_length=100,blank=True)
    allergic_to = models.CharField(max_length=50,blank=True)
    blood_pessure= models.CharField(max_length=50,blank=True)
    Diabetics= models.CharField(max_length=50,blank=True)
    other_illness=models.TextField(blank=True,null=True)
    decleration=models.BooleanField(default=False)

    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

# Emergency Contact
class EmergencyContact(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    person_name = models.CharField(max_length=100,blank=True)
    relation = models.CharField(max_length=50,blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100,blank=True)
    state = models.CharField(max_length=100,blank=True)
    city = models.CharField(max_length=100,blank=True)
    pincode = models.CharField(max_length=10,blank=True)
    phone = models.CharField(max_length=15,blank=True)
    landline=models.CharField(max_length=15,blank=True,null=True)
    email = models.EmailField(blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

class CandidateReference(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    person_name = models.CharField(max_length=100,blank=True)
    relation = models.CharField(max_length=50,blank=True)
    # address = models.TextField(blank=True)
    # country = models.CharField(max_length=100,blank=True)
    # state = models.CharField(max_length=100,blank=True)
    # city = models.CharField(max_length=100,blank=True) 
    # pincode= models.CharField(max_length=100,blank=True)
    phone = models.CharField(max_length=15,blank=True)
    email = models.EmailField(blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

# Experience (Chronological Order Excluding Last position)

class ExceperienceModel(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    organisation=models.CharField(max_length=100, blank=True)
    #Period
    from_date  = models.DateField(null=True, blank=True)
    to_date = models.DateField(null=True, blank=True)
    # Designation
    last_possition_held=models.CharField(max_length=100, blank=True)
    at_the_time_of_joining=models.CharField(max_length=100, blank=True)

    job_responsibility=models.CharField(max_length=100, blank=True)
    immediate_superior_designation=models.CharField(max_length=100, blank=True)
    gross_salary_drawn=models.CharField(max_length=100, blank=True)
    reason_for_leaving=models.CharField(max_length=100, blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

class Last_Position_Held(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    organisation=models.CharField(max_length=100, blank=True,null=True)
    designation=models.CharField(max_length=100, blank=True,null=True)
    address=models.TextField(blank=True)
    # repoting_to
    repoting_to_name=models.CharField(max_length=100, blank=True,null=True)
    repoting_to_designation=models.CharField(max_length=100, blank=True,null=True)
    repoting_to_email=models.CharField(max_length=100, blank=True,null=True)
    repoting_to_phone=models.CharField(max_length=100, blank=True,null=True)
    gross_salary_per_month=models.CharField(max_length=100, blank=True,null=True)
    # cash benefits
    basic=models.CharField(max_length=100, blank=True,null=True)
    HRA=models.CharField(max_length=100, blank=True,null=True)
    LTA=models.CharField(max_length=100, blank=True,null=True)
    DA=models.CharField(max_length=100, blank=True,null=True)
    medical=models.CharField(max_length=100, blank=True,null=True)
    conveyance=models.CharField(max_length=100, blank=True,null=True)
    others=models.CharField(max_length=100, blank=True,null=True)
    total=models.CharField(max_length=100, blank=True,null=True)
    # non-cash benefits
    provident_fund=models.CharField(max_length=100, blank=True,null=True)
    gratuity=models.CharField(max_length=100, blank=True,null=True)
    non_cash_others=models.CharField(max_length=100, blank=True,null=True)
    non_cash_total=models.CharField(max_length=100, blank=True,null=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)
    
# Employee Personal Information
class EmployeePersonalInformation(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    blood_group = models.CharField(max_length=10,blank=True, null=True)
    # fathers_name = models.CharField(max_length=100,blank=True, null=True)
    marital_status = models.CharField(max_length=20,blank=True, null=True)
    marriage_date = models.DateField(null=True, blank=True)
    spouse_name = models.CharField(max_length=100, blank=True, null=True)
    nationality = models.CharField(max_length=100,blank=True, null=True)
    residential_status = models.CharField(max_length=100,blank=True, null=True)
    place_of_birth = models.CharField(max_length=100,blank=True, null=True)
    country_of_origin = models.CharField(max_length=100,blank=True, null=True)
    religion = models.ForeignKey(ReligionModels,on_delete=models.CASCADE,blank=True,null=True)
    international_employee = models.BooleanField(default=True,blank=True, null=True)
    physically_challenged = models.BooleanField(default=True,blank=True, null=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True, null=True)

# Employee Identity
from django.core.validators import RegexValidator
from django.db.models.signals import post_delete
from django.dispatch import receiver
import os

class EmployeeIdentity(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    aadhar_no = models.CharField(max_length=12, validators=[RegexValidator(r'^\d{12}$')],blank=True)
    name_as_per_aadhar = models.CharField(max_length=100,blank=True)
    aadher_proof=models.FileField(upload_to="EmployeeDocuments/aadher_folder/",blank=True)
    pan_no = models.CharField(max_length=100,blank=True)
    pan_proof=models.FileField(upload_to="EmployeeDocuments/pancard_folder/",blank=True)
    passport_num=models.CharField(max_length=100, blank=True,null=True)
    validate=models.DateField(blank=True,null=True)
    passport_proof=models.FileField(upload_to="EmployeeDocuments/passport_folder/",blank=True,null=True)
    driving_license=models.FileField(upload_to="EmployeeDocuments/passport_folder/",blank=True,null=True)
    voter_id=models.FileField(upload_to="EmployeeDocuments/passport_folder/",blank=True,null=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

@receiver(post_delete, sender=EmployeeIdentity)
def delete_files_on_instance_delete(sender, instance, **kwargs):
    if instance.aadher_proof:
        if os.path.isfile(instance.aadher_proof.path):
            a=instance.aadher_proof.path
            os.remove(instance.aadher_proof.path)
    
    # Delete pan_proof file if it exists
    if instance.pan_proof:
        if os.path.isfile(instance.pan_proof.path):
            os.remove(instance.pan_proof.path)
    
    if instance.driving_license:
        if os.path.isfile(instance.driving_license.path):
            os.remove(instance.driving_license.path)

    if instance.voter_id:
        if os.path.isfile(instance.voter_id.path):
            os.remove(instance.voter_id.path)

    if instance.passport_proof:
        if os.path.isfile(instance.passport_proof.path):
            os.remove(instance.passport_proof.path)

# Bank Account Details
class BankAccountDetails(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    Holder_Name=models.CharField(max_length=100,blank=True,null=True)
    bank_name = models.CharField(max_length=100,blank=True)
    account_no = models.CharField(max_length=20,blank=True)#, validators=[RegexValidator(r'^\d{9,18}$')]
    ifsc = models.CharField(max_length=11,blank=True)
    branch_address=models.TextField(blank=True)
    branch= models.CharField(max_length=1000,blank=True)
    account_proof=models.FileField(upload_to="EmployeeDocuments/accoun_folder/",blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

# PF Details
class PFDetails(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    employee_is_covered_under_pf = models.BooleanField(default=False)
    uan = models.CharField(max_length=12,blank=True,null=True)
    pf = models.CharField(max_length=20,blank=True,null=True)
    pf_join_date = models.DateField(blank=True,null=True)
    # family_pf_no = models.CharField(max_length=20,blank=True,null=True)
    is_existing_number_of_eps = models.BooleanField(blank=True,null=True)
    allow_epf_excess_contribution = models.BooleanField(blank=True,null=True)
    allow_eps_excess_contribution = models.BooleanField(blank=True,null=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

class AditionalInformationModel(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    # have you
    ch=(("yes","YES"),("no","No"))
    marital_ineptness=models.CharField(max_length=100,choices=ch)
    court_proceeding=models.CharField(max_length=100,choices=ch)
    # if yes
    details=models.TextField(blank=True)
    language_known=models.TextField(blank=True)
    hobbies=models.TextField(blank=True)
    intrests=models.TextField(blank=True)
    goals_or_aims=models.TextField(blank=True)
    three_principles1=models.CharField(max_length=100,blank=True)
    three_principles2=models.CharField(max_length=100,blank=True)
    three_principles3=models.CharField(max_length=100,blank=True)
    strengths1=models.CharField(max_length=100,blank=True)
    strengths2=models.CharField(max_length=100,blank=True)
    strengths3=models.CharField(max_length=100,blank=True)
    weaknesses1=models.CharField(max_length=100,blank=True)
    weaknesses2=models.CharField(max_length=100,blank=True)
    weaknesses3=models.CharField(max_length=100,blank=True)
    # willing_to_travel
    in_india=models.CharField(max_length=100,choices=ch,blank=True)
    in_abroad=models.CharField(max_length=100,choices=ch,blank=True)
    state_restrictions=models.TextField(blank=True)
    # passport_num=models.CharField(max_length=100, blank=True)
    # validate=models.DateField(blank=True,null=True)
    # passport_proof=models.FileField(upload_to="EmployeeDocuments/passport_folder/",blank=True)
    employee_relation=models.CharField(max_length=100, blank=True)
    association=models.CharField(max_length=100, blank=True)
    publication=models.CharField(max_length=100, blank=True)
    specialized_training=models.CharField(max_length=100, blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

class AttachmentsModel(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    Degree_mark_sheets=models.FileField(upload_to="EmployeeDocuments/Degree_mark_sheets/",blank=True,null=True)
    Offer_letter_copy=models.FileField(upload_to="EmployeeDocuments/Offer_letter_copy/",blank=True,null=True)
    upload_photo=models.ImageField(upload_to="EmployeeDocuments/employee_images/",blank=True,null=True)
    present_address_proof=models.FileField(upload_to="EmployeeDocuments/present_address_proof/",blank=True,null=True)
    permanent_address_proof=models.FileField(upload_to="EmployeeDocuments/address_proof/",blank=True,null=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)


    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        documents = {
            'Degree Mark Sheets': self.Degree_mark_sheets,
            'Offer Letter Copy': self.Offer_letter_copy,
            'Upload Photo': self.upload_photo,
            'Present Address Proof': self.present_address_proof,
            'Permanent Address Proof': self.permanent_address_proof
        }
        for doc_type, file_field in documents.items():
            doc_instance, created = Documents_Submited.objects.get_or_create(
                EMP_Information=self.EMP_Information,
                Document=doc_type
            )
            if file_field:
                doc_instance.submitted = True
                doc_instance.submitted_date = timezone.localtime()
            else:
                doc_instance.submitted = False
                doc_instance.submitted_date = None
            doc_instance.save()

class Documents_Submited(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    Document=models.CharField(max_length=100, blank=True,null=True)
    submitted=models.BooleanField(default=False)
    submitted_date=models.DateTimeField(blank=True,null=True)
    will_submit_date=models.DateField(blank=True,null=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)

    # def save(self, *args, **kwargs):
    #     if self.submitted==True:
    #         self.submitted_date=timezone.localtime()
    #     super().save(*args, **kwargs)

class Declaration(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    name=models.CharField(max_length=100, blank=True)
    date=models.DateField(blank=True)
    place=models.CharField(max_length=100, blank=True)
    signature=models.ImageField(upload_to="EmployeeDocuments/Signature/",blank=True)
    is_verified=models.BooleanField(default=False)
    reason=models.TextField(blank=True)
    
class EmployeeAssetsModel(models.Model):
    EMP_Information=models.ForeignKey(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    ch=(('Hardware','Hard ware'),('Software','Soft ware'))
    assets_type=models.CharField(max_length=20,blank=True,null=True,choices=ch)
    assets_ch=[
    ('official_mail_id', 'Official Mail ID'),
    ('portals', 'Portals'),
    ('social_media_credentials', 'Social Media Credentials'),
    ('official_data', 'Official Data'),
    ('sim_card', 'SIM Card'),
    ('id_card', 'ID Card'),
    ('others', 'Others'),]

    asset_name=models.CharField(max_length=500,blank=True,null=True,choices=assets_ch)
    added_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    added_on=models.DateTimeField(default=timezone.localtime)


from LMS_App.models import EmployeeSelfEvaluation

class CompanyEmployeesPositionHistory(models.Model):
    Appraisal_instance=models.ForeignKey(EmployeeSelfEvaluation,on_delete=models.CASCADE,blank=True,null=True)
    employee = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, blank=True, null=True)
    designation = models.ForeignKey(DesignationModel, on_delete=models.CASCADE, blank=True, null=True)
    das_position = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    rm_manager = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, blank=True, null=True,related_name="rm_manager")
    responsibilities = models.TextField(blank=True, null=True)
    achievements = models.TextField(blank=True, null=True)
    reason_for_change = models.TextField(blank=True, null=True)
    start_date = models.DateField(default=timezone.localdate)
    
    assigned_salary = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # New Field
    salary_changes = models.TextField(blank=True, null=True)  # New Field
    comments = models.TextField(blank=True, null=True)

    choice=(("intern","Intern"),("permanent","permanent"))
    Employeement_Type=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    #if intern
    internship_Duration_From=models.DateField(blank=True,null=True)
    internship_Duration_To=models.DateField(blank=True,null=True)

    choice=(("probationer","Probationer"),("confirmed","Confirmed"))
    probation_status= models.CharField(max_length=100, blank=True, null=True, choices=choice)
    # #if probation
    probation_Duration_From=models.DateField(blank=True,null=True)
    probation_Duration_To=models.DateField(blank=True,null=True)

    is_applicable=models.BooleanField(default=False)
    applicable_date=models.DateField(blank=True,null=True)


    def save(self, *args, **kwargs):
        # Get the latest instance for the same employee if it exists
        if self.pk is None:  # New instance
            latest_instance = CompanyEmployeesPositionHistory.objects.filter(employee=self.employee).order_by('-applicable_date').first()
            if latest_instance:
                latest_instance.is_applicable = False
                latest_instance.save() 
        else:  # Updating existing instance
            previous_instance = CompanyEmployeesPositionHistory.objects.filter(pk=self.pk).first()
            if previous_instance and previous_instance.employee != self.employee:
                # If changing the employee, reset applicability for the old employee
                old_latest_instance = CompanyEmployeesPositionHistory.objects.filter(employee=previous_instance.employee).order_by('-applicable_date').first()
                if old_latest_instance and old_latest_instance.pk != self.pk:
                    old_latest_instance.is_applicable = False
                    old_latest_instance.save()
            
            latest_instance = CompanyEmployeesPositionHistory.objects.filter(employee=self.employee).order_by('-applicable_date').first()
            if latest_instance and latest_instance.pk != self.pk:
                latest_instance.is_applicable = False
                latest_instance.save()

        super().save(*args, **kwargs)

        # Ensure that the current instance is marked as applicable
        if self.is_applicable:
            self.is_applicable = True
            super().save(*args, **kwargs)

    
    def __str__(self):
        return f"{self.employee}"
    

    # class Meta:
    #     verbose_name_plural = "Employee Position Histories"
    #     ordering = ['-start_date']


class EmployeeSalaryModel(models.Model):
    EMP_Information=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    AnnualCTC=models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    MonthlyCTC=models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)


    def save(self, *args, **kwargs):
        if self.EMP_Information and self.AnnualCTC:
            self.MonthlyCTC = self.AnnualCTC / 12
        super().save(*args, **kwargs)

class CompanyProfile(models.Model):
    company_name=models.CharField(max_length=1000)
    description = models.TextField(blank=True,null=True)
    location=models.TextField(blank=True,null=True)
    CEO=models.CharField(max_length=1000)
    Company_Head=models.CharField(max_length=1000)
    Company_logo=models.FileField(upload_to='Company_files/Company_logo/',blank=True,null=True)

class CompanyPolicy(models.Model):
    POLICY_CATEGORIES = [
        ('Category1', 'Category 1')
        # Add more categories as needed
    ]
    policy_name = models.CharField(max_length=100)
    description = models.TextField(blank=True,null=True)
    serial_no = models.CharField(max_length=20, unique=True,blank=True,null=True)
    company_policy_category = models.CharField(max_length=20, choices=POLICY_CATEGORIES,blank=True,null=True) 
    upload_file = models.FileField(upload_to='policy_files/',blank=True,null=True)
    # Employee filter based on who is applicable for this policy
    # Assuming there's a ForeignKey relationship between Policy and User (Employee)
    applicable_employees = models.ManyToManyField(EmployeeDataModel, related_name='applicable_policies',blank=True)
    def __str__(self):
        return self.policy_name
    
class CompanyMassMailsSendedModel(models.Model):
    employees_list=models.ManyToManyField(EmployeeDataModel,blank=True,null=True)
    attachment=models.FileField(upload_to='mail_attachments/',blank=True,null=True)
    mail_sended_by=models.ForeignKey(EmployeeDataModel,blank=True,null=True,on_delete=models.CASCADE,related_name="mail_sended_by")
    maill_sended_on=models.DateTimeField(default=timezone.localtime)

class ResignationModel(models.Model):
    employee_id = models.ForeignKey(EmployeeDataModel,on_delete=models.SET_NULL,blank=True,null=True,related_name="elemployee")
    name = models.CharField(max_length=100,blank=True,null=True)
    position = models.CharField(max_length=100,blank=True,null=True)
    reason = models.TextField(blank=True,null=True)
    department = models.CharField(max_length=255,blank=True,null=True)

    st=[('voluntary', 'Voluntary'), ('involuntary', 'Involuntary')]
    separation_type = models.CharField(max_length=20,choices=st,default='voluntary')

    REASONS_FOR_LEAVING = [
    ('career_growth', 'Career Growth/Better Opportunity'),
    ('personal_reasons', 'Personal Reasons'),
    ('health_issues', 'Health Issues'),
    ('relocation', 'Relocation'),
    ('higher_education', 'Pursuing Higher Education'),
    ('high_pay', 'High Pay'),
    ('Death', 'Death'),
    ('retirement', 'Retirement'),
    ('layoff', 'Layoff/Company Downsizing'),
    ('performance', 'Performance Issues'),
    ('Dismissed', 'Dismissed'),
    ('contract_end', 'End of Contract'),
    ('misconduct', 'Misconduct'),
    ('end_of_internship', 'end of internship'),
    ('job_dissatisfaction', 'Job Dissatisfaction'),
    ('other', 'Other'),
    ]
    reason_for_leaving = models.CharField(max_length=50,choices=REASONS_FOR_LEAVING,blank=True,null=True)
    other_reason= models.CharField(max_length=500,blank=True,null=True)
    resigned_letter_file = models.FileField(upload_to='resignation_letters/',blank=True,null=True)
    Applied_On=models.DateField(default=timezone.localdate,null=True,blank=True)

    reporting_manager_name = models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="Manager")
    is_rm_verified=models.BooleanField(default=False)
    rm_remarks= models.TextField(blank=True,null=True)
    rm_verified_On=models.DateField(null=True,blank=True)
    # handover details
    # handover_details_request_to=models.CharField(max_length=100)
    handover_details_request_date=models.DateField(blank=True,null=True)
    ch=[("pending","Pending"),("assigned","Assigned"),("completed","Completed")]
    handover_details_status=models.CharField(max_length=100,blank=True,null=True,choices=ch,default='pending')
    handover_details_submitted_date=models.DateField(blank=True,null=True)

    HR_manager_name = models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="HR")
    is_hr_verified=models.BooleanField(default=False)
    hr_remarks= models.TextField(blank=True,null=True)
    hr_verified_On=models.DateField(null=True,blank=True)
    Interviewer=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="interviwer")
    Date_Of_Interview=models.DateField(null=True,blank=True)

    REJOIN_INTEREST_CHOICES = [('yes', 'Yes'),('no', 'No'),('maybe', 'Maybe')]
    
    rejoin_interest = models.CharField(max_length=10,choices=REJOIN_INTEREST_CHOICES,blank=True,null=True)

    liked_most = models.TextField(verbose_name="What did you like the most about the organization?",blank=True,null=True)
    improve_welfare = models.TextField(verbose_name="What can the organization do to improve staff welfare?",blank=True,null=True)
    additional_feedback = models.TextField(verbose_name="Anything else you wish to share with us?",blank=True,null=True)

    choice=(("approved","Approved"),("declined","Declined"),("pending","Pending"),("completed","Completed"),("ongoing","On Going"))
    resignation_verification = models.CharField(max_length=100,choices=choice,blank=True,null=True,default="pending")
    remarks= models.TextField(blank=True,null=True)
    
    def __str__(self):
        return f"Resignation of {self.employee_id.Name} (ID: {self.employee_id})"
    
    def save(self, *args, **kwargs):
        if self.Interviewer and self.Date_Of_Interview:

            sep_obj=ResignationModel.objects.filter(pk=self.pk).first()
            if not ExitDetailsModel.objects.filter(resignation__pk=self.pk).exists():
                data=ExitDetailsModel.objects.create(resignation=sep_obj)
                if data:
                    data.employment_start_date= self.employee_id.employeeProfile.hired_date if self.employee_id.employeeProfile else None
                    data.save()
                    
        super().save(*args, **kwargs)
    

class ExitDetailsModel(models.Model):
    resignation=models.ForeignKey(ResignationModel,on_delete=models.CASCADE,null=True,blank=True)
    EMPLOYEE_RATING_CHOICES = [
        ('outstanding', 'Outstanding'),
        ('verygood', 'Very Good'),
        ('satisfactory', 'Satisfactory'),
        ('fair', 'Fair'),
        ('unsatisfactory', 'Unsatisfactory'),
    ]
    employment_start_date = models.DateField(blank=True, null=True)
    employment_end_date = models.DateField(blank=True, null=True)
    accepted_another_position = models.BooleanField(null=True, blank=True,default=None)
    new_title = models.CharField(max_length=255, blank=True, null=True)
    new_organization_details=models.TextField(blank=True, null=True)
    additional_benefits = models.TextField(blank=True, null=True)

    career_goals_met = models.BooleanField(null=True, blank=True,default=None)
    spoke_with_manager_or_hr = models.BooleanField(null=True, blank=True,default=None)
    got_along_with_manager = models.BooleanField(null=True, blank=True,default=None)
    manager_issue_explanation = models.TextField(blank=True, null=True)
    supervisor_handling_complaints = models.TextField(blank=True, null=True)
    improvements_for_more_rewarding_job = models.TextField(blank=True, null=True)
    liked_best_about_job = models.TextField(blank=True, null=True)
    disliked_about_job = models.TextField(blank=True, null=True)
    # merida_good_place_to_work = models.TextField(blank=True, null=True)
    # merida_poor_place_to_work = models.TextField(blank=True, null=True)
    good_place_to_work = models.TextField(blank=True, null=True)
    poor_place_to_work = models.TextField(blank=True, null=True)

    job_responsibilities_rating = models.CharField(max_length=20, choices=EMPLOYEE_RATING_CHOICES,blank=True, null=True)
    achieving_goals_rating = models.CharField(max_length=20, choices=EMPLOYEE_RATING_CHOICES,blank=True, null=True)
    work_environment_rating = models.CharField(max_length=20, choices=EMPLOYEE_RATING_CHOICES,blank=True, null=True)
    manager_rating = models.CharField(max_length=20, choices=EMPLOYEE_RATING_CHOICES,blank=True, null=True)
    pay_rating = models.CharField(max_length=20, choices=EMPLOYEE_RATING_CHOICES,blank=True, null=True)
    benefits_rating = models.CharField(max_length=20, choices=EMPLOYEE_RATING_CHOICES,blank=True, null=True)

    would_rejoin = models.BooleanField(null=True, blank=True,default=None)
    recommendations = models.TextField(blank=True, null=True)
    would_have_stayed_if_satisfied = models.BooleanField(default=False)
    more_satisfactory_explanation = models.TextField(blank=True, null=True)

    submission_date = models.DateField(default=timezone.localdate)
    handed_over_to = models.CharField(max_length=100,blank=True, null=True)
    handed_over_signature_date = models.DateField(blank=True, null=True)

    Days_to_Serve_Notice=models.IntegerField(blank=True,null=True)
    notice_period_agrry=models.BooleanField(null=True, blank=True,default=None)
    compensation=models.IntegerField(blank=True,null=True)
    compensation_pay_agrry=models.BooleanField(null=True, blank=True,default=None)
    last_working_day=models.DateField(null=True,blank=True)
    # Date_to_Leave=models.DateField(default=timezone.localdate,null=True,blank=True)
    FitToBeRehired=models.BooleanField(null=True, blank=True,default=None)
    AlternateEmail=models.CharField(max_length=100,blank=True,null=True)
    AlternateMobile=models.CharField(max_length=100,blank=True,null=True)
    mail_sent=models.BooleanField(default=False)
    NoticedServed=models.BooleanField(null=True, blank=True,default=None)

    Retrenchment_Compensation=models.IntegerField(blank=True,null=True)
    leave_encashment=models.IntegerField(blank=True,null=True)
    salary_month=models.CharField(max_length=100,blank=True,null=True)
    grand_total=models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)

    Company_Loans=models.CharField(max_length=1000,blank=True,null=True)
    Other_Recoveries=models.TextField(blank=True,null=True)

    acknowledgement_receipt=models.FileField(upload_to="acknowledgement_receipt",blank=True,null=True)

    TotalSettlement=models.IntegerField(blank=True,null=True)
    SettledOn=models.DateField(null=True,blank=True)
    EmpLeftOrganization=models.BooleanField(null=True, blank=True,default=False)
    Date_of_Left_Organization=models.DateField(null=True,blank=True)
    # Required_letters=models.FileField(upload_to="Resignation_Certificates",blank=True)
    # is_required_letters_taken=models.BooleanField(default=False)
    # required_letters_taken_date=models.DateField(null=True,blank=True)

    # class Meta:
    #     unique_together = ("resignation",)

class HandoversDetails(models.Model):
    resignation=models.ForeignKey(ResignationModel,on_delete=models.CASCADE)
    handover_from = models.CharField(max_length=1000,null=True, blank=True)
    handover_title=models.CharField(max_length=500)
    description=models.TextField(blank=True,null=True)
    handover_to = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, null=True, blank=True)
    handover_ak_assigned_date=models.DateField(blank=True, null=True)
    assigned_handover_emp_accept_status=models.CharField(max_length=50, null=True, blank=True, choices=[('accepted', 'Accepted'), ('rejected', 'rejected'),('pending', 'Pending')])
    emp_accept_status_reason=models.TextField(blank=True,null=True)
    handover_ak_received_date=models.DateField(blank=True, null=True)
    handover_status = models.CharField(max_length=50, null=True, blank=True, choices=[('pending', 'Pending'), ('in_progress', 'In Progress'), ('completed', 'Completed')],default="pending")
    handover_ak_received_date=models.DateField(blank=True, null=True)
    handover_documents = models.FileField(upload_to='handovers/', blank=True, null=True)
    comments = models.TextField(blank=True, null=True) 

    def save(self, *args, **kwargs):
        if not self.handover_ak_assigned_date and self.handover_to:
            self.handover_ak_assigned_date= timezone.localdate()
            self.assigned_handover_emp_accept_status="pending"
        if self.resignation:
            self.handover_from=self.resignation.employee_id.Name
        if not self.assigned_handover_emp_accept_status=="pending":
            self.handover_ak_received_date= timezone.localdate()

        super().save(*args, **kwargs)



class AssetsClearance(models.Model):

    separation_information=models.OneToOneField(ExitDetailsModel,on_delete=models.CASCADE,null=True,blank=True)
    Communication_Address=models.TextField(blank=True,null=True)

    ASSET_STATUS_CHOICES = [
        ('Cleared', 'Cleared'),
        ('Pending', 'Pending'),
        ('Damaged', 'Damaged'),
        ('Lost', 'Lost'),
        ]
    # Assets Clearance Status
    desktop_laptop_status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES,blank=True, null=True)
    accessories_tools_status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES,blank=True, null=True)
    mobile_sim_uniform_status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES,blank=True, null=True)
    sim_card_status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES,blank=True, null=True)
    name_plate_id_card_status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES,blank=True, null=True)
    stationeries_status = models.CharField(max_length=20, choices=ASSET_STATUS_CHOICES,blank=True, null=True)
    
    # Asset Clearance Remarks from Dept. Head
    dept_head_signature = models.CharField(max_length=255,blank=True, null=True)
    clearance_date = models.DateField(blank=True, null=True)

    # HR Remarks and Handover Details
    hr_remarks = models.TextField(blank=True, null=True)
    handover_details_received = models.TextField(blank=True, null=True)
    handed_over_to = models.CharField(max_length=255,blank=True, null=True)
    employee_handover_signature = models.CharField(max_length=255,blank=True, null=True)
    handover_signature_date = models.DateField(blank=True, null=True)

    # def __str__(self):
    #     return f"Assets Clearance for {self.employee_name}"



class Deductions(models.Model):
    pf = models.DecimalField(max_digits=5, decimal_places=2, default=12.0)  # Percentage
    esi = models.DecimalField(max_digits=5, decimal_places=2, default=0.7)  # Percentage
    profession_tax = models.DecimalField(max_digits=10, decimal_places=2, default=200.0)  # Fixed amount


class PaySlip(models.Model):
    employee = models.ForeignKey(EmployeeInformation, on_delete=models.CASCADE)

    month = models.CharField(max_length=50)
    year = models.IntegerField()
    company_name = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    employee_name = models.CharField(max_length=100)
    uan_number = models.CharField(max_length=50)
    pf_number = models.CharField(max_length=50)
    total_working_days = models.DecimalField(max_digits=5, decimal_places=2)
    paid_days = models.DecimalField(max_digits=5, decimal_places=2)
    leaves_taken = models.DecimalField(max_digits=5, decimal_places=2)
    lop_days = models.DecimalField(max_digits=5, decimal_places=2)
    account_number = models.CharField(max_length=50)
    bank_branch = models.CharField(max_length=100)
    doj = models.DateField()
    designation = models.CharField(max_length=50)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.localtime)

    def __str__(self):
        return f"Pay Slip for {self.employee.full_name} - {self.month} {self.year}"

    def calculate_totals(self):
        allowances = self.items.filter(type='allowance').aggregate(total=models.Sum('amount'))['total'] or 0
        deductions = self.items.filter(type='deduction').aggregate(total=models.Sum('amount'))['total'] or 0
        self.total_earnings = allowances + deductions
        self.total_deductions = deductions
        self.net_salary = self.total_earnings - self.total_deductions
        self.save()

class AllowanceDeduction(models.Model):
    PAYSLIP_ITEM_CHOICES = [
        ('allowance', 'Allowance'),
        ('deduction', 'Deduction'),
    ]
    
    type = models.CharField(max_length=10, choices=PAYSLIP_ITEM_CHOICES)
    name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payslip = models.ForeignKey('PaySlip', on_delete=models.CASCADE, related_name='items')

    def __str__(self):
        return f"{self.type.capitalize()}: {self.name} - {self.amount}"





 
    
    













