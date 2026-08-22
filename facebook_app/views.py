import requests
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import FacebookConfig, FacebookPage, FacebookLead
from .serializers import FacebookConfigSerializer, FacebookPageSerializer, FacebookLeadSerializer

CRM_URL = 'https://crmclient.skilllearningacademy.com'


# Utility functions
def get_assigned_employee(lead_page_id):
    if not lead_page_id:
        return None
    try:
        page = FacebookPage.objects.filter(page_id=lead_page_id, active_status='active').first()
        if page:
            return page.auto_assign_employee
    except Exception as e:
        print(f"Error finding assigned employee: {str(e)}")
    return None


def get_lead_from_facebook_token_and_lead_id(lead_id, tokens):
    for token in tokens:
        try:
            print(f"Attempting to fetch lead {lead_id} with token starting with {token[:10]}...")
            url = f"https://graph.facebook.com/v25.0/{lead_id}"
            params = {
                "fields": "created_time,ad_id,ad_name,form_id,field_data",
                "access_token": token,
            }
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                lead_details = {}
                field_data = data.get('field_data', [])
                if isinstance(field_data, list):
                    for field in field_data:
                        name = field.get('name')
                        values = field.get('values')
                        lead_details[name] = values[0] if values and len(values) > 0 else None
                return {
                    "lead_id": data.get('id'),
                    "created_time": data.get('created_time'),
                    "ad_id": data.get('ad_id'),
                    "ad_name": data.get('ad_name'),
                    "form_id": data.get('form_id'),
                    **lead_details,
                    "success": True
                }
        except Exception as e:
            print(f"Facebook Lead Fetch Error: {str(e)}")
            
    return {"success": False, "message": "Failed to fetch lead from Facebook API with all provided tokens"}


def sync_to_crm_leads_individual(lead_instance):
    try:
        lead_page_id = None
        if lead_instance.lead_gen_data:
            lead_page_id = lead_instance.lead_gen_data.get('page_id')
            
        assigned_emp = get_assigned_employee(lead_page_id)
        if not assigned_emp:
            return {'success': False, 'message': 'No assigned employee found'}
            
        if not lead_instance.facebook_ad_detail:
            return {'success': False, 'message': 'Lead has to be synced with facebook first'}
            
        lead_serializer = FacebookLeadSerializer(lead_instance)
        
        req_obj = {
            'leads': [lead_serializer.data],
            'lead_type': 'b2c',
            'assigned_to': assigned_emp,
        }
        
        resp = requests.post(f"{CRM_URL}/api/facebook/classify/", json=req_obj, timeout=10)
        if resp.status_code == 200:
            return {'success': True, 'data': resp.json()}
        else:
            return {'success': False, 'message': f"CRM API returned code {resp.status_code}"}
    except Exception as e:
        return {'success': False, 'message': str(e)}


