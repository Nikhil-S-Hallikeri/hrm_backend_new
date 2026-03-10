
from django.db import models
from django.utils import timezone
import uuid
from django.conf import settings
import requests

# Create your models here.

class RegistrationModel(models.Model):
    EmployeeId=models.CharField(max_length=100,null=False,blank=False)
    UserName=models.CharField(max_length=100,null=False,blank=False)
    Email=models.CharField(max_length=100,null=True,blank=True)
    PhoneNumber=models.CharField(max_length=100,null=True,blank=True)
    Password=models.CharField(max_length=100,null=True,blank=True)
    profile_img=models.FileField(upload_to='Profile_Images/',blank=True,null=True)
    is_active=models.BooleanField(default=True)
    is_login=models.BooleanField(default=False)
    
    def __str__(self):
        return self.EmployeeId
    
def candidate_id():
    return "MTM"+str(uuid.uuid4().hex)[:7].upper()

#23-12-2025
class CandidateApplicationModel(models.Model): 
    CandidateId=models.CharField(max_length=100,blank=True,null=True,unique=True,default=candidate_id)
    FirstName=models.CharField(max_length=100,blank=True,null=True)
    LastName=models.CharField(max_length=100,blank=True,null=True)
    Email=models.EmailField(max_length=100,blank=True,null=True)
    PrimaryContact=models.CharField(max_length=100,blank=True,null=True)
    DOB=models.DateField(blank=True,null=True)
    SecondaryContact=models.CharField(max_length=100,blank=True,null=True)
    Location=models.TextField(max_length=100,blank=True,null=True)
    choices=(("male","Male"),("female","Female"),("others","Others"))
    Gender=models.CharField(max_length=100,blank=True,null=True,choices=choices)
    Fresher=models.BooleanField(default=False)
    Experience=models.BooleanField(default=False)
    cp=[("Experience","Experience"),("Fresher","Fresher"),("Student","Student"),("Consultant","Consultant")]
    current_position=models.CharField(max_length=100,blank=True,null=True,choices=cp)

    HighestQualification=models.CharField(max_length=100,blank=True,null=True)
    University=models.CharField(max_length=100,blank=True,null=True)
    Specialization=models.CharField(max_length=100,blank=True,null=True)
    Percentage=models.CharField(max_length=100,blank=True,null=True)
    YearOfPassout=models.CharField(max_length=100,blank=True,null=True)
    CurrentDesignation=models.CharField(max_length=100,blank=True,null=True)
    TotalExperience=models.CharField(max_length=100,blank=True,null=True)
    TechnicalSkills_with_Exp=models.CharField(max_length=2000,blank=True,null=True) 
    GeneralSkills_with_Exp=models.CharField(max_length=2000,blank=True,null=True)
    SoftSkills_with_Exp=models.CharField(max_length=2000,blank=True,null=True)
    TechnicalSkills=models.CharField(max_length=2000,blank=True,null=True)
    GeneralSkills=models.CharField(max_length=2000,blank=True,null=True)
    SoftSkills=models.CharField(max_length=2000,blank=True,null=True)
    NoticePeriod=models.CharField(max_length=100,blank=True,null=True)
    CurrentCTC=models.CharField(max_length=100,blank=True,null=True)
    AppliedDesignation=models.CharField(max_length=100,blank=True,null=True,db_index=True) #applied designation
    ExpectedSalary=models.CharField(max_length=100,blank=True,null=True)
    ContactedBy=models.CharField(max_length=100,blank=True,null=True)
    af=[("Intern","Intern"),("Employeement","Employeement")]
    Appling_for=models.CharField(max_length=100,choices=af,blank=True,null=True)#internship / job
    jps_choice=(("naukri","Naukri"),("linkedin","Linkedin"),("foundit","Foundit"),("referral","Referral"),("direct","Direct"),("indeed","Indeed"),("others","Others"))
    JobPortalSource=models.CharField(max_length=100,blank=True,null=True,choices=jps_choice,db_index=True) #job portal source
    Other_jps=models.CharField(max_length=100,blank=True,null=True)
    Referred_by=models.CharField(max_length=1000,blank=True,null=True)
    Filled_by=models.CharField(max_length=100,blank=True,null=True,db_index=True,default="Candidate") #filled by
    AppliedDate=models.DateTimeField(default=timezone.localtime,db_index=True) #applied date
    DataOfApplied=models.DateField(blank=True,null=True,db_index=True,default=timezone.localdate) #data of applied
    choices=[("Pending","Pending"),("Assigned","Assigned"),("Completed","Completed")]
    Telephonic_Round_Status=models.CharField(max_length=100,choices=choices,default="Pending")
    Test_levels=models.CharField(max_length=100,choices=choices,default="Pending")
    Interview_Schedule=models.CharField(max_length=100,choices=choices,default="Pending")
    FR=[("consider_to_client","consider to client"),
            ("Internal_Hiring","Internal Hiring"),
            ("Reject","Reject"),("Rejected_by_Candidate","Rejected_by_Candidate"),("Pending","Pending"),("On_Hold","OnHold"),
            ("offered","Offered"),
            ("Offer_did_not_accept","Offer did't accept"),("walkout","Walkout"),("client_offered","client_offered"),("candidate_joined","candidate_joined")]
    
    Final_Results=models.CharField(max_length=100,blank=True,null=True,choices=FR,default="Pending",db_index=True)
    DChoices=[("Pending","Pending"),("Uploaded","Uploaded")]
    Documents_Upload_Status=models.CharField(max_length=100,blank=True,null=True,choices=DChoices,default="Pending")
    BGChoices=[("Pending","Pending"),("Verified","Verified")]
    BG_Status=models.CharField(max_length=100,blank=True,null=True,choices=BGChoices,default="Pending")
    OfferChoice=[("Offered","Offered"),("Cancled","Cancled"),("Pending","Pending")]
    Offer_Letter_Status=models.CharField(max_length=100,choices=OfferChoice,default="Pending")
    status=[("Accept","Accept"),("Reject","Reject")]
    Interview_Accept_Status=models.CharField(max_length=100,blank=True,null=True,choices=status)
    Offer_Accept_Status=models.CharField(max_length=100,choices=status,blank=True,null=True)

    def __str__(self):
        print(self.pk)
        return self.CandidateId
    
class Deparments(models.Model):
    Dep_Name=models.CharField(max_length=100,unique=True,default='')

    def __str__(self):
        return self.Dep_Name

    def save(self, *args, **kwargs):
        if self.pk is not None:
            updated = True
        else:
            updated = False
        super(Deparments, self).save(*args, **kwargs)
        data = {
            'department_name': self.Dep_Name,
            'hrid':self.id }

        if updated:
            url = f'{settings.DAS_URL}api/DisplayDepartments/'
            response = requests.put(url, json=data)
        else:
            url = f'{settings.DAS_URL}api/DisplayDepartments/'
            response = requests.post(url, json=data)

        
        try:
            # response = requests.post(url, json=data)
            response.raise_for_status()
            print("API Response:", response.json())
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
    def delete(self, *args, **kwargs):

        # Call the external API for deletion
        url = f'{settings.DAS_URL}api/deletedepartments/{self.id}/'  # Delete URL
        try:
            response = requests.post(url)
            response.raise_for_status()
            if response.status_code == 200:
                print("API Response:", response.json())
                super(Deparments, self).delete(*args, **kwargs)
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
    
class DesignationModel(models.Model):
    Department=models.ForeignKey(Deparments,on_delete=models.CASCADE,default='')
    Name=models.CharField(max_length=100)

    def __str__(self):
        return self.Name

    def save(self, *args, **kwargs):
        if self.pk is not None:
            # This is an update operation
            updated = True
        else:
            # This is a creation operation
            updated = False
        super(DesignationModel, self).save(*args, **kwargs)
        data = {
            'position':self.Name,
            'hrid':self.pk,
            'did':self.Department.id,
            'position_id':self.id,
            'name':self.Name
        }
        
        if updated:
            url = f'{settings.DAS_URL}api/DisplayDepartments/'
            response = requests.patch(url, json=data)
        else:
            url = f'{settings.DAS_URL}api/DisplayDepartments/'
            response = requests.post(url, json=data)
        try:
            # response = requests.post(url, json=data)
            response.raise_for_status()
            print("API Response:", response.json())
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
    def delete(self,*args, **kwargs):
        data = {
            # 'id':self.id,
            'position':self.id
            }
        url = f'{settings.DAS_URL}api/deletedepartments/{self.id}/'

        requests.post(url,data)
        super(DesignationModel, self).delete(*args, **kwargs)
    
