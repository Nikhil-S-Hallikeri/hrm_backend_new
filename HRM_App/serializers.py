from rest_framework import serializers
from .models import *

class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model=RegistrationModel
        fields='__all__'


class excludeRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model=RegistrationModel
        exclude=["Password","is_active","is_login"]

class FilterCandidateApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields='__all__'
    
from datetime import datetime, date, timedelta

class CandidateApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName','LastName','DOB','Email','PrimaryContact',"AppliedDesignation","AppliedDate","Appling_for","current_position","Final_Results",'JobPortalSource',"Other_jps","Referred_by"]
    def to_representation(self, instance):
        representation=super().to_representation(instance)
        name=instance.FirstName
        if instance.LastName:
            name=name+" "+instance.LastName

        portal=instance.JobPortalSource
        if instance.JobPortalSource == "referral":
            portal = f"{instance.JobPortalSource}(By-{instance.Referred_by})" if instance.Referred_by else f"{instance.JobPortalSource}(By- not filled)"
        representation['JobPortalSource'] = portal
        
        representation['FirstName'] = name
        applied_time = instance.AppliedDate.time().replace(microsecond=0)
        applied_time_with_offset = (datetime.combine(date.min, applied_time) + timedelta(hours=5, minutes=30)).time()
        representation['AppliedTime'] = applied_time_with_offset
        representation['AppliedDate'] = instance.AppliedDate.date()
        representation['ScreeningStatus'] = instance.Telephonic_Round_Status
        representation['InterviewStatus'] = instance.Interview_Schedule
        return representation

class FinalResultCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName','Email','PrimaryContact',"AppliedDesignation","Fresher","Experience","DOB","Final_Results","Documents_Upload_Status","BG_Status","Offer_Letter_Status","current_position","Appling_for"]
class RecCandidateFillingserializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName','Email','PrimaryContact',"AppliedDesignation","Fresher","Experience","current_position","Appling_for"]

class ScreeningCandidateApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName',"Telephonic_Round_Status"]

class InterviewCandidateApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName',"Interview_Schedule"]

class FresherApplicationSerializer(serializers.ModelSerializer):

    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName','LastName','Email','PrimaryContact','SecondaryContact','Location','Fresher',"current_position",'Gender',"DOB",
                'HighestQualification','University','Specialization','Percentage','YearOfPassout','TechnicalSkills',
                'GeneralSkills','SoftSkills','AppliedDesignation','ExpectedSalary','ContactedBy','JobPortalSource',"Other_jps","Referred_by",'AppliedDate',"Appling_for"]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        portals= instance.JobPortalSource
        if instance.JobPortalSource=="others":
            portals = f"{instance.JobPortalSource}({instance.Other_jps})" if instance.Other_jps else instance.JobPortalSource
        elif instance.JobPortalSource=="referral":
            portals= f"{instance.JobPortalSource}(By-{instance.Referred_by})" if instance.Referred_by else f"{instance.JobPortalSource}(By- not filled)"
        # representation['AppliedDate']=instance.AppliedDate.date().strftime('%d-%m-%Y')
        representation['JobPortalSource']=portals.title()
        return representation
        
class ExperienceApplicationSerializer(serializers.ModelSerializer):
    class Meta: 
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName','LastName','Email','PrimaryContact','SecondaryContact','Location','Gender',"DOB",'Experience',"current_position",
                'HighestQualification','University','Specialization','Percentage','YearOfPassout','TechnicalSkills_with_Exp',
                'GeneralSkills_with_Exp','SoftSkills_with_Exp','JobPortalSource',"Other_jps","Referred_by",'AppliedDesignation','NoticePeriod','CurrentDesignation','CurrentCTC','TotalExperience','ExpectedSalary','ContactedBy','AppliedDate',"Appling_for"]
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)

        portals= instance.JobPortalSource
        if instance.JobPortalSource=="others":
            portals = f"{instance.JobPortalSource}({instance.Other_jps})" if instance.Other_jps else instance.JobPortalSource
        elif instance.JobPortalSource=="referral":
            portals= f"{instance.JobPortalSource}(By-{instance.Referred_by})" if instance.Referred_by else f"{instance.JobPortalSource}(By- not filled)"
        
        # representation['AppliedDate']=instance.AppliedDate.date()
        representation['JobPortalSource']=portals.title()

        return representation

class CalledCandidatesSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalledCandidatesModel
        fields = '__all__'

    def to_representation(self, instance):
        representation=super().to_representation(instance)
        representation['called_by'] = instance.called_by.EmployeeId if instance.called_by else None
        called_Time= instance.called_date.time().replace(microsecond=0)
        applied_time_with_offset = (datetime.combine(date.min, called_Time) + timedelta(hours=5, minutes=30)).time()
        representation['called_Time'] = applied_time_with_offset
        representation['called_date'] = instance.called_date.date()
        return representation

class EmployeeInformationSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = EmployeeInformation
        # exclude=["Offered_Instance"]
        fields="__all__"

        


class EmployeeDataSerializer(serializers.ModelSerializer):
    # employeeProfile = EmployeeInformationSerializer(read_only=True)
    class Meta:
        model = EmployeeDataModel
        fields = "__all__"

    #19/02/2026
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Include employee_status from the linked EmployeeInformation profile
        # This allows the attendance API to expose whether the employee is active/in_active/Resigned
        if instance.employeeProfile:
            representation['employee_status'] = instance.employeeProfile.employee_status
        else:
            representation['employee_status'] = None
        return representation

class ScreeningEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDataModel
        fields = ("id",'EmployeeId', 'Name')

class InterviewSchedulSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedulModel
        fields = ('id',"Candidate","InterviewRoundName","interviewer","InterviewDate","InterviewType","ScheduledBy","ScheduledOn","for_whome","assigned_requirement")
    
    def to_representation(self, instance):
        representation=super().to_representation(instance)
        representation['InterviewDate'] = instance.InterviewDate.date()
        representation['InterviewTime'] = instance.InterviewDate.time().replace(second=0, microsecond=0)
        representation['ScheduledOn'] = instance.ScheduledOn.date()
        representation['ScheduledTime'] = instance.ScheduledOn.time().replace(second=0, microsecond=0)
        return representation
    

class AssignedCLientInterviewSchedulSerializer(serializers.ModelSerializer):
    # Candidates=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = InterviewSchedulModel
        fields = ('id',"Candidate","InterviewRoundName","interviewer","InterviewDate","InterviewType","ScheduledBy","ScheduledOn","for_whome","assigned_requirement")
    
    def to_representation(self, instance):
        representation=super().to_representation(instance)
        representation['InterviewDate'] = instance.InterviewDate.date()
        representation['InterviewTime'] = instance.InterviewDate.time().replace(second=0, microsecond=0)
        representation['ScheduledOn'] = instance.ScheduledOn.date()
        representation['ScheduledTime'] = instance.ScheduledOn.time().replace(second=0, microsecond=0)
        return representation


from Contract_Emp_App.serializer import Requirementserializer
class AssignedRequirementSerializer(serializers.ModelSerializer):
    requirement_data=serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = RequirementAssign
        fields ="__all__"
    
    def get_requirement_data(self,obj):
        if obj and hasattr(obj, 'requirement'):
            req=Requirementserializer(obj.requirement).data
            return req
        return {}