# Facebook Config CRUD View/APIs
@api_view(['GET', 'POST', 'PUT'])
def facebook_config_list_create_update(request):
    if request.method == 'GET':
        config_id = request.query_params.get('id')
        active = request.query_params.get('active')
        page_num = request.query_params.get('page', 1)
        
        if config_id:
            try:
                config = FacebookConfig.objects.get(id=config_id)
                serializer = FacebookConfigSerializer(config)
                return Response(serializer.data)
            except FacebookConfig.DoesNotExist:
                return Response({'message': 'Config not found'}, status=status.HTTP_404_NOT_FOUND)
                
        if active:
            configs = FacebookConfig.objects.filter(active_status=active)
            serializer = FacebookConfigSerializer(configs, many=True)
            return Response({'data': serializer.data})

        # Paginated configs
        all_configs = FacebookConfig.objects.all().order_by('-created_at')
        limit = 20
        total = all_configs.count()
        
        try:
            page_num = int(page_num)
        except ValueError:
            page_num = 1
            
        start = (page_num - 1) * limit
        end = start + limit
        
        paginated_configs = all_configs[start:end]
        serializer = FacebookConfigSerializer(paginated_configs, many=True)
        
        has_next = end < total
        has_prev = start > 0
        
        return Response({
            'currentPage': page_num,
            'pages': (total + limit - 1) // limit,
            'count': total,
            'hasPrev': has_prev,
            'hasNext': has_next,
            'data': serializer.data
        })

    elif request.method == 'POST':
        # saveFacebookConfig
        app_name = request.data.get('appName') or request.data.get('app_name')
        if FacebookConfig.objects.filter(app_name=app_name).exists():
            return Response("Facebook config with this app name already exists", status=status.HTTP_400_BAD_REQUEST)
            
        # Map frontend camelCase payload keys to backend snake_case fields
        data = {
            'app_name': app_name,
            'app_id': request.data.get('appId') or request.data.get('app_id'),
            'app_secret': request.data.get('appSecret') or request.data.get('app_secret'),
            'verify_token': request.data.get('verifyToken') or request.data.get('verify_token'),
            'active_status': request.data.get('activeStatus') or request.data.get('active_status', 'active'),
            'pages': []
        }
        
        # Map nested pages
        pages = request.data.get('pages', [])
        for page in pages:
            data['pages'].append({
                'page_name': page.get('pageName') or page.get('page_name'),
                'page_id': page.get('pageId') or page.get('page_id'),
                'page_access_token': page.get('pageAccessToken') or page.get('page_access_token'),
                'expiry_date': page.get('expiryDate') or page.get('expiry_date'),
                'generated_date': page.get('generatedDate') or page.get('generated_date'),
                'active_status': page.get('activeStatus') or page.get('active_status', 'active'),
                'allowed_ad_ids': page.get('allowed_Ad_id') or page.get('allowed_ad_ids', []),
                'not_allowed_ad_ids': page.get('not_allowed_Ad_id') or page.get('not_allowed_ad_ids', []),
                'auto_assign_employee': page.get('autoAssignEmployee') or page.get('auto_assign_employee')
            })
            
        serializer = FacebookConfigSerializer(data=data)
        if serializer.is_valid():
            config = serializer.save()
            return Response(FacebookConfigSerializer(config).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        # updateFacebookConfig
        config_id = request.data.get('_id') or request.data.get('id')
        if not config_id:
            return Response("Config ID is required", status=status.HTTP_400_BAD_REQUEST)
            
        try:
            config = FacebookConfig.objects.get(id=config_id)
        except FacebookConfig.DoesNotExist:
            return Response("Config not found", status=status.HTTP_404_NOT_FOUND)

        app_name = request.data.get('appName') or request.data.get('app_name')
        if FacebookConfig.objects.filter(app_name=app_name).exclude(id=config_id).exists():
            return Response("Facebook config with this app name already exists", status=status.HTTP_400_BAD_REQUEST)

        # Map frontend camelCase payload keys to snake_case fields
        data = {
            'app_name': app_name,
            'app_id': request.data.get('appId') or request.data.get('app_id'),
            'app_secret': request.data.get('appSecret') or request.data.get('app_secret'),
            'verify_token': request.data.get('verifyToken') or request.data.get('verify_token'),
            'active_status': request.data.get('activeStatus') or request.data.get('active_status', 'active'),
            'pages': []
        }
        
        pages = request.data.get('pages', [])
        for page in pages:
            data['pages'].append({
                'page_name': page.get('pageName') or page.get('page_name'),
                'page_id': page.get('pageId') or page.get('page_id'),
                'page_access_token': page.get('pageAccessToken') or page.get('page_access_token'),
                'expiry_date': page.get('expiryDate') or page.get('expiry_date'),
                'generated_date': page.get('generatedDate') or page.get('generated_date'),
                'active_status': page.get('activeStatus') or page.get('active_status', 'active'),
                'allowed_ad_ids': page.get('allowed_Ad_id') or page.get('allowed_ad_ids', []),
                'not_allowed_ad_ids': page.get('not_allowed_Ad_id') or page.get('not_allowed_ad_ids', []),
                'auto_assign_employee': page.get('autoAssignEmployee') or page.get('auto_assign_employee')
            })
            
        serializer = FacebookConfigSerializer(config, data=data)
        if serializer.is_valid():
            updated_config = serializer.save()
            return Response(FacebookConfigSerializer(updated_config).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
def facebook_config_detail_delete(request, id):
    try:
        config = FacebookConfig.objects.get(id=id)
    except FacebookConfig.DoesNotExist:
        return Response({'message': 'Config not found'}, status=status.HTTP_404_NOT_FOUND)
        
    if request.method == 'GET':
        serializer = FacebookConfigSerializer(config)
        return Response(serializer.data)
        
    elif request.method == 'DELETE':
        config.delete()
        return Response("Facebook config deleted successfully")


# Facebook Leads Endpoints
@api_view(['GET', 'POST'])
def facebook_lead_list_create(request):
    if request.method == 'POST':
        data = request.data
        lead_id = data.get('leadgen_id') or data.get('lead_id')
        
        try:
            lead = FacebookLead.objects.get(leadgen_id=lead_id)
            serializer = FacebookLeadSerializer(lead)
            return Response({"message": "Lead already exists", "lead": serializer.data})
        except FacebookLead.DoesNotExist:
            pass
            
        mapped_data = {
            'leadgen_id': lead_id,
            'ad_id': data.get('ad_id'),
            'ad_name': data.get('ad_name'),
            'full_name': data.get('full_name'),
            'phone': data.get('phone'),
            'facebook_ad_detail': data.get('facebookAdDetail') or data.get('facebook_ad_detail'),
            'lead_gen_data': data.get('leadGenData') or data.get('lead_gen_data'),
            'synced': data.get('synced', False),
            'synced_at': data.get('syncedAt') or data.get('synced_at'),
            'crm_sync': data.get('crmSync', False),
            'crm_sync_at': data.get('crmSyncAt') or data.get('crm_sync_at'),
        }
        
        serializer = FacebookLeadSerializer(data=mapped_data)
        if serializer.is_valid():
            saved_lead = serializer.save()
            return Response(FacebookLeadSerializer(saved_lead).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'GET':
        page_num = request.query_params.get('page', 1)
        search = request.query_params.get('search')
        ad_id = request.query_params.get('ad_id')
        start_date = request.query_params.get('startDate')
        end_date = request.query_params.get('endDate')
        
        from django.utils import timezone
        from datetime import datetime, time

        find_query = Q()
        
        if start_date or end_date:
            try:
                s_date_str = start_date if start_date else "2000-01-01"
                e_date_str = end_date if end_date else "2100-12-31"
                
                s_date = datetime.strptime(s_date_str, "%Y-%m-%d").date()
                e_date = datetime.strptime(e_date_str, "%Y-%m-%d").date()
                
                start_dt = timezone.make_aware(datetime.combine(s_date, time.min))
                end_dt = timezone.make_aware(datetime.combine(e_date, time.max))
                
                find_query &= Q(created_at__range=(start_dt, end_dt))
            except Exception as ex:
                print("Error parsing date filters:", ex)
            
        if ad_id:
            find_query &= (Q(ad_id=ad_id) | Q(facebook_ad_detail__ad_id=ad_id))
            
        if search:
            find_query &= (
                Q(leadgen_id__icontains=search) |
                Q(full_name__icontains=search) |
                Q(phone__icontains=search) |
                Q(ad_name__icontains=search) |
                Q(ad_id__icontains=search) |
                Q(facebook_ad_detail__full_name__icontains=search) |
                Q(facebook_ad_detail__phone__icontains=search) |
                Q(facebook_ad_detail__email__icontains=search) |
                Q(facebook_ad_detail__ad_name__icontains=search) |
                Q(facebook_ad_detail__ad_id__icontains=search) |
                Q(facebook_ad_detail__form_id__icontains=search) |
                Q(facebook_ad_detail__city__icontains=search) |
                Q(facebook_ad_detail__state__icontains=search)
            )
            
        all_leads = FacebookLead.objects.filter(find_query).order_by('-created_at')
        limit = 20
        total = all_leads.count()
        
        try:
            page_num = int(page_num)
        except ValueError:
            page_num = 1
            
        start = (page_num - 1) * limit
        end = start + limit
        
        paginated_leads = all_leads[start:end]
        serializer = FacebookLeadSerializer(paginated_leads, many=True)
        
        has_next = end < total
        has_prev = start > 0
        
        return Response({
            'currentPage': page_num,
            'pages': (total + limit - 1) // limit,
            'count': total,
            'hasPrev': has_prev,
            'hasNext': has_next,
            'data': serializer.data
        })


@api_view(['GET'])
def get_unique_ads(request):
    try:
        # aggregate unique ad_ids and names
        main_ads = FacebookLead.objects.exclude(ad_id__isnull=True).exclude(ad_name__isnull=True).values('ad_id', 'ad_name').distinct()
        ad_map = {}
        for ad in main_ads:
            if ad['ad_id']:
                ad_map[ad['ad_id']] = ad['ad_name'] or ad['ad_id']
                
        detail_leads = FacebookLead.objects.exclude(facebook_ad_detail__isnull=True)
        for lead in detail_leads:
            detail = lead.facebook_ad_detail
            if isinstance(detail, dict):
                ad_id = detail.get('ad_id')
                ad_name = detail.get('ad_name')
                if ad_id and ad_id not in ad_map:
                    ad_map[ad_id] = ad_name or ad_id
                    
        unique_ads = [{'ad_id': id, 'ad_name': name} for id, name in ad_map.items()]
        return Response(unique_ads)
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def sync_facebook_lead_data(request):
    leadgen_id = request.data.get('leadgen_id')
    if not leadgen_id:
        return Response("leadgen_id is required", status=status.HTTP_400_BAD_REQUEST)
        
    try:
        lead = FacebookLead.objects.get(leadgen_id=leadgen_id)
    except FacebookLead.DoesNotExist:
        return Response("Lead not found", status=status.HTTP_404_NOT_FOUND)
        
    try:
        active_pages = FacebookPage.objects.filter(active_status='active')
        tokens = [page.page_access_token for page in active_pages]
        
        lead_data = get_lead_from_facebook_token_and_lead_id(leadgen_id, tokens)
        if not lead_data.get('success'):
            return Response({'success': False, 'message': lead_data.get('message', 'Failed to fetch lead')}, status=status.HTTP_400_BAD_REQUEST)
            
        lead.facebook_ad_detail = lead_data
        lead.synced = True
        lead.synced_at = timezone.now()
        lead.save()
        
        sync_res = sync_to_crm_leads_individual(lead)
        lead.crm_sync = sync_res.get('success', False)
        lead.crm_sync_at = timezone.now() if sync_res.get('success') else None
        lead.save()
        
        return Response({
            'success': True,
            'message': 'Lead synced successfully',
            'lead': FacebookLeadSerializer(lead).data
        })
    except Exception as e:
        return Response({'success': False, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def synced_data(request):
    try:
        body = request.data
        leadgen_id = body.get('leadgen_id')
        
        try:
            lead = FacebookLead.objects.get(leadgen_id=leadgen_id)
        except FacebookLead.DoesNotExist:
            lead = FacebookLead(leadgen_id=leadgen_id)
            lead.facebook_ad_detail = body
            lead.synced = True
            lead.synced_at = timezone.now()
            lead.save()
            
        lead.synced = True
        lead.synced_at = timezone.now()
        lead.facebook_ad_detail = body.get('facebookAdDetail') or body.get('facebook_ad_detail') or body
        lead.save()
        
        sync_res = sync_to_crm_leads_individual(lead)
        lead.crm_sync = sync_res.get('success', False)
        lead.crm_sync_at = timezone.now() if sync_res.get('success') else None
        lead.save()
        
        return Response("Lead synced successfully")
    except Exception as e:
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def passing_one_lead_to_crm(request):
    try:
        body = request.data
        lead_ids = body.get('leads', [])
        assigned_to = body.get('assigned_to')

        if not lead_ids:
            return Response({'success': False, 'message': 'No leads provided'}, status=status.HTTP_400_BAD_REQUEST)

        if not assigned_to:
            return Response({'success': False, 'message': 'assigned_to is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Import required models inline to avoid circular imports
        from HRM_App.models import (
            EmployeeDataModel, ActivityListModel, NewActivityModel,
            MonthAchivesListModel, NewDailyAchivesModel
        )

        # Find the target recruiter employee
        target_employee = EmployeeDataModel.objects.filter(
            EmployeeId=assigned_to,
            employeeProfile__employee_status='active'
        ).first()

        if not target_employee:
            return Response({'success': False, 'message': f'Employee {assigned_to} not found or inactive'}, status=status.HTTP_400_BAD_REQUEST)

        today = timezone.localtime().date()

        # Ensure the interview_calls activity and activity instance exist for this employee
        activity_list, _ = ActivityListModel.objects.get_or_create(
            activity_name='interview_calls',
            defaults={'added_by': target_employee}
        )

        new_activity_instance, _ = NewActivityModel.objects.get_or_create(
            Activity=activity_list,
            Employee=target_employee,
            Activity_assigned_Date__month=today.month,
            Activity_assigned_Date__year=today.year,
            defaults={
                'Activity_assigned_Date': today,
                'targets': 0,
                'activity_assigned_by': target_employee,
            }
        )

        month_achieve_instance, _ = MonthAchivesListModel.objects.get_or_create(
            Activity_instance=new_activity_instance,
            Date=today,
            defaults={'achieved': 0}
        )

        # Process each selected Facebook lead
        created_leads = []
        skipped_leads = []

        lead_instances = FacebookLead.objects.filter(leadgen_id__in=lead_ids)

        for lead in lead_instances:
            # Extract candidate info from facebook_ad_detail
            detail = lead.facebook_ad_detail or {}
            if not isinstance(detail, dict):
                skipped_leads.append(lead.leadgen_id)
                continue

            candidate_name = detail.get('full_name') or lead.full_name or ''
            candidate_phone = detail.get('phone') or lead.phone or ''
            candidate_email = detail.get('email') or ''
            candidate_location = detail.get('city') or detail.get('state') or ''
            candidate_designation = detail.get('position_applied_for') or detail.get('position') or ''

            if not candidate_phone:
                skipped_leads.append(lead.leadgen_id)
                continue

            # Skip only if this exact Facebook lead was already transferred (crm_sync=True)
            if lead.crm_sync:
                skipped_leads.append(lead.leadgen_id)
                continue

            # Always create a fresh candidate lead for this Facebook lead
            NewDailyAchivesModel.objects.create(
                current_day_activity=month_achieve_instance,
                assigned_by=target_employee,
                candidate_name=candidate_name,
                candidate_phone=candidate_phone,
                candidate_email=candidate_email,
                candidate_location=candidate_location,
                candidate_designation=candidate_designation,
                sourcing_channel='facebook',
                source=lead.ad_name or 'facebook',
                lead_status='active',
                lead_stage='newlead',
                current_status='newlead',
                interview_status=None,
            )

            created_leads.append(lead.leadgen_id)

        # Mark transferred leads as CRM synced
        if created_leads:
            FacebookLead.objects.filter(leadgen_id__in=created_leads).update(
                crm_sync=True,
                crm_sync_at=timezone.now()
            )

            # Update recruiter's daily achievement count
            achievement_count = NewDailyAchivesModel.objects.filter(
                current_day_activity=month_achieve_instance
            ).exclude(lead_status='staged').count()
            month_achieve_instance.achieved = achievement_count
            month_achieve_instance.save()

        return Response({
            'success': True,
            'message': f'{len(created_leads)} lead(s) transferred successfully to {target_employee.Name}.',
            'created': created_leads,
            'skipped': skipped_leads
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
