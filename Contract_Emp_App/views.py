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
        
            serializer=Requirementserializer(req_obj,data=request.data)

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
            req_objs=RequirementAssign.objects.filter(requirement__pk=requirement)
            if not req_objs.exists():
                return Response([],status=status.HTTP_200_OK)
            requirement_assigned_list=[]
            for assign in req_objs:
                serializer=ClientRequirementAssignSerializer(assign,context={"request":request}).data
                interview_obj=InterviewSchedulModel.objects.filter(assigned_requirement=assign).count()
                serializer["candidate_assigned"]=interview_obj
                requirement_assigned_list.append(serializer)
            return Response(requirement_assigned_list,status=status.HTTP_200_OK)
            
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
                    return Response("no interviews found",status=status.HTTP_400_BAD_REQUEST)
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
            
        

class ClientCandidateJoiningHistoryView(APIView):
    def get(self, request):
        interview_id = request.GET.get("interview_id")
        
        # Check if interview_id is provided
        if not interview_id:
            return Response({"error": "interview_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the InterviewSchedulModel object
        interview_obj = InterviewSchedulModel.objects.filter(pk=interview_id).first()
        if not interview_obj:
            return Response({"error": "Interview not found."}, status=status.HTTP_404_NOT_FOUND)

        # Serialize the interview object
        interview_serializer = ClientInterviewSchedulSerializer(interview_obj).data

        # Get final status results for the interview
        final_results = HRFinalStatusModel.objects.filter(
            req_id=interview_obj.assigned_requirement.requirement,
            CandidateId=interview_obj.Candidate
        )
        # Serialize the final status results
        final_status_serializer = HRInterviewReviewSerializer(final_results, many=True).data
        interview_serializer["FinalStatusList"] = final_status_serializer

        # Get the joining history associated with the interview
        joining_history_obj = ClientCandidateJoiningHistory.objects.filter(client_interview=interview_obj)
        
        joining_history_serializer = ClientCandidateJoiningHistorySerializer(joining_history_obj,many=True).data 
           
        interview_serializer["Joining_History"] = joining_history_serializer

        return Response(interview_serializer, status=status.HTTP_200_OK)

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


       



        