class EmployeeShifts_Model(models.Model):
    Shift_Name=models.CharField(max_length=100,blank=True,null=True,unique=True)
    start_shift=models.TimeField(blank=True,null=True)
    end_shift=models.TimeField(blank=True,null=True)
    def __str__(self):
        return self.Shift_Name if self.Shift_Name else "Shift Name Blank"
# class EmployeeWeekoffs_Model(models.Model):
#     choices=(("0","Su"),("1","Mo"),("2","Tu"),("3","We"),("4","Th"),("5","Fr"),("6","Sa"))
#     weekoffs=models.CharField(max_length=100,blank=True,null=True,choices=choices,unique=True)
    
class EmployeeIDTracker(models.Model):
    current_number = models.IntegerField(default=1000)  # Start from 10000 so the first ID is 10001
    @classmethod
    def get_next_employee_number(cls):
        tracker, created = cls.objects.get_or_create(id=1)
        tracker.current_number += 1
        tracker.save()
        return tracker.current_number

from django.db.models.signals import post_save
from django.dispatch import receiver

class EmployeeInformation(models.Model):
    Candidate_id = models.OneToOneField(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    employee_Id=models.CharField(max_length=100,blank=True,unique=True,null=True)
    created_at = models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    salutation=models.CharField(max_length=100,blank=True,null=True)
    full_name = models.CharField(max_length=300,blank=True,null=True)
    last_name=models.CharField(max_length=200,blank=True,null=True)
    date_of_birth = models.DateField(blank=True,null=True)
    age=models.IntegerField(blank=True,null=True)
    choices=(("male", "Male"),
    ("female", "Female"),
    ("non_binary", "Non-Binary"),
    ("genderqueer", "Genderqueer"),
    ("genderfluid", "Genderfluid"),
    ("agender", "Agender"),
    ("bigender", "Bigender"),
    ("transgender", "Transgender"),
    ("intersex", "Intersex"),
    ("demiboy", "Demiboy"),
    ("demigirl", "Demigirl"),
    ("demigender", "Demigender"),
    ("two_spirit", "Two-Spirit"),
    ("butch", "Butch"),
    ("binary_gender", "Binary Gender"),
    ("other", "Other"))
    gender = models.CharField(max_length=100,blank=True,null=True,choices=choices)
    mobile = models.CharField(max_length=15, blank=True,null=True)
    email = models.CharField(max_length=100,blank=True,null=True,unique=False)
    weight = models.CharField(max_length=15, blank=True,null=True)
    height = models.CharField(max_length=15, blank=True,null=True)
    permanent_address = models.TextField(blank=True,null=True)
    permanent_City=models.CharField(max_length=1000,blank=True,null=True)
    permanent_state=models.CharField(max_length=1000,blank=True,null=True)
    permanent_pincode=models.CharField(max_length=1000,blank=True,null=True)

    present_address = models.TextField(blank=True,null=True)
    present_City=models.CharField(max_length=1000,blank=True,null=True)
    present_state=models.CharField(max_length=1000,blank=True,null=True)
    present_pincode=models.CharField(max_length=1000,blank=True,null=True)

    PVC=(("success","Success"),("failed","Failed"))
    ProfileVerification=models.CharField(max_length=100,choices=PVC,blank=True,null=True)
    es=(("active","Active"),("in_active","In_Active"),("Resigned","Resigned"))
    employee_status=models.CharField(max_length=100,choices=es,blank=True,null=True)

    hired_date=models.DateField(blank=True,null=True)
    form_submitted_status=models.BooleanField(default=False)
    date_of_submitted=models.DateTimeField(blank=True,null=True)
    restricted_leave_count=models.IntegerField(blank=True,null=True)
    employee_attendance_id=models.CharField(max_length=1000,blank=True,null=True)
    choice=(("intern","Intern"),("permanent","permanent"),("Trainee", "Trainee"),("Consultant","Consultant"))
    Employeement_Type=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    work_location=models.CharField(max_length=1000,blank=True,null=True)
    #if intern
    internship_Duration_From=models.DateField(blank=True,null=True)
    internship_Duration_To=models.DateField(blank=True,null=True)

    # STATUS_CHOICES = (("pending", "pending"), ("completed", "completed"))
    # internship_status = models.CharField(max_length=100, blank=True, null=True, choices=STATUS_CHOICES)

    choice=(("probationer","Probationer"),("confirmed","Confirmed"))
    probation_status= models.CharField(max_length=100, blank=True, null=True, choices=choice)
    # #if probation
    probation_Duration_From=models.DateField(blank=True,null=True)
    probation_Duration_To=models.DateField(blank=True,null=True)
    consultant_Duration_From=models.DateField(blank=True,null=True)
    consultant_Duration_To=models.DateField(blank=True,null=True)
    EmployeeShifts=models.ForeignKey(EmployeeShifts_Model,on_delete=models.CASCADE,blank=True,null=True)
    source_of_hire= models.CharField(max_length=100, blank=True, null=True)
    is_verified=models.BooleanField(default=False)
    wish_mail=models.BooleanField(default=False)
    bd_wish_mail=models.BooleanField(default=False)
    Policies_NDA_Accept=models.BooleanField(default=False)
    notice_period=models.IntegerField(blank=True,null=True)
    # EmployeeWeekoffs=models.ManyToManyField(EmployeeWeekoffs_Model)
    # is_probation_status = models.CharField(max_length=100, blank=True, null=True, choices=STATUS_CHOICES)
    Offered_Instance=models.ManyToManyField("OfferLetterModel",blank=True)
    secondary_email = models.CharField(max_length=199,blank=True,null=True)
    secondary_mobile_number = models.CharField(max_length=10,blank=True,null=True)
    
    # work from home option
    WFH_Status=models.BooleanField(default=False)
    from_duration=models.DateTimeField(blank=True,null=True)
    to_duration=models.DateTimeField(blank=True,null=True)
    longitude=models.CharField(max_length=1000,blank=True,null=True)
    latitude=models.CharField(max_length=1000,blank=True,null=True)
    distance=models.IntegerField(blank=True,null=True)
    
    #10/1/2026
    def save(self, *args, **kwargs):

        if self.Candidate_id and not self.source_of_hire:
            # can_obj=CandidateApplicationModel.objects.filter(pk=self.Candidate_id).first()
            # if can_obj:
            #     self.source_of_hire=can_obj.JobPortalSource
            # Candidate_id is a ForeignKey, so it's already an object
            # No need to filter, just use it directly
            if self.Candidate_id.JobPortalSource:
                self.source_of_hire = self.Candidate_id.JobPortalSource

        if not self.Candidate_id and not self.source_of_hire:
            self.source_of_hire="direct" 
            
        if self.employee_status=="active":
            # Check if another active employee with the same email exists
            if EmployeeInformation.objects.filter(email=self.email, employee_status = "active").exclude(id=self.id).exists():
                raise ValidationError('An active employee with this email already exists.')
            
        try:
            data = {"blocked_status": True,"email":self.email,"bs":self.employee_status}
            url = f'{settings.DAS_URL}api2/BlockUser/{self.employee_Id}/'
            response = requests.post(url, json=data)

            if response.status_code == 200:
                print("In DAS also blocked")
            else:
                print("In DAS not blocked error")
        except Exception as e:
            print(e)
                
        if self.form_submitted_status==True:
            self.date_of_submitted=timezone.localtime()
            
            # Update OfferLetterModel to mark joining form as filled
            try:
                if self.Candidate_id:
                    offer = OfferLetterModel.objects.filter(CandidateId=self.Candidate_id).first()
                    if offer and not offer.joining_form_filled:
                        offer.joining_form_filled = True
                        offer.joining_form_filled_date = timezone.localtime()
                        offer.save()
                        print(f"Marked joining form as filled for candidate {self.Candidate_id.CandidateId}")
            except Exception as e:
                print(f"Error updating OfferLetterModel: {e}")
            
        super().save(*args, **kwargs)
    
    #class Meta:
        #unique_together = ('employee_attendance_id',)

    def __str__(self):
        return f"{self.employee_Id}{self.full_name}" if self.employee_Id else ''
 

class EmployeeDataModel(models.Model):
    EmployeeId=models.CharField(max_length=100)
    Name=models.CharField(max_length=100)
    choice=(("Admin",'Admin'),("HR",'HR'),("Employee","Employee"),("Recruiter","Recruiter"))
    Designation=models.CharField(max_length=100,choices=choice,blank=True,null=True)
    Position=models.ForeignKey(DesignationModel,on_delete=models.SET_NULL,blank=True,null=True)
    Reporting_To=models.ForeignKey('self',on_delete=models.SET_NULL,blank=True,null=True,related_name="Repotinf_to")
    employeeProfile=models.OneToOneField(EmployeeInformation,on_delete=models.CASCADE,blank=True,null=True)
    applied_list_access=models.BooleanField(default=False)
    screening_shedule_access=models.BooleanField(default=False)
    interview_shedule_access=models.BooleanField(default=False)
    final_status_access=models.BooleanField(default=False)
    
    self_activity_add=models.BooleanField(default=False)
    all_employees_view=models.BooleanField(default=False)
    all_employees_edit=models.BooleanField(default=False)
    employee_personal_details_view=models.BooleanField(default=False)
    massmail_communication=models.BooleanField(default=False)
    holiday_calender_creation=models.BooleanField(default=False)
    assign_offerletter_prepare=models.BooleanField(default=False)
    job_post=models.BooleanField(default=False)
    attendance_upload=models.BooleanField(default=False)
    leave_create=models.BooleanField(default=False)
    leave_edit=models.BooleanField(default=False)
    salary_component_creation=models.BooleanField(default=False)
    salary_template_creation=models.BooleanField(default=False)
    assign_resignation_apply=models.BooleanField(default=False)
    assign_leave_apply=models.BooleanField(default=False)
    
    
    verified_by=models.ForeignKey('self',on_delete=models.SET_NULL,blank=True,null=True,related_name="progile_verifier")
    
    def __str__(self):
        return self.EmployeeId if self.EmployeeId else ''

    def save(self, *args, **kwargs):
        # Determine if the instance is being created or updated
        is_new_instance = self.pk is None
    
        # Determine the status based on the business logic
        rep_to = EmployeeDataModel.objects.filter(Reporting_To=self.pk)
        sub_rep_to = False
        for rep in rep_to:
            emp_obj = EmployeeDataModel.objects.filter(Reporting_To=rep.pk)
            if emp_obj.exists():
                sub_rep_to = True
                break

        if self.Designation == "Admin":
            status = "admin"
        elif self.Designation == "HR" or sub_rep_to:
            status = "manager"
        elif rep_to.exists() and (self.Designation == "Employee" or self.Designation == "Recruiter"):
            status = "team_leader"
        elif self.Designation == "Recruiter" or self.Designation == "Employee":
            status = "employee"
        else:
            status = None

        super(EmployeeDataModel, self).save(*args, **kwargs)

        data = {
            "pk": self.pk,
            "id": self.pk,
            "employee_id": self.EmployeeId,
            "name": self.Name,
            "email": self.employeeProfile.email if self.employeeProfile else None,
            "position": self.Position.pk if self.Position else None,
            "department": self.Position.Department.pk if self.Position else None,
            "registered_date": self.employeeProfile.hired_date.strftime('%Y-%m-%d') if self.employeeProfile and self.employeeProfile.hired_date else None,
            "reporting_to": self.Reporting_To.EmployeeId if self.Reporting_To else None,
            "status": status,
        }

        if is_new_instance:
            # Create the new instance via POST
            url = f'{settings.DAS_URL}api/EmployeeRegistration/'
            response = requests.post(url, json=data)
            if response.status_code != 200:

                emp_obj=EmployeeInformation.objects.filter(employee_Id=self.EmployeeId).first()
                idtrack=EmployeeIDTracker.objects.filter(id=1).first()
                if idtrack:
                    if emp_obj.Employeement_Type == "intern":
                        idtrack.current_intern_number-=1
                    elif emp_obj.Employeement_Type == "permanent":
                        idtrack.current_emp_number-=1
                    idtrack.save()
                emp_obj.delete()

                EmployeeDataModel.objects.filter(pk=self.pk).delete()

                raise Exception("API Response:", response.json())
                # raise Exception(f"Failed to register employee: {response.status_code} - {response.text}")
        else:
            url = f'{settings.DAS_URL}api/EmployeeRegistration/'
            response = requests.patch(url, json=data)
            if response.status_code != 200:
                raise Exception(f"Failed to update employee: {response.status_code} - {response.text}")
            
    def delete(self, *args, **kwargs):
        print("method called succssfully")
        data = {"employee_id": self.EmployeeId}
        url = f'{settings.DAS_URL}/api/EmployeeRegistration/'  # Corrected URL format
        try:
            response = requests.put(url, json=data)
            response.raise_for_status()
            if response.status_code in [200, 204]:
                print("API Response:", response.json())
                # super(EmployeeDataModel, self).delete(*args, **kwargs)
            else:
                print(f"Unexpected status code: {response.status_code}")
        
        except requests.exceptions.RequestException as e:
            print(f"API call failed: {e}")
        
    
    

    
class CalledCandidatesModel(models.Model):
    name=models.CharField(max_length=100)
    phone=models.CharField(max_length=100)
    location=models.CharField(max_length=100)
    designation=models.CharField(max_length=100)
    ch=(("fresher","Fresher"),("experience","Experience"))
    current_status=models.CharField(max_length=100,choices=ch)
    experience=models.IntegerField(blank=True,null=True)
    
    choice=[
            ("interview_scheduled","Interview_Scheduled"),
            ("rejected","Rejected"),("Rejected_by_Candidate","Rejected_by_Candidate"),
            ("to_client","Consider_to_Client"),]
    
    status=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    interview_scheduled_date=models.DateField(blank=True,null=True)
    remarks=models.TextField()
    called_by=models.ForeignKey(EmployeeDataModel,on_delete=models.SET_NULL,blank=True,null=True)
    called_date=models.DateTimeField(default=timezone.localtime,blank=True,null=True)


from Contract_Emp_App.models import OurClients,Requirement
class RequirementAssign(models.Model):
    client = models.ForeignKey(OurClients, on_delete=models.CASCADE,blank=True, null=True)
    requirement = models.ForeignKey(Requirement, on_delete=models.CASCADE,blank=True, null=True)
    assigned_to_recruiter = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='assigned_recruiter',blank=True, null=True)
    assigned_by_employee = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='assigned_by',blank=True, null=True)
    assigned_on = models.DateTimeField(default=timezone.localtime)
    position_count = models.IntegerField(default=0,blank=True, null=True)
    closed_pos_count = models.IntegerField(default=0,blank=True, null=True)

    def __str__(self):
        return f"Assignment for {self.requirement.job_title}" 


