# ===== ACTIVITY DASHBOARD PAGINATION VIEWS =====

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
            today = timezone.localdate()
            if filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today.replace(day=monthrange(today.year, today.month)[1])
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif filter_type == 'today':
                start_date = end_date = today
            elif filter_type == 'custom' and start_date_str and end_date_str:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                start_date = end_date = today
            
            # Get pending follow-ups
            pending_followups = FollowUpModel.objects.filter(
                activity_record__current_day_activity__Employee__in=target_employees,
                activity_record__current_day_activity__Date__range=(start_date, end_date),
                status='pending'
            ).select_related('activity_record').order_by('expected_date', 'expected_time')
            
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
                "followups": serializer.data,
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
            today = timezone.localdate()
            if filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today.replace(day=monthrange(today.year, today.month)[1])
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif filter_type == 'today':
                start_date = end_date = today
            elif filter_type == 'custom' and start_date_str and end_date_str:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                start_date = end_date = today
            
            # Get completed follow-ups
            completed_followups = FollowUpModel.objects.filter(
                activity_record__current_day_activity__Employee__in=target_employees,
                activity_record__current_day_activity__Date__range=(start_date, end_date),
                status='completed'
            ).select_related('activity_record').order_by('-completed_on')
            
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
                "followups": serializer.data,
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
            today = timezone.localdate()
            if filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today.replace(day=monthrange(today.year, today.month)[1])
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif filter_type == 'today':
                start_date = end_date = today
            elif filter_type == 'custom' and start_date_str and end_date_str:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                start_date = end_date = today
            
            # Get all activities
            activities = NewDailyAchivesModel.objects.filter(
                current_day_activity__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date)
            ).select_related('current_day_activity__Employee').order_by('-current_day_activity__Date')
            
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
                "activities": records,
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
            today = timezone.localdate()
            if filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today.replace(day=monthrange(today.year, today.month)[1])
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif filter_type == 'today':
                start_date = end_date = today
            elif filter_type == 'custom' and start_date_str and end_date_str:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                start_date = end_date = today
            
            # Get successful outcomes (closed with positive result)
            activities = NewDailyAchivesModel.objects.filter(
                current_day_activity__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date),
                lead_status='closed'
            ).select_related('current_day_activity__Employee').order_by('-current_day_activity__Date')
            
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
                "activities": records,
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
            
            # Role-based filtering
            if current_user.Designation == 'Admin':
                target_employees = EmployeeDataModel.objects.all()
            elif current_user.Designation in ['HR', 'Recruiter']:
                team_members = EmployeeDataModel.objects.filter(Reporting_To=current_user)
                target_employees = team_members | EmployeeDataModel.objects.filter(pk=current_user.pk)
            else:
                target_employees = EmployeeDataModel.objects.filter(pk=current_user.pk)
            
            # Date range filtering
            today = timezone.localdate()
            if filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today.replace(day=monthrange(today.year, today.month)[1])
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif filter_type == 'today':
                start_date = end_date = today
            elif filter_type == 'custom' and start_date_str and end_date_str:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                start_date = end_date = today
            
            # Get rejected leads
            activities = NewDailyAchivesModel.objects.filter(
                current_day_activity__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date),
                lead_status='rejected'
            ).select_related('current_day_activity__Employee').order_by('-current_day_activity__Date')
            
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
                    'rejection_type': activity.rejection_type,
                    'rejection_reason': getattr(activity, 'rejection_reason', ''),
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
                "activities": records,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
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
            today = timezone.localdate()
            if filter_type == 'this_month':
                start_date = today.replace(day=1)
                end_date = today.replace(day=monthrange(today.year, today.month)[1])
            elif filter_type == 'this_week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=6)
            elif filter_type == 'today':
                start_date = end_date = today
            elif filter_type == 'custom' and start_date_str and end_date_str:
                start_date = timezone.datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = timezone.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            else:
                start_date = end_date = today
            
            # Get closed leads
            activities = NewDailyAchivesModel.objects.filter(
                current_day_activity__Employee__in=target_employees,
                current_day_activity__Date__range=(start_date, end_date),
                lead_status='closed'
            ).select_related('current_day_activity__Employee').order_by('-current_day_activity__Date')
            
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
                "activities": records,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
