from .imports import *
#hired data
from django.utils import timezone
from django.db.models import Q
from datetime import datetime

def review_duration(duration,FromDate=None,ToDate=None):
    # duration = datetime.strptime(duration, "%Y-%m-%d").date()
    if duration == "Today":
            # Filter candidates reviewed today
        review_date = timezone.localdate()
        return review_date
    elif duration == "Last_Week":
            # Filter candidates reviewed in the last week
        review_date = timezone.localdate() - timezone.timedelta(days=7)
        return review_date
    elif duration == "Month":
            # Filter candidates reviewed in the last month
        review_date = timezone.localdate() - timezone.timedelta(days=30)
        return review_date
    elif duration == "Year":
            # Filter candidates reviewed in the last month
        review_date = timezone.localdate() - timezone.timedelta(days=360)
        return review_date
    else:
        while ToDate <= FromDate:
            ToDate += timedelta(days=1)


class Candidates_Hired_Filter_View(APIView):
    def get(self, request, duration="Today"):
        Final_Result=review_duration(duration)
        try:
            if Final_Result:
                interview_hired_list = CandidateApplicationModel.objects.filter(CandidateId__Final_Results="Internal Hiring")
                serializer = FinalResultCandidateSerializer(interview_hired_list, many=True)
            else:
                serializer=[]
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Review.DoesNotExist:
            return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)

class Candidates_Rejected_Filter_View(APIView):
    def get(self, request, duration="Today"):
        Final_Result=review_duration(duration)
        try:
            if Final_Result:
                interview_hired_list = CandidateApplicationModel.objects.filter(CandidateId__Final_Results="Reject")
                serializer = FinalResultCandidateSerializer(interview_hired_list, many=True)
            else:
                serializer=[]
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Review.DoesNotExist:
            return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
        
class Candidates_Client_Filter_View(APIView):
    def get(self, request, duration="Today"):
        Final_Result=review_duration(duration)
        try:
            if Final_Result:
                interview_hired_list = CandidateApplicationModel.objects.filter(CandidateId__Final_Results="consider to client")
                serializer = FinalResultCandidateSerializer(interview_hired_list, many=True)
            else:
                serializer=[]
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Review.DoesNotExist:
            return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
        
# .............................Candidate Search................................

# from django.db.models import Q
# class CandidateApplicationSearchView(APIView):
#     def post(self, request):
#         search_value = request.data.get("search_value")
#         duration = request.data.get("duration")
#         from_date = request.data.get("FromDate")
#         to_date = request.data.get("ToDate")
#         # status_filter = request.data.get("Status")
#         applied_designation = request.data.get("AppliedDesignation")
#         job_portal_source = request.data.get("JobPortalSource")
#         applied_date = request.data.get("AppliedDate")

#         filters = Q(Filled_by="Candidate")  # Default filter condition

#         # **Search by value across multiple fields**
#         if search_value:
#             filters &= (Q(CandidateId__icontains=search_value) |
#                         Q(Email__icontains=search_value) |
#                         Q(PrimaryContact__icontains=search_value) |
#                         Q(AppliedDesignation__icontains=search_value) |
#                         Q(FirstName__icontains=search_value) |
#                         Q(LastName__icontains=search_value) |
#                         Q(JobPortalSource__icontains=search_value))

#         # **Filter by Applied Date Range**
#         if from_date and to_date:
#             filters &= Q(DataOfApplied__range=(from_date, to_date))

#         # **Filter by Specific Applied Date**
#         if applied_date:
#             filters &= Q(DataOfApplied=applied_date)

#         # **Filter by Designation**
#         if applied_designation:
#             filters &= Q(AppliedDesignation__icontains=applied_designation)

#         # **Filter by Job Portal Source**
#         if job_portal_source:
#             filters &= Q(JobPortalSource__icontains=job_portal_source)

#         # **Filter by Duration (Today, Week, Month, Year)**
#         if duration:
#             today = timezone.localdate()
#             if duration == "Today":
#                 filters &= Q(DataOfApplied=today)
#             elif duration == "Week":
#                 filters &= Q(DataOfApplied__range=(today - timezone.timedelta(days=7), today))
#             elif duration == "Month":
#                 filters &= Q(DataOfApplied__range=(today - timezone.timedelta(days=30), today))
#             elif duration == "Year":
#                 filters &= Q(DataOfApplied__range=(today - timezone.timedelta(days=360), today))

#         # **Retrieve filtered candidates**
#         candidates = CandidateApplicationModel.objects.filter(filters).order_by("-AppliedDate")
#         serializer = CandidateApplicationSerializer(candidates, many=True)
#         return Response(serializer.data, status=status.HTTP_200_OK)

        


#23-12-2025
from rest_framework.pagination import PageNumberPagination

class CandidateSearchPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 200



from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import timedelta