class InterviewSchedulModel(models.Model):
    Candidate=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE)
    assigned_requirement=models.ForeignKey(RequirementAssign,on_delete=models.CASCADE,blank=True,null=True)
    ch=[("client","client"),("ours","ours")]
    for_whome=models.CharField(max_length=100,blank=True,null=True,choices=ch)
    ir_choice=(("technical_round","Technical_Round"),("manager_round","Manager_Round"),("hr_round","HR_Round"),("ceo_round","CEO_Round"))
    InterviewRoundName=models.CharField(max_length=100,choices=ir_choice,default="hr_round")
    # TaskAssigned=models.CharField(max_length=100,blank=True,null=True)
    interviewer=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,related_name="interviewer",blank=True,null=True)
    InterviewDate=models.DateTimeField(default=timezone.localtime)
    it_choice=(("online","Online"),("offline","Offline"))
    InterviewType=models.CharField(max_length=100,blank=True,null=True,choices=it_choice)
    choice=[("Assigned","Assigned"),("Completed","Completed")]
    status=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    EmailStatus=models.BooleanField(default=False)
    ScheduledBy=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="ScheduledBy")
    ScheduledOn=models.DateTimeField(default=timezone.localtime)
    inside_interviewer=models.BooleanField(default=True)
    Out_EMP_email=models.CharField(max_length=100,blank=True,null=True)

    def __str__(self):
        return self.Candidate.CandidateId

