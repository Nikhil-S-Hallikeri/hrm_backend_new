import os
import csv
import zipfile
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
from django.http import HttpResponse
from django.core.files.base import ContentFile
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from HRM_App.models import CandidateApplicationModel, CandidateResumeFile
from HRM_App.parsers import parse_resume_data

class CandidateResumeFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CandidateResumeFile
        fields = ['file', 'uploaded_at']

class CandidateResumeSerializer(serializers.ModelSerializer):
    resume_file = CandidateResumeFileSerializer(read_only=True)
    resume_url = serializers.SerializerMethodField()

    class Meta:
        model = CandidateApplicationModel
        fields = [
            'id', 'CandidateId', 'FirstName', 'LastName', 'Email', 
            'PrimaryContact', 'HighestQualification', 'TotalExperience', 
            'AppliedDesignation', 'Filled_by', 'AppliedDate', 'DataOfApplied',
            'resume_file', 'resume_url'
        ]

    def get_resume_url(self, obj):
        if hasattr(obj, 'resume_file') and obj.resume_file and obj.resume_file.file:
            return obj.resume_file.file.url
        return None

from rest_framework.pagination import PageNumberPagination
from django.db.models import Q

class ResumePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class ResumeParserViewSet(viewsets.ModelViewSet):
    serializer_class = CandidateResumeSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    pagination_class = ResumePagination

    def get_queryset(self):
        queryset = CandidateApplicationModel.objects.filter(Filled_by='ResumeParser')
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(FirstName__icontains=search) |
                Q(LastName__icontains=search) |
                Q(Email__icontains=search) |
                Q(PrimaryContact__icontains=search) |
                Q(AppliedDesignation__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        """
        Supports 3 Upload Modes:
        1. Single PDF File Upload ('file')
        2. Multiple PDF Files Upload ('files')
        3. Bulk ZIP Archive Upload (extracts & parses every PDF inside)
        """
        uploaded_files = request.FILES.getlist('files')
        if not uploaded_files and 'file' in request.FILES:
            uploaded_files = [request.FILES['file']]

        if not uploaded_files:
            return Response(
                {"error": "No files provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_candidates = []

        for uploaded_file in uploaded_files:
            file_name = uploaded_file.name.lower()

            # Handle Mode 3: Bulk ZIP Archive Upload
            if file_name.endswith('.zip'):
                try:
                    file_bytes = uploaded_file.read()
                    with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
                        for member_name in zf.namelist():
                            if member_name.lower().endswith('.pdf') and not member_name.startswith('__MACOSX') and not os.path.basename(member_name).startswith('.'):
                                pdf_bytes = zf.read(member_name)
                                pdf_basename = os.path.basename(member_name) or "resume.pdf"
                                content_file = ContentFile(pdf_bytes, name=pdf_basename)

                                parsed_data = parse_resume_data(pdf_bytes, file_name=pdf_basename)

                                name = parsed_data.get('name', 'Candidate Name')
                                name_parts = name.split(' ', 1)
                                first_name = name_parts[0][:100]
                                last_name = (name_parts[1] if len(name_parts) > 1 else "")[:100]
                                email = parsed_data.get('email', '')[:100]
                                phone = parsed_data.get('phone', '')[:100]
                                qualifications = parsed_data.get('qualifications', 'Not Specified')[:100]
                                experience = parsed_data.get('experience', 'Not Specified')[:100]
                                applied_role = parsed_data.get('applied_role', 'Software Engineer')[:100]

                                # Check if candidate already exists by email or contact
                                existing_candidate = None
                                if email or phone:
                                    from django.db.models import Q
                                    q_filt = Q()
                                    if email:
                                        q_filt |= Q(Email=email)
                                    if phone:
                                        q_filt |= Q(PrimaryContact=phone)
                                    existing_candidate = CandidateApplicationModel.objects.filter(q_filt).first()

                                if existing_candidate:
                                    # Update existing candidate
                                    existing_candidate.FirstName = first_name
                                    existing_candidate.LastName = last_name
                                    if email:
                                        existing_candidate.Email = email
                                    if phone:
                                        existing_candidate.PrimaryContact = phone
                                    existing_candidate.HighestQualification = qualifications
                                    existing_candidate.TotalExperience = experience
                                    existing_candidate.AppliedDesignation = applied_role
                                    existing_candidate.Filled_by = 'ResumeParser'
                                    existing_candidate.save()
                                    
                                    # Update/replace the resume file
                                    resume_file, _ = CandidateResumeFile.objects.get_or_create(candidate=existing_candidate)
                                    resume_file.file = content_file
                                    resume_file.save()
                                    
                                    created_candidates.append(existing_candidate)
                                else:
                                    # Create new candidate
                                    candidate = CandidateApplicationModel.objects.create(
                                        FirstName=first_name,
                                        LastName=last_name,
                                        Email=email,
                                        PrimaryContact=phone,
                                        HighestQualification=qualifications,
                                        TotalExperience=experience,
                                        AppliedDesignation=applied_role,
                                        Filled_by='ResumeParser',
                                        JobPortalSource='others',
                                    )
                                    CandidateResumeFile.objects.create(
                                        candidate=candidate,
                                        file=content_file
                                    )
                                    created_candidates.append(candidate)
                except Exception as e:
                    return Response(
                        {"error": f"Failed to process ZIP archive: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Handle Mode 1 & 2: Single or Multiple PDF File Upload
            elif file_name.endswith('.pdf'):
                try:
                    file_bytes = uploaded_file.read()
                    parsed_data = parse_resume_data(file_bytes, file_name=uploaded_file.name)

                    name = parsed_data.get('name', 'Candidate Name')
                    name_parts = name.split(' ', 1)
                    first_name = name_parts[0][:100]
                    last_name = (name_parts[1] if len(name_parts) > 1 else "")[:100]
                    email = parsed_data.get('email', '')[:100]
                    phone = parsed_data.get('phone', '')[:100]
                    qualifications = parsed_data.get('qualifications', 'Not Specified')[:100]
                    experience = parsed_data.get('experience', 'Not Specified')[:100]
                    applied_role = parsed_data.get('applied_role', 'Software Engineer')[:100]

                    uploaded_file.seek(0)
                    
                    # Check if candidate already exists
                    existing_candidate = None
                    if email or phone:
                        from django.db.models import Q
                        q_filt = Q()
                        if email:
                            q_filt |= Q(Email=email)
                        if phone:
                            q_filt |= Q(PrimaryContact=phone)
                        existing_candidate = CandidateApplicationModel.objects.filter(q_filt).first()

                    if existing_candidate:
                        # Update existing candidate
                        existing_candidate.FirstName = first_name
                        existing_candidate.LastName = last_name
                        if email:
                            existing_candidate.Email = email
                        if phone:
                            existing_candidate.PrimaryContact = phone
                        existing_candidate.HighestQualification = qualifications
                        existing_candidate.TotalExperience = experience
                        existing_candidate.AppliedDesignation = applied_role
                        existing_candidate.Filled_by = 'ResumeParser'
                        existing_candidate.save()
                        
                        # Update/replace the resume file
                        resume_file, _ = CandidateResumeFile.objects.get_or_create(candidate=existing_candidate)
                        resume_file.file = uploaded_file
                        resume_file.save()
                        
                        created_candidates.append(existing_candidate)
                    else:
                        # Create new candidate
                        candidate = CandidateApplicationModel.objects.create(
                            FirstName=first_name,
                            LastName=last_name,
                            Email=email,
                            PrimaryContact=phone,
                            HighestQualification=qualifications,
                            TotalExperience=experience,
                            AppliedDesignation=applied_role,
                            Filled_by='ResumeParser',
                            JobPortalSource='others',
                        )
                        CandidateResumeFile.objects.create(
                            candidate=candidate,
                            file=uploaded_file
                        )
                        created_candidates.append(candidate)
                except Exception as e:
                    return Response(
                        {"error": f"Failed to process PDF {uploaded_file.name}: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        if created_candidates:
            if len(created_candidates) == 1 and len(uploaded_files) == 1 and not uploaded_files[0].name.lower().endswith('.zip'):
                serializer = self.get_serializer(created_candidates[0])
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            
            serializer = self.get_serializer(created_candidates, many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(
            {"error": "No valid PDF or ZIP files provided"},
            status=status.HTTP_400_BAD_REQUEST
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Handle parsed structure conversion for updates if user edits name directly
        data = request.data.copy()
        if 'name' in data:
            name_parts = data['name'].split(' ', 1)
            data['FirstName'] = name_parts[0]
            data['LastName'] = name_parts[1] if len(name_parts) > 1 else ""

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid_raise_exception = True
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Clean up resume file first
        if hasattr(instance, 'resume_file') and instance.resume_file:
            instance.resume_file.delete()
        self.perform_destroy(instance)
        return Response(
            {"message": "Candidate deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['delete', 'post'], url_path='bulk_delete')
    def bulk_delete(self, request):
        """
        Bulk delete multiple candidate profiles by IDs
        Payload: {"ids": ["id1", "id2", ...]}
        """
        ids = request.data.get('ids', [])
        if not ids or not isinstance(ids, list):
            return Response(
                {"error": "Please provide a list of candidate IDs in 'ids'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        candidates_to_delete = CandidateApplicationModel.objects.filter(id__in=ids)
        for cand in candidates_to_delete:
            if hasattr(cand, 'resume_file') and cand.resume_file:
                cand.resume_file.delete()

        count = candidates_to_delete.delete()[0]
        return Response(
            {"message": f"Successfully deleted {count} candidates", "deleted_count": count},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'], url_path='export_csv')
    def export_csv(self, request):
        """
        Export selected (or all) candidate resumes as CSV file.
        Payload: {"ids": ["id1", "id2"]} (optional)
        """
        ids = request.data.get('ids', [])
        if ids and isinstance(ids, list):
            candidates = CandidateApplicationModel.objects.filter(id__in=ids)
        else:
            candidates = CandidateApplicationModel.objects.filter(Filled_by='ResumeParser')

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="candidates_export.csv"'

        writer = csv.writer(response)
        writer.writerow(['ID', 'Name', 'Applied Role', 'Email', 'Phone', 'Submission Date', 'Qualifications', 'Experience'])

        for c in candidates:
            name = f"{c.FirstName or ''} {c.LastName or ''}".strip()
            writer.writerow([
                str(c.id),
                name,
                c.AppliedDesignation or '',
                c.Email or '',
                c.PrimaryContact or '',
                str(c.AppliedDate.date()) if c.AppliedDate else '',
                c.HighestQualification or '',
                c.TotalExperience or ''
            ])

        return response

    @action(detail=False, methods=['post'], url_path='export_excel')
    def export_excel(self, request):
        """
        Export selected (or all) candidate resumes as Excel (.xlsx) file with professional auto-alignment & styling.
        Payload: {"ids": ["id1", "id2"]} (optional)
        """
        ids = request.data.get('ids', [])
        if ids and isinstance(ids, list):
            candidates = CandidateApplicationModel.objects.filter(id__in=ids)
        else:
            candidates = CandidateApplicationModel.objects.filter(Filled_by='ResumeParser')

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Candidate Resumes"
        ws.views.sheetView[0].showGridLines = True

        headers = ['ID', 'Name', 'Applied Role', 'Email', 'Phone', 'Submission Date', 'Qualifications', 'Experience']
        ws.append(headers)

        # Header Row Styling
        header_font = Font(name='Calibri', size=11, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='1F2937', end_color='1F2937', fill_type='solid')
        header_align = Alignment(horizontal='left', vertical='center')

        ws.row_dimensions[1].height = 26

        for col_num in range(1, len(headers) + 1):
            cell = ws.cell(row=1, column=col_num)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        # Data Rows Styling & Borders
        data_font = Font(name='Calibri', size=10.5, color='111827')
        thin_border = Border(
            left=Side(style='thin', color='E5E7EB'),
            right=Side(style='thin', color='E5E7EB'),
            top=Side(style='thin', color='E5E7EB'),
            bottom=Side(style='thin', color='E5E7EB')
        )

        row_idx = 2
        for c in candidates:
            name = f"{c.FirstName or ''} {c.LastName or ''}".strip()
            row_data = [
                str(c.id),
                name,
                c.AppliedDesignation or '',
                c.Email or '',
                c.PrimaryContact or '',
                str(c.AppliedDate.date()) if c.AppliedDate else '',
                c.HighestQualification or '',
                c.TotalExperience or ''
            ]
            ws.append(row_data)
            ws.row_dimensions[row_idx].height = 22

            # Apply cell styles
            for col_idx, val in enumerate(row_data, 1):
                cell = ws.cell(row=row_idx, column=col_idx)
                cell.font = data_font
                cell.border = thin_border
                
                # Center align ID, Phone, Date; Left align text fields
                if col_idx in [1, 5, 6]:
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                else:
                    cell.alignment = Alignment(horizontal='left', vertical='center')

            row_idx += 1

        # Auto-fit Column Widths cleanly
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)

        response = HttpResponse(
            stream.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="candidates_export.xlsx"'
        return response

    @action(detail=False, methods=['POST'], url_path='assign')
    def assign_candidates(self, request):
        candidate_ids = request.data.get("candidate_ids", [])
        assign_to_emp_id = request.data.get("assign_to_emp_id")
        login_emp_id = request.data.get("login_emp_id")

        if not candidate_ids or not assign_to_emp_id or not login_emp_id:
            return Response(
                {"error": "candidate_ids, assign_to_emp_id, and login_emp_id are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from HRM_App.models import (
            EmployeeDataModel, NewDailyAchivesModel, ActivityListModel,
            NewActivityModel, MonthAchivesListModel
        )
        from django.utils import timezone

        # 1. Check logged-in user and permissions
        try:
            current_user = EmployeeDataModel.objects.get(EmployeeId=login_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Logged-in user not found."}, status=status.HTTP_404_NOT_FOUND)

        if current_user.Designation not in ['Admin', 'HR', 'Recruiter']:
            return Response({"error": "Only Admin, HR, or Recruiter can assign candidates."}, status=status.HTTP_403_FORBIDDEN)

        # 2. Check target recruiter
        try:
            target_recruiter = EmployeeDataModel.objects.get(EmployeeId=assign_to_emp_id)
        except EmployeeDataModel.DoesNotExist:
            return Response({"error": "Target recruiter not found."}, status=status.HTTP_404_NOT_FOUND)

        # 3. Get or create active activity context for target recruiter (interview_calls)
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

        # 4. Process assignment
        assigned_count = 0
        for cid in candidate_ids:
            try:
                candidate = CandidateApplicationModel.objects.get(pk=cid)
                
                # Check if this candidate is already assigned to this recruiter today
                full_name = f"{candidate.FirstName or ''} {candidate.LastName or ''}".strip()
                phone = candidate.PrimaryContact or ''
                email = candidate.Email or ''
                
                # Global all-time duplicate check: check if this candidate has ever been assigned to ANY recruiter
                if phone or email:
                    from django.db.models import Q
                    q_filter = Q()
                    if phone:
                        q_filter |= Q(candidate_phone=phone)
                    if email:
                        q_filter |= Q(candidate_email=email)
                    exists = NewDailyAchivesModel.objects.filter(q_filter).exists()
                else:
                    exists = NewDailyAchivesModel.objects.filter(candidate_name=full_name).exists()

                if exists:
                    continue

                # Create the NewDailyAchivesModel entry
                NewDailyAchivesModel.objects.create(
                    current_day_activity=target_day_activity,
                    assigned_by=current_user,
                    sourcing_channel='assigned',
                    candidate_name=full_name,
                    candidate_phone=phone,
                    candidate_email=email,
                    candidate_designation=candidate.AppliedDesignation or '',
                    source='ResumeParser',
                    lead_status='active',
                    interview_status=None
                )
                assigned_count += 1
            except CandidateApplicationModel.DoesNotExist:
                continue

        return Response({
            "message": f"Successfully assigned {assigned_count} candidate(s) to {target_recruiter.Name or target_recruiter.EmployeeId}."
        }, status=status.HTTP_200_OK)
