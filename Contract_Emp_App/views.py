# Django query  optimization
"""
1.Use select_related and prefetch_related
select_related() is used for foreign key relationships and performs a SQL join, retrieving related objects in a single query.
prefetch_related() is used for many-to-many and reverse foreign key relationships. It performs multiple queries but optimizes how data is loaded, reducing the number of queries.

# Example using select_related for foreign key relationships
books = Book.objects.select_related('author').all()

# Example using prefetch_related for many-to-many relationships
books = Book.objects.prefetch_related('genres').all()

2.Use values and values_list Instead of Fetching Entire Objects
If you only need specific fields from a model, use values() or values_list(). These methods fetch only the fields you need, reducing the data transferred from the database.

# Fetch only the 'name' field
book_names = Book.objects.values_list('name', flat=True)

3. Avoid the N+1 Query Problem
The N+1 problem occurs when a query is made for a list of objects, and then separate queries are made for related objects. Using select_related or prefetch_related solves this issue.

# Avoid N+1 by prefetching related objects
authors = Author.objects.prefetch_related('books').all()

4. Use only() and defer() for Large Data Sets
only() is used to retrieve only specific fields, avoiding loading unnecessary fields.
defer() is the opposite—it retrieves all fields except the ones you specify.

# Retrieve only 'name' field from books
books = Book.objects.only('name')

# Retrieve all fields except 'description'
books = Book.objects.defer('description')

Use annotate() and aggregate() Wisely
If you need aggregates (e.g., count, sum, average), use annotate() and aggregate() to perform calculations at the database level rather than in Python.

# Count the number of books per author
author_books = Author.objects.annotate(book_count=Count('books'))

# Get the total number of books
total_books = Book.objects.aggregate(total=Count('id'))

Avoid Unnecessary Queries in Loops
Performing database queries inside a loop can be expensive. Fetch all the data at once outside of the loop to avoid multiple round-trips to the database.

# Inefficient (inside loop)
for author in authors:
    print(author.books.count())  # This hits the DB on each iteration

# Efficient (outside loop)
authors = Author.objects.prefetch_related('books')
for author in authors:
    print(author.books.count())  # Uses cached data

Use bulk_create and bulk_update for Batch Operations
When inserting or updating multiple records, avoid doing it one at a time. Use bulk_create and bulk_update to handle large data sets in a single query.

# Inserting multiple objects in bulk
Book.objects.bulk_create([
    Book(name="Book 1"),
    Book(name="Book 2"),
])

# Updating multiple objects in bulk
books = Book.objects.filter(author="Some Author")
for book in books:
    book.name = "Updated Name"
Book.objects.bulk_update(books, ['name'])

Reduce Query Set Size with iterator()
If you're working with large querysets, use iterator() to load records in batches instead of loading the entire result set into memory.

# Efficient iteration over large querysets
for book in Book.objects.all().iterator():
    print(book.name)

    Use Indexes on Frequently Queried Fields
Ensure that frequently queried fields have database indexes. Django allows you to specify indexes on models.

class Book(models.Model):
    name = models.CharField(max_length=200, db_index=True)  # Add index here
"""

from django.shortcuts import render
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import *
from .serializer import *
from HRM_App.models import *
from HRM_App.serializers import *
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db.models import Count,Sum

