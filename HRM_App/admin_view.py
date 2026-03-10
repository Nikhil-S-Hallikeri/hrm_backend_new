from .imports import *

# Applied candidate display ,edit,delete,add

class AppliedCandidatesManuplation(APIView):
    def patch(self,request,instance): 
        try:
            can_obj=CandidateApplicationModel.objects.get(CandidateId=instance)
            can_serializer=FilterCandidateApplicationSerializer(can_obj,data=request.data,partial=True)
            if can_serializer.is_valid():
                can_serializer.save()
                return Response(can_serializer.data,status=status.HTTP_200_OK)
            else:
                return Response(can_serializer.errors,status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
    def delete(self, request, instance):
        try:
            # Retrieve the instance you want to delete
            can_obj = CandidateApplicationModel.objects.filter(CandidateId=instance).first()
            if not can_obj:
                return Response("Candidate not found", status=status.HTTP_404_NOT_FOUND)
            # Delete the instance
            can_obj.delete()
            return Response("Candidate deleted successfully", status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

# ........................Dashboard design......................

from django.db.models import Count

class DepartmentRatioAPIView(APIView):
    def get(self, request):
        total_employees = EmployeeDataModel.objects.count()

        if total_employees == 0:
            return Response({}, status=status.HTTP_200_OK)

        department_counts = EmployeeDataModel.objects.values('Position__Department__Dep_Name').annotate(count=Count('id'))
        
        department_ratios = {}
        for dept in department_counts:
            
            department_ratios[dept['Position__Department__Dep_Name']] = round((dept['count'] / total_employees)*100,0)
            # department_ratios[f"{dept['Position__Department__Dep_Name']}_count"] = dept['count']

        print(department_ratios)
        return Response(department_ratios, status=status.HTTP_200_OK)
    
    
class GenderDiversityAPIView(APIView):
    def get(self, request):
        total_candidates = CandidateApplicationModel.objects.count()

        if total_candidates == 0:
            return Response({
                "male_percentage": 0,
                "female_percentage": 0,
                "others_percentage": 0
            }, status=status.HTTP_200_OK)

        gender_counts = CandidateApplicationModel.objects.values('Gender').annotate(count=Count('id'))

        gender_ratios = {
            "male_percentage": 0,
            "female_percentage": 0,
            "others_percentage": 0
        }
        for gender in gender_counts:
            if gender['Gender'] == 'male':
                gender_ratios['male_percentage'] = round((gender['count'] / total_candidates) * 100,0)
            elif gender['Gender'] == 'female':
                gender_ratios['female_percentage'] = round((gender['count'] / total_candidates) * 100,0)
            elif gender['Gender'] == 'others':
                gender_ratios['others_percentage'] =round((gender['count'] / total_candidates) * 100,0)

        return Response(gender_ratios, status=status.HTTP_200_OK)
    
from django.db.models import Q
class EmployeeDiversityView(APIView):
    """
    API view to return diversity percentages by gender category:
    - Male
    - Female
    - Transgender
    - Other (all other gender choices)
    """

    def get(self, request):
        # Calculate the total count of employees
        total_count = EmployeeInformation.objects.filter(employee_status="active").count()
        if total_count == 0:
            return Response({"Male": 0, "Female": 0, "Transgender": 0, "Other": 0})

        # Calculate counts for each gender category
        male_count = EmployeeInformation.objects.filter(employee_status="active",gender="male").count()
        female_count = EmployeeInformation.objects.filter(employee_status="active",gender="female").count()
        transgender_count = EmployeeInformation.objects.filter(employee_status="active",gender="transgender").count()

        print(male_count)
        print(female_count)
        
        # Count for 'Other' category (all genders except male, female, and transgender)
        other_count = EmployeeInformation.objects.filter(employee_status="active").exclude(
            Q(gender="male") | Q(gender="female") | Q(gender="transgender")
        ).count()

        # Calculate percentages
        diversity_data = {
            "Male": round((male_count / total_count) * 100, 0),
            "Male_count": male_count ,
            "Female": round((female_count / total_count) * 100, 0),
            "Female_count": female_count,
            "Transgender": round((transgender_count / total_count) * 100, 0),
            "Transgender_count": transgender_count,
            "Other": round((other_count / total_count) * 100, 0),
            "Other_count": other_count
        }

        return Response(diversity_data)
    
from django.utils import timezone   
class JobPortalSourceCountAPIView(APIView):
    def get(self, request):
        # Define job portal choices mapping
        job_portal_choices = dict(CandidateApplicationModel.jps_choice)

        # Initialize response data with all job portals set to count 0
        response_data = {name: 0 for key, name in job_portal_choices.items()}

        # Get the date parameter from the request
        date_str = request.query_params.get('date')
        
        if date_str:
            try:
                query_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                # Filter candidates by the provided date
                candidates = CandidateApplicationModel.objects.filter(DataOfApplied=query_date)
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # No date filter; retrieve all candidates
            candidates = CandidateApplicationModel.objects.all()
        # Count the number of candidates for each job portal source
        source_counts = candidates.values('JobPortalSource').annotate(count=Count('id'))

        # Update response data with actual counts
        for source in source_counts:
            source_name = job_portal_choices.get(source['JobPortalSource'])
            if source_name:
                response_data[source_name] = source['count']

        # Convert response_data to list of dictionaries
        response_list = [{'JobPortalSource': key, 'count': value} for key, value in response_data.items()]
        # response_list = [{key:value} for key, value in response_data.items()]

        return Response(response_list, status=status.HTTP_200_OK)
    
class JobPortalSourceFilter(APIView):
    def get(self, request):
        # Get the source name from query params
        source_name = request.GET.get("source_name")

        # Validate if source_name is provided
        if not source_name:
            return Response("source name is required", status=status.HTTP_400_BAD_REQUEST)
        
        # Initialize query filter with JobPortalSource
        filter_conditions = {'JobPortalSource': source_name}

        # Get the date from query params
        date_str = request.query_params.get('date')
        if date_str:
            try:
                # Parse the date
                query_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                # Add date filter if provided
                filter_conditions['DataOfApplied'] = query_date
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Query based on the filter conditions
        applied_obj = CandidateApplicationModel.objects.filter(**filter_conditions)

        # Check if any candidates exist with the given filter
        if not applied_obj.exists():
            return Response("No candidates found for the given source and/or date.", status=status.HTTP_400_BAD_REQUEST)

        # Serialize the results
        applied_serializer = CandidateApplicationSerializer(applied_obj, many=True)

        return Response(applied_serializer.data, status=status.HTTP_200_OK)


# ///////////////////////////////////////////// JOB Posting ////////////////////////////////////////////////////////

import requests

class Job_Post(APIView):
    def get(self,request):
        url = f'{settings.MERIDAHR_URL}api/job_description'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            can_obj=CandidateApplicationModel.objects.filter(JPS_Id__isnull=False)

            for job_post in data:
                candidates=can_obj.filter(JPS_Id=job_post["id"])
                job_post["applied_count"]=candidates.count()
                job_post["candidate_list"]=CandidateApplicationSerializer(candidates,many=True).data
            return Response(data)
        return Response("okkkkkkk")