class CandidateApplicationSearchView(APIView):
    pagination_class = CandidateSearchPagination

    def post(self, request):
        data = request.data

        search_value = data.get("search_value")
        duration = data.get("duration")
        from_date = data.get("FromDate")
        to_date = data.get("ToDate")
        applied_designation = data.get("AppliedDesignation")
        job_portal_source = data.get("JobPortalSource")
        applied_date = data.get("AppliedDate")
        screening_status = data.get("ScreeningStatus")
        final_results = data.get("FinalResults")

        # Base queryset (all candidates)
        base_queryset = CandidateApplicationModel.objects.all()
        absolute_count = base_queryset.count()
        queryset = base_queryset

        today = timezone.localdate()

        if applied_date:
            queryset = queryset.filter(DataOfApplied=applied_date)

        elif from_date and to_date:
            queryset = queryset.filter(DataOfApplied__range=(from_date, to_date))

        elif duration:
            if duration == "Today":
                queryset = queryset.filter(DataOfApplied=today)
            elif duration == "Week":
                queryset = queryset.filter(DataOfApplied__gte=today - timedelta(days=7))
            elif duration == "Month":
                queryset = queryset.filter(DataOfApplied__gte=today - timedelta(days=30))
            elif duration == "Year":
                queryset = queryset.filter(DataOfApplied__gte=today - timedelta(days=365))

        if applied_designation:
            queryset = queryset.filter(AppliedDesignation__icontains=applied_designation)

        if job_portal_source:
            queryset = queryset.filter(JobPortalSource=job_portal_source)

        if screening_status:
            if screening_status == 'Pending':
                queryset = queryset.filter(Q(Telephonic_Round_Status='Pending') | Q(Telephonic_Round_Status__isnull=True) | Q(Telephonic_Round_Status=''))
            else:
                queryset = queryset.filter(Telephonic_Round_Status=screening_status)

        if final_results:
            if final_results == 'Pending':
                queryset = queryset.filter(Q(Final_Results='Pending') | Q(Final_Results__isnull=True) | Q(Final_Results=''))
            else:
                queryset = queryset.filter(Final_Results=final_results)

        if search_value:
            queryset = queryset.filter(
                Q(CandidateId__icontains=search_value) |
                Q(Email__icontains=search_value) |
                Q(PrimaryContact__icontains=search_value) |
                Q(FirstName__icontains=search_value) |
                Q(LastName__icontains=search_value) |
                Q(AppliedDesignation__icontains=search_value)
            )

        total_count = queryset.count()

        queryset = queryset.only(
            "id",
            "CandidateId",
            "FirstName",
            "LastName",
            "DOB",
            "Email",
            "PrimaryContact",
            "AppliedDesignation",
            "AppliedDate",
            "Appling_for",
            "current_position",
            "Final_Results",
            "JobPortalSource",
            "Other_jps",
            "Referred_by",
            "Telephonic_Round_Status",
            "Interview_Schedule",
        ).order_by("-AppliedDate")

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)

        serializer = CandidateApplicationSerializer(page, many=True)

        response = paginator.get_paginated_response(serializer.data)
        response.data['total_all'] = absolute_count
        return response








# ...............................search functions..............................

class Candidate_Model_Filter(APIView):
    def post(self,request):
            search_value = request.data.get('search_value', '')  # Assuming the search value is passed in the query parameter 'search_value'
            q_objects = Q()

            for field in CandidateApplicationModel._meta.fields:
                if field.name != 'id':
                    q_objects |= Q(**{f"{field.name}__icontains": search_value})

            matched_objects = CandidateApplicationModel.objects.filter(q_objects)
            serializer = FilterCandidateApplicationSerializer(matched_objects, many=True)  # Assuming you have a serializer for YourModel
            return Response(serializer.data)


    
# class FinalResultsCount(APIView):
#     def get(self,request):
#         try:
#             internal_hiring=CandidateApplicationModel.objects.filter(Final_Results="Internal_Hiring").count()
#             consider_to_client=CandidateApplicationModel.objects.filter(Final_Results="consider_to_client").count()
#             Reject=CandidateApplicationModel.objects.filter(Final_Results="Reject").count()
#             count_dict={"internal_hiring":internal_hiring,"consider_to_client":consider_to_client,"Reject":Reject}
            
#             return Response(count_dict, status=status.HTTP_200_OK)
#         except:
#             return Response("bad", status=status.HTTP_200_OK)
        