class ScreeningAssigningModel(models.Model):
    Candidate=models.OneToOneField (CandidateApplicationModel,max_length=100,blank=True,null=True,on_delete=models.CASCADE,related_name="Recruiter")
    Recruiter=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE)
    choice=[("Assigned","Assigned"),("Completed","Completed")]
    status=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    AssignedBy=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="AssignedBy")
    Date_of_assigned=models.DateTimeField(default=timezone.localtime)

    def __str__(self):
        return self.Candidate.CandidateId
    
class ScreeningProcessModel(models.Model):
    CandidateId=models.CharField(max_length=100)
    Date=models.DateTimeField(default=timezone.localtime)
    Questions=models.TextField()
    CalledBy=models.CharField(max_length=100)
    CallerNumber=models.CharField(max_length=100)
    screeningStatus=models.CharField(max_length=100)

from django.core.exceptions import ValidationError
def validate_positive(value):
    if value <= 0:
        raise ValidationError(
            '%(value)s is not a positive number',
            params={'value': value},
        )
    
class Review(models.Model):
    choice=[("yes","Yes"),("no","No")]
    CandidateId=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    interview_id = models.OneToOneField(InterviewSchedulModel,on_delete=models.CASCADE,blank=True,null=True,default=None)
    screeingreview =  models.OneToOneField(ScreeningAssigningModel,on_delete=models.CASCADE,blank=True,null=True,default=None)
    Name=models.CharField(max_length=100 ,blank=True,null=True)
    PositionAppliedFor=models.CharField(max_length=100 ,blank=True,null=True)
    SourceBy=models.CharField(max_length=100 ,blank=True,null=True)
    SourceName=models.CharField(max_length=100 ,blank=True,null=True)
    Date=models.DateTimeField(blank=True,null=True)
    LocationAppliedFor=models.CharField(max_length=100,blank=True,null=True)
    Contact=models.CharField(max_length=100,blank=True,null=True)
    Qualification=models.CharField(max_length=100,blank=True,null=True)
    RelatedExperience=models.CharField(max_length=100,blank=True,null=True)
    JobStabilityWithPreviousEmployers=models.CharField(max_length=100,blank=True,null=True)
    ReasionForLeavingImadiateEmployeer=models.CharField(max_length=100,blank=True,null=True)
    Appearence_and_Personality=models.FloatField( validators=[validate_positive],help_text=" -ress,Grooming,Body Language,Manners out of 10",blank=True,null=True)
    ClarityOfThought=models.FloatField(validators=[validate_positive],help_text="ClarityOfThought out of 10",blank=True,null=True)  
    EnglishLanguageSkills=models.FloatField(validators=[validate_positive],help_text="English Skils out of 10",blank=True,null=True)

    AwarenessOnTechnicalDynamics=models.FloatField(validators=[validate_positive],help_text=" Awareness on Technical Dynamics out of 10",blank=True,null=True)            
    InterpersonalSkills=models.FloatField(validators=[validate_positive],help_text=" Interpersonal Skills/Attitude Twords Task,People etc out of 10",blank=True,null=True)                       
    ConfidenceLevel=models.FloatField(validators=[validate_positive],help_text=" ConfidenceLevel out of 10",blank=True,null=True)                        
    AgeGroupSuitability=models.CharField(max_length=100,choices=choice,blank=True,null=True)

    Analytical_and_logicalReasoningSkills=models.FloatField(validators=[validate_positive],help_text=" Analytical and logical Reasoning Skills out of 10",blank=True,null=True)
                                        
    CareerPlans=models.CharField(max_length=100,blank=True,null=True)
                                        
    AchivementOrientation=models.CharField(max_length=1000,blank=True,null=True)
                                       
    ProblemSolvingAbilites=models.FloatField( validators=[validate_positive],help_text="Problem Solving Abilites  out of 10",blank=True,null=True)
                                        
    AbilityToTakeChallenges=models.FloatField( validators=[validate_positive],help_text=" Ability to Take up Challenges out of 10",blank=True,null=True)
                                        
    LeadershipAbilities=models.IntegerField( validators=[validate_positive],help_text=" Leadership Abilities out of 10",blank=True,null=True)
                                        
    IntrestWithCompany=models.CharField(max_length=100,choices=choice,blank=True,null=True)
    ResearchedAboutCompany=models.CharField(max_length=100,choices=choice,blank=True,null=True)

    HandelTargets_Pressure=models.FloatField( validators=[validate_positive],help_text=" Ability to handel targets/Pressure out of 10",blank=True,null=True)
    CustomerService=models.FloatField( validators=[validate_positive],help_text="Customer Service out of 10",blank=True,null=True)
    Coding_Questions_Score=models.IntegerField( help_text="Coding Questions Score",blank=True,null=True)
    OverallCandidateRanking=models.FloatField( help_text="OverallCandidateRanking",blank=True,null=True)  

    LastCTC=models.CharField(max_length=100,blank=True,null=True)
    ExpectedCTC=models.CharField(max_length=100,blank=True,null=True)
    NoticePeriod=models.CharField(max_length=100,blank=True,null=True)
    Designation=models.CharField(max_length=100,blank=True,null=True)
    TotalYearOfExp=models.CharField(max_length=100,blank=True,null=True)
    InterviewScheduleDate=models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    DOJ=models.DateField(blank=True,null=True)
    Six_Days_Working=models.CharField(max_length=10,choices=choice,blank=True,null=True)
    FlexibilityOnWorkTimings=models.CharField(max_length=10,blank=True,null=True)
    OwnLoptop=models.CharField(max_length=10,choices=choice,blank=True,null=True)
    RelocateToOtherCity=models.CharField(max_length=10,choices=choice,blank=True,null=True)
    RelocateToOtherCenters=models.CharField(max_length=10,choices=choice,blank=True,null=True)
    Leagel_cases=models.CharField(max_length=2000,blank=True,null=True)
    CurrentLocation=models.CharField(max_length=100,blank=True,null=True)
    ModeOfCommutation=models.CharField(max_length=100,blank=True,null=True)
    Residingat=models.CharField(max_length=100,blank=True,null=True)
    Native=models.CharField(max_length=100,blank=True,null=True)
    Mother_Tongue=models.CharField(max_length=100,blank=True,null=True)
    # Family
    About_Family=models.TextField(blank=True,null=True)
    status_choice=[("single","Single"),("marrid","Married"),("divorced","Divorced")]
    MeritalStatus=models.CharField(max_length=10,choices=status_choice,blank=True,null=True)
    FathersName=models.CharField(max_length=100,blank=True,null=True)
    FathersDesignation=models.CharField(max_length=100,blank=True,null=True)
    MothersName=models.CharField(max_length=100,blank=True,null=True)
    MothersDesignation=models.CharField(max_length=100,blank=True,null=True)
    SpouseName=models.CharField(max_length=100,blank=True,null=True)
    SpouseDesignation=models.CharField(max_length=100,blank=True,null=True)
    devorced_statement=models.CharField(max_length=1000,blank=True,null=True)
    About_Childrens=models.CharField(max_length=1000,blank=True,null=True)
    LanguagesKnown=models.CharField(max_length=100,blank=True,null=True)

    IStatus=[("consider_to_client","Consider to Client"),
            ("Internal_Hiring","Internal Hiring"),
            ("Reject","Reject"),("Rejected_by_Candidate","Rejected_by_Candidate"),
            ("On_Hold","On Hold"),
            ("Offer_did_not_accept","Offer did't accept"),
            ("client_rejected","client_rejected"),("client_offered","client_offered"),("client_kept_on_hold","client_kept_on_hold"),
            ("client_offer_rejected","client_offer_rejected"),("candidate_joined","candidate_joined")]
    
    
    interview_Status=models.CharField(max_length=100,choices=IStatus,blank=True,null=True)
    SStatus=[
            ("scheduled","Scheduled For Next Round"),
            ("rejected","Rejected"),("Rejected_by_Candidate","Rejected_by_Candidate"),
            ("to_client","Scheduled Interview to Client"),
            ("walkout","Walkout")]
    
    # SStatus=[
    #         ("scheduled","Scheduled For Next Round"),
    #         ("didn't connect","Didn't Connect"),
    #         ("not intrested","Not Intrested"),
    #         ("rejected","Rejected"),
    #         ("scheduled interview to client","Scheduled Interview to Client")]
    
    Screening_Status=models.CharField(max_length=100,choices=SStatus,blank=True,null=True)
    ReviewedBy = models.CharField(max_length=100,blank=True,null=True)
    Signature  = models.CharField(max_length=100,blank=True,null=True)
    ReviewedOn = models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    InterviewerName=models.CharField(max_length=100,blank=True,null=True)
    ReviewedDate=models.DateField(default=timezone.localdate)
    Comments=models.TextField(blank=True,null=True)

    def __str__(self):
        return self.CandidateId.CandidateId
        
