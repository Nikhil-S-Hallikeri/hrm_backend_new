# ===== ACTIVITY DASHBOARD PAGINATION VIEWS =====
#17/4/2026
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta, datetime
from calendar import monthrange
from django.db.models import Q, Count
from .models import EmployeeDataModel, NewDailyAchivesModel, FollowUpModel, NewActivityModel, MonthAchivesListModel, ActivityListModel
from .serializers import FollowUpSerializer, NewDailyAchivesModelSerializer

#1/6/2026
def parse_date_range(filter_type, start_date_str=None, end_date_str=None):
    """
    Helper to parse dynamic date filters consistently.
    """
    today = timezone.localdate()
    if filter_type == 'this_month':
        start_date = today.replace(day=1)
        end_date = today.replace(day=monthrange(today.year, today.month)[1])
    elif filter_type == 'this_week':
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
    elif filter_type == 'today':
        start_date = end_date = today
    elif filter_type == 'prev_month':
        first_day_this = today.replace(day=1)
        last_prev = first_day_this - timedelta(days=1)
        start_date = last_prev.replace(day=1)
        end_date = last_prev
    elif filter_type == 'all':
        start_date = datetime(2000, 1, 1).date()
        end_date = datetime(2100, 1, 1).date()
    elif filter_type == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            start_date = end_date = today
    else:
        start_date = end_date = today
    return start_date, end_date



class PendingFollowUpsView(APIView):
    """
    Get pending follow-ups with pagination and search.
    GET /root/activity/pending-followups?login_emp_id=MTM25I1056&filter_type=this_month&page=1&page_size=10&search=john
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Role-based filtering
            if current_user.Designation == 'Admin':
                target_employees = EmployeeDataModel.objects.all()
            elif current_user.Designation in ['HR', 'Recruiter']:
                team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
                target_employees = team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
            else:
                target_employees = EmployeeDataModel.objects.filter(pk=current_user.pk)
            
            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            # Get pending follow-ups
            requirement_id = request.GET.get("requirement_id")
            pending_followups = FollowUpModel.objects.filter(
                # activity_record__current_day_activity__Employee__in=target_employees,
                activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
                activity_record__current_day_activity__Date__range=(start_date, end_date),
                status='pending'
            )
            
            if requirement_id:
                pending_followups = pending_followups.filter(activity_record__assigned_requirement_id=requirement_id)
                
            pending_followups = pending_followups.select_related('activity_record').order_by('-expected_date', '-expected_time')

            
            # Apply search filter
            if search_query:
                pending_followups = pending_followups.filter(
                    Q(activity_record__candidate_name__icontains=search_query) |
                    Q(activity_record__client_name__icontains=search_query) |
                    Q(activity_record__candidate_phone__icontains=search_query) |
                    Q(activity_record__client_phone__icontains=search_query)
                )
            
            # Pagination
            total_count = pending_followups.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_followups = pending_followups[start_index:end_index]
            
            serializer = FollowUpSerializer(paginated_followups, many=True)
            return Response({
                # "followups": serializer.data,
                "results": serializer.data,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CompletedFollowUpsView(APIView):
    """
    Get completed follow-ups with pagination and search.
    GET /root/activity/completed-followups?login_emp_id=MTM25I1056&filter_type=this_month&page=1&page_size=10&search=john
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Role-based filtering
            if current_user.Designation == 'Admin':
                target_employees = EmployeeDataModel.objects.all()
            elif current_user.Designation in ['HR', 'Recruiter']:
                team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
                target_employees = team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
            else:
                target_employees = EmployeeDataModel.objects.filter(pk=current_user.pk)
            
            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            # Get completed follow-ups
            requirement_id = request.GET.get("requirement_id")
            completed_followups = FollowUpModel.objects.filter(
                activity_record__current_day_activity__Activity_instance__Employee__in=target_employees,
                activity_record__current_day_activity__Date__range=(start_date, end_date),
                status='completed'
            )
            
            if requirement_id:
                completed_followups = completed_followups.filter(activity_record__assigned_requirement_id=requirement_id)
                
            completed_followups = completed_followups.select_related('activity_record').order_by('-completed_on')

            
            # Apply search filter
            if search_query:
                completed_followups = completed_followups.filter(
                    Q(activity_record__candidate_name__icontains=search_query) |
                    Q(activity_record__client_name__icontains=search_query) |
                    Q(activity_record__candidate_phone__icontains=search_query) |
                    Q(activity_record__client_phone__icontains=search_query)
                )
            
            # Pagination
            total_count = completed_followups.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_followups = completed_followups[start_index:end_index]
            
            serializer = FollowUpSerializer(paginated_followups, many=True)
            return Response({
                # "followups": serializer.data,
                "results": serializer.data,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TotalActivitiesView(APIView):
    """
    Get all activities (interview + client calls) with pagination and search.
    GET /root/activity/total-activities?login_emp_id=MTM25I1056&filter_type=this_month&page=1&page_size=10&search=john
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Role-based filtering
            if current_user.Designation == 'Admin':
                target_employees = EmployeeDataModel.objects.all()
            elif current_user.Designation in ['HR', 'Recruiter']:
                team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
                target_employees = team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
            else:
                target_employees = EmployeeDataModel.objects.filter(pk=current_user.pk)
            
            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            # Get all activities
            requirement_id = request.GET.get("requirement_id")
            
            activities = NewDailyAchivesModel.objects.filter(
                # current_day_activity__Employee__in=target_employees,
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date)
            # ).select_related('current_day_activity__Employee').order_by('-current_day_activity__Date')    
            ).exclude(lead_status='staged')

            if requirement_id:
                activities = activities.filter(assigned_requirement_id=requirement_id)
            
            activities = activities.select_related('current_day_activity__Activity_instance__Employee').order_by('-current_day_activity__Date')
            
            # Apply search filter
            if search_query:
                activities = activities.filter(
                    Q(candidate_name__icontains=search_query) |
                    Q(client_name__icontains=search_query) |
                    Q(candidate_phone__icontains=search_query) |
                    Q(client_phone__icontains=search_query)
                )
            
            # Pagination
            total_count = activities.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_activities = activities[start_index:end_index]
            
            # Serialize data
            records = []
            for activity in paginated_activities:
                record = {
                    'id': activity.id,
                    'lead_status': activity.lead_status,
                }
                
                if activity.candidate_name:
                    record.update({
                        'type': 'interview',
                        'candidate_name': activity.candidate_name,
                        'candidate_phone': activity.candidate_phone,
                        'candidate_designation': activity.candidate_designation,
                        'interview_status': activity.interview_status,
                    })
                elif activity.client_name:
                    record.update({
                        'type': 'client',
                        'client_name': activity.client_name,
                        'client_phone': activity.client_phone,
                        'client_enquire_purpose': activity.client_enquire_purpose,
                        'client_status': activity.client_status,
                    })
                
                records.append(record)
            
            return Response({
                # "activities": records,
                "results": records,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SuccessfulOutcomesView(APIView):
    """
    Get successful outcomes with pagination and search.
    GET /root/activity/successful-outcomes?login_emp_id=MTM25I1056&filter_type=this_month&page=1&page_size=10&search=john
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Role-based filtering
            if current_user.Designation == 'Admin':
                target_employees = EmployeeDataModel.objects.all()
            elif current_user.Designation in ['HR', 'Recruiter']:
                team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
                target_employees = team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
            else:
                target_employees = EmployeeDataModel.objects.filter(pk=current_user.pk)
            
            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            # Get successful outcomes (based on dashboard criteria)
            requirement_id = request.GET.get("requirement_id")
            
            activities = NewDailyAchivesModel.objects.filter(
            #     current_day_activity__Employee__in=target_employees,
            #     current_day_activity__Date__range=(start_date, end_date),
            #     lead_status='closed'
            # ).select_related('current_day_activity__Employee').order_by('-current_day_activity__Date')
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date)
            ).exclude(lead_status='staged').filter(
                Q(interview_status='joined')
            )

            if requirement_id:
                activities = activities.filter(assigned_requirement_id=requirement_id)
            
            activities = activities.select_related('current_day_activity__Activity_instance__Employee').order_by('-current_day_activity__Date')
            
            # Apply search filter
            if search_query:
                activities = activities.filter(
                    Q(candidate_name__icontains=search_query) |
                    Q(client_name__icontains=search_query) |
                    Q(candidate_phone__icontains=search_query) |
                    Q(client_phone__icontains=search_query)
                )
            
            # Pagination
            total_count = activities.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_activities = activities[start_index:end_index]
            
            # Serialize data
            records = []
            for activity in paginated_activities:
                record = {
                    'id': activity.id,
                    'lead_status': activity.lead_status,
                    'closure_reason': activity.closure_reason,
                }
                
                if activity.candidate_name:
                    record.update({
                        'type': 'interview',
                        'candidate_name': activity.candidate_name,
                        'candidate_phone': activity.candidate_phone,
                        'candidate_designation': activity.candidate_designation,
                        'interview_status': activity.interview_status,
                    })
                elif activity.client_name:
                    record.update({
                        'type': 'client',
                        'client_name': activity.client_name,
                        'client_phone': activity.client_phone,
                        'client_enquire_purpose': activity.client_enquire_purpose,
                        'client_status': activity.client_status,
                    })
                
                records.append(record)
            
            return Response({
                "results": records,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RejectedLeadsView(APIView):
    """
    Get rejected leads with pagination and search.
    GET /root/activity/rejected?login_emp_id=MTM25I1056&filter_type=this_month&page=1&page_size=10&search=john
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            target_emp_id = request.GET.get("target_emp_id")

            # Role-based filtering
            if target_emp_id:
                target_employees_q = Q(EmployeeId=target_emp_id)
            else:
                target_employees_q = Q(pk=current_user.pk)
                if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
                    if current_user.Designation == 'Admin':
                        target_employees_q = Q()
                    else:
                        team_members_q = Q(Reporting_To=current_user)
                        if current_user.Designation == 'HR':
                            target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk)
                        elif current_user.Designation == 'Recruiter':
                            target_employees_q = team_members_q | Q(pk=current_user.pk)

            target_employees = EmployeeDataModel.objects.filter(target_employees_q)

            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)

            activities = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date)
            ).filter(
                Q(lead_status='rejected') | 
                (Q(lead_status__isnull=True) & (Q(interview_status='rejected') | Q(interview_status='Rejected_by_Candidate')))
            )

            requirement_id = request.GET.get("requirement_id")
            if requirement_id:
                activities = activities.filter(assigned_requirement_id=requirement_id)



            # activities = activities.select_related('current_day_activity__Activity_instance__Employee').order_by('-current_day_activity__Date')
            
            # # Apply search filter
            # if search_query:
            #     activities = activities.filter(
            #         Q(candidate_name__icontains=search_query) |
            #         Q(client_name__icontains=search_query) |
            #         Q(candidate_phone__icontains=search_query) |
            #         Q(client_phone__icontains=search_query)
            #     )
            
            # # Pagination
            # total_count = activities.count()
            # start_index = (page - 1) * page_size
            # end_index = start_index + page_size
            # paginated_activities = activities[start_index:end_index]
            
            # # Serialize data
            # records = []
            # for activity in paginated_activities:
            #     record = {
            #         'id': activity.id,
            #         'lead_status': activity.lead_status,
            #         'rejection_type': activity.rejection_type,
            #         'rejection_reason': getattr(activity, 'rejection_reason', ''),
            #     }
                
            #     if activity.candidate_name:
            #         record.update({
            #             'type': 'interview',
            #             'candidate_name': activity.candidate_name,
            #             'candidate_phone': activity.candidate_phone,
            #             'candidate_designation': activity.candidate_designation,
            #             'interview_status': activity.interview_status,
            #         })
            #     elif activity.client_name:
            #         record.update({
            #             'type': 'client',
            #             'client_name': activity.client_name,
            #             'client_phone': activity.client_phone,
            #             'client_enquire_purpose': activity.client_enquire_purpose,
            #             'client_status': activity.client_status,
            #         })
                
            #     records.append(record)
            
            # return Response({
            #     "results": records,
            #     "total_count": total_count,
            #     "page": page,
            #     "page_size": page_size,
            #     "total_pages": (total_count + page_size - 1) // page_size
            # }, status=status.HTTP_200_OK)




            activities = activities.select_related(
                'current_day_activity__Activity_instance__Employee',
                'current_day_activity__Activity_instance__activity_assigned_by'
            ).order_by('-current_day_activity__Date')

            return _paginate_and_serialize(request, activities)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClosedLeadsView(APIView):
    """
    Get closed leads with pagination and search.
    GET /root/activity/closed?login_emp_id=MTM25I1056&filter_type=this_month&page=1&page_size=10&search=john
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            target_emp_id = request.GET.get("target_emp_id")

            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

            # Role-based filtering
            if target_emp_id:
                target_employees_q = Q(EmployeeId=target_emp_id)
            else:
                target_employees_q = Q(pk=current_user.pk)
                if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
                    if current_user.Designation == 'Admin':
                        target_employees_q = Q()
                    else:
                        team_members_q = Q(Reporting_To=current_user)
                        if current_user.Designation == 'HR':
                            target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk)
                        elif current_user.Designation == 'Recruiter':
                            target_employees_q = team_members_q | Q(pk=current_user.pk)

            target_employees = EmployeeDataModel.objects.filter(target_employees_q)

            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)

            activities = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date)
            ).filter(
                Q(lead_status='closed') | 
                (Q(lead_status__isnull=True) & Q(client_status='closed'))
            )

            requirement_id = request.GET.get("requirement_id")
            if requirement_id:
                activities = activities.filter(assigned_requirement_id=requirement_id)


            # activities = activities.select_related('current_day_activity__Activity_instance__Employee').order_by('-current_day_activity__Date')
            
            # # Apply search filter
            # if search_query:
            #     activities = activities.filter(
            #         Q(candidate_name__icontains=search_query) |
            #         Q(client_name__icontains=search_query) |
            #         Q(candidate_phone__icontains=search_query) |
            #         Q(client_phone__icontains=search_query)
            #     )
            
            # # Pagination
            # total_count = activities.count()
            # start_index = (page - 1) * page_size
            # end_index = start_index + page_size
            # paginated_activities = activities[start_index:end_index]
            
            # # Serialize data
            # records = []
            # for activity in paginated_activities:
            #     record = {
            #         'id': activity.id,
            #         'lead_status': activity.lead_status,
            #         'closure_reason': activity.closure_reason,
            #     }
                
            #     if activity.candidate_name:
            #         record.update({
            #             'type': 'interview',
            #             'candidate_name': activity.candidate_name,
            #             'candidate_phone': activity.candidate_phone,
            #             'candidate_designation': activity.candidate_designation,
            #             'interview_status': activity.interview_status,
            #         })
            #     elif activity.client_name:
            #         record.update({
            #             'type': 'client',
            #             'client_name': activity.client_name,
            #             'client_phone': activity.client_phone,
            #             'client_enquire_purpose': activity.client_enquire_purpose,
            #             'client_status': activity.client_status,
            #         })
                
            #     records.append(record)
            
            # return Response({
            #     # "activities": records,
            #     "results": records, #17/4/2026
            #     "total_count": total_count,
            #     "page": page,
            #     "page_size": page_size,
            #     "total_pages": (total_count + page_size - 1) // page_size
            # }, status=status.HTTP_200_OK)




            activities = activities.select_related(
                'current_day_activity__Activity_instance__Employee',
                'current_day_activity__Activity_instance__activity_assigned_by'
            ).order_by('-current_day_activity__Date')

            return _paginate_and_serialize(request, activities)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#17/4/2026