# class FinalResultsCount(APIView):
#     def get(self, request, duration=None,login_user=None ,FromDate=None, ToDate=None):
#         if duration == "today":
#             date = timezone.localdate()
#         elif duration == "week":
#             date = timezone.localdate() - timezone.timedelta(days=7)
#         elif duration == "month":
#             date = timezone.localdate() - timezone.timedelta(days=30)
#         elif duration == "year":
#             date = timezone.localdate() - timezone.timedelta(days=360)
#         else:
#             date=None
#         try:
#             final_status = HRFinalStatusModel.objects.filter(Final_Result="Internal_Hiring", CandidateId__Final_Results="Internal_Hiring")
#             if date:
#                 final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             Internal_Hiring_List = set()
#             for fs in final_status:
#                 if fs.CandidateId not in Internal_Hiring_List:
#                     Internal_Hiring_List.add(fs.CandidateId)
#             count_dict={"internal_hiring":len(Internal_Hiring_List)}
           
#             final_status = HRFinalStatusModel.objects.filter(Final_Result="consider_to_client", CandidateId__Final_Results="consider_to_client")
#             if date:
#                 final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             Internal_Hiring_List = set()
#             for fs in final_status:
#                 if fs.CandidateId not in Internal_Hiring_List:
#                     Internal_Hiring_List.add(fs.CandidateId)
        
#             Screening_review_obj = Review.objects.filter(Screening_Status="to_client")
#             if date:
#                 Screening_review_obj=Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             for scr_obj in Screening_review_obj:
#                 Internal_Hiring_List.add(scr_obj.CandidateId.CandidateId)
#             count_dict.update({"consider_to_client":len(Internal_Hiring_List)})

#             final_status = HRFinalStatusModel.objects.filter(Final_Result="On_Hold", CandidateId__Final_Results="On_Hold")
#             if date:
#                 final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             Internal_Hiring_List = set()
#             for fs in final_status:
#                 if fs.CandidateId not in Internal_Hiring_List:
#                     Internal_Hiring_List.add(fs.CandidateId)
#             count_dict.update({"On_Hold":len(Internal_Hiring_List)})
            

#             final_status = HRFinalStatusModel.objects.filter(Final_Result="Reject", CandidateId__Final_Results="Reject")
#             if date:
#                 final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             Internal_Hiring_List = set()
#             for fs in final_status:
#                 if fs.CandidateId not in Internal_Hiring_List:
#                     Internal_Hiring_List.add(fs.CandidateId)
            
        
#             final_status = HRFinalStatusModel.objects.filter(Final_Result="Reject", CandidateId__Final_Results="Reject")
#             final_status_by_can = HRFinalStatusModel.objects.filter(Final_Result="Rejected_by_Candidate", CandidateId__Final_Results="Rejected_by_Candidate")
#             if date:
#                 final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#                 final_status_by_can=final_status_by_can.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             Internal_Hiring_List = set()
#             for fs in final_status:
#                 if fs.CandidateId not in Internal_Hiring_List:
#                     Internal_Hiring_List.add(fs.CandidateId)

#             for fs in final_status_by_can:
#                 if fs.CandidateId not in Internal_Hiring_List:
#                     Internal_Hiring_List.add(fs.CandidateId)
                   
#             Screening_review_obj = Review.objects.filter(Screening_Status="rejected")
            
#             if date:
#                 Screening_review_obj=Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate()))
#             else:
#                 pass
#             for scr_obj in Screening_review_obj:
#                 Internal_Hiring_List.add(scr_obj.CandidateId.CandidateId)

#             count_dict.update({"Reject":len(Internal_Hiring_List)})

#             if date:
#                 offered_candidates = OfferLetterModel.objects.filter(Letter_sended_status=True,OfferedDate__range=(date, timezone.localdate())).count()
#             else:
#                 offered_candidates = OfferLetterModel.objects.filter(Letter_sended_status=True).count()
#             count_dict.update({"offered_candidates":offered_candidates})

            
#             Screening_review_obj = Review.objects.filter(Screening_Status="scheduled").count()
#             if date:
#                 Screening_review_obj = Review.objects.filter(Screening_Status="scheduled")
#                 Screening_review_obj=Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate())).count()
#             else:
#                 pass
#             count_dict.update({"scheduled":Screening_review_obj})
           

#             Screening_review_obj = Review.objects.filter(Screening_Status="walkout").count()
#             if date:
#                 Screening_review_obj = Review.objects.filter(Screening_Status="walkout")
#                 Screening_review_obj=Screening_review_obj.filter(ReviewedOn__date__range=(date, timezone.localdate())).count()
#             else:
#                 pass
#             count_dict.update({"walkout":Screening_review_obj})


#             candidates = CandidateApplicationModel.objects.filter(Filled_by="Candidate").order_by("-AppliedDate").count()
#             count_dict.update({"AppliedCandidates":candidates})

#             return Response(count_dict,status=status.HTTP_200_OK)
#         except Exception as e:
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)