class HRFinalStatusModel(models.Model):
    
    CandidateId=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    req_id=models.ForeignKey(Requirement,on_delete=models.CASCADE,blank=True,null=True)
    IStatus=[("consider_to_client","Consider_to_Client"),
            ("Internal_Hiring","Internal Hiring"),("Rejected_by_Candidate","Rejected_by_Candidate"),
            ("Reject","Reject"),#Rejected,
            ("On_Hold","On Hold"),
            ("walkout","Walkout"),
            ("Pending","Pending"),("Offer_did_not_accept","Offer did't accept"),

            ("client_rejected","client_rejected"),("client_offered","client_offered"),("client_kept_on_hold","client_kept_on_hold"),
            ("client_offer_rejected","client_offer_rejected"),("candidate_joined","candidate_joined")]
    
    Final_Result=models.CharField(max_length=100,choices=IStatus,blank=True,null=True)
    ReviewedBy = models.CharField(max_length=100,blank=True,null=True)
    Signature  = models.CharField(max_length=100,blank=True,null=True)
    ReviewedOn = models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    Comments=models.TextField(blank=True,null=True)

    def __str__(self):
        str(self.CandidateId.CandidateId) + str(self.ReviewedOn)


class Documents_Upload_Model(models.Model):
    CandidateID=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    Name=models.CharField(max_length=100)
    Provious_Company=models.CharField(max_length=100)
    Provious_Designation=models.CharField(max_length=100)
    experience=models.CharField(max_length=100)
    from_date=models.DateField(blank=True,null=True)
    To_date=models.DateField(blank=True,null=True)
    Current_CTC=models.CharField(max_length=100)
    Reporting_Manager_name=models.CharField(max_length=100,blank=True,null=True)
    Reporting_Manager_email=models.CharField(max_length=100,blank=True,null=True)
    ReportingManager_phone=models.CharField(max_length=100,blank=True,null=True)
    HR_name=models.CharField(max_length=100,blank=True,null=True)
    HR_email=models.CharField(max_length=100,blank=True,null=True)
    HR_phone=models.CharField(max_length=100,blank=True,null=True)
    Salary_Drawn_Payslips=models.FileField(upload_to='payslips/',blank=True,null=True)
    Document=models.FileField(upload_to='proofs/',blank=True,null=True)
    mail_sended_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    submitted_on=models.DateTimeField(default=timezone.localtime)

class Documents_Model(models.Model):
    Document_name=models.CharField(max_length=100,blank=True,null=True)
    document_file=models.FileField(upload_to='documents/',blank=True,null=True)
    Documents=models.ForeignKey(Documents_Upload_Model,on_delete=models.CASCADE,blank=True,null=True)
    
class BG_VerificationModel(models.Model):
    candidate=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    Documents=models.ForeignKey(Documents_Upload_Model,on_delete=models.CASCADE,blank=True,null=True)
    VerifiersName=models.CharField(max_length=100,blank=True,null=True)
    VerifiersDesignation=models.CharField(max_length=100,blank=True,null=True)
    VerifiersEmployer=models.CharField(max_length=100,blank=True,null=True)
    VerifiersPhoneNumber=models.CharField(max_length=100,blank=True,null=True)
    choice=(("yes","YES"),("no","No"))
    CandidateKnows=models.CharField(max_length=100,choices=choice,help_text="Do you know the candidate ?",blank=True,null=True)
    CandidateDesignation=models.CharField(max_length=100,help_text="Candidates designation when worked with you ?",blank=True,null=True)
    CandidateWorksFrom=models.CharField(max_length=100,help_text="For how long did the candidate work with you?",blank=True,null=True)
    CandidateReportingTo=models.CharField(max_length=100,help_text="Was the candidate directly reporting to you?",blank=True,null=True)
    CandidatePositives=models.CharField(max_length=100,help_text="Candidates Positives",blank=True,null=True)
    CandidateNegatives=models.CharField(max_length=100,help_text="Candidates Areas of Improvement (negatives)",blank=True,null=True)
    CandidatesPerformanceFeedBack=models.FloatField( validators=[validate_positive],help_text=" Your feedback on the candidates performance",blank=True,null=True)
    ch=(("Excellent","Excellent"),("Good","Good"),("Average","Average"))
    CandidatePerformanceLevel=models.CharField(max_length=100,choices=ch,blank=True,null=True)
    Candidates_ability=models.CharField(max_length=100,choices=ch,help_text="Candidate’s ability to work under Target & handle Target Pressure?",blank=True,null=True)
    Candidates_Achieve_Targets=models.CharField(max_length=100,blank=True,null=True,help_text="Candidate’s ability to achieve Targets? On an average what would be the Target Vs Achieved %?")
    Candidate_Behavior_Feedback=models.FloatField( help_text="Your feedback on Candidates behavior, integrity & work ethics",blank=True,null=True)
    Candidate_Leaving_Reason=models.CharField(max_length=100,help_text="Candidates reason for leaving",blank=True,null=True)
    choices=(("yes","YES"),("no","NO"))
    Candidate_Rehire=models.CharField(max_length=100,help_text="Is the candidate eligible for rehire?",blank=True,null=True,choices=choices)
    Comments_On_Candidate=models.TextField(blank=True,null=True)
    PackageOffered=models.CharField(max_length=100,help_text="Package offered?",blank=True,null=True)
    Ever_Handled_Team=models.CharField(max_length=100,help_text="Ever handled team",blank=True,null=True,choices=choices)
    TeamSize=models.IntegerField( blank=True,null=True)
    # FinalVerifyStatus=models.BooleanField(default=False)
    Remarks=models.TextField(blank=True,null=True)

class InterviewScheduleStatusModel(models.Model):
    InterviewScheduledCandidate=models.ForeignKey(CandidateApplicationModel,max_length=100,blank=True,null=True,on_delete=models.CASCADE,db_index=True)
    choices=[("Pending","Pending"),("Assigned","Assigned"),("Completed","Completed"),("Verifyed","Verifyed"),("Uploaded","Uploaded")]
    Interview_Schedule_Status=models.CharField(max_length=100,blank=True,null=True,choices=choices,default="Pending")
    interviewe = models.ForeignKey(InterviewSchedulModel,max_length=100,blank=True,null=True,on_delete=models.CASCADE)
    screening = models.ForeignKey(ScreeningAssigningModel,max_length=100,blank=True,null=True,on_delete=models.CASCADE)
    documents=models.ForeignKey(Documents_Upload_Model,max_length=100,blank=True,null=True,on_delete=models.CASCADE)
    bg_verification=models.ForeignKey(BG_VerificationModel,max_length=100,blank=True,null=True,on_delete=models.CASCADE)
    review=models.OneToOneField(Review,max_length=100,blank=True,null=True,on_delete=models.CASCADE)


    def __str__(self):
        return self.InterviewScheduledCandidate.CandidateId