class ClientInterviewSchedulSerializer(serializers.ModelSerializer):
    assigned_requiremint=serializers.SerializerMethodField(read_only=True)
    candidate_data=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = InterviewSchedulModel
        fields = "__all__"
    def get_assigned_requiremint(self,obj):
        if obj and hasattr(obj, 'assigned_requirement'):
            assign_req=AssignedRequirementSerializer(obj.assigned_requirement).data
            assign_req["requirement_data"].pop('client_details', None)
            return assign_req
        return {}
    
    def get_candidate_data(self,obj):
        if obj and hasattr(obj,"Candidate"):
            assigned_candidate=CandidateApplicationSerializer(obj.Candidate).data
            return assigned_candidate
    
    def to_representation(self, instance):
        representation=super().to_representation(instance)
        representation['InterviewDate'] = instance.InterviewDate.date()
        representation['InterviewTime'] = instance.InterviewDate.time().replace(second=0, microsecond=0)
        representation['ScheduledOn'] = instance.ScheduledOn.date()
        representation['ScheduledTime'] = instance.ScheduledOn.time().replace(second=0, microsecond=0)
        representation['Interviewer_name'] = instance.interviewer.Name
        representation['assigner_name'] = instance.ScheduledBy.Name
        return representation

class InterviewScheduleStatusSreializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewScheduleStatusModel
        fields = "__all__"

class FilterInterviewSchedulSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedulModel
        fields = "__all__"

class ScreeningProcessSerializer(serializers.ModelSerializer):
    class Meta:
        model= ScreeningProcessModel
        fields="__all__"

class ActivityScreeningReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields=['CandidateId', 'Name', 'PositionAppliedFor', 'SourceBy', 'SourceName','TotalYearOfExp',
                'LastCTC', 'ExpectedCTC','InterviewScheduleDate','CurrentLocation', 'ModeOfCommutation', 'Residingat', 'Native', 
                'About_Family', 'MeritalStatus','LanguagesKnown','LastCTC', 'ExpectedCTC', 'NoticePeriod' ,"OwnLoptop"
                ,'DOJ', 'Six_Days_Working', 'FlexibilityOnWorkTimings', 'RelocateToOtherCity', 'RelocateToOtherCenters', 
                "FathersName","FathersDesignation","MothersName","MothersDesignation","SpouseDesignation","SpouseName","About_Childrens",
                "devorced_statement",'Screening_Status','Comments','ReviewedBy',"InterviewerName",'Signature', 'ReviewedOn',
                  ]
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.screeingreview:
            representation["Assigned_by"]=instance.screeingreview.AssignedBy.EmployeeId
            representation["Assigned_on"]=instance.screeingreview.Date_of_assigned
        representation["CandidateId"]=instance.CandidateId.CandidateId
        return representation
        


       
    
    


class ScreeningAssigningSerializer(serializers.ModelSerializer):
    class Meta:
        model=ScreeningAssigningModel
        fields=('id',"Candidate","Recruiter","AssignedBy","Date_of_assigned")

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['recruiter_name'] = instance.Recruiter.Name
        representation['assigner_name'] = instance.AssignedBy.Name
        # representation['recruiter_Id'] = instance.Recruiter.id
        # representation['assigner_Id'] = instance.AssignedBy.id
        # representation['Date_of_assigned'] = instance.Date_of_assigned.date()
        # representation['Time'] = instance.Date_of_assigned.time()
        return representation
    

class NewScreeningAssigningSerializer(serializers.ModelSerializer):
    class Meta:
        model=ScreeningAssigningModel
        fields=('id',"Candidate","Recruiter","AssignedBy","Date_of_assigned")
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        name=instance.Candidate.FirstName
        if instance.Candidate.LastName:
            name=name+" "+instance.Candidate.LastName
            
        representation['Candidate_name'] = name
        representation['Applied_Designation'] = instance.Candidate.AppliedDesignation
        representation['Candidate'] = instance.Candidate.CandidateId
        representation['Candidate_Id'] = instance.Candidate.id
        representation['recruiter_name'] = instance.Recruiter.Name
        representation['assigner_name'] = instance.AssignedBy.Name
        representation['recruiter_Id'] = instance.Recruiter.id
        representation['assigner_Id'] = instance.AssignedBy.id
        representation['Recruiter'] = instance.Recruiter.EmployeeId
        representation['AssignedBy'] = instance.AssignedBy.EmployeeId
        return representation
    
class NewInterviewSchedulSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSchedulModel
        fields = ('id',"Candidate","InterviewRoundName","interviewer","InterviewDate","InterviewType","ScheduledBy","ScheduledOn")
    
    def to_representation(self, instance):

        representation=super().to_representation(instance)
        name=instance.Candidate.FirstName
        if instance.Candidate.LastName:
            name=name+" "+instance.Candidate.LastName

        if not instance.inside_interviewer:
            representation['Out_EMP_email']=instance.Out_EMP_email
        representation['Candidate_name'] = name
        representation['Applied_Designation'] = instance.Candidate.AppliedDesignation
        representation['Candidate'] = instance.Candidate.CandidateId
        representation['Candidate_Id'] = instance.Candidate.id
        representation["interviewer"]=instance.interviewer.EmployeeId
        representation["interviewer_name"]=instance.interviewer.Name
        representation["interviewer_Id"]=instance.interviewer.id
        representation["ScheduledBy"]=instance.ScheduledBy.EmployeeId
        representation["ScheduledBy_name"]=instance.ScheduledBy.Name
        representation["ScheduledBy_Id"]=instance.ScheduledBy.id
        return representation

class CandidateExcelUploadSerializer(serializers.Serializer):
    excel_file = serializers.FileField()

class EmployeeExcelUploadSerializer(serializers.Serializer):
    excel_file = serializers.FileField()

class ScreeningReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields=['CandidateId', 'Name', 'PositionAppliedFor', 'SourceBy', 'SourceName','TotalYearOfExp',
                'LastCTC', 'ExpectedCTC','InterviewScheduleDate','CurrentLocation', 'ModeOfCommutation', 'Residingat', 'Native', 
                'About_Family', 'MeritalStatus','LanguagesKnown','LastCTC', 'ExpectedCTC', 'NoticePeriod' ,"OwnLoptop"
                ,'DOJ', 'Six_Days_Working', 'FlexibilityOnWorkTimings', 'RelocateToOtherCity', 'RelocateToOtherCenters', 
                "FathersName","FathersDesignation","MothersName","MothersDesignation","SpouseDesignation","SpouseName","About_Childrens",
                "devorced_statement",'Screening_Status','Comments','ReviewedBy',"InterviewerName",'Signature', 'ReviewedOn',
                  ]
                