#22-12-2025
from django.db.models import Q
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class FinalResultsCount(APIView):
    def get(self, request, duration=None):
        try:

            today = timezone.localdate()

            if duration == "today":
                start_date = today
            elif duration == "week":
                start_date = today - timezone.timedelta(days=7) 
            elif duration == "month":
                start_date = today - timezone.timedelta(days=30)
            elif duration == "year":
                start_date = today - timezone.timedelta(days=360)
            else:
                start_date = None

            date_filter = {}
            if start_date:
                date_filter = {
                    "ReviewedOn__date__range": (start_date, today)
                }

            internal_hiring = HRFinalStatusModel.objects.filter(
                Final_Result="Internal_Hiring",
                CandidateId__Final_Results="Internal_Hiring",
                **date_filter
            ).values("CandidateId").distinct().count()

            consider_hr_ids = set(
                HRFinalStatusModel.objects.filter(
                    Final_Result="consider_to_client",
                    CandidateId__Final_Results="consider_to_client",
                    **date_filter
                ).values_list("CandidateId_id", flat=True)
            )

            consider_review_ids = set(
                Review.objects.filter(
                    Screening_Status="to_client",
                    **date_filter
                ).values_list("CandidateId_id", flat=True)
            )

            consider_to_client = len(consider_hr_ids | consider_review_ids)

            on_hold = HRFinalStatusModel.objects.filter(
                Final_Result="On_Hold",
                CandidateId__Final_Results="On_Hold",
                **date_filter
            ).values("CandidateId").distinct().count()

            rejected_hr_ids = set(
                HRFinalStatusModel.objects.filter(
                    Final_Result__in=["Reject", "Rejected_by_Candidate"],
                    **date_filter
                ).values_list("CandidateId_id", flat=True)
            )

            rejected_review_ids = set(
                Review.objects.filter(
                    Screening_Status="rejected",
                    **date_filter
                ).values_list("CandidateId_id", flat=True)
            )

            rejected = len(rejected_hr_ids | rejected_review_ids)

            if start_date:
                offered = OfferLetterModel.objects.filter(
                    Letter_sended_status=True,
                    OfferedDate__range=(start_date, today)
                ).count()
            else:
                offered = OfferLetterModel.objects.filter(
                    Letter_sended_status=True
                ).count()

            scheduled = Review.objects.filter(
                Screening_Status="scheduled",
                **date_filter
            ).count()

            walkout = Review.objects.filter(
                Screening_Status="walkout",
                **date_filter
            ).count()

            applied_candidates = CandidateApplicationModel.objects.filter(
                Filled_by="Candidate"
            ).count()
            
            response_data = {
                "internal_hiring": internal_hiring,
                "consider_to_client": consider_to_client,
                "On_Hold": on_hold,
                "Reject": rejected,
                "offered_candidates": offered,
                "scheduled": scheduled,
                "walkout": walkout,
                "AppliedCandidates": applied_candidates
            }

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )








class Final_Candidate_Model_Filter(APIView):
    def post(self,request,Final_Results):
            if Final_Results=="Internal Hiring":
                search_value = request.data.get('search_value')  # Assuming the search value is passed in the query parameter 'search_value'
                q_objects = Q()
                for field in CandidateApplicationModel._meta.fields:
                    if field.name != 'id':
                        q_objects |= Q(**{f"{field.name}__icontains": search_value})
                print(q_objects)
                matched_objects = CandidateApplicationModel.objects.filter(q_objects,Final_Results="Internal Hiring")
                serializer = FinalResultCandidateSerializer(matched_objects, many=True)  # Assuming you have a serializer for YourModel
                return Response(serializer.data)
            elif Final_Results=="consider to client":
                search_value = request.data.get('search_value')  # Assuming the search value is passed in the query parameter 'search_value'
                q_objects = Q()
                for field in CandidateApplicationModel._meta.fields:
                    if field.name != 'id':
                        q_objects |= Q(**{f"{field.name}__icontains": search_value})
                print(q_objects)
                matched_objects = CandidateApplicationModel.objects.filter(q_objects,Final_Results="consider to client")
                serializer = FinalResultCandidateSerializer(matched_objects, many=True)  # Assuming you have a serializer for YourModel
                return Response(serializer.data)
            elif Final_Results=="Reject":
                search_value = request.data.get('search_value')  # Assuming the search value is passed in the query parameter 'search_value'
                q_objects = Q()
                for field in CandidateApplicationModel._meta.fields:
                    if field.name != 'id':
                        q_objects |= Q(**{f"{field.name}__icontains": search_value})
                print(q_objects)
                matched_objects = CandidateApplicationModel.objects.filter(q_objects,Final_Results="Reject")
                serializer = FinalResultCandidateSerializer(matched_objects, many=True)  # Assuming you have a serializer for YourModel
                return Response(serializer.data)