#changes
# class Notification(models.Model):
#     sender = models.ForeignKey(RegistrationModel, on_delete=models.CASCADE,related_name="sender",blank=True,null=True)
#     receiver = models.ForeignKey(RegistrationModel, on_delete=models.CASCADE,related_name='receiver',blank=True,null=True)
#     message = models.CharField(max_length=255)
#     not_ch=(("cal","cal"),("scr_assign","scr_assign"),("int_assign","int_assign"),("scr_com","scr_com"),("int_com","int_com"))
#     not_type=models.CharField(max_length=100,choices=not_ch,blank=True,null=True)
#     timestamp = models.DateTimeField(default=timezone.localtime,blank=True,null=True)
#     read_status = models.BooleanField(default=False)
#     candidate_id=models.ForeignKey(CandidateApplicationModel, on_delete=models.CASCADE,blank=True,null=True)


class Notification(models.Model):
    sender = models.ForeignKey(RegistrationModel, on_delete=models.CASCADE,related_name="sender",blank=True,null=True)
    receiver = models.ForeignKey(RegistrationModel, on_delete=models.CASCADE,related_name='receiver',blank=True,null=True)
    message = models.CharField(max_length=255)
    # not_ch=(("cal","cal"),("scr_assign","scr_assign"),("int_assign","int_assign"),("scr_com","scr_com"),("int_com","int_com"))
    not_ch=(("cal","cal"),("scr_assign","scr_assign"),("int_assign","int_assign"),("scr_com","scr_com"),("int_com","int_com"), ("task_assign", "task_assign")) 
    not_type=models.CharField(max_length=100,choices=not_ch,blank=True,null=True)
    timestamp = models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    read_status = models.BooleanField(default=False)
    candidate_id=models.ForeignKey(CandidateApplicationModel, on_delete=models.CASCADE,blank=True,null=True)
    reference_id=models.CharField(max_length=100,blank=True,null=True)

# class WishNotifications(models.Model):
#     wishes_to_emp=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="wishes_to_emp")
#     # fest_wishes=models.CharField(max_length=100)
#     created_on=models.DateTimeField(default=timezone.localtime())
#     message=models.TextField(blank=True,null=True)
#     is_activate=models.BooleanField(default=True)
#     wish_message=models.TextField(blank=True,null=True)
#     wished_emps=models.ManyToManyField("EmployeeDataModel",blank=True,null=True)

# ===================================================================================================

class WishNotifications(models.Model):
    wishes_to_emp = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE)
    wish_message = models.TextField()
    message = models.TextField()
    wished_emps = models.ManyToManyField(EmployeeDataModel, related_name='wish_notifications')
    created_on = models.DateTimeField(auto_now_add=True)
    is_activate = models.BooleanField(default=True)



class LetterTemplatesModel(models.Model):
    TemplateName=models.CharField(max_length=100,blank=True,null=True)
    TemplateFile=models.FileField(upload_to='Letter_Templates',blank=True,null=True)
    UploadedDate=models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    UploadedBy=models.CharField(max_length=100,blank=True,null=True)

    def __str__(self):
        return self.TemplateName

#9/1/2026
class OfferLetterModel(models.Model):
    CandidateId=models.ForeignKey(CandidateApplicationModel,max_length=100,blank=True,null=True,on_delete=models.CASCADE)
    Name=models.CharField(max_length=100,blank=True,null=True)
    Email=models.CharField(max_length=100,blank=True,null=True)
    father_name=models.CharField(max_length=100,blank=True,null=True)
    address=models.CharField(max_length=500,blank=True,null=True)
    DOB=models.DateField(default=timezone.localdate,blank=True,null=True)
    Date_of_Joining=models.DateField(blank=True,null=True)
    CTC=models.DecimalField(max_digits=12, decimal_places=2 , blank=True,null=True)
    WorkLocation=models.CharField(max_length=100,blank=True,null=True)
    choice=(("intern","Intern"),("permanent","permanent"))
    Employeement_Type=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    #if intern
    internship_Duration_From=models.DateField(blank=True,null=True)
    internship_Duration_To=models.DateField(blank=True,null=True)

    STATUS_CHOICES = (("pending", "pending"), ("completed", "completed"))
    internship_status = models.CharField(max_length=100, blank=True, null=True, choices=STATUS_CHOICES)

    choice=(("probationer","Probationer"),("confirmed","Confirmed"))
    probation_status= models.CharField(max_length=100, blank=True, null=True, choices=choice)
    #if probation
    probation_Duration_From=models.DateField(blank=True,null=True)
    probation_Duration_To=models.DateField(blank=True,null=True)
    is_probation_status = models.CharField(max_length=100, blank=True, null=True, choices=STATUS_CHOICES)
    notice_period=models.IntegerField(blank=True,null=True)
    # position=models.CharField(max_length=100,blank=True,null=True)
    position=models.ForeignKey(DesignationModel,on_delete=models.CASCADE,blank=True,null=True)
    OfferedDate=models.DateTimeField(default=timezone.localtime,blank=True,null=True)
    # fixed_salary=models.DecimalField(max_digits=12, decimal_places=2 , blank=True,null=True)
    letter_prepared_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="letter_prepared_by")
    letter_prepared_date=models.DateTimeField(blank=True,null=True)
    Letter_sended_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="offered_by")
    Letter_sended_status=models.BooleanField(default=False)
    v_ch=[("Pending","Pending"),("Approved","Approved"),("Denied","Denied")]   
    verification_status=models.CharField(max_length=100,blank=True,null=True,choices=v_ch)
    approval_status=models.BooleanField(default=False)
    approval_reason=models.TextField(blank=True,null=True)
    letter_verified_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True,related_name="verifed_by")
    VerifiedDate=models.DateTimeField(blank=True,null=True)
    Mail_Status=models.BooleanField(default=False)
    PDF_File=models.FileField(upload_to='OfferLetters/',blank=True,null=True)
    status=[("Pending","Pending"),("Accept","Accept"),("Reject","Reject")]
    Accept_status=models.CharField(max_length=100,blank=True,null=True,choices=status,default="Pending")
    contact_info=models.CharField(max_length=100,blank=True,null=True)
    offer_expire=models.DateField(blank=True,null=True)
    remarks=models.TextField(blank=True,null=True)
    
    # Joining Form Tracking Fields
    joining_form_sent_date=models.DateTimeField(blank=True,null=True)  # When joining form email was first sent
    joining_form_resend_count=models.IntegerField(default=0)  # How many times form email was resent
    joining_form_filled=models.BooleanField(default=False)  # Whether candidate filled the form
    joining_form_filled_date=models.DateTimeField(blank=True,null=True)  # When form was filled
    manual_offer_sent=models.BooleanField(default=False)  # If offer letter was sent manually after delay


    def save(self, *args, **kwargs):

        if self.internship_Duration_To:
            if self.internship_Duration_To  == timezone.localdate():
                self.internship_status = 'completed'
            else:
                self.internship_status = 'pending'

        if self.probation_Duration_To:
            if self.probation_Duration_To  == timezone.localdate():
                self.is_probation_status = 'completed'
            else:
                self.is_probation_status = 'pending'

        super().save(*args, **kwargs)
    class Meta:
        unique_together = ("CandidateId",)


# ///////////////////// Phase 2  ///////////////////////////

class ClientCandidateJoiningHistory(models.Model):

    candidate=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    requirement=models.ForeignKey(Requirement,on_delete=models.CASCADE,blank=True,null=True)
    client_interview=models.ForeignKey(InterviewSchedulModel,on_delete=models.CASCADE,blank=True,null=True)
    joining_date=models.DateField(blank=True,null=True)
    remarks=models.TextField(blank=True,null=True)
    CTC=models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField(blank=True,null=True)
    commisition_percentage=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    gst_percentage=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    is_active=models.BooleanField(default=False)
    is_invoice_created=models.BooleanField(default=False)
    is_joined=models.BooleanField(default=False)
    created_on=models.DateTimeField(default=timezone.localtime)

    def save(self, *args, **kwargs):
        if self.client_interview:
            # Deactivate all other instances for the same interview
            ClientCandidateJoiningHistory.objects.filter(
                client_interview=self.client_interview
            ).update(is_active=False, is_joined=False)
        
        # Set the current instance as active and joined
        self.is_active = True
        self.is_joined = True

        super().save(*args, **kwargs)


def invoice_num_id():
    return "MTM"+str(uuid.uuid4().hex)[:7].upper()