class SRS(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields=['CandidateId','Screening_Status','ReviewedBy', "InterviewerName",'ReviewedOn',"id"]


review_fields=['CandidateId', 'Name', 'PositionAppliedFor', 'SourceBy', 'SourceName', 'Date', 'LocationAppliedFor', 
                  'Contact', 'Qualification', 'RelatedExperience', 'JobStabilityWithPreviousEmployers', 
                  'ReasionForLeavingImadiateEmployeer', 'Appearence_and_Personality', 'ClarityOfThought', 
                  'EnglishLanguageSkills', 'AwarenessOnTechnicalDynamics', 'InterpersonalSkills', 'ConfidenceLevel', 
                  'AgeGroupSuitability', 'Analytical_and_logicalReasoningSkills', 'CareerPlans', 'AchivementOrientation', 
                  'ProblemSolvingAbilites', 'AbilityToTakeChallenges', 'LeadershipAbilities', 'IntrestWithCompany', 
                  'ResearchedAboutCompany', 'HandelTargets_Pressure', 'CustomerService', 'OverallCandidateRanking', 
                  'interview_Status', 'ReviewedBy',"InterviewerName",'Signature', 'ReviewedOn', 'Comments']

class InterviewReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = review_fields

class clientInterviewReviewSerializer(serializers.ModelSerializer):
    interview_details=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Review
        fields = review_fields
    def get_interview_details(self,obj):
        if obj and hasattr(obj, 'interview_id'):
            assigned_interview=ClientInterviewSchedulSerializer(obj.interview_id).data
            # assigned_interview["requirement_data"].pop('client_details', None)
            return assigned_interview
        return {}
        

class TrInterviewReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ['CandidateId', 'Name', 'PositionAppliedFor', 'SourceBy', 'SourceName', 'Date', 'LocationAppliedFor', 
                  'Contact', 'Qualification', 'RelatedExperience', 'AwarenessOnTechnicalDynamics', 'ConfidenceLevel', 
                  'ProblemSolvingAbilites', 'AbilityToTakeChallenges', 'LeadershipAbilities',"Coding_Questions_Score",'OverallCandidateRanking'
                  ,'interview_Status', 'ReviewedBy',"InterviewerName",'Signature', 'ReviewedOn', 'Comments']
        
class HRInterviewReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = HRFinalStatusModel
        fields="__all__"

class ClientHRInterviewReviewSerializer(serializers.ModelSerializer):
    CandidateId=serializers.SerializerMethodField(read_only=True)
    requirement=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = HRFinalStatusModel
        fields="__all__"
    
    def get_CandidateId(self,obj):
        if obj and hasattr(obj, 'CandidateId'):
            final_candidate=CandidateApplicationSerializer(obj.CandidateId).data
            return final_candidate
        return {}
    def get_requirement(self,obj):
        if obj and hasattr(obj,"req_id"):
            requirement=Requirementserializer(obj.req_id).data
            return requirement
        return {}

class ClientCandidateJoiningHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCandidateJoiningHistory
        fields = "__all__"

class ClientInvoiceSerializer(serializers.ModelSerializer):
    joining_data=serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Client_Invoice
        fields = "__all__"
    
    def get_joining_data(self,obj):
        if obj and hasattr(obj,"joined_details"):
            serializer=ClientCandidateJoiningHistorySerializer(obj.joined_details).data
            return serializer
        return {}
    


class IRS(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields=['CandidateId','interview_Status','ReviewedBy', "InterviewerName",'ReviewedOn',"id"]

    def to_representation(self, instance):
        representation= super().to_representation(instance)
        representation['Candidate_Id'] = instance.CandidateId.CandidateId
        can_fullname= f'{instance.CandidateId.FirstName} {instance.CandidateId.LastName}' if instance.CandidateId.LastName else instance.CandidateId.FirstName
        representation['CandidateName'] = can_fullname.title()
        return representation 
    
        
class CandidateApplicationCompletedSerializer(serializers.ModelSerializer):
    class Meta:
        model=CandidateApplicationModel
        fields=["id",'CandidateId','FirstName',"AppliedDesignation","Telephonic_Round_Status","Interview_Schedule","Test_levels","Offer_Letter_Status"]


class DocumentsModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Documents_Model
        fields = '__all__'  # Serialize all fields

class DocumentsUploadModelSerializer(serializers.ModelSerializer):
    # Documents = DocumentsModelSerializer()  # Nested serializer for Documents_Model
    class Meta:
        model = Documents_Upload_Model
        fields = '__all__'
        
class BGVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=BG_VerificationModel
        fields="__all__"
class DetailsBGVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model=BG_VerificationModel
        exclude = ['Documents', 'candidate']

        
class profileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistrationModel
        fields = ["profile_img"]


class OfferLetterserializer(serializers.ModelSerializer):
    position_name = serializers.SerializerMethodField()
    class Meta:
        model = OfferLetterModel
        fields = "__all__"

    def get_position_name(self, obj):
        return obj.position.Name if obj.position else None

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.letter_verified_by:
            representation['letter_verified_by'] = instance.letter_verified_by.EmployeeId
            representation['letter_verified_by_name'] = instance.letter_verified_by.Name
        if instance.Letter_sended_by:
            representation['Letter_sended_by_emp'] = instance.Letter_sended_by.EmployeeId
            representation['Letter_sended_by_name'] = instance.Letter_sended_by.Name
        if instance.letter_prepared_by:
            representation['letter_prepared_by'] = instance.letter_prepared_by.EmployeeId
            representation['letter_prepared_by_name'] = instance.letter_prepared_by.Name
        representation['CandidateId'] = instance.CandidateId.CandidateId
        representation['current_position'] = instance.CandidateId.current_position
        return representation
    

from django.utils import timezone

class OfferedCandidatesserializer(serializers.ModelSerializer):
    position_name = serializers.SerializerMethodField()
    class Meta:
        model=OfferLetterModel
        fields=["id","CandidateId","Name","DOB","Email","Date_of_Joining","Employeement_Type","OfferedDate","Accept_status","position"]

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['CandidateId'] = instance.CandidateId.CandidateId
        return representation
        

class DOJ_OfferLetterserializer(serializers.ModelSerializer):
    class Meta:
        model=OfferLetterModel
        fields=["Date_of_Joining"]

class Positionsserializer(serializers.ModelSerializer):
    class Meta:
        model=DesignationModel
        fields="__all__"

class AcceptOfferLetterserializer(serializers.ModelSerializer):
    class Meta:
        model=OfferLetterModel
        fields=["CandidateId","Date_of_Joining","Letter_sended_by","Mail_Status"]

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model=Deparments
        fields="__all__"
    
class DesignationSerializer(serializers.ModelSerializer):
    class Meta:
        model=DesignationModel
        fields="__all__"
    def to_representation(self, instance):
        representation=super().to_representation(instance)
        representation['Department'] = instance.Department.Dep_Name
        return representation

# class WishNotificationsSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = WishNotifications
#         fields = "__all__"
    
#     def to_representation(self, instance):
#         representation=super().to_representation(instance)
#         representation['wishes_to_emp'] = instance.wishes_to_emp.EmployeeId if instance.wishes_to_emp else None
#         return representation




# Edited
class WishNotificationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishNotifications
        fields = "__all__"
    
    # def to_representation(self, instance):
    #     representation = super().to_representation(instance)
    #     representation['wish_message'] = instance.wishes_to_emp.EmployeeId if instance.wishes_to_emp else None
    #     return representation


    # Orignal from Server 
    
    # def to_representation(self, instance):
    #     representation=super().to_representation(instance)
    #     representation['wishes_to_emp'] = instance.wishes_to_emp.EmployeeId if instance.wishes_to_emp else None
    #     return representation










# from rest_framework import serializers
# from datetime import datetime, timedelta, timezone

# class NotificationSerializer(serializers.ModelSerializer):
#     timestamp = serializers.SerializerMethodField()
#     class Meta:
#         model = Notification
#         fields = "__all__" 

#     def get_timestamp(self, obj):
#         now = datetime.now(timezone.utc)  # Ensure 'now' is timezone-aware
#         # Convert obj.timestamp to UTC if it's timezone-aware
#         if obj.timestamp.tzinfo is not None:
#             obj_timestamp_utc = obj.timestamp.astimezone(timezone.utc)
#         else:
#             obj_timestamp_utc = obj.timestamp  # Otherwise, it's already UTC

#         time_difference = now - obj_timestamp_utc

#         if time_difference < timedelta(minutes=1):  # Less than a minute
#             return "just now"
#         elif time_difference < timedelta(minutes=2):  # Less than 2 minutes
#             return "1 minute ago"
#         elif time_difference < timedelta(hours=1):  # Less than an hour
#             return f"{int(time_difference.total_seconds() // 60)} minutes ago"
#         elif time_difference < timedelta(hours=2):  # Less than 2 hours
#             return "1 hour ago"
#         elif time_difference < timedelta(days=1):  # Less than a day
#             return f"{int(time_difference.total_seconds() // 3600)} hours ago"
#         elif time_difference < timedelta(days=2):  # Less than 2 days
#             return "1 day ago"
#         elif time_difference < timedelta(weeks=1):  # Less than a week
#             return f"{time_difference.days} days ago"
#         elif time_difference < timedelta(weeks=2):  # Less than 2 weeks
#             return "1 week ago"
#         elif time_difference < timedelta(weeks=52):  # Less than a year
#             return f"{time_difference.days // 7} weeks ago"
#         else:  # More than a year
#             return f"{time_difference.days // 365} years ago"
        
#     def to_representation(self, instance):
#         representation = super().to_representation(instance)
#         if instance.sender:
#             representation['sender'] = instance.sender.EmployeeId
#         if instance.receiver:
#             representation['receiver'] = instance.receiver.EmployeeId
#         if instance.candidate_id:
#             representation['candidate_id'] = instance.candidate_id.CandidateId
#         return representation

#changes
from rest_framework import serializers
from django.utils.timesince import timesince 

class NotificationSerializer(serializers.ModelSerializer):
    timesince = serializers.SerializerMethodField()
    sender_name = serializers.CharField(source='sender.UserName', read_only=True, default='System')
    notification_type = serializers.CharField(source='not_type', read_only=True)
    candidate_name = serializers.CharField(source='candidate_id.FirstName', read_only=True, default='')
    # reference_id = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ('id', 'sender', 'receiver', 'message', 'notification_type', 'reference_id', 
                  'read_status', 'timestamp', 'timesince', 'sender_name', 'candidate_name')
        # fields = "__all__"
    
    def get_timesince(self, obj):
        return timesince(obj.timestamp, depth=1) + " ago"  
    
    def get_reference_id(self, obj):
        if obj.candidate_id:
            return obj.candidate_id.CandidateId
        return None
        
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if instance.sender:
            representation['sender'] = instance.sender.EmployeeId
        if instance.receiver:
            representation['receiver'] = instance.receiver.EmployeeId
        if instance.candidate_id:
            representation['candidate_id'] = instance.candidate_id.CandidateId
        return representation

class LetterTemplatesSerializer(serializers.ModelSerializer):
    class Meta:
        model=LetterTemplatesModel
        fields="__all__"

class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model=Activity 
        fields="__all__"
        
    Activity_instance = serializers.StringRelatedField()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['Employee'] = instance.Employee.EmployeeId
        # representation['Assigned_by'] = instance.Assigned_by.EmployeeId 
        return representation

class DailyAchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model=DailyAchives
        fields="__all__"
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['Activity_instance'] = instance.Activity_instance.Activity_Name
        return representation
    
class ActivityInterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model=InterviewSchedule
        fields="__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['Employee'] = instance.Employee.EmployeeId
        representation['Assigned_by'] = instance.Assigned_by.EmployeeId
        representation['Walkins_target'] = None
        representation['Offers_target'] = None
        return representation
    
class ActivityInterviewWalkinsSerializer(serializers.ModelSerializer):
    class Meta:
        model=InterviewSchedule
        fields="__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['Employee'] = instance.Employee.EmployeeId
        representation['Assigned_by'] = instance.Assigned_by.EmployeeId
        representation['targets'] = None
        representation['Offers_target'] = None
        return representation
    
class ActivityInterviewOffersSerializer(serializers.ModelSerializer):
    class Meta:
        model=InterviewSchedule
        fields="__all__"
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['Employee'] = instance.Employee.EmployeeId
        representation['Assigned_by'] = instance.Assigned_by.EmployeeId
        representation['Walkins_target'] = None
        representation['targets'] = None
        return representation

class DailyAchiveInterviewScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model=DailyAchivesInterviewSchedule
        fields="__all__"
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['InterviewSchedule'] = instance.InterviewSchedule.position
        return representation

class WalkInSerializer(serializers.ModelSerializer):
    class Meta:
        model=WalkIns
        fields="__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['InterviewSchedule'] = instance.InterviewSchedule.position
        return representation

class OffredScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model=OfferedPosition
        fields="__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['InterviewSchedule'] = instance.InterviewSchedule.position
        return representation
    

# ............................................... new activity serializers ...............................................

# Serializer for ActivityListModel
class ActivityListModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityListModel
        fields = "__all__"


# Serializer for NewActivityModel
class NewActivityModelSerializer(serializers.ModelSerializer):
    # Nested representation for Activity and Employee details
    # Activity_details = ActivityListModelSerializer(read_only=True)

    class Meta:
        model = NewActivityModel
        fields = "__all__"
    
    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['activity_name'] = instance.Activity.activity_name
        return representation
    

class MonthAchivesListSerializer(serializers.ModelSerializer):
    # Nested representation for related foreign key fields
    # Activity_instance = NewActivityModelSerializer(read_only=True)
    class Meta:
        model = MonthAchivesListModel
        fields = "__all__"

# Serializer for NewDailyAchivesModel
class NewDailyAchivesModelSerializer(serializers.ModelSerializer):
    # Nested representation for related foreign key fields
    # current_day_activity = MonthAchivesListSerializer(read_only=True)

    class Meta:
        model = NewDailyAchivesModel
        fields = "__all__"

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        activity_name = "-"
        try:
            if instance.current_day_activity and instance.current_day_activity.Activity_instance and instance.current_day_activity.Activity_instance.Activity:
                activity_name = instance.current_day_activity.Activity_instance.Activity.activity_name
        except AttributeError:
            pass
        representation['Activity_instance'] = activity_name
        return representation
    
#28-01-2026
# Serializer for FollowUpModel
class FollowUpSerializer(serializers.ModelSerializer):
    # Nested fields for better readability
    created_by_name = serializers.CharField(source='created_by.Name', read_only=True)
    created_by_id = serializers.CharField(source='created_by.EmployeeId', read_only=True)
    candidate_or_client_name = serializers.SerializerMethodField(read_only=True)
    candidate_or_client_phone = serializers.SerializerMethodField(read_only=True)
    activity_type = serializers.CharField(source='activity_record.current_day_activity.Activity_instance.Activity.activity_name', read_only=True)
    activity_lead_status = serializers.CharField(source='activity_record.lead_status', read_only=True)  # For showing completion type
    
    class Meta:
        model = FollowUpModel
        fields = '__all__'
    
    def get_candidate_or_client_name(self, obj):
        """Get the name from the activity record (candidate or client)"""
        if obj.activity_record:
            return obj.activity_record.candidate_name or obj.activity_record.client_name
        return None
    
    def get_candidate_or_client_phone(self, obj):
        """Get the phone from the activity record (candidate or client)"""
        if obj.activity_record:
            return obj.activity_record.candidate_phone or obj.activity_record.client_phone
        return None


class ClientServicesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientServicesModel
        fields = "__all__"



#############################################################################
# hrm_project/serializers.py
# HRM_App/serializers.py

from rest_framework import serializers
from .models import Company, JobPosting, Skill

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']

class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'website', 'industry', 'logo']

class JobPostingSerializer(serializers.ModelSerializer):
    company = CompanySerializer(read_only=True)
    skills_required = SkillSerializer(many=True, read_only=True)
    posted_by_username = serializers.CharField(source='posted_by.username', read_only=True)
    
    company_id = serializers.PrimaryKeyRelatedField(
        queryset=Company.objects.all(), source='company', write_only=True
    )
    skills_required_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(), source='skills_required', many=True, write_only=True, required=False
    )

    class Meta:
        model = JobPosting
        fields = [
            'id', 'title', 'job_description', 'location', 'job_type', 'vacancies',
            'company', 'company_id',
            'salary_min', 'salary_max', 'salary_currency', 'salary_type',
            'experience_required_min_years', 'experience_required_max_years',
            'education_required',
            'skills_required', 'skills_required_ids',
            'is_active', 'application_deadline', 'posted_on', 'posted_by_username'
        ]
        read_only_fields = ['posted_on', 'posted_by_username']

    def validate(self, data):
        if 'salary_min' in data and 'salary_max' in data and data['salary_min'] is not None and data['salary_max'] is not None:
            if data['salary_min'] > data['salary_max']:
                raise serializers.ValidationError({"salary_max": "Maximum salary cannot be less than minimum salary."})
        return data