def InterviewScheduleSearch(interviewlist=None,screeninglist=None):
    assigned_candidates_data = []
    if interviewlist:
        for assigned_candidate in interviewlist:
            if assigned_candidate.interviewe:
                InterviewScheduleStatus=InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                assigned_candidate_data = InterviewSchedulSerializer(InterviewScheduleStatus).data

                ipk=assigned_candidate_data.get("interviewer")
                emp=EmployeeDataModel.objects.get(pk=ipk)
                cpk=assigned_candidate_data.get("Candidate")
                can=CandidateApplicationModel.objects.get(pk=cpk)

                assigned_candidate_data["interviewer"]=emp.EmployeeId
                assigned_candidate_data["Candidate"]=can.CandidateId
                assigned_candidate_data["Name"]=can.FirstName
                assigned_candidate_data["Assigned_Status"]=assigned_candidate.Interview_Schedule_Status
                assigned_candidates_data.append(assigned_candidate_data)

                if assigned_candidate.review:
                    review_candidates=Review.objects.get(id=assigned_candidate.review.pk)
                    rev_data=IRS(review_candidates).data
                    assigned_candidate_data.update({"Review":rev_data})
                else:
                    assigned_candidate_data.update({"Review":{}})

        return assigned_candidates_data
    elif screeninglist:
        for assigned_candidate in screeninglist:
            if assigned_candidate.screening:
                interviewe_data = ScreeningAssigningSerializer(assigned_candidate.screening).data
                Recruiter = EmployeeDataModel.objects.filter(pk=interviewe_data["Recruiter"]).first()
                candidate = CandidateApplicationModel.objects.filter(pk=interviewe_data["Candidate"]).first()
                assigned_by = EmployeeDataModel.objects.filter(pk=interviewe_data["AssignedBy"]).first()
                if Recruiter or candidate:
                    assigned_candidate_data = {
                        "id": assigned_candidate.screening.id,
                        "Candidate": candidate.CandidateId,
                        "Name": candidate.FirstName,
                        "Recruiter": Recruiter.EmployeeId,
                        "AssignedBy": assigned_by.EmployeeId,
                        "Date_of_assigned": interviewe_data["Date_of_assigned"],
                        # "Time_of_assigned": assigned_candidate.Date_of_assigned.time().replace(second=0, microsecond=0),
                    }
                    if assigned_candidate.review:
                        review_candidates = Review.objects.get(id=assigned_candidate.review.pk)
                        rev_data = IRS(review_candidates).data
                        assigned_candidate_data["Review"] = rev_data
                    else:
                        assigned_candidate_data["Review"] = {}
                    assigned_candidates_data.append(assigned_candidate_data)
        return assigned_candidates_data
    else:
        return assigned_candidates_data

   
class InterviewScheduleSearchView(APIView):
    def get(self, request, search_value=None,duration=None,Status=None,employee=None):
        if Status=="Completed" and employee:
            try:
                if duration == "Today":
                    Today = timezone.localdate()
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Q(interviewe__ScheduledBy__EmployeeId=employee) | Q(interviewe__interviewer__EmployeeId=employee),interviewe__ScheduledOn__date=Today ,Interview_Schedule_Status="Completed")
                elif duration=="Week":
                    date = timezone.localdate() - timezone.timedelta(days=7)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Q(interviewe__ScheduledBy__EmployeeId=employee) | Q(interviewe__interviewer__EmployeeId=employee),interviewe__ScheduledOn__date__range=(date,timezone.localdate()),Interview_Schedule_Status="Completed")
                elif duration == "Month":
                    date = timezone.localdate() - timezone.timedelta(days=30)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Q(interviewe__ScheduledBy__EmployeeId=employee) | Q(interviewe__interviewer__EmployeeId=employee),interviewe__ScheduledOn__date__range=(date,timezone.localdate()),Interview_Schedule_Status="Completed")
                elif duration == "Year":
                    date = timezone.localdate() - timezone.timedelta(days=360)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Q(interviewe__ScheduledBy__EmployeeId=employee) | Q(interviewe__interviewer__EmployeeId=employee),interviewe__ScheduledOn__date__range=(date,timezone.localdate()),Interview_Schedule_Status="Completed")
                else:
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Q(interviewe__ScheduledBy__EmployeeId=employee) | Q(interviewe__interviewer__EmployeeId=employee),Interview_Schedule_Status="Completed")

                data=InterviewScheduleSearch(interviewlist=Candidate_list)
                return Response(data, status=status.HTTP_200_OK)
            except Review.DoesNotExist:
                return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
            
        elif Status=="Assigned" and employee:
            try:
                if duration == "Today":
                    Today = timezone.localdate()
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledOn__date=Today,Interview_Schedule_Status="Assigned")    
                elif duration=="Week":
                    date = timezone.localdate() - timezone.timedelta(days=7)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledOn__date__range=(date,timezone.localdate()),Interview_Schedule_Status="Assigned")
                elif duration == "Month":
                    date = timezone.localdate() - timezone.timedelta(days=30)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledOn__date__range=(date,timezone.localdate()),Interview_Schedule_Status="Assigned")
                elif duration == "Year":
                    date = timezone.localdate() - timezone.timedelta(days=360)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledOn__date__range=(date,timezone.localdate()),Interview_Schedule_Status="Assigned")
                else:
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Assigned")
                
                data=InterviewScheduleSearch(interviewlist=Candidate_list)
                return Response(data, status=status.HTTP_200_OK)
            
            except Review.DoesNotExist:
                return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
        else:
            try :
                assigned_candidates = InterviewScheduleStatusModel.objects.filter(
                    Q(interviewe__id__icontains=search_value) |
                    Q(interviewe__Candidate__FirstName__icontains=search_value) |
                    Q(interviewe__Candidate__CandidateId__icontains=search_value) |
                    Q(interviewe__InterviewRoundName__icontains=search_value) |
                    Q(interviewe__interviewer__EmployeeId__icontains=search_value) |
                    Q(interviewe__InterviewDate__icontains=search_value) |
                    Q(interviewe__InterviewType__icontains=search_value) |
                    Q(interviewe__ScheduledBy__EmployeeId__icontains=search_value) |
                    Q(interviewe__ScheduledOn__icontains=search_value) |
                    Q(Interview_Schedule_Status__icontains=search_value) |
                    Q(review__interview_Status__icontains=search_value) |
                    Q(review__ReviewedBy__icontains=search_value) |
                    Q(review__ReviewedOn__icontains=search_value) |
                    Q(review__id__icontains=search_value) )
                
                emp_obj=EmployeeDataModel.objects.filter(EmployeeId=employee).first()
                if emp_obj and emp_obj.Designation in ["HR","Admin"]:
                    search_emps=assigned_candidates.filter(Q(interviewe__ScheduledBy__EmployeeId=employee) | Q(interviewe__interviewer__EmployeeId=employee))
                else:
                    search_emps=assigned_candidates

                data=InterviewScheduleSearch(interviewlist=search_emps)
                print(data)
                return Response(data, status=status.HTTP_200_OK)
            
            except Exception as e:
                print(e)
                return Response("error", status=status.HTTP_400_BAD_REQUEST)
                