class RequirementPerformanceView(APIView):
    """
    Get paginated requirement performance metrics.
    Groups non-staged activities by assigned_requirement and calculates totals.
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date")
            end_date_str = request.GET.get("end_date")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            # Role-based filtering
            if current_user.Designation == 'Admin':
                target_employees = EmployeeDataModel.objects.all()
            elif current_user.Designation in ['HR', 'Recruiter']:
                team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
                target_employees = team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
            else:
                target_employees = EmployeeDataModel.objects.filter(pk=current_user.pk)
            
            # Date range filtering
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            # Get base queryset (exclude staged)
            base_qs = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date),
                assigned_requirement__isnull=False
            ).exclude(lead_status='staged')
            
            # Aggregate by requirement
            breakdown_qs = base_qs.values(
                'assigned_requirement',
                'assigned_requirement__requirement__pk',
                'assigned_requirement__requirement__client__client_name',
                'assigned_requirement__requirement__job_title',
                'assigned_requirement__position_count',
            ).annotate(
                total_calls=Count('id'),
                successful_outcomes=Count('id', filter=Q(interview_status='joined'))
            )
            
            # Apply search filter (on aggregated results)
            if search_query:
                breakdown_qs = breakdown_qs.filter(
                    Q(assigned_requirement__requirement__job_title__icontains=search_query) |
                    Q(assigned_requirement__requirement__client__client_name__icontains=search_query)
                )
            
            # Pagination
            total_count = breakdown_qs.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_breakdown = list(breakdown_qs[start_index:end_index])
            
            results = []
            for item in paginated_breakdown:
                results.append({
                    'assigned_requirement': item['assigned_requirement'],
                    'requirement_name': f"[ID: {item['assigned_requirement__requirement__pk']}] {item['assigned_requirement__requirement__client__client_name']} - {item['assigned_requirement__requirement__job_title']}",
                    'client_name': item['assigned_requirement__requirement__client__client_name'],
                    'job_title': item['assigned_requirement__requirement__job_title'],
                    'total_calls': item['total_calls'],
                    'successful_outcomes': item['successful_outcomes'],
                    'position_count': item['assigned_requirement__position_count'] or 0
                })
            
            return Response({
                "results": results,
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size,
                "next": page + 1 if end_index < total_count else None,
                "previous": page - 1 if page > 1 else None
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#26/05/2026
class IncomingLeadsView(APIView):
    """
    Get all incoming candidate leads (NewDailyAchivesModel with activity_name = 'interview_calls')
    with pagination, filtering, search, and sorting.
    """
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            # Additional column-level filters
            status_filter = request.GET.get('status', '').strip()
            source_filter = request.GET.get('source', '').strip()
            assigned_to_filter = request.GET.get('assigned_to', '').strip()
            date_filter = request.GET.get('date', '').strip()
            sort_by = request.GET.get('sort_by', '-Created_Date').strip()

            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

            # Core filtering: only show interview call leads (candidates)
            queryset = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Activity__activity_name="interview_calls"
            )

            # Role-Based Filtering
            if current_user.Designation not in ['Admin', 'HR']:
                # Recruiters/Employees only see their assigned leads
                queryset = queryset.filter(
                    current_day_activity__Activity_instance__Employee=current_user
                )

            # Apply date range filtering (Default: this_month)
            filter_type = request.GET.get("filter_type", "this_month").strip()
            start_date_str = request.GET.get("start_date", "").strip()
            end_date_str = request.GET.get("end_date", "").strip()

            today = timezone.localdate()
            start_date = None
            end_date = None

            if filter_type == 'today':
                start_date = today
                end_date = today
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = today
            elif filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today
            elif filter_type == 'prev_month':
                first_day_of_this_month = today.replace(day=1)
                last_day_of_prev_month = first_day_of_this_month - timedelta(days=1)
                start_date = last_day_of_prev_month.replace(day=1)
                end_date = last_day_of_prev_month
            elif filter_type == 'custom' and start_date_str and end_date_str:
                from datetime import datetime
                try:
                    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            if start_date and end_date:
                import datetime as dt
                tz = timezone.get_current_timezone()
                start_datetime = timezone.make_aware(dt.datetime.combine(start_date, dt.time.min), tz)
                end_datetime = timezone.make_aware(dt.datetime.combine(end_date, dt.time.max), tz)
                queryset = queryset.filter(Created_Date__range=(start_datetime, end_datetime))

            # Apply Global Search across name, candidate id, source, position, status, handled by, assigned by, remarks, and follow-up notes/date
            if search_query:
                # 1. Candidate ID integer filter
                id_filter = Q()
                if search_query.isdigit():
                    id_filter = Q(id=int(search_query))

                # 2. Map human-readable status searches to database choices
                status_query = search_query.lower()
                status_mappings = {
                    "interview attended": "walkin",
                    "attended": "walkin",
                    "joined": "joined",
                    "offer": "offer",
                    "offered": "offer",
                    "rejected": "rejected",
                    "consider to client": "to_client",
                    "to client": "to_client",
                    "client": "to_client",
                    "interview scheduled": "interview_scheduled",
                    "scheduled": "interview_scheduled",
                    "call not picked": "call_notpicked",
                    "not picked": "call_notpicked",
                    "disconnect": "dis_connect",
                    "will revert back": "will_revert_back",
                    "revert": "will_revert_back"
                }
                matched_codes = [code for label, code in status_mappings.items() if status_query in label]
                status_filter_q = Q(interview_status__in=matched_codes) if matched_codes else Q()

                # 3. Parse and search follow-up dates (expected_date)
                date_q = Q()
                from datetime import datetime
                for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
                    try:
                        parsed_date = datetime.strptime(search_query, date_format).date()
                        date_q = Q(followups__expected_date=parsed_date)
                        break
                    except ValueError:
                        pass

                queryset = queryset.filter(
                    Q(candidate_name__icontains=search_query) |
                    id_filter |
                    Q(source__icontains=search_query) |
                    Q(candidate_designation__icontains=search_query) |
                    Q(position__icontains=search_query) |
                    status_filter_q |
                    Q(current_day_activity__Activity_instance__Employee__Name__icontains=search_query) |
                    Q(current_day_activity__Activity_instance__activity_assigned_by__Name__icontains=search_query) |
                    Q(interview_call_remarks__icontains=search_query) |
                    Q(followups__notes__icontains=search_query) |
                    Q(candidate_email__icontains=search_query) |
                    Q(candidate_phone__icontains=search_query) |
                    date_q
                ).distinct()

            # Apply specific column filters
            if status_filter:
                queryset = queryset.filter(interview_status=status_filter)
            if source_filter:
                queryset = queryset.filter(source__icontains=source_filter)
            if assigned_to_filter:
                queryset = queryset.filter(current_day_activity__Activity_instance__Employee__EmployeeId=assigned_to_filter)
            if date_filter:
                try:
                    from datetime import datetime
                    import datetime as dt
                    spec_date = datetime.strptime(date_filter, "%Y-%m-%d").date()
                    tz = timezone.get_current_timezone()
                    spec_start = timezone.make_aware(dt.datetime.combine(spec_date, dt.time.min), tz)
                    spec_end = timezone.make_aware(dt.datetime.combine(spec_date, dt.time.max), tz)
                    queryset = queryset.filter(Created_Date__range=(spec_start, spec_end))
                except ValueError:
                    pass

            # Apply sorting
            if sort_by in ['Created_Date', '-Created_Date', 'candidate_name', '-candidate_name', 'interview_status', '-interview_status']:
                queryset = queryset.order_by(sort_by)
            else:
                queryset = queryset.order_by('-Created_Date')

            # Pagination
            total_count = queryset.count()
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_queryset = queryset[start_index:end_index]

            # Serialize data
            serializer = NewDailyAchivesModelSerializer(paginated_queryset, many=True)
            
            # Enrich representation with employee details
            results = []
            for item in serializer.data:
                try:
                    obj = NewDailyAchivesModel.objects.get(id=item['id'])
                    handled_by_name = "Unknown"
                    handled_by_id = None
                    assigned_by_name = "System"
                    assigned_by_id = None
                    
                    if obj.current_day_activity and obj.current_day_activity.Activity_instance:
                        recruiter = obj.current_day_activity.Activity_instance.Employee
                        if recruiter:
                            handled_by_name = recruiter.Name
                            handled_by_id = recruiter.EmployeeId
                        
                        assigner = obj.current_day_activity.Activity_instance.activity_assigned_by
                        if assigner:
                            assigned_by_name = assigner.Name
                            assigned_by_id = assigner.EmployeeId
                except Exception:
                    handled_by_name = "Unknown"
                    handled_by_id = None
                    assigned_by_name = "System"
                    assigned_by_id = None
                
                # Fetch latest pending follow-up details
                latest_pending_followup = FollowUpModel.objects.filter(
                    activity_record=obj,
                    status='pending'
                ).order_by('-expected_date', '-expected_time').first()
                
                if latest_pending_followup:
                    item['next_followup_date'] = latest_pending_followup.expected_date.strftime('%Y-%m-%d')
                    item['next_followup_time'] = latest_pending_followup.expected_time.strftime('%H:%M')
                    item['next_followup_notes'] = latest_pending_followup.notes
                    item['next_followup_id'] = latest_pending_followup.id
                else:
                    item['next_followup_date'] = None
                    item['next_followup_time'] = None
                    item['next_followup_notes'] = None
                    item['next_followup_id'] = None

                item['handled_by'] = handled_by_name
                item['handled_by_id'] = handled_by_id
                item['assigned_by'] = assigned_by_name
                item['assigned_by_id'] = assigned_by_id
                results.append(item)

            return Response({
                "results": results,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            lead_ids = request.data.get("lead_ids", [])
            assign_to_emp_id = request.data.get("assign_to_emp_id")
            login_emp_id = request.data.get("login_emp_id")

            if not lead_ids or not assign_to_emp_id or not login_emp_id:
                return Response({"error": "lead_ids, assign_to_emp_id, and login_emp_id are required."}, status=status.HTTP_400_BAD_REQUEST)

            # Check permissions: only Admin or HR can reassign leads
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Logged-in user not found."}, status=status.HTTP_404_NOT_FOUND)

            if current_user.Designation not in ['Admin', 'HR']:
                return Response({"error": "Only Admin or HR can reassign leads."}, status=status.HTTP_403_FORBIDDEN)

            try:
                target_recruiter = EmployeeDataModel.objects.get(EmployeeId=assign_to_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Target recruiter not found."}, status=status.HTTP_404_NOT_FOUND)

            # Get or create active activity context for target recruiter
            today = timezone.localdate()
            activity_list = ActivityListModel.objects.filter(activity_name="interview_calls").first()
            if not activity_list:
                return Response({"error": "Activity type 'interview_calls' does not exist."}, status=status.HTTP_400_BAD_REQUEST)

            target_activity, _ = NewActivityModel.objects.get_or_create(
                Activity=activity_list,
                Employee=target_recruiter,
                Activity_assigned_Date__month=today.month,
                Activity_assigned_Date__year=today.year,
                defaults={
                    'Activity_assigned_Date': today,
                    'activity_assigned_by': current_user,
                    'targets': 0
                }
            )

            target_day_activity, _ = MonthAchivesListModel.objects.get_or_create(
                Activity_instance=target_activity,
                Date=today,
                defaults={'achieved': 0}
            )

            # Track unique previous day activities to recalculate achievements later
            prev_day_activities = set()

            reassigned_count = 0
            for lead_id in lead_ids:
                try:
                    lead = NewDailyAchivesModel.objects.get(pk=lead_id)
                    #4/6/26
                    current_owner = lead.current_day_activity.Activity_instance.Employee if (lead.current_day_activity and lead.current_day_activity.Activity_instance) else None
                    
                    if current_owner == target_recruiter:
                        # Already assigned to this recruiter, skip
                        continue
                    
                    # Determine whether we should shift the record or clone it
                    should_shift = False
                    if not lead.current_day_activity or not lead.current_day_activity.Activity_instance:
                        should_shift = True
                    else:
                        # Shift only if owned by Admin/HR, and hasn't been assigned/worked on yet
                        if current_owner.Designation in ['Admin', 'HR'] and lead.sourcing_channel != 'assigned' and not lead.interview_status:
                            should_shift = True
                    
                    if should_shift:
                        if lead.current_day_activity:
                            prev_day_activities.add(lead.current_day_activity)
                        
                        # Shift assignment to target recruiter
                        lead.current_day_activity = target_day_activity
                        lead.sourcing_channel = 'assigned'
                        lead.save()
                        #4/6/26
                        reassigned_count += 1
                    else:
                        # Clone the lead for the target recruiter
                        # First check if this candidate is already assigned to the target recruiter on this day activity
                        exists = False
                        if lead.candidate_phone:
                            exists = NewDailyAchivesModel.objects.filter(
                                current_day_activity=target_day_activity,
                                candidate_phone=lead.candidate_phone
                            ).exists()
                        elif lead.candidate_email:
                            exists = NewDailyAchivesModel.objects.filter(
                                current_day_activity=target_day_activity,
                                candidate_email=lead.candidate_email
                            ).exists()
                        else:
                            exists = NewDailyAchivesModel.objects.filter(
                                current_day_activity=target_day_activity,
                                candidate_name=lead.candidate_name
                            ).exists()

                        if not exists:
                            NewDailyAchivesModel.objects.create(
                                current_day_activity=target_day_activity,
                                sourcing_channel='assigned',
                                candidate_name=lead.candidate_name,
                                candidate_phone=lead.candidate_phone,
                                candidate_email=lead.candidate_email,
                                candidate_location=lead.candidate_location,
                                candidate_designation=lead.candidate_designation,
                                candidate_current_status=lead.candidate_current_status,
                                candidate_experience=lead.candidate_experience,
                                industries_worked=lead.industries_worked,
                                source=lead.source,
                                expected_ctc=lead.expected_ctc,
                                current_ctc=lead.current_ctc,
                                DOJ=lead.DOJ,
                                have_laptop=lead.have_laptop,
                                candidate_for=lead.candidate_for,
                                position=lead.position,
                                url=lead.url,
                                job_post_remarks=lead.job_post_remarks,
                                assigned_requirement=lead.assigned_requirement,
                                lead_status='active',
                                interview_status=None,  # Reset status so they start fresh
                                interview_scheduled_date=None,
                                interview_walkin_date=None,
                                interview_call_remarks=None
                            )
                            reassigned_count += 1
                except NewDailyAchivesModel.DoesNotExist:
                    pass

            # Recalculate achievement counts
            for prev_act in prev_day_activities:
                prev_act.achieved = NewDailyAchivesModel.objects.filter(
                    current_day_activity=prev_act
                ).exclude(lead_status='staged').count()
                prev_act.save()

            target_day_activity.achieved = NewDailyAchivesModel.objects.filter(
                current_day_activity=target_day_activity
            ).exclude(lead_status='staged').count()
            target_day_activity.save()

            return Response({
                "message": f"Successfully assigned {reassigned_count} leads to {target_recruiter.Name}.", #4/6/26
                "reassigned_count": reassigned_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ======================================================
# COMPREHENSIVE ANALYTICS DRILLDOWN VIEWS (28/05/2026)
# ======================================================

def _get_base_interview_queryset(request):
    """
    Shared helper: Returns (current_user, base interview queryset, error_response).
    Handles auth, role-based scoping, date filtering.
    """
    login_emp_id = request.GET.get("login_emp_id")
    filter_type = request.GET.get("filter_type", "this_month")
    start_date_str = request.GET.get("start_date", "")
    end_date_str = request.GET.get("end_date", "")
    target_emp_id = request.GET.get("target_emp_id", "")

    if not login_emp_id:
        return None, None, Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
    except EmployeeDataModel.DoesNotExist:
        return None, None, Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)

    # Role-based scoping
    if target_emp_id:
        target_employees_q = Q(EmployeeId=target_emp_id)
    else:
        target_employees_q = Q(pk=current_user.pk)
        if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
            if current_user.Designation == 'Admin':
                target_employees_q = Q()
            else:
                team_members_q = Q(Reporting_To=current_user)
                if current_user.Designation == 'HR':
                    target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk)
                elif current_user.Designation == 'Recruiter':
                    target_employees_q = team_members_q | Q(pk=current_user.pk)

    target_employees = EmployeeDataModel.objects.filter(target_employees_q)

    # Date range
    start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)

    base_qs = NewDailyAchivesModel.objects.filter(
        current_day_activity__Activity_instance__Employee__in=target_employees,
        current_day_activity__Date__range=(start_date, end_date),
        current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
    ).exclude(lead_status='staged').select_related(
        'current_day_activity__Activity_instance__Employee',
        'current_day_activity__Activity_instance__activity_assigned_by'
    ).order_by('-Created_Date')

    requirement_id = request.GET.get("requirement_id")
    if requirement_id:
        base_qs = base_qs.filter(assigned_requirement_id=requirement_id)

    return current_user, base_qs, None



def _paginate_and_serialize(request, queryset):
    """Paginate queryset and return serialized candidate records."""
    page = int(request.GET.get('page', 1))
    page_size = int(request.GET.get('page_size', 10))
    search_query = request.GET.get('search', '').strip()

    if search_query:
        queryset = queryset.filter(
            Q(candidate_name__icontains=search_query) |
            Q(candidate_phone__icontains=search_query) |
            Q(candidate_email__icontains=search_query) |
            Q(source__icontains=search_query) |
            Q(candidate_designation__icontains=search_query) |
            Q(interview_call_remarks__icontains=search_query) |
            Q(client_name__icontains=search_query) |
            Q(client_phone__icontains=search_query) |
            Q(client_email__icontains=search_query)
        )

    total_count = queryset.count()
    start_index = (page - 1) * page_size
    paginated = queryset[start_index:start_index + page_size]

    serializer = NewDailyAchivesModelSerializer(paginated, many=True)
    results = []
    for item in serializer.data:
        try:
            obj = NewDailyAchivesModel.objects.get(id=item['id'])
            handled_by_name = "Unknown"
            handled_by_id = None
            if obj.current_day_activity and obj.current_day_activity.Activity_instance:
                recruiter = obj.current_day_activity.Activity_instance.Employee
                if recruiter:
                    handled_by_name = recruiter.Name
                    handled_by_id = recruiter.EmployeeId
        except Exception:
            handled_by_name = "Unknown"
            handled_by_id = None
        item['handled_by'] = handled_by_name
        item['handled_by_id'] = handled_by_id
        results.append(item)

    return Response({
        "results": results,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size
    }, status=status.HTTP_200_OK)


# ----- Section 1: Profiles Added -----

class ProfilesWalkinView(APIView):
    """Walk-in / Direct profiles (source contains 'direct', 'walkin')"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.exclude(sourcing_channel='bulk_upload').filter(
                Q(sourcing_channel='direct') | (
                    (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                        Q(source__icontains='direct') | Q(source__icontains='walkin') |
                        Q(source__icontains='walk-in') | Q(source__icontains='walk in')
                    )
                )
            )
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilesWebsiteView(APIView):
    """Website / API sourced profiles"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.exclude(sourcing_channel='bulk_upload').filter(
                Q(sourcing_channel='website') | (
                    (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                        Q(source__icontains='website') | Q(source__icontains='linkedin') |
                        Q(source__icontains='naukri') | Q(source__icontains='indeed') |
                        Q(source__icontains='portal') | Q(source__icontains='online') |
                        Q(source__icontains='api')
                    )
                )
            ).exclude(
                Q(source__icontains='crm') | Q(source__icontains='facebook') | Q(source__icontains='meta') | Q(source__icontains='social')
            )
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilesCrmView(APIView):
    """CRM sourced profiles"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.exclude(sourcing_channel='bulk_upload').filter(
                Q(sourcing_channel='crm') | (
                    (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & Q(source__icontains='crm')
                )
            )
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilesFacebookView(APIView):
    """Facebook / Social sourced profiles"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.exclude(sourcing_channel='bulk_upload').filter(
                Q(sourcing_channel='facebook') | (
                    (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                        Q(source__icontains='facebook') | Q(source__icontains='meta') | Q(source__icontains='social')
                    )
                )
            )
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilesSelfView(APIView):
    """Self-added profiles (employee manually added)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.exclude(sourcing_channel='bulk_upload').filter(
                Q(sourcing_channel='self_adding') | (
                    (Q(sourcing_channel__isnull=True) | Q(sourcing_channel='')) & (
                        Q(source__icontains='self') | Q(source__icontains='manual') | Q(source__iexact='')
                    )
                )
            ).exclude(
                Q(source__icontains='crm') | Q(source__icontains='facebook') | Q(source__icontains='meta') | Q(source__icontains='social')
            )
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilesBulkView(APIView):
    """Bulk-uploaded profiles (lead_status='staged')"""
    def get(self, request):
        try:
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date", "")
            end_date_str = request.GET.get("end_date", "")
            target_emp_id = request.GET.get("target_emp_id", "")
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            if target_emp_id:
                target_employees_q = Q(EmployeeId=target_emp_id)
            else:
                target_employees_q = Q(pk=current_user.pk)
                if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
                    if current_user.Designation == 'Admin':
                        target_employees_q = Q()
                    else:
                        team_members_q = Q(Reporting_To=current_user)
                        if current_user.Designation == 'HR':
                            target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk)
                        elif current_user.Designation == 'Recruiter':
                            target_employees_q = team_members_q | Q(pk=current_user.pk)

            target_employees = EmployeeDataModel.objects.filter(target_employees_q)
            # Date range
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            qs = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date),
                current_day_activity__Activity_instance__Activity__activity_name='interview_calls'
            ).filter(
                Q(sourcing_channel='bulk_upload') | Q(lead_status='staged')
            ).order_by('-Created_Date')
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProfilesAssignedView(APIView):
    """Profiles assigned to a recruiter (both candidate applications and sourced daily leads)"""
    def get(self, request):
        try:
#             _, qs, err = _get_base_interview_queryset(request)
#             if err: return err
#             qs = qs.filter(sourcing_channel='assigned')
#             return _paginate_and_serialize(request, qs)            
            # 6/6/26
            from .models import ScreeningAssigningModel, EmployeeDataModel, NewDailyAchivesModel, CandidateApplicationModel, FollowUpModel
            from django.db.models import Q
            
            login_emp_id = request.GET.get("login_emp_id")
            filter_type = request.GET.get("filter_type", "this_month")
            start_date_str = request.GET.get("start_date", "")
            end_date_str = request.GET.get("end_date", "")
            target_emp_id = request.GET.get("target_emp_id", "")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            search_query = request.GET.get('search', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
                
            # Date range
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            # Scoping target employees
            if target_emp_id:
                target_employees_q = Q(EmployeeId=target_emp_id)
            else:
                target_employees_q = Q(pk=current_user.pk)
                if current_user.Designation in ['Admin', 'HR', 'Recruiter']:
                    if current_user.Designation == 'Admin':
                        target_employees_q = Q()
                    else:
                        team_members_q = Q(Reporting_To=current_user)
                        if current_user.Designation == 'HR':
                            target_employees_q = team_members_q | Q(Designation='Recruiter') | Q(pk=current_user.pk)
                        elif current_user.Designation == 'Recruiter':
                            target_employees_q = team_members_q | Q(pk=current_user.pk)
                            
            target_employees = EmployeeDataModel.objects.filter(target_employees_q)
            
            # 1. Fetch Sourced Leads (NewDailyAchivesModel)
            lead_qs = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date),
                current_day_activity__Activity_instance__Activity__activity_name='interview_calls',
                sourcing_channel='assigned'
            ).exclude(lead_status='staged').select_related(
                'current_day_activity__Activity_instance__Employee',
                'current_day_activity__Activity_instance__activity_assigned_by'
            )
            
            # 2. Fetch Candidate Applications (ScreeningAssigningModel)
            import datetime as dt
            tz = timezone.get_current_timezone()
            start_datetime = timezone.make_aware(dt.datetime.combine(start_date, dt.time.min), tz)
            end_datetime = timezone.make_aware(dt.datetime.combine(end_date, dt.time.max), tz)
            
            cand_assign_qs = ScreeningAssigningModel.objects.filter(
                Recruiter__in=target_employees,
                Date_of_assigned__range=(start_datetime, end_datetime)
            ).select_related('Candidate', 'Recruiter', 'AssignedBy')
            
            # Apply Search Filtering
            if search_query:
                lead_q = Q(candidate_name__icontains=search_query) | \
                         Q(candidate_email__icontains=search_query) | \
                         Q(candidate_phone__icontains=search_query) | \
                         Q(source__icontains=search_query) | \
                         Q(candidate_designation__icontains=search_query) | \
                         Q(position__icontains=search_query) | \
                         Q(interview_call_remarks__icontains=search_query)
                lead_qs = lead_qs.filter(lead_q)
                
                cand_q = Q(Candidate__FirstName__icontains=search_query) | \
                         Q(Candidate__LastName__icontains=search_query) | \
                         Q(Candidate__Email__icontains=search_query) | \
                         Q(Candidate__PrimaryContact__icontains=search_query) | \
                         Q(Candidate__JobPortalSource__icontains=search_query) | \
                         Q(Candidate__AppliedDesignation__icontains=search_query)
                cand_assign_qs = cand_assign_qs.filter(cand_q)
                
            # Build Combined Lightweight items
            combined_items = []
            
            # Sourced leads
            for l in lead_qs:
                handled_by_name = "Unknown"
                handled_by_id = None
                assigned_by_name = "System"
                assigned_by_id = None
                if l.current_day_activity and l.current_day_activity.Activity_instance:
                    recruiter = l.current_day_activity.Activity_instance.Employee
                    if recruiter:
                        handled_by_name = recruiter.Name
                        handled_by_id = recruiter.EmployeeId
                    assigner = l.current_day_activity.Activity_instance.activity_assigned_by
                    if assigner:
                        assigned_by_name = assigner.Name
                        assigned_by_id = assigner.EmployeeId
                        
                next_f_date = None
                next_f_time = None
                next_f_notes = None
                latest_pending_followup = FollowUpModel.objects.filter(
                    activity_record=l,
                    status='pending'
                ).order_by('-expected_date', '-expected_time').first()
                if latest_pending_followup:
                    next_f_date = latest_pending_followup.expected_date.strftime('%Y-%m-%d')
                    next_f_time = latest_pending_followup.expected_time.strftime('%H:%M')
                    next_f_notes = latest_pending_followup.notes

                combined_items.append({
                    'id': l.id,
                    'lead_type': 'sourced',
                    'original_id': l.id,
                    'sort_date': l.Created_Date,
                    'candidate_name': l.candidate_name or "N/A",
                    'candidate_email': l.candidate_email or "—",
                    'candidate_phone': l.candidate_phone or "—",
                    'Created_Date': l.Created_Date,
                    'source': l.source or "N/A",
                    'candidate_designation': l.candidate_designation or l.position or "N/A",
                    'interview_status': l.interview_status or "Newlead",
                    'interview_scheduled_date': l.interview_scheduled_date,
                    'handled_by': handled_by_name,
                    'handled_by_id': handled_by_id,
                    'assigned_by': assigned_by_name,
                    'assigned_by_id': assigned_by_id,
                    'interview_call_remarks': l.interview_call_remarks or "—",
                    'next_followup_date': next_f_date,
                    'next_followup_time': next_f_time,
                    'next_followup_notes': next_f_notes
                })
                
            # Candidate assignments
            from .models import InterviewScheduleStatusModel
            for ca in cand_assign_qs:
                c = ca.Candidate
                if not c:
                    continue
                # Fetch interview date
                int_date = None
                latest_int_status = InterviewScheduleStatusModel.objects.filter(
                    InterviewScheduledCandidate=c
                ).select_related('interviewe').order_by('-id').first()
                if latest_int_status and latest_int_status.interviewe:
                    int_date = latest_int_status.interviewe.InterviewDate
                    
                # Fetch follow-up details for the candidate assignment
                next_f_date = None
                next_f_time = None
                next_f_notes = None
                candidate_lead = NewDailyAchivesModel.objects.filter(url=f"candidate:{c.id}").first()
                if candidate_lead:
                    latest_pending_followup = FollowUpModel.objects.filter(
                        activity_record=candidate_lead,
                        status='pending'
                    ).order_by('-expected_date', '-expected_time').first()
                    if latest_pending_followup:
                        next_f_date = latest_pending_followup.expected_date.strftime('%Y-%m-%d')
                        next_f_time = latest_pending_followup.expected_time.strftime('%H:%M')
                        next_f_notes = latest_pending_followup.notes
                    
                combined_items.append({
                    'id': f"c_{c.id}",
                    'lead_type': 'candidate',
                    'original_id': c.id,
                    'sort_date': ca.Date_of_assigned,
                    'candidate_name': f"{c.FirstName} {c.LastName or ''}".strip(),
                    'candidate_email': c.Email or "—",
                    'candidate_phone': c.PrimaryContact or "—",
                    'Created_Date': ca.Date_of_assigned,
                    'source': c.JobPortalSource or "N/A",
                    'candidate_designation': c.AppliedDesignation or "N/A",
                    'interview_status': c.Telephonic_Round_Status or "Pending",
                    'interview_scheduled_date': int_date,
                    'handled_by': ca.Recruiter.Name if ca.Recruiter else "Unknown",
                    'handled_by_id': ca.Recruiter.EmployeeId if ca.Recruiter else None,
                    'assigned_by': ca.AssignedBy.Name if ca.AssignedBy else "System",
                    'assigned_by_id': ca.AssignedBy.EmployeeId if ca.AssignedBy else None,
                    'interview_call_remarks': c.Other_jps or "—",
                    'next_followup_date': next_f_date,
                    'next_followup_time': next_f_time,
                    'next_followup_notes': next_f_notes
                })
                
            # Sort combined results
            combined_items.sort(key=lambda x: x['sort_date'] or timezone.now(), reverse=True)
            
            total_count = len(combined_items)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            page_items = combined_items[start_index:end_index]
            
            return Response({
                "results": page_items,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----- Section 2: Calls Made -----

class CallsNewView(APIView):
    """New calls (status set, no prior completed follow-ups)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            completed_ids = FollowUpModel.objects.filter(
                activity_record__in=qs, status='completed'
            ).values_list('activity_record_id', flat=True)
            qs = qs.filter(interview_status__isnull=False).exclude(interview_status='').exclude(id__in=completed_ids)
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CallsFollowupView(APIView):
    """Completed follow-up calls (interview type)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            followup_ids = FollowUpModel.objects.filter(
                activity_record__in=qs, status='completed', follow_up_type='interview'
            ).values_list('activity_record_id', flat=True)
            qs = qs.filter(id__in=followup_ids)
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CallsNotPickedView(APIView):
    """Calls where candidate didn't pick up"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(interview_status='call_notpicked')
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----- Section 3: Interview Pipeline -----

class InterviewScheduledTodayView(APIView):
    """Interviews scheduled for today"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            today_local = timezone.localdate()
            import datetime as dt
            tz = timezone.get_current_timezone()
            today_start = timezone.make_aware(dt.datetime.combine(today_local, dt.time.min), tz)
            today_end = timezone.make_aware(dt.datetime.combine(today_local, dt.time.max), tz)
            qs = qs.filter(interview_status='interview_scheduled', interview_scheduled_date__range=(today_start, today_end))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InterviewScheduledTomorrowView(APIView):
    """Interviews scheduled for tomorrow"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            tomorrow_local = timezone.localdate() + timedelta(days=1)
            import datetime as dt
            tz = timezone.get_current_timezone()
            tomorrow_start = timezone.make_aware(dt.datetime.combine(tomorrow_local, dt.time.min), tz)
            tomorrow_end = timezone.make_aware(dt.datetime.combine(tomorrow_local, dt.time.max), tz)
            qs = qs.filter(interview_status='interview_scheduled', interview_scheduled_date__range=(tomorrow_start, tomorrow_end))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InterviewScheduledFutureView(APIView):
    """Interviews scheduled for beyond tomorrow"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            beyond_local = timezone.localdate() + timedelta(days=1)
            import datetime as dt
            tz = timezone.get_current_timezone()
            beyond_end = timezone.make_aware(dt.datetime.combine(beyond_local, dt.time.max), tz)
            qs = qs.filter(interview_status='interview_scheduled', interview_scheduled_date__gt=beyond_end)
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InterviewAttendedView(APIView):
    """Candidates who attended interview (walkin)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(Q(interview_walkin_date__isnull=False) | Q(interview_status='walkin'))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----- Section 4: Client Requirement Calls -----

class ClientReqTotalView(APIView):
    """All leads tagged to a client requirement"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(assigned_requirement__isnull=False)
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientReqNewView(APIView):
    """New requirement calls (status not set or empty, and active)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(
                assigned_requirement__isnull=False,
                lead_status='active'
            ).filter(Q(interview_status__isnull=True) | Q(interview_status=''))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientReqFollowupView(APIView):
    """Follow-up calls on requirement-tagged leads (lead_status='follow_up')"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(
                assigned_requirement__isnull=False,
                lead_status='follow_up'
            ).exclude(lead_status__in=['closed', 'rejected']).exclude(interview_status__in=['to_client', 'offer', 'joined'])
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientReqProspectView(APIView):
    """Requirement leads in active pipeline (lead_status='active' and contacted)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(
                assigned_requirement__isnull=False,
                lead_status='active',
                interview_status__in=['call_notpicked', 'dis_connect', 'will_revert_back', 'interview_scheduled', 'walkin']
            ).exclude(lead_status__in=['closed', 'rejected'])
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientReqConvertedView(APIView):
    """Requirement leads forwarded to client, offered, or joined"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(
                assigned_requirement__isnull=False,
                interview_status__in=['to_client', 'offer', 'joined']
            ).exclude(lead_status__in=['closed', 'rejected'])
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ClientReqClosedView(APIView):
    """Closed/Rejected requirement leads"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(
                assigned_requirement__isnull=False,
                lead_status__in=['closed', 'rejected']
            )
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ----- Section 5: Final Status -----

class FinalOfferedView(APIView):
    """Offered candidates"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(interview_status='offer')
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinalJoinedView(APIView):
    """Joined candidates"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(interview_status='joined')
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinalNotJoinedView(APIView):
    """Offered but didn't join (offer + lead closed)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(interview_status='offer', lead_status='closed')
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinalRejectedByUsView(APIView):
    """Rejected by the company"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(Q(interview_status='rejected') | Q(rejection_type='emp_rejected'))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class FinalRejectedByCandidateView(APIView):
    """Rejected by the candidate"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(Q(interview_status='Rejected_by_Candidate') | Q(rejection_type='candidate_rejected'))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PendingWalkinsView(APIView):
    """Walk-ins pending (scheduled for today or future)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            today_local = timezone.localdate()
            import datetime as dt
            tz = timezone.get_current_timezone()
            today_start = timezone.make_aware(dt.datetime.combine(today_local, dt.time.min), tz)
            qs = qs.filter(interview_status='interview_scheduled', interview_scheduled_date__gte=today_start)
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PendingYetToContactView(APIView):
    """Profiles added but never contacted (no interview_status set)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            qs = qs.filter(Q(interview_status__isnull=True) | Q(interview_status=''))
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#1/6/2026
class InterviewNotAttendedView(APIView):
    """Candidates who were scheduled but didn't attend (date passed, status unchanged)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            today_local = timezone.localdate()
            import datetime as dt
            tz = timezone.get_current_timezone()
            today_start = timezone.make_aware(dt.datetime.combine(today_local, dt.time.min), tz)
            qs = qs.filter(interview_status='interview_scheduled', interview_scheduled_date__lt=today_start)
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InterviewFollowupPendingView(APIView):
    """Interview records with pending follow-ups (implicit or explicit)"""
    def get(self, request):
        try:
            _, qs, err = _get_base_interview_queryset(request)
            if err: return err
            today_local = timezone.localdate()
            import datetime as dt
            tz = timezone.get_current_timezone()
            today_start = timezone.make_aware(dt.datetime.combine(today_local, dt.time.min), tz)
            
            not_attended_ids = qs.filter(
                interview_status='interview_scheduled',
                interview_scheduled_date__lt=today_start
            ).values_list('id', flat=True)
            
            explicit_fup_ids = FollowUpModel.objects.filter(
                activity_record__in=qs,
                status='pending',
                follow_up_type='interview'
            ).values_list('activity_record_id', flat=True)
            
            qs = qs.filter(Q(id__in=not_attended_ids) | Q(id__in=explicit_fup_ids)).distinct()
            return _paginate_and_serialize(request, qs)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#5/6/2026
class UniversalLeadsView(APIView):
    """
    Unified view combining Candidate Applications and Sourced Leads.
    """
    def get(self, request):
        try:
            from .models import CandidateApplicationModel, ScreeningAssigningModel, FollowUpModel, MonthAchivesListModel, NewActivityModel, EmployeeDataModel, InterviewScheduleStatusModel
            
            login_emp_id = request.GET.get("login_emp_id")
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 10))
            tab = request.GET.get('tab', 'all_leads').strip()
            
            search_query = request.GET.get('search', '').strip()
            sort_by = request.GET.get('sort_by', '-Created_Date').strip()
            
            # Column filters
            name_filter = request.GET.get('candidate_name', '').strip()
            email_filter = request.GET.get('candidate_email', '').strip()
            phone_filter = request.GET.get('candidate_phone', '').strip()
            location_filter = request.GET.get('location', '').strip()
            designation_filter = request.GET.get('designation', '').strip()
            source_filter = request.GET.get('source', '').strip()
            status_filter = request.GET.get('interview_status', '').strip()
            experience_filter = request.GET.get('experience', '').strip()
            
            # Additional Global filters
            salary_filter = request.GET.get('salary', '').strip()
            role_filter = request.GET.get('role', '').strip()
            exp_filter = request.GET.get('exp', '').strip()
            fresh_filter = request.GET.get('fresh', '').strip()
            attended_filter = request.GET.get('attended', '').strip()
            
            if not login_emp_id:
                return Response({"error": "login_emp_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Employee not found"}, status=status.HTTP_404_NOT_FOUND)
            
            is_admin_or_hr = current_user.Designation in ['Admin', 'HR']
            has_all_access = (
                getattr(current_user, 'all_applicants_access', False) or 
                getattr(current_user, 'universal_leads_access', False)
            )
            
            # Build base querysets
            candidate_qs = CandidateApplicationModel.objects.all()
            lead_qs = NewDailyAchivesModel.objects.filter(
                current_day_activity__Activity_instance__Activity__activity_name="interview_calls"
            )
            
            # Scope check based on recruiter role
            if not is_admin_or_hr and not has_all_access:
                candidate_qs = candidate_qs.filter(Recruiter__Recruiter=current_user)
                lead_qs = lead_qs.filter(current_day_activity__Activity_instance__Employee=current_user)
            
            # Apply Date Range
            filter_type = request.GET.get("filter_type", "this_month").strip()
            start_date_str = request.GET.get("start_date", "").strip()
            end_date_str = request.GET.get("end_date", "").strip()
            
            start_date, end_date = parse_date_range(filter_type, start_date_str, end_date_str)
            
            import datetime as dt
            tz = timezone.get_current_timezone()
            start_datetime = timezone.make_aware(dt.datetime.combine(start_date, dt.time.min), tz)
            end_datetime = timezone.make_aware(dt.datetime.combine(end_date, dt.time.max), tz)
            
            candidate_qs = candidate_qs.filter(AppliedDate__range=(start_datetime, end_datetime))
            lead_qs = lead_qs.filter(Created_Date__range=(start_datetime, end_datetime))
            
            # Apply Global Search
            if search_query:
                # 1. Candidate Application Search
                cand_q = Q(FirstName__icontains=search_query) | Q(LastName__icontains=search_query) | \
                         Q(Email__icontains=search_query) | Q(PrimaryContact__icontains=search_query) | \
                         Q(Location__icontains=search_query) | Q(AppliedDesignation__icontains=search_query) | \
                         Q(CurrentDesignation__icontains=search_query) | Q(ExpectedSalary__icontains=search_query) | \
                         Q(CurrentCTC__icontains=search_query) | Q(TotalExperience__icontains=search_query) | \
                         Q(JobPortalSource__icontains=search_query)
                
                if "fresh" in search_query.lower():
                    cand_q |= Q(Fresher=True)
                elif "exp" in search_query.lower() or "work" in search_query.lower():
                    cand_q |= Q(Experience=True)
                
                if "attend" in search_query.lower() or "walkin" in search_query.lower() or "walk-in" in search_query.lower():
                    cand_q |= Q(Telephonic_Round_Status="Completed") | Q(Final_Results="walkin")
                
                candidate_qs = candidate_qs.filter(cand_q)
                
                # 2. Sourced Leads Search
                lead_q = Q(candidate_name__icontains=search_query) | Q(candidate_email__icontains=search_query) | \
                         Q(candidate_phone__icontains=search_query) | Q(candidate_location__icontains=search_query) | \
                         Q(candidate_designation__icontains=search_query) | Q(position__icontains=search_query) | \
                         Q(expected_ctc__icontains=search_query) | Q(current_ctc__icontains=search_query) | \
                         Q(candidate_experience__icontains=search_query) | Q(source__icontains=search_query) | \
                         Q(interview_call_remarks__icontains=search_query)
                
                if "fresh" in search_query.lower():
                    lead_q |= Q(candidate_experience__icontains="fresher")
                
                if "attend" in search_query.lower() or "walkin" in search_query.lower() or "walk-in" in search_query.lower():
                    lead_q |= Q(interview_status="walkin")
                
                lead_qs = lead_qs.filter(lead_q)
            
            # Apply Column-wise & Global Filters
            if name_filter:
                candidate_qs = candidate_qs.filter(Q(FirstName__icontains=name_filter) | Q(LastName__icontains=name_filter))
                lead_qs = lead_qs.filter(candidate_name__icontains=name_filter)
            if email_filter:
                candidate_qs = candidate_qs.filter(Email__icontains=email_filter)
                lead_qs = lead_qs.filter(candidate_email__icontains=email_filter)
            if phone_filter:
                candidate_qs = candidate_qs.filter(PrimaryContact__icontains=phone_filter)
                lead_qs = lead_qs.filter(candidate_phone__icontains=phone_filter)
            if location_filter:
                candidate_qs = candidate_qs.filter(Location__icontains=location_filter)
                lead_qs = lead_qs.filter(candidate_location__icontains=location_filter)
            if designation_filter or role_filter:
                r_filter = designation_filter or role_filter
                candidate_qs = candidate_qs.filter(AppliedDesignation__icontains=r_filter)
                lead_qs = lead_qs.filter(Q(candidate_designation__icontains=r_filter) | Q(position__icontains=r_filter))
            if source_filter:
                candidate_qs = candidate_qs.filter(JobPortalSource__icontains=source_filter)
                lead_qs = lead_qs.filter(source__icontains=source_filter)
            if status_filter:
                candidate_qs = candidate_qs.filter(Telephonic_Round_Status__icontains=status_filter)
                lead_qs = lead_qs.filter(interview_status__icontains=status_filter)
            if experience_filter or exp_filter:
                e_filter = experience_filter or exp_filter
                candidate_qs = candidate_qs.filter(TotalExperience__icontains=e_filter)
                lead_qs = lead_qs.filter(candidate_experience__icontains=e_filter)
            if salary_filter:
                candidate_qs = candidate_qs.filter(Q(ExpectedSalary__icontains=salary_filter) | Q(CurrentCTC__icontains=salary_filter))
                lead_qs = lead_qs.filter(Q(expected_ctc__icontains=salary_filter) | Q(current_ctc__icontains=salary_filter))
            if fresh_filter:
                fresh_val = fresh_filter.lower()
                if fresh_val == 'fresher':
                    candidate_qs = candidate_qs.filter(Fresher=True)
                    lead_qs = lead_qs.filter(Q(candidate_experience__icontains="fresher") | Q(candidate_current_status__icontains="fresher"))
                elif fresh_val == 'experience':
                    candidate_qs = candidate_qs.filter(Experience=True)
                    lead_qs = lead_qs.filter(Q(candidate_current_status__icontains="experience") | ~Q(candidate_experience__icontains="fresher"))
            if attended_filter:
                att_val = attended_filter.lower()
                if att_val == 'attended':
                    candidate_qs = candidate_qs.filter(Q(Telephonic_Round_Status="Completed") | Q(Final_Results="walkin"))
                    lead_qs = lead_qs.filter(interview_status="walkin")
                elif att_val == 'not_attended':
                    candidate_qs = candidate_qs.exclude(Q(Telephonic_Round_Status="Completed") | Q(Final_Results="walkin"))
                    lead_qs = lead_qs.exclude(interview_status="walkin")
            
            # Select correct data sets based on tab
            if tab == 'applylist':
                candidate_qs = candidate_qs.filter(Telephonic_Round_Status__in=['Pending', 'Assigned'])
                lead_qs = lead_qs.none()
            elif tab == 'total_applications':
                lead_qs = lead_qs.none()
            elif tab == 'leads':
                candidate_qs = candidate_qs.none()
            
            # Get lightweight lists for sorting and paginating
            # For candidates:
            cand_list = []
            for c_id, app_date, f_name, l_name, status_val in candidate_qs.values_list('id', 'AppliedDate', 'FirstName', 'LastName', 'Telephonic_Round_Status'):
                cand_list.append({
                    'id': f"c_{c_id}",
                    'lead_type': 'candidate',
                    'original_id': c_id,
                    'sort_date': app_date,
                    'sort_name': f"{f_name or ''} {l_name or ''}".strip(),
                    'sort_status': status_val or 'Pending'
                })
            
            # For leads:
            lead_list = []
            for l_id, cre_date, c_name, status_val in lead_qs.values_list('id', 'Created_Date', 'candidate_name', 'interview_status'):
                lead_list.append({
                    'id': str(l_id),
                    'lead_type': 'sourced',
                    'original_id': l_id,
                    'sort_date': cre_date,
                    'sort_name': c_name or '',
                    'sort_status': status_val or 'Newlead'
                })
            
            combined_items = cand_list + lead_list
            
            # Sort combined results
            reverse_sort = sort_by.startswith('-')
            sort_key_normalized = sort_by.replace('-', '')
            
            if sort_key_normalized == 'Created_Date':
                combined_items.sort(key=lambda x: x['sort_date'] or timezone.now(), reverse=reverse_sort)
            elif sort_key_normalized == 'candidate_name':
                combined_items.sort(key=lambda x: x['sort_name'].lower(), reverse=reverse_sort)
            elif sort_key_normalized == 'interview_status':
                combined_items.sort(key=lambda x: x['sort_status'].lower(), reverse=reverse_sort)
            else:
                combined_items.sort(key=lambda x: x['sort_date'] or timezone.now(), reverse=True)
            
            total_count = len(combined_items)
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            
            page_items = combined_items[start_index:end_index]
            
            # Now, fetch full objects only for the paginated page_items
            page_candidate_ids = [item['original_id'] for item in page_items if item['lead_type'] == 'candidate']
            page_lead_ids = [item['original_id'] for item in page_items if item['lead_type'] == 'sourced']
            
            cands_dict = {}
            if page_candidate_ids:
                cands_dict = {c.id: c for c in CandidateApplicationModel.objects.filter(id__in=page_candidate_ids)}
                
            leads_dict = {}
            if page_lead_ids:
                leads_dict = {
                    l.id: l for l in NewDailyAchivesModel.objects.filter(id__in=page_lead_ids).select_related(
                        'current_day_activity__Activity_instance__Employee',
                        'current_day_activity__Activity_instance__activity_assigned_by'
                    )
                }
            
            results = []
            for item in page_items:
                if item['lead_type'] == 'candidate':
                    c = cands_dict.get(item['original_id'])
                    if c:
                        # Recruiter info
                        assigns = ScreeningAssigningModel.objects.filter(Candidate=c)
                        recruiter_names = []
                        recruiter_ids = []
                        assigner_names = []
                        for a in assigns:
                            recruiter_names.append(a.Recruiter.Name)
                            recruiter_ids.append(a.Recruiter.EmployeeId)
                            if a.AssignedBy:
                                assigner_names.append(a.AssignedBy.Name)
                        
                        # Fetch interview date
                        int_date = None
                        latest_int_status = InterviewScheduleStatusModel.objects.filter(
                            InterviewScheduledCandidate=c
                        ).select_related('interviewe').order_by('-id').first()
                        if latest_int_status and latest_int_status.interviewe:
                            int_date = latest_int_status.interviewe.InterviewDate
                        #6/6/26
                        # Fetch follow-up details for the candidate assignment
                        next_f_date = None
                        next_f_time = None
                        next_f_notes = None
                        candidate_lead = NewDailyAchivesModel.objects.filter(url=f"candidate:{c.id}").first()
                        if candidate_lead:
                            latest_pending_followup = FollowUpModel.objects.filter(
                                activity_record=candidate_lead,
                                status='pending'
                            ).order_by('-expected_date', '-expected_time').first()
                            if latest_pending_followup:
                                next_f_date = latest_pending_followup.expected_date.strftime('%Y-%m-%d')
                                next_f_time = latest_pending_followup.expected_time.strftime('%H:%M')
                                next_f_notes = latest_pending_followup.notes
                        
                        results.append({
                            "id": f"c_{c.id}",
                            "lead_type": "candidate",
                            "original_id": c.id,
                            "candidate_name": f"{c.FirstName} {c.LastName or ''}".strip(),
                            "candidate_email": c.Email or "—",
                            "candidate_phone": c.PrimaryContact or "—",
                            "Created_Date": c.AppliedDate,
                            "source": c.JobPortalSource or "N/A",
                            "candidate_designation": c.AppliedDesignation or "N/A",
                            "location": c.Location or "—",
                            "expected_ctc": c.ExpectedSalary or "—",
                            "current_ctc": c.CurrentCTC or "—",
                            "experience": c.TotalExperience or "—",
                            "fresh_experience": "Fresher" if c.Fresher else "Experience",
                            "interview_status": c.Telephonic_Round_Status or "Pending",
                            "interview_scheduled_date": int_date,
                            "handled_by": ", ".join(recruiter_names) if recruiter_names else "Unknown",
                            "handled_by_id": recruiter_ids,
                            "assigned_by": ", ".join(set(assigner_names)) if assigner_names else "System",
                            "interview_call_remarks": c.Other_jps or "—",
                            "next_followup_date": next_f_date,  #6/6/26
                            "next_followup_time": next_f_time, #6/6/26
                            "next_followup_notes": next_f_notes #6/6/26
                        })
                else:
                    l = leads_dict.get(item['original_id'])
                    if l:
                        handled_by_name = "Unknown"
                        handled_by_id = None
                        assigned_by_name = "System"
                        if l.current_day_activity and l.current_day_activity.Activity_instance:
                            recruiter = l.current_day_activity.Activity_instance.Employee
                            if recruiter:
                                handled_by_name = recruiter.Name
                                handled_by_id = recruiter.EmployeeId
                            assigner = l.current_day_activity.Activity_instance.activity_assigned_by
                            if assigner:
                                assigned_by_name = assigner.Name
                        
                        # Fetch pending followup
                        latest_pending_followup = FollowUpModel.objects.filter(
                            activity_record=l,
                            status='pending'
                        ).order_by('-expected_date', '-expected_time').first()
                        
                        next_f_date = latest_pending_followup.expected_date.strftime('%Y-%m-%d') if latest_pending_followup else None
                        next_f_time = latest_pending_followup.expected_time.strftime('%H:%M') if latest_pending_followup else None
                        next_f_notes = latest_pending_followup.notes if latest_pending_followup else None
                        
                        results.append({
                            "id": str(l.id),
                            "lead_type": "sourced",
                            "original_id": l.id,
                            "candidate_name": l.candidate_name or "N/A",
                            "candidate_email": l.candidate_email or "—",
                            "candidate_phone": l.candidate_phone or "—",
                            "Created_Date": l.Created_Date,
                            "source": l.source or "N/A",
                            "candidate_designation": l.candidate_designation or l.position or "N/A",
                            "location": l.candidate_location or "—",
                            "expected_ctc": l.expected_ctc or "—",
                            "current_ctc": l.current_ctc or "—",
                            "experience": l.candidate_experience or "—",
                            "fresh_experience": "Fresher" if l.candidate_experience == 'Fresher' else "Experience",
                            "interview_status": l.interview_status or "Newlead",
                            "interview_scheduled_date": l.interview_scheduled_date,
                            "handled_by": handled_by_name,
                            "handled_by_id": [handled_by_id] if handled_by_id else [],
                            "assigned_by": assigned_by_name,
                            "interview_call_remarks": l.interview_call_remarks or "—",
                            "next_followup_date": next_f_date,
                            "next_followup_time": next_f_time,
                            "next_followup_notes": next_f_notes
                        })
            
            return Response({
                "results": results,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        try:
            from .models import CandidateApplicationModel, ScreeningAssigningModel, InterviewScheduleStatusModel, EmployeeDataModel, MonthAchivesListModel, NewActivityModel, ActivityListModel
            
            lead_ids = request.data.get("lead_ids", [])
            candidate_ids_req = request.data.get("candidate_ids", []) #6/6/26
            assign_to_emp_ids = request.data.get("assign_to_emp_ids", [])
            login_emp_id = request.data.get("login_emp_id")
            
            if not assign_to_emp_ids:
                single_emp_id = request.data.get("assign_to_emp_id")
                if single_emp_id:
                    assign_to_emp_ids = [single_emp_id]
                    
            #6/6/26
            if not (lead_ids or candidate_ids_req) or not assign_to_emp_ids or not login_emp_id:
                return Response({"error": "lead_ids, candidate_ids, assign_to_emp_ids, and login_emp_id are required."}, status=status.HTTP_400_BAD_REQUEST)
                
            try:
                current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
            except EmployeeDataModel.DoesNotExist:
                return Response({"error": "Logged-in user not found."}, status=status.HTTP_404_NOT_FOUND)
                
            if current_user.Designation not in ['Admin', 'HR']:
                return Response({"error": "Only Admin or HR can assign/reassign leads."}, status=status.HTTP_403_FORBIDDEN)
                
            target_recruiters = []
            for emp_id in assign_to_emp_ids:
                try:
                    recruiter = EmployeeDataModel.objects.get(EmployeeId=emp_id)
                    target_recruiters.append(recruiter)
                except EmployeeDataModel.DoesNotExist:
                    return Response({"error": f"Target recruiter {emp_id} not found."}, status=status.HTTP_404_NOT_FOUND)
                    
            assigned_count = 0
            
            # Split candidate applications vs sourced leads
            candidate_ids = [int(cid) for cid in candidate_ids_req] #6/6/26
            sourced_lead_ids = []
            
            for lid in lead_ids:
                if str(lid).startswith("c_"):
                    candidate_ids.append(int(str(lid).replace("c_", ""))) #6/6/26
                else:
                    sourced_lead_ids.append(int(lid))
                    
            # Process candidate applications
            if candidate_ids:
                for cand_id in candidate_ids:
                    try:
                        cand = CandidateApplicationModel.objects.get(pk=cand_id)
                        for recruiter in target_recruiters:
                            exists = ScreeningAssigningModel.objects.filter(Candidate=cand, Recruiter=recruiter).exists()
                            if not exists:
                                screening_instance = ScreeningAssigningModel.objects.create(
                                    Candidate=cand,
                                    Recruiter=recruiter,
                                    AssignedBy=current_user,
                                    status="Assigned"
                                )
                                cand.Telephonic_Round_Status = "Assigned"
                                cand.save()
                                
                                InterviewScheduleStatusModel.objects.create(
                                    InterviewScheduledCandidate=cand,
                                    Interview_Schedule_Status="Assigned",
                                    screening=screening_instance
                                )
                                assigned_count += 1
                                
                                # Send notification
                                try:
                                    from .models import RegistrationModel, Notification
                                    sender_reg = RegistrationModel.objects.filter(EmployeeId=current_user.EmployeeId).first()
                                    receiver_reg = RegistrationModel.objects.filter(EmployeeId=recruiter.EmployeeId).first()
                                    if sender_reg and receiver_reg:
                                        message = f"{current_user.Name} assigned a new candidate for screening: {cand.FirstName} {cand.LastName or ''}."
                                        Notification.objects.create(
                                            sender=sender_reg,
                                            receiver=receiver_reg,
                                            message=message,
                                            candidate_id=cand,
                                            not_type='scr_assign',
                                            reference_id=cand.CandidateId
                                        )
                                except Exception as n_err:
                                    print(f"Failed to create candidate assignment notification: {n_err}")
                    except CandidateApplicationModel.DoesNotExist:
                        pass
                        
            # Process sourced daily leads
            if sourced_lead_ids:
                today = timezone.localdate()
                activity_list = ActivityListModel.objects.filter(activity_name="interview_calls").first()
                if not activity_list:
                    return Response({"error": "Activity type 'interview_calls' does not exist."}, status=status.HTTP_400_BAD_REQUEST)
                    
                for recruiter in target_recruiters:
                    target_activity, _ = NewActivityModel.objects.get_or_create(
                        Activity=activity_list,
                        Employee=recruiter,
                        Activity_assigned_Date__month=today.month,
                        Activity_assigned_Date__year=today.year,
                        defaults={
                            'Activity_assigned_Date': today,
                            'activity_assigned_by': current_user,
                            'targets': 0
                        }
                    )
                    
                    target_day_activity, _ = MonthAchivesListModel.objects.get_or_create(
                        Activity_instance=target_activity,
                        Date=today,
                        defaults={'achieved': 0}
                    )
                    
                    prev_day_activities = set()
                    
                    for lead_id in sourced_lead_ids:
                        try:
                            lead = NewDailyAchivesModel.objects.get(pk=lead_id)
                            current_owner = lead.current_day_activity.Activity_instance.Employee if (lead.current_day_activity and lead.current_day_activity.Activity_instance) else None
                            
                            if current_owner == recruiter:
                                continue
                                
                            should_shift = False
                            if not lead.current_day_activity or not lead.current_day_activity.Activity_instance:
                                should_shift = True
                            else:
                                if current_owner.Designation in ['Admin', 'HR'] and lead.sourcing_channel != 'assigned' and not lead.interview_status:
                                    should_shift = True
                                    
                            if should_shift:
                                if lead.current_day_activity:
                                    prev_day_activities.add(lead.current_day_activity)
                                lead.current_day_activity = target_day_activity
                                lead.sourcing_channel = 'assigned'
                                lead.save()
                                assigned_count += 1
                            else:
                                # Multi-assign: clone
                                exists = False
                                if lead.candidate_phone:
                                    exists = NewDailyAchivesModel.objects.filter(
                                        current_day_activity=target_day_activity,
                                        candidate_phone=lead.candidate_phone
                                    ).exists()
                                elif lead.candidate_email:
                                    exists = NewDailyAchivesModel.objects.filter(
                                        current_day_activity=target_day_activity,
                                        candidate_email=lead.candidate_email
                                    ).exists()
                                else:
                                    exists = NewDailyAchivesModel.objects.filter(
                                        current_day_activity=target_day_activity,
                                        candidate_name=lead.candidate_name
                                    ).exists()
                                    
                                if not exists:
                                    NewDailyAchivesModel.objects.create(
                                        current_day_activity=target_day_activity,
                                        sourcing_channel='assigned',
                                        candidate_name=lead.candidate_name,
                                        candidate_phone=lead.candidate_phone,
                                        candidate_email=lead.candidate_email,
                                        candidate_location=lead.candidate_location,
                                        candidate_designation=lead.candidate_designation,
                                        candidate_current_status=lead.candidate_current_status,
                                        candidate_experience=lead.candidate_experience,
                                        industries_worked=lead.industries_worked,
                                        source=lead.source,
                                        expected_ctc=lead.expected_ctc,
                                        current_ctc=lead.current_ctc,
                                        DOJ=lead.DOJ,
                                        have_laptop=lead.have_laptop,
                                        candidate_for=lead.candidate_for,
                                        position=lead.position,
                                        url=lead.url,
                                        job_post_remarks=lead.job_post_remarks,
                                        assigned_requirement=lead.assigned_requirement,
                                        lead_status='active',
                                        interview_status=None,
                                        interview_scheduled_date=None,
                                        interview_walkin_date=None,
                                        interview_call_remarks=None
                                    )
                                    assigned_count += 1
                        except NewDailyAchivesModel.DoesNotExist:
                            pass
                            
                    # Recalculate achievement counts
                    for prev_act in prev_day_activities:
                        prev_act.achieved = NewDailyAchivesModel.objects.filter(
                            current_day_activity=prev_act
                        ).exclude(lead_status='staged').count()
                        prev_act.save()
                        
                    target_day_activity.achieved = NewDailyAchivesModel.objects.filter(
                        current_day_activity=target_day_activity
                    ).exclude(lead_status='staged').count()
                    target_day_activity.save()
                    
            recruiter_names = ", ".join([r.Name for r in target_recruiters])
            return Response({
                "message": f"Successfully assigned selected leads to: {recruiter_names}.",
                "assigned_count": assigned_count
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