class OurClientsView(APIView):
    def get(self, request):
        try:
            client_id = request.GET.get("id")
            # Handling specific client request by ID
            if client_id:
                client_obj = OurClients.objects.filter(pk=client_id).first()
                if not client_obj:
                    return Response({"error": "Client does not exist"}, status=status.HTTP_400_BAD_REQUEST)
                serializer = OurClientSerializer(client_obj, context={"request": request})
                return Response(serializer.data, status=status.HTTP_200_OK)
            
            # Handling request for all clients
            clients = OurClients.objects.all()
            if not clients.exists():
                return Response({"error": "No clients found"}, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = OurClientSerializer(clients, context={"request": request}, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request): 
        print(request.data)
        try:
            services=request.data.get("service_list")
            if services and not isinstance(services, list):
                return Response("services required in the list form", status=status.HTTP_400_BAD_REQUEST)

            serializer=OurClientSerializer(data=request.data)

            if serializer.is_valid():
                instance=serializer.save()

                # for service in services:
                #     try:
                #         ClientServicesModel.objects.create(client=instance,service_name=service)
                #     except Exception as e:
                #         print(e)

                if request.data.get("document_proof"):
                    document_proof = request.data.get("document_proof")
                    # Check if document_proof is a list, if not, convert it to a list
                    if not isinstance(document_proof, list):
                        document_proof = [document_proof]
                    
                    for doc in document_proof:
                        request_data = {}
                        request_data["document_proof"] = doc
                        request_data["client"] = instance.pk
                        doc_serializer = ClientDocumentsSerializer(data=request_data)

                        if doc_serializer.is_valid():
                            doc_serializer.save()
                        else:
                            instance.delete()  # Rollback the instance creation if document saving fails
                            return Response("Document not saved", status=status.HTTP_400_BAD_REQUEST)
                                    
                return Response("client added successfully!",status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
   
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def patch(self,request):
        
        try:
            client_id=request.GET.get("id")
            if not client_id:
                return Response("client id required",status=status.HTTP_400_BAD_REQUEST)
            client_obj=OurClients.objects.filter(pk=client_id).first()
            if not client_obj:
                return Response("client not exist",status=status.HTTP_400_BAD_REQUEST)
            serializer=OurClientSerializer(client_obj,data=request.data,partial=True)
            if serializer.is_valid():
                instance=serializer.save()
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ClientsDocumentsAPIView(APIView):
    # POST - Create a new document
    def post(self, request):
        serializer = ClientDocumentsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # PATCH - Update an existing document
    def patch(self, request, pk):
        document = get_object_or_404(ClientsDocumentsModel, pk=pk)
        serializer = ClientDocumentsSerializer(document, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # DELETE - Delete a document
    def delete(self, request, pk):
        document = get_object_or_404(ClientsDocumentsModel, pk=pk)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RequirementsView(APIView):
    def get(self,request):
        try:
            c_id=request.GET.get("client_id")
            r_id=request.GET.get("requirement_id")
            employee_id=request.GET.get("emp_id")

            if c_id:
                client_req_obj=Requirement.objects.filter(client__pk = c_id)
                print("client_req_obj",client_req_obj)
                if not client_req_obj:
                    return Response("client not exist",status=status.HTTP_400_BAD_REQUEST)
                serializer=Requirementserializer(client_req_obj,context={"request":request},many=True)
                return Response(serializer.data,status=status.HTTP_200_OK)
        
            elif r_id:

                req_obj=Requirement.objects.filter(pk = r_id).first()
                if not req_obj:
                    return Response("requirement not exist",status=status.HTTP_400_BAD_REQUEST)
                serializer=Requirementserializer(req_obj,context={"request":request})
                return Response(serializer.data,status=status.HTTP_200_OK)
            
            else:
                if employee_id:
                    requirement_list=[]
                    emp_obj=EmployeeDataModel.objects.filter(EmployeeId=employee_id).first()
                    if emp_obj and emp_obj.Designation in ["Admin","HR"]:
                        req_objs=Requirement.objects.all()
                        serializer=Requirementserializer(req_objs,context={"request":request},many=True)
                        return Response(serializer.data,status=status.HTTP_200_OK)
                    else:
                        req_assign_objs = RequirementAssign.objects.filter(
                            assigned_to_recruiter__EmployeeId=employee_id
                        )

                    # Use a set to track already processed requirement IDs
                    seen_requirements = set()
                    for req_assign in req_assign_objs:
                        requirement_id = req_assign.requirement.id  # Adjust to match the correct field
                        if requirement_id not in seen_requirements:
                            seen_requirements.add(requirement_id)
                            serializer = Requirementserializer(req_assign.requirement, context={"request": request})
                            requirement_list.append(serializer.data)
                    return Response(requirement_list,status=status.HTTP_200_OK)
            return Response("helloooo")  
        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self,request):
        try:
            # print(request.data)
            # request_data=request.data.copy()
            # client_id=request_data.get("client_id")
            # if client_id:
            #     client_obj=OurClients.objects.filter(client_id=client_id).first()

            serializer=Requirementserializer(data=request.data)
            if serializer.is_valid():
                instance=serializer.save()
                return Response(serializer.data,status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch(self,request):
        try:
            print(request.data)
            req_id=request.GET.get("id")
            if not req_id:
                return Response("requirements id required",status=status.HTTP_400_BAD_REQUEST)
            
            req_obj=Requirement.objects.filter(pk=req_id).first()
            if not req_obj:
                return Response("requirements id not exist",status=status.HTTP_400_BAD_REQUEST)
        
            #18/03/2026
            serializer=Requirementserializer(req_obj,data=request.data,partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response("updated successfully",status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            
class ClientRequirementAssignView(APIView):
    def get(self,request):
        assigner=request.GET.get("assigner")
        recruiter=request.GET.get("recruiter")
        requirement=request.GET.get("requirement_id")

        employee_id=request.GET.get("emp_id")

        if assigner:
            req_objs=RequirementAssign.objects.select_related("assigned_by_employee").filter(assigned_by_employee__EmployeeId=assigner)
            if not req_objs.exists():
                return Response("Requirements not found",status=status.HTTP_400_BAD_REQUEST)
            serializer=ClientRequirementAssignSerializer(req_objs,many=True,context={"request":request})
            return Response(serializer.data,status=status.HTTP_200_OK)
        elif recruiter:
            req_objs=RequirementAssign.objects.select_related("assigned_to_recruiter").filter(assigned_to_recruiter__EmployeeId=recruiter)
            if not req_objs.exists():
                return Response("Requirements not found",status=status.HTTP_400_BAD_REQUEST)
            serializer=ClientRequirementAssignSerializer(req_objs,many=True,context={"request":request})
            return Response(serializer.data,status=status.HTTP_200_OK)
        elif requirement:
            req_objs = RequirementAssign.objects.filter(requirement__pk=requirement)
            if not req_objs.exists():
                return Response([], status=status.HTTP_200_OK)
            
            serializer = ClientRequirementAssignSerializer(req_objs, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
            
            # serializer=ClientRequirementAssignSerializer(req_objs,many=True,context={"request":request})
            # return Response(serializer.data,status=status.HTTP_200_OK)
            
            # serializer=ClientRequirementAssignSerializer(req_objs,many=True,context={"request":request})
            # return Response(serializer.data,status=status.HTTP_200_OK)
        else:
            if employee_id:
                emp_obj=EmployeeDataModel.objects.filter(EmployeeId=employee_id).first()
                if emp_obj and emp_obj.Designation in ["Admin","HR"]:
                    requirement_assigned_list=[]
                    req_objs=RequirementAssign.objects.all()
                    if not req_objs.exists():
                        return Response([],status=status.HTTP_200_OK)
                    serializer=ClientRequirementAssignSerializer(req_objs,many=True,context={"request":request}).data
                    return Response(serializer,status=status.HTTP_200_OK)
            return Response("assigner or recruiter required",status=status.HTTP_400_BAD_REQUEST)

    def post(self,request):
        try:
            request_data=request.data.copy()
            req_id=request.data.get("requirement")
            position=request.data.get("position_count")
            assigner=request.data.get("assigned_by_employee")

            if assigner:
                emp_obj=EmployeeDataModel.objects.filter(EmployeeId=assigner).first()
                request_data["assigned_by_employee"]=emp_obj.pk if emp_obj else None

            req_obj=Requirement.objects.filter(pk=req_id).first()
            closed_positions=RequirementAssign.objects.filter(requirement=req_id)

            if closed_positions:
                closed_positions=closed_positions.aggregate(total_position=Sum('position_count'))
                balence_position=req_obj.open_positions - closed_positions["total_position"]
        
                if int(position) > balence_position:
                    return Response(f"client requirement positions {req_obj.open_positions}. closed positions {closed_positions['total_position']}. balance positions {balence_position}.",status=status.HTTP_406_NOT_ACCEPTABLE)
        
            serializer=ClientRequirementAssignSerializer(data=request_data)
            if serializer.is_valid():
                instance=serializer.save()
                return Response("requirement assigned successfully",status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def patch():
        pass
        
          
class ClientInverviewsAssignedCandidatesList(APIView):
    def get(self,request):
        try:
            assigner=request.GET.get("assigner")
            for_whome=request.GET.get("whome")
            interviewer=request.GET.get("interviewer")

            requirement_id=request.GET.get("req_id")
            interview_id=request.GET.get("interview_id")
            login_emp=request.GET.get("login_emp_id")
    

            if requirement_id:

                emp_obj=EmployeeDataModel.objects.filter(EmployeeId=login_emp).first()
                if emp_obj.Designation not in ["HR","Admin"]:
                    interview_obj=InterviewSchedulModel.objects.filter(for_whome="client",assigned_requirement__requirement__pk=requirement_id,
                                                                       assigned_requirement__assigned_to_recruiter__EmployeeId=login_emp)
                    
                    print(interview_obj)

                else:
                    interview_obj=InterviewSchedulModel.objects.filter(for_whome="client",assigned_requirement__requirement__pk=requirement_id)
                    
            
                if not interview_obj.exists():
                    return Response([],status=status.HTTP_200_OK)
                # Exclude candidates who exist in HRFinalStatusModel

                excluded_candidates = HRFinalStatusModel.objects.values_list('CandidateId', 'req_id')

                # Exclude interviews where both Candidate and requirement_id match
                interview_obj = interview_obj.exclude(
                    Candidate__in=[candidate_id for candidate_id, assigned_requirement in excluded_candidates],
                    assigned_requirement__in=[assigned_requirement for candidate_id, assigned_requirement in excluded_candidates]
                )

                interview_list=[]
                
                for interview in interview_obj:
                    serializer=ClientInterviewSchedulSerializer(interview).data
                    review_obj=Review.objects.filter(interview_id__pk=interview.pk).first()
                    review_serializer=InterviewReviewSerializer(review_obj).data
                    serializer.update({"review":review_serializer})
                    interview_list.append(serializer)
                return Response(interview_list,status=status.HTTP_200_OK)
            
            elif interview_id:
                interview_obj=InterviewSchedulModel.objects.filter(pk=interview_id).first()
                if not interview_obj:
                    return Response({},status=status.HTTP_400_BAD_REQUEST)
                serializer=ClientInterviewSchedulSerializer(interview_obj).data
                review_obj=Review.objects.filter(interview_id__pk=interview_obj.pk).first()
                review_serializer=InterviewReviewSerializer(review_obj).data
                serializer.update({"review":review_serializer})
                return Response(serializer,status=status.HTTP_200_OK)

            if not for_whome or not assigner:
                return Response("Whome The interview was assigned is required ",status=status.HTTP_400_BAD_REQUEST)
            interview_obj=InterviewSchedulModel.objects.filter(for_whome="client",interviewer__EmployeeId=assigner)
    
            if not interview_obj.exists():
                return Response("no interviews found",status=status.HTTP_400_BAD_REQUEST)
            serializer=ClientInterviewSchedulSerializer(interview_obj,many=True)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)

class RecruitersRequirementAccess(APIView):
    def get(self,request):
        try:
            requirement_id=request.GET.get("req_id")
            login_emp=request.GET.get("login_emp_id")

            if login_emp and requirement_id:
                is_assigned_requirement=RequirementAssign.objects.filter(assigned_to_recruiter__EmployeeId=login_emp,requirement__pk=requirement_id)
                if is_assigned_requirement.exists():
                    return Response({"access":True})
                else:
                    return Response({"access":False})
        except Exception as e:
            return Response(str(e))

class ClientInterviewList(APIView):
    def get(self, request, type=None):
        try:
            # Fetch the logged-in employee ID from query params
            login_employee = request.GET.get("login_emp")
            # If login_employee is present, filter the interviews
            if login_employee:
                interview_obj = InterviewSchedulModel.objects.filter(
                    Q(interviewer__EmployeeId=login_employee) | Q(ScheduledBy__EmployeeId=login_employee),for_whome="client")
                # If no interviews are found, return a 400 response
                if not interview_obj.exists():
                    return Response("No interviews are there", status=status.HTTP_400_BAD_REQUEST)
                # Serialize and return the interview data
                # aassigned_req_obj=interview_obj.values_list('assigned_requirement', flat=True)

                serializer = ClientInterviewSchedulSerializer(interview_obj, many=True).data
                return Response(serializer, status=status.HTTP_200_OK)
            # If login_employee is not provided, return an error response
            return Response("No employee provided", status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # Return a 500 response with the exception message
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def post(self,request):
        interview_id=request.data.get("int_id")
        if not interview_id:
            return Response("interview instance is required",status=status.HTTP_400_BAD_REQUEST)
        
        interview_review_obj=Review.objects.filter(interview_id__pk=interview_id).first()
        if not interview_review_obj:
            return Response("interview Review not Exist",status=status.HTTP_400_BAD_REQUEST)
        
        review_serializer=clientInterviewReviewSerializer(interview_review_obj)
        return Response(review_serializer.data)
    
class ClientInterviewDetailsDisplay(APIView):
    def get(self,request,login_emp,filter_type=None):

        """1.get for perticular requirement how many interview is there need to display
            2.get based on the candidate how many interviews assigned for him based on the 
            3.get based on the date which are the interviews assigned need to display"""
        emp_obj=EmployeeDataModel.objects.filter(EmployeeId=login_emp).first()
        if not emp_obj:
            return Response("Employee is required",status=status.HTTP_400_BAD_REQUEST)

        if filter_type == "requirement":
            requirement_id=request.GET.get("req_id")
            if not requirement_id:
                return Response("requirement id is required",status=status.HTTP_400_BAD_REQUEST)
            if emp_obj.Designation in ["HR","Admin"]:
                interview_obj = InterviewSchedulModel.objects.filter(assigned_requirement__requirement__pk=requirement_id)
            else:
                Reporting_Team=EmployeeDataModel.objects.filter(Reporting_To=emp_obj.pk)
                if Reporting_Team:
                    def get_all_reports(reporting_head):
                        # Get direct reports for this head
                        direct_reports = EmployeeDataModel.objects.filter(Reporting_To=reporting_head.pk)
                        # Initialize a queryset with these reports
                        reports = direct_reports
                        # Recursively find sub-reports for each direct report
                        for report in direct_reports:
                            reports |= get_all_reports(report)  # Concatenate the querysets
                        return reports
                    Reporting_Team |= get_all_reports(emp_obj)

                    interview_obj = InterviewSchedulModel.objects.filter(Q(interviewer__EmployeeId__in=Reporting_Team) | Q(ScheduledBy__EmployeeId__in=Reporting_Team),
                                            assigned_requirement__requirement__pk=requirement_id)
                else:
                    
                    interview_obj = InterviewSchedulModel.objects.filter(Q(interviewer__EmployeeId=login_emp) | Q(ScheduledBy__EmployeeId=login_emp),
                                            assigned_requirement__requirement__pk=requirement_id)

            
            if not interview_obj.exists():
                return Response("No interviews are there", status=status.HTTP_400_BAD_REQUEST)
            

            
            serializer = ClientInterviewSchedulSerializer(interview_obj, many=True).data
            return Response(serializer, status=status.HTTP_200_OK)
        
class ClientFinalStatusListCountView(APIView):
    def get(self, request):
        req_id=request.GET.get("req_id")
        client_id=request.GET.get("client_id")
        rec_id=request.GET.get("rec_id")
        final_status=request.GET.get("final_status")

        try:
            """ To get the client final status count based on the requirement id, client id, recruiter id, and all """
            if req_id:
                client_finalstatus_count = {}
            
                client_final_status_obj = HRFinalStatusModel.objects.filter(req_id__pk=req_id).order_by("-ReviewedOn")

                # Step 2: Dictionary to store only the latest PK for each unique CandidateId
                candidate_latest_pk = {}

                # Loop through the queryset to ensure only the latest PK for each CandidateId is stored
                for candidate in client_final_status_obj:
                    if candidate.CandidateId.pk not in candidate_latest_pk:  # Store only the first occurrence since it is already ordered by "-ReviewedOn"
                        candidate_latest_pk[candidate.CandidateId.pk] = candidate.pk

                # Extract Candidate IDs and PKs for filtering
                candidate_ids = list(candidate_latest_pk.keys())
                latest_pks = list(candidate_latest_pk.values())

                # Step 3: Filter the queryset using the CandidateId and PKs
                client_final_status = client_final_status_obj.filter(CandidateId__pk__in=candidate_ids, pk__in=latest_pks)

                # Step 4: Check if final_status exists and filter accordingly
                if final_status:
                    if final_status == "candidate_joined":
                        final_list = client_final_status.filter(CandidateId__Final_Results="candidate_joined")
                    else:
                        final_list = client_final_status.filter(Final_Result=final_status)
                    
                    final_status_list = []
                    for final_result in final_list:
                        interview_obj = InterviewSchedulModel.objects.filter(
                            Candidate=final_result.CandidateId,
                            assigned_requirement__requirement=final_result.req_id
                        ).first()
                        
                        client_finalstatus_serializer = ClientHRInterviewReviewSerializer(final_result).data
                        client_finalstatus_serializer["interview_id"] = interview_obj.pk if interview_obj else None
                        final_status_list.append(client_finalstatus_serializer)

                    return Response(final_status_list)

                else:
                    # Update counts for each status
                    client_finalstatus_count.update({"client_rejected": client_final_status.filter(Final_Result="client_rejected").count()})
                    client_finalstatus_count.update({"client_offered": client_final_status.filter(Final_Result="client_offered", CandidateId__Final_Results="client_offered").count()})
                    client_finalstatus_count.update({"client_kept_on_hold": client_final_status.filter(Final_Result="client_kept_on_hold").count()})
                    client_finalstatus_count.update({"client_offer_rejected": client_final_status.filter(Final_Result="client_offer_rejected").count()})
                    client_finalstatus_count.update({"joining_candidates": client_final_status.filter(CandidateId__Final_Results="candidate_joined").count()})

                    return Response(client_finalstatus_count, status=status.HTTP_200_OK)

            elif client_id:
                
                client_finalstatus_count = {}

                client_final_status_obj = HRFinalStatusModel.objects.filter(req_id__client__pk=client_id).order_by("-ReviewedOn")
                # Step 2: Dictionary to store only the latest PK for each unique CandidateId
                candidate_latest_pk = {}
                # Loop through the queryset to ensure only the latest PK for each CandidateId is stored
                for candidate in client_final_status_obj:
                    if candidate.CandidateId.pk not in candidate_latest_pk:  # Store only the first occurrence since it is already ordered by "-ReviewedOn"
                        candidate_latest_pk[candidate.CandidateId.pk] = candidate.pk

                # Extract Candidate IDs and PKs for filtering
                candidate_ids = list(candidate_latest_pk.keys())
                latest_pks = list(candidate_latest_pk.values())

                # Step 3: Filter the queryset using the CandidateId and PKs
                client_final_status = client_final_status_obj.filter(CandidateId__pk__in=candidate_ids, pk__in=latest_pks)

                # Step 4: Check if final_status exists and filter accordingly
                if final_status:
                    if final_status == "candidate_joined":
                        final_list = client_final_status.filter(CandidateId__Final_Results="candidate_joined")
                    else:
                        final_list = client_final_status.filter(Final_Result=final_status)
                    
                    final_status_list = []
                    for final_result in final_list:
                        interview_obj = InterviewSchedulModel.objects.filter(
                            Candidate=final_result.CandidateId,
                            assigned_requirement__requirement=final_result.req_id
                        ).first()
                        
                        client_finalstatus_serializer = ClientHRInterviewReviewSerializer(final_result).data
                        client_finalstatus_serializer["interview_id"] = interview_obj.pk if interview_obj else None
                        final_status_list.append(client_finalstatus_serializer)

                    return Response(final_status_list)

                else:
                    # Update counts for each status
                    client_finalstatus_count.update({"client_rejected": client_final_status.filter(Final_Result="client_rejected").count()})
                    client_finalstatus_count.update({"client_offered": client_final_status.filter(Final_Result="client_offered", CandidateId__Final_Results="client_offered").count()})
                    client_finalstatus_count.update({"client_kept_on_hold": client_final_status.filter(Final_Result="client_kept_on_hold").count()})
                    client_finalstatus_count.update({"client_offer_rejected": client_final_status.filter(Final_Result="client_offer_rejected").count()})
                    client_finalstatus_count.update({"joining_candidates": client_final_status.filter(CandidateId__Final_Results="candidate_joined").count()})

                    return Response(client_finalstatus_count, status=status.HTTP_200_OK)
            
            elif rec_id:
                pass

            client_finalstatus_count = {}

            # Step 1: Query to fetch client final status objects
            client_final_status_obj = HRFinalStatusModel.objects.filter(req_id__isnull=False).order_by("-ReviewedOn")

            # Step 2: Dictionary to store only the latest PK for each unique CandidateId
            candidate_latest_pk = {}

            # Loop through the queryset to ensure only the latest PK for each CandidateId is stored
            for candidate in client_final_status_obj:
                if candidate.CandidateId.pk not in candidate_latest_pk:  # Store only the first occurrence since it is already ordered by "-ReviewedOn"
                    candidate_latest_pk[candidate.CandidateId.pk] = candidate.pk

            # Extract Candidate IDs and PKs for filtering
            candidate_ids = list(candidate_latest_pk.keys())
            latest_pks = list(candidate_latest_pk.values())

            # Step 3: Filter the queryset using the CandidateId and PKs
            client_final_status = client_final_status_obj.filter(CandidateId__pk__in=candidate_ids, pk__in=latest_pks)

            # Step 4: Check if final_status exists and filter accordingly
            if final_status:
                if final_status == "candidate_joined":
                    final_list = client_final_status.filter(CandidateId__Final_Results="candidate_joined")
                else:
                    final_list = client_final_status.filter(Final_Result=final_status)
                
                final_status_list = []
                for final_result in final_list:
                    interview_obj = InterviewSchedulModel.objects.filter(
                        Candidate=final_result.CandidateId,
                        assigned_requirement__requirement=final_result.req_id
                    ).first()
                    
                    client_finalstatus_serializer = ClientHRInterviewReviewSerializer(final_result).data
                    client_finalstatus_serializer["interview_id"] = interview_obj.pk if interview_obj else None
                    final_status_list.append(client_finalstatus_serializer)

                return Response(final_status_list)

            else:
                # Update counts for each status
                client_finalstatus_count.update({"client_rejected": client_final_status.filter(Final_Result="client_rejected").count()})
                client_finalstatus_count.update({"client_offered": client_final_status.filter(Final_Result="client_offered", CandidateId__Final_Results="client_offered").count()})
                client_finalstatus_count.update({"client_kept_on_hold": client_final_status.filter(Final_Result="client_kept_on_hold").count()})
                client_finalstatus_count.update({"client_offer_rejected": client_final_status.filter(Final_Result="client_offer_rejected").count()})
                client_finalstatus_count.update({"joining_candidates": client_final_status.filter(CandidateId__Final_Results="candidate_joined").count()})
            

                return Response(client_finalstatus_count, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AssignedRequirementsInterviews(APIView):
    def get(self,request,login_emp,req_id=None):
        try:
            emp_obj=EmployeeDataModel.objects.filter(EmployeeId=login_emp).first()

            if emp_obj and emp_obj.Designation in ["Admin","HR"]:

                if req_id:
                    requirement_obj=Requirement.objects.filter(pk=req_id).first()
                    if not requirement_obj:
                        return Response("requirement not found",status=status.HTTP_400_BAD_REQUEST)
                    
                    requirement_serilaizer=Requirementserializer(requirement_obj).data

                    req_assigns=RequirementAssign.objects.filter(requirement__pk=requirement_obj.pk)
                    if not req_assigns.exists():
                        requirement_serilaizer["RequirementAssign"]=[]

                    for req_assign in req_assigns:
                        req_assign_serializer=AssignedRequirementSerializer(req_assign).data
                        requirement_serilaizer["RequirementAssign"]=req_assign_serializer

                    
                    client_interviews=InterviewSchedulModel.objects.filter(for_whome="client",assigned_requirement__pk=requirement_obj.pk)
                    client_interviews_serializer=InterviewSchedulSerializer(client_interviews,many=True).data

                    requirement_serilaizer["InterviewSchedules"]=client_interviews_serializer


                    return Response(requirement_serilaizer,status=status.HTTP_200_OK)
                
                else:
                    requirement_objs=Requirement.objects.all()

                    requirements_list=[]

                    for requirement_obj in requirement_objs:

                        requirement_serilaizer=Requirementserializer(requirement_obj).data

                        req_assigns=RequirementAssign.objects.filter(requirement__pk=requirement_obj.pk)
                        if not req_assigns.exists():
                            requirement_serilaizer["RequirementAssign"]=[]

                        for req_assign in req_assigns:
                            req_assign_serializer=AssignedRequirementSerializer(req_assign).data
                            requirement_serilaizer["RequirementAssign"]=req_assign_serializer
                        
                        client_interviews=InterviewSchedulModel.objects.filter(for_whome="client",assigned_requirement__pk=requirement_obj.pk)
                        client_interviews_serializer=InterviewSchedulSerializer(client_interviews,many=True).data

                        requirement_serilaizer["InterviewSchedules"]=client_interviews_serializer

                        requirements_list.append(requirement_serilaizer)

                    return Response(requirements_list,status=status.HTTP_200_OK)
            return Response("still perticular employee not done",status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
            
        
# 18/03/2026
class ClientCandidateJoiningHistoryView(APIView):
    def get(self, request):
        client_id = request.GET.get("client_id")
        interview_id = request.GET.get("interview_id")

        # 18/03/2026
        # Filter by interview_id if provided
        if interview_id:
            interview_obj = InterviewSchedulModel.objects.filter(pk=interview_id).first()
            if not interview_obj:
                return Response({"error": "Interview not found."}, status=status.HTTP_404_NOT_FOUND)

            interview_serializer = ClientInterviewSchedulSerializer(interview_obj).data
            final_results = HRFinalStatusModel.objects.filter(
                req_id=interview_obj.assigned_requirement.requirement,
                CandidateId=interview_obj.Candidate
            )
            final_status_serializer = HRInterviewReviewSerializer(final_results, many=True).data
            interview_serializer["FinalStatusList"] = final_status_serializer

            joining_history_obj = ClientCandidateJoiningHistory.objects.filter(client_interview=interview_obj)
            joining_history_serializer = ClientCandidateJoiningHistorySerializer(joining_history_obj, many=True).data 
            interview_serializer["Joining_History"] = joining_history_serializer

            return Response(interview_serializer, status=status.HTTP_200_OK)

        # Filter by client_id if provided
        elif client_id:
            all_joinings = ClientCandidateJoiningHistory.objects.filter(requirement__client__pk=client_id)
            
            # --- Phase 2: Add Potential Placements ---
            # These are candidates assigned to client requirements who haven't "joined" formally yet.
            existing_interview_ids = all_joinings.values_list('client_interview_id', flat=True)
            
            potential_interviews = InterviewSchedulModel.objects.filter(
                assigned_requirement__requirement__client__pk=client_id,
                for_whome='client'
            ).exclude(id__in=existing_interview_ids)
            
            # Convert joinings to list of data
            serializer = ClientCandidateJoiningHistorySerializer(all_joinings, many=True)
            data = serializer.data
            
            # Add virtual entries for potential interviews
            for interview in potential_interviews:
                data.append({
                    "id": f"virtual_int_{interview.id}",
                    "candidate_details": {
                        "FirstName": interview.Candidate.FirstName,
                        "LastName": interview.Candidate.LastName,
                        "Email": interview.Candidate.Email
                    },
                    "requirement_details": {
                        "job_title": interview.assigned_requirement.requirement.job_title if interview.assigned_requirement and interview.assigned_requirement.requirement else "N/A",
                        "id": interview.assigned_requirement.requirement.id if interview.assigned_requirement and interview.assigned_requirement.requirement else None,
                        "billing_amount": interview.assigned_requirement.requirement.billing_amount if interview.assigned_requirement and interview.assigned_requirement.requirement else 0
                    },
                    "joining_date": interview.DOJ if hasattr(interview, 'DOJ') else None,
                    "CTC": interview.assigned_requirement.requirement.billing_amount if interview.assigned_requirement and interview.assigned_requirement.requirement else 0,
                    "is_potential": True,
                    "source": "interview"
                })

            # --- Phase 3: Add Potential Placements from HRFinalStatusModel ---
            # These are candidates who were offered or joined via FinalStatusUpdate but might not have Interviews or Joining History.
            existing_candidate_ids = all_joinings.values_list('candidate_id', flat=True)
            existing_interview_candidate_ids = potential_interviews.values_list('Candidate_id', flat=True)
            
            potential_hrfs = HRFinalStatusModel.objects.filter(
                req_id__client__pk=client_id,
                Final_Result__in=['client_offered', 'candidate_joined', 'offered']
            ).exclude(CandidateId_id__in=existing_candidate_ids).exclude(CandidateId_id__in=existing_interview_candidate_ids)

            for hrfs in potential_hrfs:
                data.append({
                    "id": f"virtual_hrfs_{hrfs.id}",
                    "candidate_details": {
                        "FirstName": hrfs.CandidateId.FirstName,
                        "LastName": hrfs.CandidateId.LastName,
                        "Email": hrfs.CandidateId.Email
                    },
                    "requirement_details": {
                        "job_title": hrfs.req_id.job_title if hrfs.req_id else "N/A",
                        "id": hrfs.req_id.id if hrfs.req_id else None,
                        "billing_amount": hrfs.req_id.billing_amount if hrfs.req_id else 0
                    },
                    "joining_date": timezone.localdate(),
                    "CTC": hrfs.req_id.billing_amount if hrfs.req_id else 0,
                    "is_potential": True,
                    "source": "hrfs"
                })
            
            print(f"DEBUG: Returning {len(data)} total placements (including potential) for client {client_id}")
            return Response(data, status=status.HTTP_200_OK)

        # Default: return all joining history records
        all_joinings = ClientCandidateJoiningHistory.objects.all()
        serializer = ClientCandidateJoiningHistorySerializer(all_joinings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new ClientCandidateJoiningHistory record."""
        serializer = ClientCandidateJoiningHistorySerializer(data=request.data)
        if serializer.is_valid():
            instance=serializer.save()

            # instance.client_interview.assigned_requirement.closed_pos_count += 1
            # instance.client_interview.assigned_requirement.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        """Update specific fields for a ClientCandidateJoiningHistory record."""
        try:
            instance = ClientCandidateJoiningHistory.objects.get(pk=pk)
        except ClientCandidateJoiningHistory.DoesNotExist:
            return Response({"error": "Record not found."}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ClientCandidateJoiningHistorySerializer(instance, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ClientRequirementInvoiceGenerationView(APIView):
    def get(self,request):
        try:
            interview_id=request.GET.get("interview_id")

            joining_history_obj=ClientCandidateJoiningHistory.objects.filter(client_interview__pk=interview_id,is_active=True).first()
            if not joining_history_obj:
                return Response("joining data not found",status=status.HTTP_400_BAD_REQUEST)
            invoice_obj=Client_Invoice.objects.filter(joined_details=joining_history_obj).first()

            if not invoice_obj:
                invoice_obj=Client_Invoice.objects.create(joined_details=joining_history_obj)
                invoice_obj.joined_details.is_invoice_created=True
                invoice_obj.joined_details.save()

            if invoice_obj:
               client_invoice_obj= Client_Invoice.objects.filter(pk=invoice_obj.pk).first()
               invoice_serializer=ClientInvoiceSerializer(client_invoice_obj).data
               get_client_details=client_invoice_obj.joined_details.client_interview.assigned_requirement.requirement.client
               invoice_serializer["client_name"]=get_client_details.client_name
               invoice_serializer["client_company_name"]=get_client_details.company_name
               invoice_serializer["client_gst_number"]=get_client_details.gst_number



               return Response(invoice_serializer,status=status.HTTP_200_OK)
            else:
                return Response("invoice creation error",status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response(str(e),status=status.HTTP_500_INTERNAL_SERVER_ERROR)


       



        



#18/03/2026
# Phase 2: Client Billing Views

class ClientBillingCycleView(APIView):
    """
    Handles billing cycles for client placements.

    GET:
        - ?joining_id=<id>  → List all billing cycles for a specific joining record.
        - ?client_id=<id>   → List all billing cycles across all placements for a client.
        - ?requirement_id=<id> → List all billing cycles for a requirement.

    POST:
        Create a new billing cycle entry for a joining record.
        Required body: { joining_details, cycle_month, billing_amount, due_date }
    """
    def get(self, request):
        try:
            joining_id = request.GET.get("joining_id")
            client_id = request.GET.get("client_id")
            requirement_id = request.GET.get("requirement_id")

            # --- Auto-mark overdue: flip PENDING/PARTIAL cycles past their due date to OVERDUE ---
            today = timezone.localdate()
            ClientBillingCycle.objects.filter(
                status__in=["pending", "partial"],
                due_date__lt=today
            ).update(status="overdue")
            # ---------------------------------------------------------------------------------

            if joining_id:
                # Virtual placements (e.g. 'virtual_hrfs_123') have no real joining record yet.
                # They can't have any existing billing cycles, so return empty list safely.
                if isinstance(joining_id, str) and joining_id.startswith("virtual_"):
                    return Response([], status=status.HTTP_200_OK)
                cycles = ClientBillingCycle.objects.filter(joining_details__pk=joining_id)
                serializer = ClientBillingCycleSerializer(cycles, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            elif client_id:
                cycles = ClientBillingCycle.objects.filter(
                    joining_details__requirement__client__pk=client_id
                ).order_by("-created_on")
                serializer = ClientBillingCycleSerializer(cycles, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            elif requirement_id:
                cycles = ClientBillingCycle.objects.filter(
                    joining_details__requirement__pk=requirement_id
                ).order_by("-created_on")
                serializer = ClientBillingCycleSerializer(cycles, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)

            else:
                return Response(
                    {"error": "Provide joining_id, client_id, or requirement_id as query param."},
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request):
        """
        Create a new billing cycle manually.
        This is used when HR wants to create the first monthly invoice
        after a candidate joins.
        Body: { joining_details, cycle_month, billing_amount, due_date, [remarks] }
        """
        try:
            # serializer = ClientBillingCycleSerializer(data=request.data)
            # --- Phase 2: Handle Virtual Joinings ---
            # If the joining_details is a string ID from a virtual placement, 
            # we create the formal joining record on the fly.
            data = request.data.copy()
            joining_id_val = data.get("joining_details")
            
            if isinstance(joining_id_val, str) and joining_id_val.startswith("virtual_"):
                if joining_id_val.startswith("virtual_int_") or (not joining_id_val.startswith("virtual_hrfs_") and joining_id_val.startswith("virtual_")):
                    # Support both old "virtual_" and new "virtual_int_" prefixes
                    str_id = joining_id_val.replace("virtual_int_", "").replace("virtual_", "")
                    interview_id = int(str_id)
                    interview_obj = InterviewSchedulModel.objects.get(pk=interview_id)
                    
                    # Check if it was already created (concurrency safeguard)
                    joining_obj = ClientCandidateJoiningHistory.objects.filter(client_interview=interview_obj).first()
                    if not joining_obj:
                        # Find the requirement from the assigned_requirement model safely
                        requirement_obj = None
                        if interview_obj.assigned_requirement and hasattr(interview_obj.assigned_requirement, 'requirement'):
                            requirement_obj = interview_obj.assigned_requirement.requirement

                        joining_obj = ClientCandidateJoiningHistory.objects.create(
                            client_interview=interview_obj,
                            candidate=interview_obj.Candidate,
                            requirement=requirement_obj,
                            joining_date=interview_obj.DOJ if hasattr(interview_obj, 'DOJ') and interview_obj.DOJ else timezone.localdate(),
                            is_joined=True,
                            is_active=True,
                            CTC=requirement_obj.billing_amount if requirement_obj else 0,
                            remarks="Auto-joined from virtual interview during billing cycle creation"
                        )
                
                elif joining_id_val.startswith("virtual_hrfs_"):
                    hrfs_id = int(joining_id_val.replace("virtual_hrfs_", ""))
                    hrfs_obj = HRFinalStatusModel.objects.get(pk=hrfs_id)
                    
                    # Check if it was already created
                    joining_obj = ClientCandidateJoiningHistory.objects.filter(
                        candidate=hrfs_obj.CandidateId,
                        requirement=hrfs_obj.req_id
                    ).first()
                    
                    if not joining_obj:
                        joining_obj = ClientCandidateJoiningHistory.objects.create(
                            candidate=hrfs_obj.CandidateId,
                            requirement=hrfs_obj.req_id,
                            joining_date=timezone.localdate(),
                            is_joined=True,
                            is_active=True,
                            CTC=0,
                            remarks="Auto-joined from virtual HRFinalStatus during billing cycle creation"
                        )
                
                data["joining_details"] = joining_obj.id

            is_contract_basis = str(data.get("is_contract_basis", "false")).lower() in ["true", "1", "yes"]
            if is_contract_basis:
                real_joining_id = data.get("joining_details")
                joining_instance = ClientCandidateJoiningHistory.objects.filter(pk=real_joining_id).first()
                if joining_instance:
                    joining_instance.is_contract_basis = True
                    candidate_payout = data.get("candidate_payout_amount")
                    if candidate_payout not in [None, '', 0, '0']:
                        joining_instance.candidate_salary = candidate_payout
                    joining_instance.save()

            # Prevent duplicate cycle for same joining + month before serializer validation
            check_joining_id = data.get("joining_details")
            check_cycle_month = data.get("cycle_month")
            if ClientBillingCycle.objects.filter(joining_details__pk=check_joining_id, cycle_month=check_cycle_month).exists():
                return Response(
                    {"error": f"Billing cycle {check_cycle_month} already exists for this placement. Please use a different month number."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = ClientBillingCycleSerializer(data=data)
            if serializer.is_valid():
                #1/04/2026
                # --- Phase 2: Copy Candidate Salary for Contract Placements ---
                try:
                    joining_id = data.get("joining_details")
                    joining_obj = ClientCandidateJoiningHistory.objects.filter(pk=joining_id).first()
                    if joining_obj and joining_obj.is_contract_basis:
                        passed_payout = data.get("candidate_payout_amount")
                        if passed_payout not in [None, '', 0, '0']:
                            serializer.validated_data["candidate_payout_amount"] = passed_payout
                        else:
                            serializer.validated_data["candidate_payout_amount"] = joining_obj.candidate_salary
                except Exception as e:
                    print(f"Error copying candidate salary: {e}")
                # -----------------------------------------------------------

                try:
                    instance = serializer.save()
                    return Response(serializer.data, status=status.HTTP_201_CREATED)
                except Exception as e:
                    # Final concurrency safeguard: if it was created in the last few ms by another request
                    existing = ClientBillingCycle.objects.filter(
                        joining_details__pk=data.get("joining_details"),
                        cycle_month=data.get("cycle_month")
                    ).first()
                    if existing:
                        return Response(ClientBillingCycleSerializer(existing).data, status=status.HTTP_201_CREATED)
                    return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientBillingPaymentView(APIView):
    """
    Records a payment for a specific billing cycle.

    PATCH  /root/cms/billing-payment/<int:pk>/
        Body: { payment_date, payment_reference, [remarks] }
        Marks the billing cycle as 'paid'.
    """
    def patch(self, request, pk):
        try:
            cycle_obj = ClientBillingCycle.objects.filter(pk=pk).first()
            if not cycle_obj:
                return Response({"error": "Billing cycle not found."}, status=status.HTTP_404_NOT_FOUND)

            # if cycle_obj.status == "paid":
            #     return Response({"error": "This cycle is already fully paid."}, status=status.HTTP_400_BAD_REQUEST)

            payment_type = request.data.get("payment_type", "client") # 'client' or 'candidate'
            payment_amount = request.data.get("payment_amount")

            if payment_amount is None:
                return Response({"error": "payment_amount is required."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                payment_amount = float(payment_amount)
            except (ValueError, TypeError):
                return Response({"error": "payment_amount must be a valid number."}, status=status.HTTP_400_BAD_REQUEST)

            if payment_amount <= 0:
                return Response({"error": "payment_amount must be greater than 0."}, status=status.HTTP_400_BAD_REQUEST)

            if payment_type == "candidate":
                # --- Phase 2: Record Candidate Payout (Money OUT) ---
                if cycle_obj.payout_status == "paid":
                    return Response({"error": "Candidate salary for this cycle is already fully paid."}, status=status.HTTP_400_BAD_REQUEST)
                
                new_payout_total = float(cycle_obj.candidate_paid_amount) + payment_amount
                max_payout = float(cycle_obj.candidate_payout_amount)

                if new_payout_total >= max_payout:
                    new_payout_total = max_payout
                    new_payout_status = "paid"
                else:
                    new_payout_status = "partial"

                cycle_obj.candidate_paid_amount = new_payout_total
                cycle_obj.payout_status = new_payout_status
                cycle_obj.payout_date = request.data.get("payment_date", timezone.localdate())
                cycle_obj.payout_reference = request.data.get("payment_reference", cycle_obj.payout_reference)
            
            else:
                # --- Standard Client Payment (Money IN) ---
                if cycle_obj.status == "paid":
                    return Response({"error": "This cycle is already fully paid by the client."}, status=status.HTTP_400_BAD_REQUEST)

                new_paid_total = float(cycle_obj.paid_amount) + payment_amount
                billing_amount = float(cycle_obj.billing_amount)

                if new_paid_total >= billing_amount:
                    new_paid_total = billing_amount
                    new_status = "paid"
                else:
                    new_status = "partial"

                cycle_obj.paid_amount = new_paid_total
                cycle_obj.status = new_status
                cycle_obj.payment_date = request.data.get("payment_date", cycle_obj.payment_date)
                cycle_obj.payment_reference = request.data.get("payment_reference", cycle_obj.payment_reference)

            if request.data.get("remarks"):
                cycle_obj.remarks = request.data.get("remarks")
            
            cycle_obj.save()

            serializer = ClientBillingCycleSerializer(cycle_obj)
            # response_data = serializer.data
            # response_data["balance_amount"] = billing_amount - new_paid_total
            # return Response(response_data, status=status.HTTP_200_OK)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



class ClientBillingCycleSummaryView(APIView):
    """
    Returns a summary dashboard of billing for a specific client.

    GET ?client_id=<id>
    Returns:
        - total_billed:  Sum of all billing amounts across all cycles.
        - total_paid:    Sum of paid billing amounts.
        - total_pending: Sum of pending billing amounts.
        - cycle_counts: { pending, paid, overdue, cancelled }
        - active_placements: Count of active joined candidates under this client.
    """
    def get(self, request):
        try:
            client_id = request.GET.get("client_id")
            if not client_id:
                return Response({"error": "client_id is required."}, status=status.HTTP_400_BAD_REQUEST)

            # --- Self-Healing Mechanism (Phase 3) ---
            # Fix any orphaned joining records that belong to this client but are missing the requirement link.
            orphaned_joinings = ClientCandidateJoiningHistory.objects.filter(
                requirement=None,
                client_interview__assigned_requirement__requirement__client__pk=client_id
            )
            for joining in orphaned_joinings:
                joining.requirement = joining.client_interview.assigned_requirement.requirement
                joining.save()
            # ----------------------------------------

            cycles = ClientBillingCycle.objects.filter(
                joining_details__requirement__client__pk=client_id
            )

            total_billed = cycles.aggregate(total=Sum("billing_amount"))["total"] or 0

            # --- Auto-mark overdue before calculating summary ---
            today = timezone.localdate()
            ClientBillingCycle.objects.filter(
                joining_details__requirement__client__pk=client_id,
                status__in=["pending", "partial"],
                due_date__lt=today
            ).update(status="overdue")
            # Re-query after update
            cycles = ClientBillingCycle.objects.filter(
                joining_details__requirement__client__pk=client_id
            )
            # -------------------------------------------------------

            # Fully paid cycles → count their full billing_amount
            sum_billed_paid = cycles.filter(status="paid").aggregate(total=Sum("billing_amount"))["total"]
            fully_paid = sum_billed_paid if sum_billed_paid is not None else 0
            
            # Partial cycles → count only what's been paid so far (paid_amount)
            sum_partial_paid = cycles.filter(status="partial").aggregate(total=Sum("paid_amount"))["total"]
            partially_paid = sum_partial_paid if sum_partial_paid is not None else 0
            total_paid = fully_paid + partially_paid

            # Pending cycles → full billing_amount is still pending
            sum_pending = cycles.filter(status="pending").aggregate(total=Sum("billing_amount"))["total"]
            pending_full = sum_pending if sum_pending is not None else 0
            
            # Partial cycles → only the remaining balance is pending
            partial_queryset = cycles.filter(status="partial")
            if partial_queryset.exists():
                partial_agg = partial_queryset.aggregate(
                    total_billed=Sum("billing_amount"),
                    total_paid=Sum("paid_amount")
                )
                partial_balance = (partial_agg["total_billed"] or 0) - (partial_agg["total_paid"] or 0)
            else:
                partial_balance = 0
            total_pending = pending_full + partial_balance

            # Overdue: remaining balance on overdue cycles
            overdue_queryset = cycles.filter(status="overdue")
            if overdue_queryset.exists():
                overdue_agg = overdue_queryset.aggregate(
                    total_billed=Sum("billing_amount"),
                    total_paid=Sum("paid_amount")
                )
                total_overdue = (overdue_agg["total_billed"] or 0) - (overdue_agg["total_paid"] or 0)
            else:
                total_overdue = 0

            # --- Phase 2: Candidate Payout & Profit Aggregations ---
            sum_payout = cycles.aggregate(total=Sum("candidate_payout_amount"))["total"]
            total_payout = sum_payout if sum_payout is not None else 0
            
            sum_paid_out = cycles.aggregate(total=Sum("candidate_paid_amount"))["total"]
            total_payout_paid = sum_paid_out if sum_paid_out is not None else 0
            
            total_profit = total_billed - total_payout
            # --------------------------------------------------------

            cycle_counts = {
                "pending": cycles.filter(status="pending").count(),
                "paid": cycles.filter(status="paid").count(),
                "overdue": cycles.filter(status="overdue").count(),
                "cancelled": cycles.filter(status="cancelled").count(),
            }

            active_placements = ClientCandidateJoiningHistory.objects.filter(
                requirement__client__pk=client_id,
                is_active=True,
                is_joined=True
            ).count()

            return Response({
                "total_billed": total_billed,
                "total_paid": total_paid,
                "total_pending": total_pending,
                "total_overdue": total_overdue,
                "total_payout": total_payout,
                "total_payout_paid": total_payout_paid,
                "total_profit": total_profit,
                "cycle_counts": cycle_counts,
                "active_placements": active_placements
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