class Client_Invoice(models.Model):
    joined_details=models.OneToOneField(ClientCandidateJoiningHistory,on_delete=models.CASCADE,blank=True,null=True)
    # candidate=models.ForeignKey(CandidateApplicationModel,on_delete=models.CASCADE,blank=True,null=True)
    # requirement=models.ForeignKey(Requirement,on_delete=models.CASCADE,blank=True,null=True)
    invoice_number = models.CharField(max_length=50,unique=True,default=invoice_num_id)
    date_issued = models.DateTimeField(default=timezone.localtime)
    # due_date = models.DateField(blank=True,null=True)
    # gst_percentage=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    gst_amount=models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    # commisition_percentage=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    commisition_amount=models.DecimalField(max_digits=10, decimal_places=2,blank=True,null=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2,blank=True,null=True) 
    is_paid = models.BooleanField(default=False)
    generated_on=models.DateTimeField(default=timezone.localtime)

    def save(self,*args, **kwargs):
        if self.joined_details and self.joined_details.CTC:
            ctc=self.joined_details.CTC

            if self.joined_details.commisition_percentage:
                self.commisition_amount= (self.joined_details.commisition_percentage/100)*ctc
            else:
                self.commisition_amount = 0

            if self.joined_details.gst_percentage:
                self.gst_amount= (self.joined_details.gst_percentage/100)* self.commisition_amount
            else:
                self.gst_amount = 0

            self.amount = self.commisition_amount + self.gst_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Invoice no- {self.invoice_number}"

class ClientPaymentent(models.Model):
    generated_invoice=models.OneToOneField(Client_Invoice,on_delete=models.CASCADE)
    success=models.BooleanField(default=False)
    code=models.CharField(max_length=100,blank=True,null=True)
    message=models.CharField(max_length=500,blank=True,null=True)
    transaction_id = models.CharField(max_length=500, blank=True, null=True)  # Required for non-cash payments
    utr = models.CharField(max_length=500, blank=True, null=True)
    payment_date = models.DateTimeField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    state=models.CharField(max_length=100,blank=True,null=True)
    responseCode=models.CharField(max_length=100,blank=True,null=True)
    payment=models.CharField(max_length=100,blank=True,null=True)
    accountType=models.CharField(max_length=100,blank=True,null=True)
    payment_status=models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        invoice_obj = Client_Invoice.objects.filter(pk= self.generated_invoice).first()
        if self.generated_invoice and self.success == True and self.payment_status == True:
             if invoice_obj:
                invoice_obj.is_paid=True
                invoice_obj.save()
        super().save(*args, **kwargs)





class EmployeeChat(models.Model):
    CHAT_TYPE_CHOICES = (
        ("group_chat", "Group Chat"),
        ("one_to_one_chat", "One-to-One Chat"),
    )
    
    from_employee = models.ForeignKey(
        EmployeeInformation, 
        on_delete=models.CASCADE, 
        related_name="sent_chats"
    )
    to_employee = models.ForeignKey(
        EmployeeInformation, 
        on_delete=models.CASCADE, 
        related_name="received_chats", 
        blank=True, 
        null=True
    )
    to_group_of_emp = models.ManyToManyField(
        EmployeeInformation, 
        related_name="group_chats", 
        blank=True
    )
    chat_type = models.CharField(
        max_length=15, 
        choices=CHAT_TYPE_CHOICES
    )
    chat_message = models.TextField()
    current_date = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Chat from {self.from_employee} - Type: {self.chat_type}"


# ///////////////////////////////..............Activity.......................///////////////////////////////////

class Activity(models.Model):
    Employee=models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='Activatys')
    Activity_added_Date=models.DateField(default=timezone.localdate,blank=True,null=True)
    Activity_Name=models.CharField(max_length=200,blank=True,null=True)
    targets = models.IntegerField(blank=True,null=True)
    # total= models.IntegerField(default=0,blank=True,null=True)
    Assigned_by=models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE,blank=True,null=True, related_name='assigner')
    def __str__(self):
        if self.Activity_Name:
            return self.Activity_Name
        else:
            return str(self.Activity_added_Date)
        
class DailyAchives(models.Model):
    Activity_instance=models.ForeignKey(Activity,on_delete=models.CASCADE,blank=True,null=True)
    achieved = models.IntegerField(default=0,blank=True,null=True)
    Date=models.DateField(blank=True,null=True)

    def __str__(self):
        return f"{self.Activity_instance.Activity_Name} / {self.Date}"

        
class InterviewSchedule(models.Model):
    Employee=models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE, related_name='Interview')
    position = models.CharField(max_length=100,blank=True,null=True)
    targets = models.IntegerField(default=0,blank=True,null=True)
    Walkins_target=models.IntegerField(default=0,blank=True,null=True)
    Offers_target=models.IntegerField(default=0,blank=True,null=True)
    Interview_Added_Date=models.DateField(default=timezone.localdate,blank=True,null=True)
    Assigned_by=models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE,blank=True,null=True)
    def __str__(self):
        return self.position
    
class DailyAchivesInterviewSchedule(models.Model):
    InterviewSchedule=models.ForeignKey(InterviewSchedule,on_delete=models.CASCADE,blank=True,null=True)
    achieved = models.IntegerField(blank=True,null=True,default=0)
    Date=models.DateField(blank=True,null=True)

    def __str__(self):
        return f"{self.InterviewSchedule.position} / {self.Date}"

class WalkIns(models.Model):
    InterviewSchedule= models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE, blank=True,null=True)
    achieved = models.IntegerField(blank=True,null=True,default=0)
    Date=models.DateField(blank=True,null=True)

    def __str__(self):
        return f"{self.InterviewSchedule.position} / {self.Date}"
    
class OfferedPosition(models.Model):
    InterviewSchedule= models.ForeignKey(InterviewSchedule, on_delete=models.CASCADE, blank=True,null=True)
    achieved = models.IntegerField(blank=True,null=True,default=0)
    Date=models.DateField(blank=True,null=True)

    def __str__(self):
        return f"{self.InterviewSchedule.position} / {self.Date}"
    


# ........................................... New Activity Process....................................................

class ActivityListModel(models.Model):
    ch=[("interview_calls","Interview Calls"),("job_posts","Job Posts"),("client_calls","Client Calls")]
    activity_name=models.CharField(max_length=1000,choices=ch)
    desctiption=models.CharField(max_length=100,blank=True,null=True)
    added_on=models.DateTimeField(default=timezone.localtime)
    added_by=models.ForeignKey(EmployeeDataModel,on_delete=models.CASCADE,blank=True,null=True)
    def __str__(self):
        return f"{self.activity_name} / {self.added_on}"

class NewActivityModel(models.Model):
    Activity=models.ForeignKey(ActivityListModel,on_delete=models.CASCADE,blank=True,null=True)
    Employee=models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE,related_name="assigned_to")
    Activity_assigned_Date=models.DateField(default=timezone.localdate,blank=True,null=True)
    targets = models.IntegerField(blank=True,null=True)
    Achived_target=models.IntegerField(default=0)
    activity_assigned_by=models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE,blank=True,null=True,related_name="assigned_from")

    def __str__(self):
        if self.Activity:
            return f'{self.Activity.activity_name}/{self.Activity_assigned_Date}/{self.Employee.EmployeeId}'
        else:
            return str(self.Activity_assigned_Date)
        
class MonthAchivesListModel(models.Model):

    Activity_instance=models.ForeignKey(NewActivityModel,on_delete=models.CASCADE,blank=True,null=True)
    achieved = models.IntegerField(default=0,blank=True,null=True)
    Date=models.DateField(default=timezone.localdate)

    def __str__(self):
        return f"{self.Activity_instance.Activity.activity_name} / {self.Date}"