class ScreeningScheduleSearchView(APIView):                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             
    def get(self, request, search_value=None,Status=None,duration=None,src_status=None):
        # if duration and Status=="Completed":
        if duration and src_status:
            try:
                if duration == "Today":
                    Today = timezone.localdate()
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(review__ReviewedDate=Today ,Interview_Schedule_Status=src_status)    
                elif duration=="Week":
                    date = timezone.localdate() - timezone.timedelta(days=7)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(review__ReviewedDate__range=(date,timezone.localdate()),Interview_Schedule_Status=src_status)
                elif duration == "Month":
                    date = timezone.localdate() - timezone.timedelta(days=30)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(review__ReviewedDate__range=(date,timezone.localdate()),Interview_Schedule_Status=src_status)
                elif duration == "Year":
                    date = timezone.localdate() - timezone.timedelta(days=360)
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(review__ReviewedDate__range=(date,timezone.localdate()),Interview_Schedule_Status=src_status)
                else:
                    Candidate_list = InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status=src_status)

                data=InterviewScheduleSearch(screeninglist=Candidate_list)
                return Response(data, status=status.HTTP_200_OK)
            except Review.DoesNotExist:
                return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
         
        else:
            try:
                print(search_value)
                assigned_candidates = InterviewScheduleStatusModel.objects.filter(
                                        Q(screening__id__icontains=search_value) |
                                        Q(screening__Candidate__FirstName__icontains=search_value) |
                                        Q(screening__Candidate__CandidateId__icontains=search_value) |
                                        Q(screening__Recruiter__EmployeeId__icontains=search_value) |
                                        Q(screening__AssignedBy__EmployeeId__icontains=search_value) ) 
                
                assigned_candidates=assigned_candidates.filter(InterviewScheduledCandidate__Telephonic_Round_Status=src_status,screening__Candidate__Filled_by="Candidate")
                data=InterviewScheduleSearch(screeninglist=assigned_candidates)
                return Response(data, status=status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response("error", status=status.HTTP_400_BAD_REQUEST)
            
            
        
class FinalCandidateSearchView(APIView):
    def get(self, request,search_value):
        try:
            obj_instance = InterviewScheduleStatusModel.objects.filter(Q(Interview_Schedule_Status="Completed") & Q(InterviewScheduledCandidate__CandidateId__icontains=search_value)
                                                                        | Q(InterviewScheduledCandidate__FirstName__icontains=search_value)
                                                                        | Q(InterviewScheduledCandidate__PrimaryContact__icontains=search_value)
                                                                        | Q(InterviewScheduledCandidate__AppliedDesignation__icontains=search_value)
                                                                        | Q(InterviewScheduledCandidate__Email__icontains=search_value)
                                                                    )
            interview_status_can = []
            for review_obj in obj_instance:
                if review_obj.interviewe:
                    print(review_obj.interviewe)
                    candidate_id = review_obj.InterviewScheduledCandidate.CandidateId
                    can_obj = CandidateApplicationModel.objects.get(CandidateId=candidate_id)
                    serializer = CandidateApplicationSerializer(can_obj)
                    serializer=serializer.data
                    serializer["FinalResult"]=can_obj.Final_Results
                    interview_status_can.append(serializer)
            return Response(interview_status_can, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


# wrok from home..........................................
class Candidates_Applied_Filter(APIView):
    def get(self, request,FromDate=None,ToDate=None,duration="Today"):
        try:
            if duration == "Today":
                Today = timezone.localdate()
                Candidate_list = CandidateApplicationModel.objects.filter(DataOfApplied=Today)
            elif duration=="Week":
                date = timezone.localdate() - timezone.timedelta(days=7)
                Candidate_list = CandidateApplicationModel.objects.filter(DataOfApplied__range=(date,timezone.localdate()))
            elif duration == "Month":
                date = timezone.localdate() - timezone.timedelta(days=30)
                Candidate_list = CandidateApplicationModel.objects.filter(DataOfApplied__range=(date,timezone.localdate()))
            elif duration == "Year":
                date = timezone.localdate() - timezone.timedelta(days=360)
                Candidate_list = CandidateApplicationModel.objects.filter(DataOfApplied__range=(date,timezone.localdate()))
                print(type(FromDate),ToDate)
                FromDate=json.loads(FromDate)
                ToDate=json.loads(ToDate)
                print(FromDate,ToDate)
                Candidate_list = CandidateApplicationModel.objects.filter(DataOfApplied__range=(FromDate,ToDate))
                
            serializer = CandidateApplicationSerializer(Candidate_list, many=True)

            return Response(serializer.data, status=status.HTTP_200_OK)
        except Review.DoesNotExist:
            return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
        
class FilterBasedFromToView(APIView):
    def get(self, request, FromDate=None, ToDate=None):
        from_date = datetime.strptime(FromDate, "%Y-%m-%d")
        to_date = datetime.strptime(ToDate, "%Y-%m-%d")
        candidate_list = CandidateApplicationModel.objects.filter(DataOfApplied__range=(from_date, to_date))
        serializer = CandidateApplicationSerializer(candidate_list, many=True)
        return Response(serializer.data)
    
class CalledCandidatesSearch(APIView):
    def get(self,request,search_value=None,filter_value=None,duration=None):
        if duration:
            try:
                if duration == "Today":
                    Today = timezone.localdate()
                    Candidate_list = CalledCandidatesModel.objects.filter(called_date__date=Today)
                elif duration=="Week":
                    date = timezone.localdate() - timezone.timedelta(days=7)
                    Candidate_list = CalledCandidatesModel.objects.filter(called_date__date__range=(date,timezone.localdate()))
                elif duration == "Month":
                    date = timezone.localdate() - timezone.timedelta(days=30)
                    Candidate_list = CalledCandidatesModel.objects.filter(called_date__date__range=(date,timezone.localdate()))
                elif duration == "Year":
                    date = timezone.localdate() - timezone.timedelta(days=360)
                    Candidate_list = CalledCandidatesModel.objects.filter(called_date__date__range=(date,timezone.localdate()))
                    print(type(FromDate),ToDate)
                    FromDate=json.loads(FromDate)
                    ToDate=json.loads(ToDate)
                    print(FromDate,ToDate)
                    Candidate_list = CalledCandidatesModel.objects.filter(called_date__date__range=(FromDate,ToDate))
                    
                serializer = CalledCandidatesSerializer(Candidate_list, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except CalledCandidatesModel.DoesNotExist:
                return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
        elif filter_value:
            try:
                Candidate_list = CalledCandidatesModel.objects.filter(interview_scheduled_date=filter_value)
                serializer = CalledCandidatesSerializer(Candidate_list, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            except CalledCandidatesModel.DoesNotExist:
                return Response("Candidate Review Not Found", status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                called_can_search=CalledCandidatesModel.objects.filter(Q(name__icontains=search_value)
                                                                    | Q(phone__icontains=search_value)
                                                                    | Q(location__icontains=search_value)
                                                                    | Q(designation__icontains=search_value)
                                                                    | Q(current_status__icontains=search_value) 
                                                                    | Q(called_by__EmployeeId__icontains=search_value)
                                                                    )
                serializer=CalledCandidatesSerializer(called_can_search,many=True)
                return Response(serializer.data,status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e),status=status.HTTP_404_NOT_FOUND)


class FinalResultsCountFunction(APIView):
    def get(self, request, dis_value=None,duration=None,login_user=None,FinalStatus=None,FromDate=None, ToDate=None):
        if duration == "today":
            date = timezone.localdate()
        elif duration == "week":
            date = timezone.localdate() - timezone.timedelta(days=7)
        elif duration == "month":
            date = timezone.localdate() - timezone.timedelta(days=30)
        elif duration == "year":
            date = timezone.localdate() - timezone.timedelta(days=360)
        else:
            date=None
        if dis_value:
            try:
                final_status = Review.objects.filter(interview_Status="Internal_Hiring",ReviewedBy=login_user)
                if date:
                    final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                else:
                    pass
                Internal_Hiring_List = set()
                for fs in final_status:
                    if fs.CandidateId not in Internal_Hiring_List:
                        Internal_Hiring_List.add(fs.CandidateId)
                count_dict={"internal_hiring":len(Internal_Hiring_List)}
            
                final_status = Review.objects.filter(Q(interview_Status="consider_to_client") | Q(Screening_Status="to_client"),ReviewedBy=login_user)
                if date:
                    final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                else:
                    pass
                Internal_Hiring_List = set()
                for fs in final_status:
                    if fs.CandidateId not in Internal_Hiring_List:
                        Internal_Hiring_List.add(fs.CandidateId)
                count_dict.update({"consider_to_client":len(Internal_Hiring_List)})
                
                final_status = Review.objects.filter(Q(interview_Status="Reject") | Q(Screening_Status="rejected"),ReviewedBy=login_user)
                if date:
                    final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                else:
                    pass
                Internal_Hiring_List = set()
                for fs in final_status:
                    if fs.CandidateId not in Internal_Hiring_List:
                        Internal_Hiring_List.add(fs.CandidateId)
                count_dict.update({"Reject":len(Internal_Hiring_List)})

                final_status = Review.objects.filter(Screening_Status="scheduled",ReviewedBy=login_user)
                if date:
                    final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                else:
                    pass

                count_dict.update({"scheduled":len(final_status)})
                return Response(count_dict,status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e))
        else:
            try:
                candidates_list=[]
                if FinalStatus=="Internal_Hiring":
                    final_status = Review.objects.filter(interview_Status="Internal_Hiring",ReviewedBy=login_user)
                    if date:
                        final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                    else:
                        pass
                    Internal_Hiring_List = set()
                    for fs in final_status:
                        if fs.CandidateId not in Internal_Hiring_List:
                            HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
                            serializer = FinalResultCandidateSerializer(HiriedCan)
                            candidates_list.append(serializer.data)
                            Internal_Hiring_List.add(fs.CandidateId)
                    count_dict={"internal_hiring":candidates_list}

                elif FinalStatus=="consider_to_client":
                    final_status = Review.objects.filter(Q(interview_Status="consider_to_client") | Q(Screening_Status="to_client"),ReviewedBy=login_user)
                    if date:
                        final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                    else:
                        pass
                    Internal_Hiring_List = set()
                    for fs in final_status:
                        if fs.CandidateId not in Internal_Hiring_List:
                            HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
                            serializer = FinalResultCandidateSerializer(HiriedCan)
                            candidates_list.append(serializer.data)
                            Internal_Hiring_List.add(fs.CandidateId)
                    count_dict={"consider_to_client":candidates_list}

                elif FinalStatus=="Reject":
                    final_status = Review.objects.filter(Q(interview_Status="Reject") | Q(Screening_Status="rejected"),ReviewedBy=login_user)
                    if date:
                        final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                    else:
                        pass
                    Internal_Hiring_List = set()
                    for fs in final_status:
                        if fs.CandidateId not in Internal_Hiring_List:
                            HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
                            serializer = FinalResultCandidateSerializer(HiriedCan)
                            candidates_list.append(serializer.data)
                            Internal_Hiring_List.add(fs.CandidateId)
                    count_dict={"Reject":candidates_list}

                elif FinalStatus=="Scheduled":
                    final_status = Review.objects.filter(Screening_Status="scheduled",ReviewedBy=login_user)
                    if date:
                        final_status=final_status.filter(ReviewedOn__date__range=(date, timezone.localdate()))
                    else:
                        pass
                    Internal_Hiring_List = set()
                    for fs in final_status:
                        if fs.CandidateId not in Internal_Hiring_List:
                            HiriedCan = CandidateApplicationModel.objects.get(CandidateId=fs.CandidateId)
                            serializer = FinalResultCandidateSerializer(HiriedCan)
                            candidates_list.append(serializer.data)
                            Internal_Hiring_List.add(fs.CandidateId)
                    count_dict={"scheduled":candidates_list}
                return Response(count_dict,status=status.HTTP_200_OK)
            except Exception as e:
                return Response(str(e))