class NewDailyAchivesModel(models.Model):
    current_day_activity=models.ForeignKey(MonthAchivesListModel,on_delete=models.CASCADE,blank=True,null=True)
    # Activity_instance=models.ForeignKey(NewActivityModel,on_delete=models.CASCADE,blank=True,null=True)
    Created_Date=models.DateTimeField(default=timezone.localtime)
    # job_posts
    position=models.CharField(max_length=500,blank=True,null=True)
    url=models.CharField(max_length=1000,blank=True,null=True)
    job_post_remarks=models.TextField(blank=True,null=True)

    # interview callss
    candidate_name=models.CharField(max_length=100,blank=True,null=True)
    candidate_phone=models.CharField(max_length=100,blank=True,null=True)
    candidate_email=models.CharField(max_length=100,blank=True,null=True)
    candidate_location=models.CharField(max_length=100,blank=True,null=True)
    candidate_designation=models.CharField(max_length=100,blank=True,null=True)
    ch=(("fresher","Fresher"),("experience","Experience"))
    candidate_current_status=models.CharField(max_length=100,choices=ch,blank=True,null=True)
    candidate_experience=models.IntegerField(blank=True,null=True)
    industries_worked=models.CharField(max_length=500,blank=True,null=True) #new
    source = models.CharField(max_length=500,blank=True,null=True) #new
    expected_ctc=models.IntegerField(blank=True,null=True)#new
    current_ctc=models.IntegerField(blank=True,null=True)#new
    DOJ=models.DateField(blank=True,null=True)#new
    have_laptop = models.BooleanField(blank=True,null=True)#new
    # if fresher means collect candidate_for ojt or internal_ihring
    choice=(("OJT","OJT"),("Internal_Hiring","Internal_Hiring"))
    candidate_for=models.CharField(max_length=100,choices=choice,blank=True,null=True)


    choice=[
            ("call_notpicked","Call Not Picked"),
            ("dis_connect","Disconnect"),
            ("will_revert_back","Will Revert Back"),
            ("interview_scheduled","Interview_Scheduled"),
            ("walkin","walkin"),
            ("rejected","Rejected"),("Rejected_by_Candidate","Rejected_by_Candidate"),
            ("to_client","Consider_to_Client"),
            ("offer","Offer"),]

    interview_status=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    message_to_candidates=models.TextField(blank=True,null=True)
    interview_scheduled_date=models.DateTimeField(blank=True,null=True)
    interview_walkin_date=models.DateTimeField(blank=True,null=True)
    interview_call_remarks=models.TextField(blank=True,null=True)

    # client callss
    #30-01-2026
    client_name=models.CharField(max_length=100,blank=True,null=True)
    client_phone=models.CharField(max_length=100,blank=True,null=True)
    client_enquire_purpose=models.CharField(max_length=1500,blank=True,null=True)
    client_spok=models.CharField(max_length=1500,blank=True,null=True)
    choice=[
            ("job","Job"),
            ("converted_to_client","Converted to Client"), # Added to match frontend
            ("closed","Closed"),
            ("followup","FollowUp"),]

    client_status=models.CharField(max_length=100,blank=True,null=True,choices=choice)
    client_call_remarks=models.TextField(blank=True,null=True)
    
    # New fields added for enhanced client tracking
    client_company_name = models.CharField(max_length=500, blank=True, null=True)
    client_email = models.CharField(max_length=150, blank=True, null=True)
    
    #28-01-2026
    # Lead status tracking for follow-up management
    lead_status_choices = [
        ('active', 'Active'),
        ('follow_up', 'Follow Up'),
        ('rejected', 'Rejected'),
        ('closed', 'Closed')
    ]
    lead_status = models.CharField(max_length=20, choices=lead_status_choices, default='active', blank=True, null=True)
    
    # Rejection categorization
    rejection_type_choices = [
        ('emp_rejected', 'Employee Rejected'),
        ('candidate_rejected', 'Candidate Rejected')
    ]
    rejection_type = models.CharField(max_length=30, choices=rejection_type_choices, blank=True, null=True)
    
    # Closure/Rejection reason
    closure_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        activity_neme=self.current_day_activity.Activity_instance.Activity.activity_name
        empid= self.current_day_activity.Activity_instance.Employee.EmployeeId
        return f"{activity_neme} /{empid}/ {self.Created_Date}"

#28-01-2026
class FollowUpModel(models.Model):
    """
    Model to track follow-up records for both interview calls and client calls.
    Supports pending and completed follow-ups with scheduling information.
    """
    activity_record = models.ForeignKey(
        NewDailyAchivesModel, 
        on_delete=models.CASCADE, 
        related_name='followups',
        help_text="Reference to the activity record being followed up" 
    )
    
    follow_up_type_choices = [
        ('interview', 'Interview'),
        ('client', 'Client')
    ]
    follow_up_type = models.CharField(
        max_length=20, 
        choices=follow_up_type_choices,
        help_text="Type of follow-up: interview or client call"
    )
    
    expected_date = models.DateField(help_text="Expected date to follow up")
    expected_time = models.TimeField(help_text="Expected time to follow up")
    notes = models.TextField(blank=True, null=True, help_text="Follow-up notes or instructions")
    
    status_choices = [
        ('pending', 'Pending'),
        ('completed', 'Completed')
    ]
    status = models.CharField(
        max_length=20, 
        choices=status_choices, 
        default='pending',
        help_text="Current status of the follow-up"
    )
    
    created_on = models.DateTimeField(default=timezone.localtime, help_text="When the follow-up was created")
    completed_on = models.DateTimeField(blank=True, null=True, help_text="When the follow-up was marked as completed")
    
    created_by = models.ForeignKey(
        EmployeeDataModel, 
        on_delete=models.CASCADE, 
        related_name='created_followups',
        help_text="Employee who created this follow-up"
    )
    
    class Meta:
        ordering = ['-created_on']
        verbose_name = "Follow Up"
        verbose_name_plural = "Follow Ups"
    
    def __str__(self):
        candidate_or_client = self.activity_record.candidate_name or self.activity_record.client_name or "Unknown"
        return f"{self.follow_up_type} Follow-up for {candidate_or_client} - {self.status}"


class ClientServicesModel(models.Model):
    client=models.ForeignKey(OurClients,on_delete=models.CASCADE,blank=True,null=True)
    client_contact=models.ForeignKey(NewDailyAchivesModel,on_delete=models.CASCADE,blank=True,null=True)
    service_name=models.CharField(max_length=1500,blank=True,null=True)
    created_on=models.DateTimeField(default=timezone.localtime)



###############################################################################################################

# HRM_App/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="e.g., Python, Django, React, Project Management")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Company(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Technology, Finance, Healthcare")
    logo = models.ImageField(upload_to='company_logos/', blank=True, null=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

class JobPosting(models.Model):
    class JobType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full-Time'
        PART_TIME = 'PART_TIME', 'Part-Time'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        CONTRACT = 'CONTRACT', 'Contract'

    class SalaryType(models.TextChoices):
        PER_YEAR = 'YEARLY', 'Per Year'
        PER_MONTH = 'MONTHLY', 'Per Month'
        PER_HOUR = 'HOURLY', 'Per Hour'

    class EducationLevel(models.TextChoices):
        ANY = 'ANY', 'Any'
        HIGH_SCHOOL = 'HIGH_SCHOOL', 'High School'
        BACHELORS = 'BACHELORS', "Bachelor's Degree"
        MASTERS = 'MASTERS', "Master's Degree"
        PHD = 'PHD', "PhD"
    
    title = models.CharField(max_length=255)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='job_postings')
    location = models.CharField(max_length=255, help_text="e.g., 'New York, NY', 'Remote'")
    job_description = models.TextField()
    job_type = models.CharField(max_length=20, choices=JobType.choices, default=JobType.FULL_TIME)
    vacancies = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    salary_min = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    salary_max = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    salary_currency = models.CharField(max_length=5, default='USD', help_text="e.g., USD, EUR, INR")
    salary_type = models.CharField(max_length=10, choices=SalaryType.choices, default=SalaryType.PER_YEAR)
    experience_required_min_years = models.PositiveIntegerField(default=0)
    experience_required_max_years = models.PositiveIntegerField(blank=True, null=True)
    education_required = models.CharField(max_length=20, choices=EducationLevel.choices, default=EducationLevel.ANY)
    skills_required = models.ManyToManyField(Skill, blank=True, related_name='job_postings')
    is_active = models.BooleanField(default=True, help_text="Uncheck this to hide the job from students/public API")
    application_deadline = models.DateField(blank=True, null=True)
    posted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, editable=False, related_name='job_postings')
    posted_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-posted_on']

    def save(self, *args, **kwargs):
        if self.application_deadline and self.application_deadline < timezone.now().date():
            self.is_active = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} at {self.company.name}"