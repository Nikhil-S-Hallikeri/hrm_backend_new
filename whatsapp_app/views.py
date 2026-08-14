from rest_framework import viewsets, status, serializers
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from datetime import timedelta
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.db.models import Q, Max, F
from django.utils import timezone
import datetime
from django.utils.dateparse import parse_datetime
from django.conf import settings
from django.http import HttpResponse
import requests
import threading
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import logging

logger = logging.getLogger(__name__)


def _download_and_save_media(message_id, media_id, token):
    try:
        from .models import Message
        from .views import _broadcast_crm_event

        headers = {"Authorization": f"Bearer {token}"}
        import requests

        url_response = requests.get(
            f"https://graph.facebook.com/v20.0/{media_id}", headers=headers, timeout=10
        )
        if url_response.status_code == 200:
            dl_url = url_response.json().get("url")
            mime_type = url_response.json().get("mime_type", "image/jpeg")
            if dl_url:
                media_response = requests.get(dl_url, headers=headers, timeout=15)
                if media_response.status_code == 200:
                    ext = mime_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    if len(ext) > 5:
                        ext = "bin"
                    filename = f"incoming_messages/{media_id}.{ext}"
                    saved_path = default_storage.save(
                        filename, ContentFile(media_response.content)
                    )

                    # Update DB
                    msg = Message.objects.get(id=message_id)
                    msg.media_url = f"/media/{saved_path}"
                    msg.save(update_fields=["media_url"])

                    # Broadcast to frontend to refresh the image!
                    _broadcast_crm_event(
                        "new_message", contact=msg.contact, message=msg
                    )

    except Exception as e:
        logger.warning(f"Failed to download incoming media in background: {e}")


import re
import uuid
import logging
from user_agents import parse
from whatsapp_app.serializers import (
    LoginSerializers,
    SignupWithOTPSerializer,
    VerifySignupOTPSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
    UserPreferenceSerializer,
    ContactSerializer,
    ContactGroupSerializer,
    TemplateSerializer,
    CampaignSerializer,
    CampaignListSerializer,
    CampaignDetailSerializer,
    CampaignCreateSerializer,
    CampaignHistorySerializer,
    CampaignScheduledSerializer,
    MessageSerializer,
    MessageTemplateSerializer,
    MessageTemplateListSerializer,
    WebhookEventSerializer,
    WhatsAppConfigSerializer,
    LoginSessionSerializer,
)
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from whatsapp_app.models import (
    User,
    Contact,
    ContactGroup,
    Template,
    Campaign,
    Message,
    MessageTemplate,
    WhatsAppConfig,
    LoginSession,
    Notification,
    Category,
    SubCategory,
    Product,
)
from whatsapp_app.permissions import HasActiveSubscription

from whatsapp_app.utils import (
    create_otp_record,
    send_signup_otp_to_admin,
    send_signup_otp_to_user,
    verify_otp,
    send_account_approval_email,
    send_password_reset_otp,
    send_password_reset_confirmation,
    extract_variables,
    execute_campaign,
    get_public_api_user,
    _normalize_phone_number,
    get_whatsapp_config,
    get_whatsapp_headers,
    extract_provider_message_id,
    extract_media_url_from_components,
    _broadcast_crm_event,
)

logger = logging.getLogger(__name__)


def get_whatsapp_config_id(request):
    config_id = request.headers.get("X-WhatsApp-Config-ID") or request.META.get(
        "HTTP_X_WHATSAPP_CONFIG_ID"
    )
    tenant_email = request.headers.get("X-Tenant-Email") or request.META.get(
        "HTTP_X_TENANT_EMAIL"
    )
    user = getattr(request, "user", None)

    if (
        (not user or not user.is_authenticated)
        and tenant_email
        and tenant_email not in ["None", "null", "undefined"]
    ):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        u = User.objects.filter(email__iexact=tenant_email.strip()).first()
        if u:
            user = u

    if config_id:
        try:
            config_id = int(config_id)
            if user and user.is_authenticated:
                # 1. Superusers have access to all configs
                if getattr(user, "is_superuser", False):
                    return config_id

                # 2. Direct owners have access
                if WhatsAppConfig.objects.filter(id=config_id, user=user).exists():
                    return config_id

                # 3. Synced employees/agents mapped to this configuration in the SaaS mapping table
                from django.db import connection, DatabaseError

                try:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT whatsapp_config_id FROM whatsapp_saas_whatsappuser WHERE user_id = %s",
                            [user.id],
                        )
                        row = cursor.fetchone()
                        if row and row[0] == config_id:
                            return config_id
                except DatabaseError:
                    pass

                # Fallback to user's first config or create default if requested config is not valid/owned
                first_config = (
                    WhatsAppConfig.objects.filter(user=user).order_by("id").first()
                )
                if first_config:
                    return first_config.id

                default_config = WhatsAppConfig.objects.create(
                    user=user, name="Default WhatsApp", is_ai_enabled=True
                )
                return default_config.id
            else:
                return config_id
        except ValueError:
            pass

    # Fallback to the first config belonging to this user
    if user and user.is_authenticated:
        # Check if they mapped to a config first
        from django.db import connection, DatabaseError

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT whatsapp_config_id FROM whatsapp_saas_whatsappuser WHERE user_id = %s",
                    [user.id],
                )
                row = cursor.fetchone()
                if row and row[0]:
                    return row[0]
        except DatabaseError:
            pass

        first_config = WhatsAppConfig.objects.filter(user=user).order_by("id").first()
        if first_config:
            return first_config.id

        default_config = WhatsAppConfig.objects.create(
            user=user, name="Default WhatsApp", is_ai_enabled=True
        )
        return default_config.id

    # For non-authenticated requests (e.g. public API webhooks), fall back to global first config
    from whatsapp_app.middleware import get_current_request_config_id

    mid_id = get_current_request_config_id()
    if mid_id:
        return mid_id
    config = WhatsAppConfig.objects.order_by("id").first()
    if config:
        return config.id

    return None


from whatsapp_app.services import (
    send_whatsapp_message,
    create_whatsapp_template,
    delete_whatsapp_template_from_meta,
)


def _resolve_pricing_date_range(
    request, max_lookback_days=89, default_range="last_7_days"
):
    """
    Shared date-range resolution for the Message Pricing insights endpoints.
    Returns (start_date, end_date, range_key, clamped) or None on an invalid custom range.
    Clamped to max_lookback_days since Meta's pricing_analytics only retains ~90 days
    of DAILY-granularity history.
    """
    from datetime import date

    today = timezone.localdate()
    range_key = (request.query_params.get("range") or default_range).lower()
    start_param = request.query_params.get("start_date")
    end_param = request.query_params.get("end_date")

    if range_key == "today":
        start_date, end_date = today, today
    elif range_key == "yesterday":
        start_date = end_date = today - timedelta(days=1)
    elif range_key == "last_7_days":
        start_date, end_date = today - timedelta(days=6), today
    elif range_key == "last_30_days":
        start_date, end_date = today - timedelta(days=29), today
    elif range_key == "custom" and start_param and end_param:
        try:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)
            if end_date < start_date:
                start_date, end_date = end_date, start_date
        except ValueError:
            return None
    else:
        start_date, end_date = today - timedelta(days=max_lookback_days), today

    oldest_allowed = today - timedelta(days=max_lookback_days)
    clamped = start_date < oldest_allowed
    if clamped:
        start_date = oldest_allowed

    return start_date, end_date, range_key, clamped


def _serialize_event_payload(event_type, contact=None, message=None, extra=None):
    from whatsapp_app.utils import _serialize_event_payload as serialize_payload

    return serialize_payload(event_type, contact=contact, message=message, extra=extra)


def _create_and_broadcast_notification(contact, message, notif_type="new_message"):
    """
    Creates a Notification DB record and broadcasts it via WebSocket
    to all connected agents in the 'notifications_all' group.
    Idempotent: uses get_or_create keyed on message_id + notification_type.
    """
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            return

        contact_name = getattr(contact, "name", None)
        contact_phone = getattr(contact, "phone_number", None) or ""
        msg_text = getattr(message, "text", "") or ""
        msg_id = getattr(message, "provider_message_id", None) or str(
            getattr(message, "id", "")
        )
        display_name = contact_name or contact_phone or "Unknown"
        title = f"New message from {display_name}"
        preview = msg_text[:80] + ("â€¦" if msg_text and len(msg_text) > 80 else "")

        # Idempotent create â€” skip if already exists for this message + type
        notif, created = Notification.objects.get_or_create(
            message_id=msg_id,
            notification_type=notif_type,
            defaults={
                "title": title,
                "message": preview,
                "contact_phone": contact_phone,
                "contact_name": contact_name,
                "is_read": False,
                "whatsapp_config": contact.whatsapp_config,
            },
        )

        if not created:
            # Already broadcasted for this message; skip
            return

        unread_count = Notification.objects.filter(
            whatsapp_config=contact.whatsapp_config, is_read=False
        ).count()

        notif_payload = {
            "event": "new_notification",
            "notification": {
                "id": notif.id,
                "type": notif_type,
                "title": title,
                "message": preview,
                "contact_phone": contact_phone,
                "contact_name": contact_name,
                "is_read": False,
                "created_at": notif.created_at.isoformat(),
                "whatsapp_config_id": contact.whatsapp_config_id,
            },
            "unread_count": unread_count,
        }

        from whatsapp_app.consumers import NOTIFICATIONS_GROUP

        async_to_sync(channel_layer.group_send)(
            NOTIFICATIONS_GROUP, {"type": "notification_event", "data": notif_payload}
        )
    except Exception as e:
        import traceback

        with open("webhook_debug.log", "a") as f_log:
            f_log.write(f"\n[NOTIFICATION ERROR] {str(e)}\n{traceback.format_exc()}\n")


def perform_template_sync(config=None):
    """
    Core logic to sync live templates for the configured WABA/Facebook ID.
    Returns (created_count, updated_count, deleted_count, error_msg)
    """
    if not config:
        config = WhatsAppConfig.get_solo()
    if not config:
        return 0, 0, 0, "No active WhatsApp configuration found."

    waba_id = (config.whatsapp_business_account_id or "").strip()
    access_token = (config.whatsapp_api_token or "").strip()

    def _fetch_templates_from_meta():
        graph_version = getattr(settings, "META_GRAPH_API_VERSION", "v20.0")
        endpoint = (
            f"https://graph.facebook.com/{graph_version}/{waba_id}/message_templates"
        )
        templates = []
        params = {
            "access_token": access_token,
            "fields": "id,name,status,category,language,components",
            "limit": 100,
        }

        while endpoint:
            response = requests.get(endpoint, params=params, timeout=20)
            if response.status_code != 200:
                return None, f"Meta error: {response.status_code} - {response.text}"

            payload = response.json()
            templates.extend(payload.get("data", []))
            endpoint = (payload.get("paging") or {}).get("next")
            params = None

        return templates, None

    def _fetch_templates_from_flask():
        headers, flask_url = get_whatsapp_headers(config_id=config.id)
        endpoint = f"{flask_url}/api/templates/list"
        params = {
            "whatsapp_business_account_id": waba_id,
            "waba_id": waba_id,
            "phone_number_id": config.phone_number_id or "",
            "app_id": config.whatsapp_app_id or "",
        }

        response = requests.get(endpoint, headers=headers, params=params, timeout=20)
        if response.status_code != 200:
            return None, f"Flask error: {response.status_code}"

        payload = response.json()
        return payload.get("templates", []), None

    endpoint = "Meta Graph" if waba_id and access_token else "Flask template list"

    try:
        if waba_id and access_token:
            templates_data, fetch_error = _fetch_templates_from_meta()
        else:
            templates_data, fetch_error = _fetch_templates_from_flask()

        if fetch_error:
            return 0, 0, 0, fetch_error

        synced_names = []
        created_count = 0
        updated_count = 0

        def _extract_body(components):
            for comp in components or []:
                if str(comp.get("type", "")).upper() == "BODY":
                    return comp.get("text") or ""
            return ""

        def _extract_header(components):
            for comp in components or []:
                if str(comp.get("type", "")).upper() == "HEADER":
                    fmt = comp.get("format", "NONE")
                    text = comp.get("text")
                    sample_values = {}
                    example = comp.get("example", {})
                    if example.get("header_handle"):
                        handle = example.get("header_handle")[0]
                        sample_values["header_handle"] = handle

                        # Convert ephemeral Facebook/WhatsApp CDN URLs to permanent Base64 Data URLs
                        if (
                            handle
                            and isinstance(handle, str)
                            and handle.startswith("http")
                            and ("fbcdn" in handle or "whatsapp" in handle)
                        ):
                            try:
                                import base64

                                resp = requests.get(handle, timeout=15)
                                if resp.ok:
                                    mime = resp.headers.get(
                                        "Content-Type", "image/jpeg"
                                    )
                                    b64 = base64.b64encode(resp.content).decode("utf-8")
                                    sample_values["header_handle"] = (
                                        f"data:{mime};base64,{b64}"
                                    )
                            except Exception as e:
                                print(f"Failed to cache template header media: {e}")

                    return fmt, text, sample_values
            return "NONE", None, {}

        def _extract_footer(components):
            for comp in components or []:
                if str(comp.get("type", "")).upper() == "FOOTER":
                    return comp.get("text")
            return None

        for t_data in templates_data or []:
            name = (t_data.get("name") or "").strip()
            if not name:
                continue

            synced_names.append(name)
            status = str(t_data.get("status", "PENDING")).upper()
            if status == "PENDING_REVIEW":
                status = "PENDING"

            body = _extract_body(t_data.get("components"))
            h_type, h_text, h_sample = _extract_header(t_data.get("components"))

            meta_media = h_sample.get("header_handle") if h_sample else None
            # Do not store massive base64 strings in the fixed-length URLFields.
            # They will fall back to being read from sample_values JSON.
            if meta_media and meta_media.startswith("data:"):
                meta_media = None
            footer = _extract_footer(t_data.get("components"))
            template_variables = extract_variables(body)

            # Find and update or create
            template, created = MessageTemplate.objects.update_or_create(
                name=name,
                whatsapp_config=config,
                defaults={
                    "body": body,
                    "category": str(t_data.get("category") or "MARKETING").upper(),
                    "status": status,
                    "language": t_data.get("language") or "en_US",
                    "header_type": h_type,
                    "header_text": h_text,
                    "sample_values": h_sample,
                    "meta_media_url": meta_media,
                    "header_media": meta_media,
                    "footer_text": footer,
                    "buttons": next(
                        (
                            c.get("buttons", [])
                            for c in t_data.get("components", [])
                            if c.get("type") == "BUTTONS"
                        ),
                        [],
                    ),
                    "variables": template_variables,
                    "variables_count": len(template_variables),
                    "last_synced_at": timezone.now(),
                },
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        deleted_count, _ = (
            MessageTemplate.objects.filter(whatsapp_config=config)
            .exclude(name__in=synced_names)
            .delete()
        )

        return created_count, updated_count, deleted_count, None

    except requests.exceptions.RequestException as e:
        print(f"âš ï¸ Flask Server Connection Offline (URL: {endpoint}): {e}")
        return 0, 0, 0, "Template sync service is currently offline or unreachable."
    except Exception as e:
        import traceback

        print(traceback.format_exc())
        return 0, 0, 0, str(e)


from asgiref.sync import async_to_sync


def broadcast_user_status(user_id, is_online):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "user_status",
        {
            "type": "status_update",
            "message": {
                "user_id": user_id,
                "is_online": is_online,
                "last_seen": timezone.now().isoformat(),
            },
        },
    )


class LoginViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializers

    def get_client_ip(self, request):
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded:
            return x_forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def get_location(self, ip):
        try:
            # Using ip-api.com (free for development)
            r = requests.get(f"http://ip-api.com/json/{ip}", timeout=3)
            data = r.json()
            if data.get("status") == "success":
                return data.get("city", ""), data.get("country", "")
        except:
            pass
        return "", ""

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        # Generate token
        refresh = RefreshToken.for_user(user)
        jti = refresh.get("jti")  # SimpleJWT generates JTI automatically
        refresh.access_token["refresh_jti"] = jti

        # Track session
        ip = self.get_client_ip(request)
        ua = parse(request.META.get("HTTP_USER_AGENT", ""))
        city, country = self.get_location(ip)

        # Deactivate previous 'current' flag for this user
        LoginSession.objects.filter(user=user).update(is_current=False)

        # Check if a session already exists for this exact device + IP
        existing_session = LoginSession.objects.filter(
            user=user,
            ip_address=ip,
            device_name=ua.device.family,
            browser=ua.browser.family,
            os=ua.os.family,
        ).first()

        if existing_session:
            # Update the existing session instead of creating a new one
            existing_session.jti = jti
            existing_session.is_current = True
            existing_session.is_active = True
            existing_session.logged_in_at = timezone.now()
            existing_session.last_active = timezone.now()
            existing_session.save()
        else:
            # Create new session
            LoginSession.objects.create(
                user=user,
                jti=jti,
                ip_address=ip,
                device_name=ua.device.family,
                browser=ua.browser.family,
                os=ua.os.family,
                location_city=city,
                location_country=country,
                is_current=True,
                is_active=True,
            )

        # Update user status
        user.is_online = True
        user.last_seen = timezone.now()
        user.save(update_fields=["is_online", "last_seen"])

        # Broadcast status via WebSocket
        broadcast_user_status(user.id, True)

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "user_id": user.id,
                "name": user.name,
                "role": user.role,
                "email": user.email,
                "phone_number": user.phone_number,
                "theme_preference": user.theme_preference,
            }
        )


class SignupViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = SignupWithOTPSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_user_data = {
            "email": serializer.validated_data["email"],
            "password_hash": make_password(serializer.validated_data["password"]),
            "role": serializer.validated_data.get("role", "ADMIN"),
        }
        otp_record = create_otp_record(
            email=serializer.validated_data["email"],
            otp_type="signup",
            user_data=otp_user_data,
        )
        # Send OTP to admin for approval
        send_signup_otp_to_admin(
            email=serializer.validated_data["email"],
            role=serializer.validated_data.get("role", "ADMIN"),
            otp=otp_record.otp,
        )
        # Send OTP to host email (EMAIL_HOST_USER) instead of user's signup email
        email_sent = send_signup_otp_to_user(
            email=settings.EMAIL_HOST_USER, otp=otp_record.otp
        )
        if not email_sent:
            return Response(
                {
                    "error": "Failed to send signup OTP email. Please verify your email address or try again later."
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "message": "Signup OTP sent. Please check your inbox and verify to complete signup.",
                "email": serializer.validated_data["email"],
            }
        )


class VerifySignupViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = VerifySignupOTPSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = verify_otp(
            serializer.validated_data["email"],
            serializer.validated_data["otp"],
            "signup",
        )
        if not otp_record:
            return Response(
                {"error": "Invalid or expired OTP. Please request a new signup."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_data = otp_record.user_data
        if not user_data or "password_hash" not in user_data:
            return Response(
                {"error": "Signup data is invalid. Please request a new signup."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():  # type: ignore
            user = User(email=user_data["email"], role=user_data.get("role", "ADMIN"))
            user.password = user_data["password_hash"]
            user.save()
            otp_record.is_verified = True
            otp_record.save(update_fields=["is_verified"])

        send_account_approval_email(user_data["email"])
        return Response(
            {
                "message": "Signup completed successfully! You can now login with your credentials.",
                "email": user_data["email"],
                "role": user_data.get("role", "ADMIN"),
            },
            status=status.HTTP_201_CREATED,
        )


class ForgotPasswordViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = create_otp_record(
            email=serializer.validated_data["email"], otp_type="forgot_password"
        )
        send_password_reset_otp(serializer.validated_data["email"], otp_record.otp)
        return Response({"message": "OTP sent to email"})


class ResetPasswordViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = ResetPasswordSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        otp_record = verify_otp(
            serializer.validated_data["email"],
            serializer.validated_data["otp"],
            "forgot_password",
        )
        if not otp_record:
            return Response(
                {"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.get(email=serializer.validated_data["email"])
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        otp_record.is_verified = True
        otp_record.save()
        send_password_reset_confirmation(user.email)
        return Response({"message": "Password reset successful"})


class ChangePasswordViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user

        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": ["Wrong password."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response(
            {"message": "Password updated successfully."}, status=status.HTTP_200_OK
        )


class LogoutViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]
    serializer_class = LogoutSerializer

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            token = RefreshToken(serializer.validated_data["refresh"])

            # Deactivate LoginSession matching this token's JTI
            jti = token.get("jti")
            if jti:
                LoginSession.objects.filter(jti=jti).update(
                    is_active=False, is_current=False
                )

                # Check if user has any other active sessions
                user_id = token.get("user_id")
                if not LoginSession.objects.filter(
                    user_id=user_id, is_active=True
                ).exists():
                    User.objects.filter(id=user_id).update(
                        is_online=False, last_seen=timezone.now()
                    )
                    broadcast_user_status(user_id, False)

            token.blacklist()
        except TokenError:
            return Response(
                {"error": "Invalid refresh token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "Logged out successfully"})


class UserPreferencesViewSet(viewsets.GenericViewSet):
    """ViewSet for managing user preferences like theme"""

    permission_classes = [AllowAny]

    @action(detail=False, methods=["get", "patch"])
    def me(self, request):
        """Get or update current user profile and preferences"""
        user = (
            request.user
            if getattr(request.user, "is_authenticated", False)
            else get_public_api_user()
        )

        if request.method == "PATCH":
            name = request.data.get("name")
            if name is not None:
                user.name = name.strip()
            phone_number = request.data.get("phone_number")
            if phone_number is not None:
                user.phone_number = phone_number.strip()
            email = request.data.get("email")
            if email is not None and email.strip():
                user.email = email.strip()

            user.save()

        # Get configuration limit from SaaS table
        from django.db import connection

        limit = 1
        catalog_access = True
        crm_access = True
        whatsapp_access = True
        ai_config_access = True
        chatbot_access = True
        followup_access = True
        reminder_access = True
        autoreply_access = True
        if user and getattr(user, "is_authenticated", False):
            if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
                limit = 9999
                catalog_access = True
                crm_access = True
                whatsapp_access = True
                ai_config_access = True
                chatbot_access = True
            else:
                with connection.cursor() as cursor:
                    try:
                        cursor.execute(
                            "SELECT app_limit, catalog_access, crm_access, ai_config_access, chatbot_access, followup_access, reminder_access, autoreply_access, whatsapp_access FROM whatsapp_saas_whatsappuser WHERE user_id = %s",
                            [user.id],
                        )
                        row = cursor.fetchone()
                        if row:
                            limit = int(row[0])
                            catalog_access = bool(row[1])
                            crm_access = bool(row[2])
                            ai_config_access = bool(row[3])
                            chatbot_access = bool(row[4])
                            followup_access = bool(row[5])
                            reminder_access = bool(row[6])
                            autoreply_access = bool(row[7])
                            whatsapp_access = bool(row[8])
                    except Exception:
                        pass

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "name": user.name or "",
                "role": user.role,
                "phone_number": user.phone_number or "",
                "theme_preference": user.theme_preference,
                "config_limit": limit,
                "catalog_access": catalog_access,
                "crm_access": crm_access,
                "whatsapp_access": whatsapp_access,
                "ai_config_access": ai_config_access,
                "chatbot_access": chatbot_access,
                "followup_access": followup_access,
                "reminder_access": reminder_access,
                "autoreply_access": autoreply_access,
            }
        )

    @action(detail=True, methods=["get"], url_path="profile")
    def user_profile(self, request, pk=None):
        """Get specific user profile by ID"""
        try:
            user = User.objects.get(pk=pk)
            return Response(
                {
                    "id": user.id,
                    "name": user.email.split("@")[0].replace(".", " ").title(),
                    "email": user.email,
                    "role": user.role,
                    "role_display": user.get_role_display(),
                    "phone_number": user.phone_number or "",
                    "is_active": user.is_active,
                }
            )
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["patch"])
    def theme(self, request):
        """Update theme preference"""
        serializer = UserPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = get_public_api_user()
        validated_data = serializer.validated_data or {}
        user.theme_preference = validated_data.get("theme_preference", "auto")
        user.save(update_fields=["theme_preference"])

        return Response(
            {
                "message": "Theme preference updated",
                "theme_preference": user.theme_preference,
            }
        )


# Contact ViewSet
class ContactPagination(PageNumberPagination):
    page_size = 1000
    page_size_query_param = "page_size"
    max_page_size = 10000


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet for managing contacts"""

    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = ContactSerializer
    pagination_class = ContactPagination

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        queryset = Contact.objects.filter(whatsapp_config_id=config_id)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(phone_number__icontains=search)
            )

        group_id = self.request.query_params.get("group")
        if group_id:
            queryset = queryset.filter(groups__id=group_id)

        date_from = self.request.query_params.get("created_from")
        date_to = self.request.query_params.get("created_to")
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)

        return queryset.order_by(
            F("last_message_time").desc(nulls_last=True), "-created_at"
        )

    def perform_create(self, serializer):
        user = (
            self.request.user
            if getattr(self.request.user, "is_authenticated", False)
            else get_public_api_user()
        )
        config_id = get_whatsapp_config_id(self.request)
        contact = serializer.save(user=user, whatsapp_config_id=config_id)

        # Trigger auto-send template if configured
        config = contact.whatsapp_config
        if config and config.auto_send_template and config.auto_send_template_name:
            try:
                from whatsapp_app.services import send_whatsapp_message_direct_to_meta

                cached_tpl = MessageTemplate.objects.filter(
                    name=config.auto_send_template_name, whatsapp_config=config
                ).first()
                lang = "en_US"
                body_text = f"Sent template: {config.auto_send_template_name}"
                if cached_tpl:
                    lang = cached_tpl.language
                    body_text = cached_tpl.body
                else:
                    from whatsapp_app.models import WhatsAppTemplate

                    whatsapp_tpl = WhatsAppTemplate.objects.filter(
                        template_name=config.auto_send_template_name,
                        whatsapp_config=config,
                    ).first()
                    if whatsapp_tpl:
                        lang = whatsapp_tpl.language
                        body_text = whatsapp_tpl.body_text

                import uuid
                from django.utils import timezone

                provider_message_id = str(uuid.uuid4())

                meta_response, status_code = send_whatsapp_message_direct_to_meta(
                    recipient_id=contact.phone_number,
                    waba_config=config,
                    template_name=config.auto_send_template_name,
                    language_code=lang,
                    components=[],
                )

                if status_code in (200, 201):
                    # Save outgoing template message
                    Message.objects.create(
                        contact=contact,
                        text=body_text,
                        sender="agent",
                        direction="OUTGOING",
                        status="Sent",
                        type="template",
                        provider_message_id=provider_message_id,
                        timestamp=timezone.now(),
                    )
                    contact.last_message = body_text
                    contact.last_message_time = timezone.now()
                    contact.save(update_fields=["last_message", "last_message_time"])
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(
                    f"Failed to auto-send new contact template: {e}"
                )

    def create(self, request, *args, **kwargs):
        """Override create to prevent duplicate contacts with the same phone number."""
        phone_number = request.data.get("phone_number", "")
        phone_number = (
            _normalize_phone_number(phone_number) if phone_number else phone_number
        )
        if phone_number:
            user = (
                request.user
                if getattr(request.user, "is_authenticated", False)
                else get_public_api_user()
            )
            config_id = get_whatsapp_config_id(request)
            existing = Contact.objects.filter(
                phone_number=phone_number, whatsapp_config_id=config_id
            ).first()
            if existing:
                # Update name if a non-empty name was provided and existing has none
                new_name = request.data.get("name", "").strip()
                if new_name and (
                    not existing.name or existing.name == existing.phone_number
                ):
                    existing.name = new_name
                    existing.save(update_fields=["name"])
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)
        return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["PATCH"], url_path=r"(?P<phone>[^/.]+)/mark-read")
    def mark_read_by_phone(self, request, phone=None):
        config_id = get_whatsapp_config_id(request)
        contact = (
            Contact.objects.filter(phone_number=phone, whatsapp_config_id=config_id)
            .order_by("id")
            .first()
        )
        if not contact:
            return Response(
                {"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND
            )

        contact.unread_count = 0
        contact.save(update_fields=["unread_count"])
        now = timezone.now()
        Message.objects.filter(
            contact=contact, direction="INCOMING", read=False
        ).update(
            read=True,
            status="Read",
            read_at=now,
        )
        _broadcast_crm_event(
            "message_read",
            contact=contact,
            extra={
                "data": {
                    "contact_id": contact.id,
                    "phone_number": contact.phone_number,
                    "unread_count": 0,
                }
            },
        )
        _broadcast_crm_event(
            "unread_updated",
            contact=contact,
            extra={
                "data": {
                    "contact_id": contact.id,
                    "phone_number": contact.phone_number,
                    "unread_count": 0,
                }
            },
        )

        return Response(ContactSerializer(contact).data)

    @action(detail=False, methods=["POST"], url_path="bulk")
    def bulk_create(self, request):
        if not isinstance(request.data, list):
            return Response(
                {"error": "Expected a list of contact objects."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        raw_numbers = []
        for item in request.data:
            num = item.get("phone_number")
            if num:
                normalized = _normalize_phone_number(num)
                raw_numbers.append(normalized)

        if len(raw_numbers) != len(set(raw_numbers)):
            return Response(
                {
                    "error": "Duplicate phone numbers (including formatted ones) found in request payload."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rows whose phone number already exists for this config are skipped rather than failing
        # the whole batch. Scoped by whatsapp_config_id only (no user filter) - same scope
        # ContactViewSet.create() already uses for its single-contact dedupe check above, since
        # this ModelViewSet requires IsAuthenticated so request.user is always the real tenant
        # user, not get_public_api_user() (that's only the anonymous-request fallback below,
        # matching perform_create's pattern) - checking existence under the wrong user here
        # would silently let true duplicates through to the serializer's own per-row uniqueness
        # validator, which fails the same "must be unique per user" error for the whole batch.
        target_user = (
            request.user
            if getattr(request.user, "is_authenticated", False)
            else get_public_api_user()
        )
        config_id = get_whatsapp_config_id(request)
        existing_by_number = {
            c["phone_number"]: c["id"]
            for c in Contact.objects.filter(
                whatsapp_config_id=config_id, phone_number__in=raw_numbers
            ).values("phone_number", "id")
        }

        rows_to_create = []
        skipped_numbers = []
        skipped_contact_ids = []
        for item in request.data:
            normalized = _normalize_phone_number(item.get("phone_number") or "")
            if normalized and normalized in existing_by_number:
                skipped_numbers.append(normalized)
                skipped_contact_ids.append(existing_by_number[normalized])
            else:
                rows_to_create.append(item)

        if not rows_to_create:
            return Response(
                {
                    "created": 0,
                    "skipped_existing": len(skipped_numbers),
                    "skipped_numbers": skipped_numbers,
                    "skipped_contact_ids": skipped_contact_ids,
                    "results": [],
                },
                status=status.HTTP_200_OK,
            )

        serializer = self.get_serializer(data=rows_to_create, many=True)
        try:
            serializer.is_valid(raise_exception=True)
        except serializers.ValidationError as ve:
            # Debug log to file
            with open("webhook_debug.log", "a") as f_log:
                f_log.write(f"\n!!! BULK VALIDATION ERROR AT {timezone.now()} !!!\n")
                f_log.write(f"Errors: {serializer.errors}\n")
                # Log first 2 items of payload for context
                f_log.write(f"Payload Sample: {rows_to_create[:2]}\n")

            return Response(
                {
                    "error": "Validation failed for one or more rows.",
                    "details": serializer.errors,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():  # type: ignore
                serializer.save(user=target_user, whatsapp_config_id=config_id)
            return Response(
                {
                    "created": len(serializer.data),
                    "skipped_existing": len(skipped_numbers),
                    "skipped_numbers": skipped_numbers,
                    "skipped_contact_ids": skipped_contact_ids,
                    "results": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            error_msg = str(e)
            if (
                "UNIQUE constraint failed" in error_msg
                or "Duplicate entry" in error_msg
            ):
                return Response(
                    {
                        "error": "Some contacts already exist in the database with the same phone number."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                {"error": f"Failed to save bulk contacts: {error_msg}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


# Contact Group ViewSet
class ContactGroupViewSet(viewsets.ModelViewSet):
    """ViewSet for managing contact groups (tags) used to segment the Contacts page and campaign targeting."""

    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = ContactGroupSerializer

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        return ContactGroup.objects.filter(whatsapp_config_id=config_id)

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        user = (
            self.request.user
            if getattr(self.request.user, "is_authenticated", False)
            else None
        )
        serializer.save(whatsapp_config_id=config_id, created_by=user)

    @action(detail=True, methods=["POST"], url_path="add-contacts")
    def add_contacts(self, request, pk=None):
        group = self.get_object()
        contact_ids = request.data.get("contact_ids", [])
        config_id = get_whatsapp_config_id(request)
        contacts = Contact.objects.filter(
            id__in=contact_ids, whatsapp_config_id=config_id
        )
        group.contacts.add(*contacts)
        return Response(
            {"added": contacts.count(), "total_in_group": group.contacts.count()}
        )

    @action(detail=True, methods=["POST"], url_path="remove-contacts")
    def remove_contacts(self, request, pk=None):
        group = self.get_object()
        contact_ids = request.data.get("contact_ids", [])
        config_id = get_whatsapp_config_id(request)
        contacts = Contact.objects.filter(
            id__in=contact_ids, whatsapp_config_id=config_id
        )
        group.contacts.remove(*contacts)
        return Response(
            {"removed": contacts.count(), "total_in_group": group.contacts.count()}
        )


# Template ViewSet
class TemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing message templates"""

    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = TemplateSerializer

    def get_queryset(self):
        return Template.objects.all()

    def perform_create(self, serializer):
        serializer.save(created_by=get_public_api_user())

    @action(detail=False, methods=["get"])
    def approved(self, request):
        """Get only approved templates"""
        templates = self.get_queryset().filter(status="APPROVED")
        serializer = self.get_serializer(templates, many=True)
        return Response(serializer.data)


# Campaign ViewSet
class CampaignViewSet(viewsets.ModelViewSet):
    """ViewSet for managing campaigns"""

    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        return Campaign.objects.filter(whatsapp_config_id=config_id)

    def get_serializer_class(self):
        if self.action == "create_campaign":
            return CampaignCreateSerializer
        if self.action == "history":
            return CampaignHistorySerializer
        if self.action == "scheduled":
            return CampaignScheduledSerializer
        if self.action == "retrieve":
            return CampaignDetailSerializer
        if self.action in ["update", "partial_update"]:
            return CampaignSerializer
        return CampaignListSerializer

    def perform_update(self, serializer):
        data = self.request.data
        template_id = data.get("template_id")
        if template_id is not None:
            if template_id:
                try:
                    template = MessageTemplate.objects.get(id=template_id)
                    serializer.validated_data["template"] = template
                except MessageTemplate.DoesNotExist:
                    pass
            else:
                serializer.validated_data["template"] = None

        header_media_file = self.request.FILES.get("header_media_file")
        if header_media_file:
            from django.core.files.storage import default_storage

            file_name = default_storage.save(
                f"campaign_media/{header_media_file.name}", header_media_file
            )
            file_url = self.request.build_absolute_uri(default_storage.url(file_name))

            # Extract variables (it might be a string if sent via FormData, but update uses JSON usually. Just to be safe:)
            variables = data.get("variables", serializer.instance.variables or {})
            if isinstance(variables, str):
                import json

                try:
                    variables = json.loads(variables)
                except:
                    pass
            if isinstance(variables, dict):
                variables["__header_media_url__"] = file_url
                variables["__header_media_type__"] = header_media_file.content_type
                serializer.validated_data["variables"] = variables

        instance = serializer.save()

        contact_ids = data.get("contact_ids")
        if contact_ids is not None:
            if isinstance(contact_ids, str):
                import json

                try:
                    contact_ids = json.loads(contact_ids)
                except:
                    pass
            if isinstance(contact_ids, list):
                contacts = Contact.objects.filter(id__in=contact_ids)
                instance.contacts.set(contacts)

        instance.total_contacts = instance.contacts.count()
        instance.save(update_fields=["total_contacts"])

    def _message_template_from_whatsapp_template(self, whatsapp_template_id):
        # Fetch directly from MessageTemplate (unified model)
        try:
            template = MessageTemplate.objects.get(id=whatsapp_template_id)
            return template, None
        except MessageTemplate.DoesNotExist:
            return None, Response(
                {"error": "Template does not exist"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], url_path="create")
    def create_campaign(self, request):
        data = request.data.copy() if hasattr(request.data, "copy") else request.data

        # Parse JSON strings if data came from FormData
        if isinstance(data.get("contact_ids"), str):
            import json

            try:
                data["contact_ids"] = json.loads(data["contact_ids"])
            except json.JSONDecodeError:
                pass

        if isinstance(data.get("variables"), str):
            import json

            try:
                data["variables"] = json.loads(data["variables"])
            except json.JSONDecodeError:
                pass

        header_media_file = request.FILES.get("header_media_file")
        if header_media_file:
            from django.core.files.storage import default_storage

            file_name = default_storage.save(
                f"campaign_media/{header_media_file.name}", header_media_file
            )
            file_url = request.build_absolute_uri(default_storage.url(file_name))
            variables = data.get("variables", {})
            if isinstance(variables, dict):
                variables["__header_media_url__"] = file_url
                variables["__header_media_type__"] = header_media_file.content_type
                data["variables"] = variables

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        name = serializer.validated_data["name"]
        template_id = serializer.validated_data.get("template_id")
        whatsapp_template_id = serializer.validated_data.get("whatsapp_template_id")
        contact_ids = serializer.validated_data.get("contact_ids", [])
        variables = serializer.validated_data.get("variables", {})

        template = None
        if whatsapp_template_id:
            template, error_response = self._message_template_from_whatsapp_template(
                whatsapp_template_id
            )
            if error_response:
                return error_response
        elif template_id:
            try:
                template = MessageTemplate.objects.get(id=template_id)
            except MessageTemplate.DoesNotExist:
                return Response(
                    {"error": "Template does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        contacts = Contact.objects.filter(id__in=contact_ids)
        if contacts.count() != len(set(contact_ids)):
            return Response(
                {"error": "One or more leads do not exist"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        config_id = get_whatsapp_config_id(request)

        with transaction.atomic():  # type: ignore
            campaign = Campaign.objects.create(
                name=name,
                template=template,
                variables=variables,
                status="DRAFT",
                total_contacts=contacts.count(),
                created_by=get_public_api_user(),
                whatsapp_config_id=config_id,
            )
            campaign.contacts.set(contacts)

        return Response(
            CampaignDetailSerializer(campaign).data, status=status.HTTP_201_CREATED
        )

    @action(detail=False, methods=["post"], url_path="create-draft-action")
    def create_draft(self, request):
        from django.utils.dateparse import parse_datetime

        data = request.data
        campaign_id = data.get("id")
        name = data.get("name")
        template_id = data.get("template_id")
        contacts_phones = data.get("contacts", [])
        variables = data.get("variables", {})
        scheduled_at_raw = data.get("scheduled_at")

        if not name:
            return Response(
                {"error": "Campaign name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Resolve template
        template = None
        if template_id:
            try:
                template = MessageTemplate.objects.get(id=template_id)
            except MessageTemplate.DoesNotExist:
                return Response(
                    {"error": "Template does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        # 2. Resolve contacts (find or create Contact objects from phone numbers)
        config_id = get_whatsapp_config_id(request)
        contact_user = (
            request.user
            if (request.user and request.user.is_authenticated)
            else get_public_api_user()
        )

        contact_objs = []
        seen_contact_ids = set()
        for phone_num in contacts_phones:
            phone = _normalize_phone_number(phone_num)
            if not phone:
                continue
            contact, _ = Contact.objects.get_or_create(
                phone_number=phone,
                user=contact_user,
                whatsapp_config_id=config_id,
                defaults={"name": phone},
            )
            # Uploaded lists routinely contain the same number more than once - get_or_create
            # resolves repeats to the same row, but appending on every iteration inflated
            # total_contacts (raw row count) far past the actual, de-duplicated M2M size.
            if contact.id not in seen_contact_ids:
                seen_contact_ids.add(contact.id)
                contact_objs.append(contact)

        # 3. Parse scheduled_at
        scheduled_at = None
        if scheduled_at_raw:
            scheduled_at = parse_datetime(str(scheduled_at_raw))
            if scheduled_at and timezone.is_naive(scheduled_at):
                import zoneinfo

                try:
                    local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                except Exception:
                    local_tz = timezone.get_current_timezone()
                scheduled_at = timezone.make_aware(scheduled_at, local_tz)

        # 4. Create or update Campaign
        with transaction.atomic():  # type: ignore
            if campaign_id:
                try:
                    campaign = Campaign.objects.get(
                        id=campaign_id, whatsapp_config_id=config_id
                    )
                    campaign.name = name
                    campaign.template = template
                    campaign.variables = variables
                    campaign.scheduled_at = scheduled_at
                    campaign.total_contacts = len(contact_objs)
                    campaign.status = "DRAFT"
                    campaign.save()
                except Campaign.DoesNotExist:
                    return Response(
                        {"error": f"Campaign with ID {campaign_id} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                campaign = Campaign.objects.create(
                    name=name,
                    template=template,
                    variables=variables,
                    status="DRAFT",
                    total_contacts=len(contact_objs),
                    scheduled_at=scheduled_at,
                    created_by=contact_user,
                    whatsapp_config_id=config_id,
                )
            campaign.contacts.set(contact_objs)

        return Response(
            {"id": campaign.id, "status": campaign.status},
            status=status.HTTP_201_CREATED if not campaign_id else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="crm-launch-action")
    def crm_launch(self, request):
        from django.utils.dateparse import parse_datetime

        data = request.data
        campaign_id = data.get("id")
        name = data.get("name")
        template_id = data.get("template_id")
        contacts_phones = data.get("contacts", [])
        variables = data.get("variables", {})
        scheduled_at_raw = data.get("scheduled_at")

        if not name:
            return Response(
                {"error": "Campaign name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 1. Resolve template
        template = None
        if template_id:
            try:
                template = MessageTemplate.objects.get(id=template_id)
            except MessageTemplate.DoesNotExist:
                return Response(
                    {"error": "Template does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not template:
            return Response(
                {"error": "Please select a template before sending this campaign"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Resolve contacts
        config_id = get_whatsapp_config_id(request)
        contact_user = (
            request.user
            if (request.user and request.user.is_authenticated)
            else get_public_api_user()
        )

        contact_objs = []
        seen_contact_ids = set()
        for phone_num in contacts_phones:
            phone = _normalize_phone_number(phone_num)
            if not phone:
                continue
            contact, _ = Contact.objects.get_or_create(
                phone_number=phone,
                user=contact_user,
                whatsapp_config_id=config_id,
                defaults={"name": phone},
            )
            # See create_draft above - de-dupe so total_contacts matches the actual M2M size.
            if contact.id not in seen_contact_ids:
                seen_contact_ids.add(contact.id)
                contact_objs.append(contact)

        if not contact_objs:
            return Response(
                {"error": "Please select at least one contact"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 3. Parse scheduled_at
        scheduled_at = None
        if scheduled_at_raw:
            scheduled_at = parse_datetime(str(scheduled_at_raw))
            if scheduled_at and timezone.is_naive(scheduled_at):
                import zoneinfo

                try:
                    local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
                except Exception:
                    local_tz = timezone.get_current_timezone()
                scheduled_at = timezone.make_aware(scheduled_at, local_tz)

        # 4. Create or update Campaign
        with transaction.atomic():  # type: ignore
            if campaign_id:
                try:
                    campaign = Campaign.objects.get(
                        id=campaign_id, whatsapp_config_id=config_id
                    )
                    campaign.name = name
                    campaign.template = template
                    campaign.variables = variables
                    campaign.scheduled_at = scheduled_at
                    campaign.total_contacts = len(contact_objs)

                    is_past_schedule = False
                    from django.utils import timezone as django_timezone

                    if scheduled_at and scheduled_at < django_timezone.now():
                        is_past_schedule = True

                    if campaign.status == "RUNNING" or is_past_schedule:
                        campaign.status = "RUNNING"
                        scheduled_at = (
                            None  # Clear local variable so it runs immediately
                        )
                    else:
                        campaign.status = "SCHEDULED" if scheduled_at else "RUNNING"

                    campaign.save()
                except Campaign.DoesNotExist:
                    return Response(
                        {"error": f"Campaign with ID {campaign_id} does not exist"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                campaign = Campaign.objects.create(
                    name=name,
                    template=template,
                    variables=variables,
                    status="SCHEDULED" if scheduled_at else "RUNNING",
                    total_contacts=len(contact_objs),
                    scheduled_at=scheduled_at,
                    created_by=contact_user,
                    whatsapp_config_id=config_id,
                )
            campaign.contacts.set(contact_objs)

        # 5. Launch the campaign if it is not scheduled (if scheduled, the background task will pick it up)
        if not scheduled_at:

            def run_campaign_in_thread(camp_id):
                from django.db import connection
                import logging

                logger = logging.getLogger(__name__)
                try:
                    from whatsapp_app.models import Campaign

                    camp = Campaign.objects.get(id=camp_id)
                    execute_campaign(camp)
                except Exception as thread_err:
                    import traceback

                    logger.error(
                        f"Campaign thread error for campaign {camp_id}: {thread_err}\n{traceback.format_exc()}"
                    )
                finally:
                    connection.close()

            import threading

            campaign_thread = threading.Thread(
                target=run_campaign_in_thread, args=(campaign.id,)
            )
            campaign_thread.daemon = True
            campaign_thread.start()

        return Response(
            {"id": campaign.id, "status": campaign.status},
            status=status.HTTP_201_CREATED if not campaign_id else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def running(self, request):
        """Get all running campaigns"""
        campaigns = self.get_queryset().filter(status="RUNNING")
        serializer = self.get_serializer(campaigns, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        queryset = (
            self.get_queryset()
            .filter(status__in=["STOPPED", "COMPLETED", "FAILED"])
            .order_by("-completed_at")
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def scheduled(self, request):
        queryset = (
            self.get_queryset().filter(status="SCHEDULED").order_by("scheduled_at")
        )
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="send")
    def send(self, request):
        name = request.data.get("name")
        template_id = request.data.get("template_id")
        leads_data = request.data.get("leads", [])  # Expecting list of {phone, name}
        components = request.data.get("components", [])  # Meta components format
        request_media_url = (
            request.data.get("media_url")
            or request.data.get("mediaUrl")
            or request.data.get("header_media_url")
            or extract_media_url_from_components(components)
        )
        request_buttons = request.data.get("buttons")

        if not name or not template_id or not leads_data:
            return Response(
                {"error": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST
            )

        if len(leads_data) > 500:
            return Response(
                {"error": "Cannot send to more than 500 leads at once"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            template = MessageTemplate.objects.get(id=template_id, status="APPROVED")
        except MessageTemplate.DoesNotExist:
            return Response(
                {"error": "Approved template not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            # Create campaign record
            config_id = get_whatsapp_config_id(request)
            with transaction.atomic():  # type: ignore
                campaign = Campaign.objects.create(
                    name=name,
                    template=template,
                    variables=request.data.get("variables", {}),
                    status="RUNNING",
                    total_contacts=len(leads_data),
                    created_by=get_public_api_user(),
                    started_at=timezone.now(),
                    whatsapp_config_id=config_id,
                )

                # Pre-normalize and find/create contacts
                contact_objs = []
                for l in leads_data:
                    phone = _normalize_phone_number(l.get("phone", ""))

                    if not phone:
                        continue
                    contact_name = l.get("name") or phone

                    contact, _ = Contact.objects.get_or_create(
                        phone_number=phone,
                        user=get_public_api_user(),
                        whatsapp_config_id=config_id,
                        defaults={"name": contact_name},
                    )
                    contact_objs.append(contact)

                campaign.contacts.set(contact_objs)

            # Start dispatch loop directly to Meta Cloud API
            from whatsapp_app.services import send_whatsapp_message_direct_to_meta

            waba_config = get_whatsapp_config()

            sent_count = 0
            failed_count = 0
            sent_messages = []

            for contact in contact_objs:
                provider_message_id = str(uuid.uuid4())
                template_buttons = (
                    request_buttons
                    if request_buttons is not None
                    else (template.buttons or [])
                )

                # Construct the message text using the template body and variables
                msg_text = template.body or f"Template: {template.name}"
                if components:
                    from whatsapp_app.utils import render_template

                    # Extract simple variables dict for rendering
                    vars_dict = {}
                    for comp in components:
                        if comp.get("type") == "body":
                            params = comp.get("parameters", [])
                            for i, p in enumerate(params):
                                vars_dict[str(i + 1)] = p.get("text", "")

                    try:
                        msg_text = render_template(msg_text, vars_dict)
                    except:
                        pass

                try:
                    res_data, status_code = send_whatsapp_message_direct_to_meta(
                        recipient_id=contact.phone_number,
                        waba_config=waba_config,
                        template_name=template.name,
                        language_code=template.language or "en_US",
                        components=components,
                    )

                    if status_code in [200, 201]:
                        sent_count += 1

                        provider_id = extract_provider_message_id(
                            res_data,
                            fallback=provider_message_id,
                        )

                        message = Message.objects.create(
                            contact=contact,
                            campaign=campaign,
                            text=msg_text,
                            sender="agent",
                            direction="OUTGOING",
                            status="Sent",
                            type="template",
                            provider_message_id=provider_id,
                            media_url=request_media_url,
                            buttons=template_buttons,
                            timestamp=timezone.now(),
                        )
                        sent_messages.append(
                            {
                                "id": message.id,
                                "contact_id": contact.id,
                                "phone": contact.phone_number,
                                "provider_message_id": message.provider_message_id,
                                "media_url": message.media_url,
                                "buttons": message.buttons,
                            }
                        )
                    else:
                        failed_count += 1
                        if status_code == 401:
                            print(
                                f"Auth Error (401): Check token for {contact.phone_number}"
                            )
                        elif status_code == 403:
                            print(
                                f"Service Window Closed (403) for {contact.phone_number}"
                            )
                        else:
                            print(
                                f"Meta error ({status_code}) for {contact.phone_number}: {res_data}"
                            )

                        Message.objects.create(
                            contact=contact,
                            campaign=campaign,
                            text=msg_text,
                            sender="agent",
                            direction="OUTGOING",
                            status="Failed",
                            type="template",
                            media_url=request_media_url,
                            buttons=template_buttons,
                            timestamp=timezone.now(),
                            failed_at=timezone.now(),
                        )

                except Exception as e:
                    failed_count += 1
                    print(f"Connection failed for {contact.phone_number}: {str(e)}")
                    Message.objects.create(
                        contact=contact,
                        campaign=campaign,
                        text=msg_text,
                        sender="agent",
                        direction="OUTGOING",
                        status="Failed",
                        type="template",
                        media_url=request_media_url,
                        buttons=template_buttons,
                        timestamp=timezone.now(),
                        failed_at=timezone.now(),
                    )

            # Update campaign metrics â€” stays RUNNING until user stops or all done
            campaign.total_sent = sent_count
            campaign.total_failed = failed_count
            campaign.status = "RUNNING"
            campaign.save()

            return Response(
                {
                    "message": f"Campaign process finished. Sent: {sent_count}, Failed: {failed_count}",
                    "campaign_id": campaign.id,
                    "messages": sent_messages,
                }
            )

        except Exception as global_e:
            import traceback

            error_trace = traceback.format_exc()
            return Response(
                {
                    "error": "Global error in campaign dispatch",
                    "details": str(global_e),
                    "traceback": error_trace,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        campaign = self.get_object()

        if campaign.status != "DRAFT":
            return Response(
                {"error": "Only draft campaigns can be scheduled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template = campaign.template
        variables = campaign.variables or {}
        if not template:
            return Response(
                {"error": "Please select a template before scheduling this campaign"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template_vars = sorted([str(v) for v in (template.variables or [])])

        # Exclude internal/private variables (starting with __ or _) from user-facing comparison
        provided_vars = sorted(
            [
                str(k)
                for k in (variables or {}).keys()
                if not str(k).startswith("__") and not str(k).startswith("_")
            ]
        )

        # Only reject if template requires variables but none are provided at all.
        if template_vars and not provided_vars:
            return Response(
                {
                    "error": f"This template requires variables: {template_vars}. Please fill in all required fields."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        scheduled_at_raw = request.data.get("scheduled_at")
        if not scheduled_at_raw:
            return Response(
                {"error": "scheduled_at is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        scheduled_at = parse_datetime(scheduled_at_raw)
        if scheduled_at is None:
            return Response(
                {"error": "Invalid datetime format for scheduled_at"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if timezone.is_naive(scheduled_at):
            import zoneinfo

            try:
                local_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
            except Exception:
                local_tz = timezone.get_current_timezone()
            scheduled_at = timezone.make_aware(scheduled_at, local_tz)

        campaign.status = "SCHEDULED"
        campaign.scheduled_at = scheduled_at
        campaign.save(update_fields=["status", "scheduled_at"])

        return Response({"message": "Campaign scheduled successfully"})

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        """Launch a campaign"""
        campaign = self.get_object()
        if campaign.status not in ["DRAFT", "SCHEDULED", "RUNNING"]:
            return Response(
                {"error": "Only active campaigns can be launched"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        template = campaign.template
        variables_data = request.data.get("variables", campaign.variables or {})

        if isinstance(variables_data, str):
            import json

            try:
                variables_data = json.loads(variables_data)
            except:
                pass

        # Merge: campaign.variables (saved draft) + request variables (latest user input)
        # Request variables take precedence so the latest values are used
        merged_variables = {}
        if isinstance(campaign.variables, dict):
            merged_variables.update(campaign.variables)
        if isinstance(variables_data, dict):
            merged_variables.update(variables_data)
        variables_data = merged_variables

        header_media_file = request.FILES.get("header_media_file")
        if header_media_file:
            from django.core.files.storage import default_storage

            file_name = default_storage.save(
                f"campaign_media/{header_media_file.name}", header_media_file
            )
            file_url = request.build_absolute_uri(default_storage.url(file_name))
            if isinstance(variables_data, dict):
                variables_data["__header_media_url__"] = file_url
                variables_data["__header_media_type__"] = header_media_file.content_type
                variables_data["__header_filename__"] = header_media_file.name

                # Pre-upload directly to Meta since Meta cannot download from local network URLs
                try:
                    from whatsapp_app.services import upload_media_for_message
                    import logging

                    logger = logging.getLogger(__name__)

                    file_bytes = header_media_file.read()
                    mime_type = header_media_file.content_type or "image/jpeg"
                    waba_config = get_whatsapp_config(
                        campaign.whatsapp_config_id
                        if campaign.whatsapp_config
                        else None
                    )

                    media_id = upload_media_for_message(
                        file_bytes, header_media_file.name, mime_type, waba_config
                    )
                    if media_id:
                        variables_data["__header_media_id__"] = media_id
                        logger.info(
                            f"Successfully pre-uploaded campaign media to Meta. Media ID: {media_id}"
                        )
                except Exception as e:
                    import logging

                    logging.getLogger(__name__).error(
                        f"Failed to pre-upload campaign media to Meta during launch: {e}"
                    )

        whatsapp_template_id = request.data.get("whatsapp_template_id")
        template_id = request.data.get("template_id")

        if whatsapp_template_id:
            template, error_response = self._message_template_from_whatsapp_template(
                whatsapp_template_id
            )
            if error_response:
                return error_response
        elif template_id:
            try:
                template = MessageTemplate.objects.get(id=template_id)
            except MessageTemplate.DoesNotExist:
                return Response(
                    {"error": "Template does not exist"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not template:
            return Response(
                {"error": "Please select a template before sending this campaign"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Normalize template variables for reliable comparison
        template_vars = sorted([str(v) for v in (template.variables or [])])

        # Exclude internal/private variables (starting with __ or _) from user-facing comparison
        provided_vars = sorted(
            [
                str(k)
                for k in (variables_data or {}).keys()
                if not str(k).startswith("__") and not str(k).startswith("_")
            ]
        )

        # Only reject if template requires variables but none are provided at all.
        # Allow extra/fewer provided vars in edge cases to avoid blocking sends.
        if template_vars and not provided_vars:
            return Response(
                {
                    "error": f"This template requires variables: {template_vars}. Please fill in all required fields."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update contact_ids if the launch payload includes them
        contact_ids = request.data.get("contact_ids")
        if contact_ids is not None:
            if isinstance(contact_ids, str):
                import json

                try:
                    contact_ids = json.loads(contact_ids)
                except Exception:
                    pass
            if isinstance(contact_ids, list) and contact_ids:
                new_contacts = Contact.objects.filter(id__in=contact_ids)
                campaign.contacts.set(new_contacts)

        campaign.template = template
        campaign.variables = variables_data
        campaign.save(update_fields=["template", "variables"])

        def run_campaign_in_thread(camp_id):
            from django.db import connection
            import logging

            logger = logging.getLogger(__name__)
            try:
                from whatsapp_app.models import Campaign

                camp = Campaign.objects.get(id=camp_id)
                execute_campaign(camp)
            except Exception as thread_err:
                import traceback

                logger.error(
                    f"Campaign thread error for campaign {camp_id}: {thread_err}\n{traceback.format_exc()}"
                )
            finally:
                connection.close()

        import threading

        campaign_thread = threading.Thread(
            target=run_campaign_in_thread, args=(campaign.id,)
        )
        campaign_thread.daemon = True
        campaign_thread.start()

        return Response(
            {
                "message": "Campaign launched successfully and is now running in the background.",
                "status": "RUNNING",
                "total_sent": 0,
            }
        )

    @action(detail=True, methods=["get"])
    def messages(self, request, pk=None):
        campaign = self.get_object()
        messages = campaign.messages.select_related("contact").order_by(
            "-timestamp", "-created_at"
        )
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def stop(self, request, pk=None):
        campaign = self.get_object()

        if campaign.status in ["STOPPED", "COMPLETED", "FAILED"]:
            return Response(
                {"error": "Campaign is already finished"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        campaign.status = "COMPLETED"
        campaign.completed_at = timezone.now()
        campaign.save(update_fields=["status", "completed_at"])

        return Response(
            {
                "message": "Campaign completed successfully",
                "status": campaign.status,
                "completed_at": campaign.completed_at,
            }
        )


# Message ViewSet
class MessageViewSet(viewsets.ModelViewSet):
    """ViewSet for managing messages"""

    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = MessageSerializer

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        return Message.objects.select_related("contact").filter(
            contact__whatsapp_config_id=config_id
        )

    @action(detail=False, methods=["get"])
    def contact_messages(self, request):
        """Get all messages for a specific contact"""
        contact_id = request.query_params.get("contact_id")
        if not contact_id:
            return Response(
                {"error": "contact_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            config_id = get_whatsapp_config_id(request)
            contact = Contact.objects.get(id=contact_id, whatsapp_config_id=config_id)
            messages = (
                Message.objects.select_related("contact")
                .filter(contact=contact)
                .order_by("created_at")
            )
            serializer = self.get_serializer(messages, many=True)
            return Response(serializer.data)
        except Contact.DoesNotExist:
            return Response(
                {"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=["get"], url_path=r"phone/(?P<phone>[^/.]+)")
    def by_phone(self, request, phone=None):
        """Get all messages for a specific contact by phone number"""
        try:
            config_id = get_whatsapp_config_id(request)
            contact = Contact.objects.get(
                phone_number=phone, whatsapp_config_id=config_id
            )
            messages = Message.objects.filter(contact=contact).order_by("timestamp")

            # Reset unread count when chat is opened
            if contact.unread_count > 0:
                contact.unread_count = 0
                contact.save(update_fields=["unread_count"])

            serializer = self.get_serializer(messages, many=True)
            return Response(serializer.data)
        except Contact.DoesNotExist:
            return Response(
                {"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND
            )


class IsTemplateOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return True


# MessageTemplate ViewSet
class MessageTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for managing WhatsApp message templates."""

    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = MessageTemplateSerializer
    queryset = MessageTemplate.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return MessageTemplateListSerializer
        return MessageTemplateSerializer

    def get_permissions(self):
        if self.action == "header_media":
            return [AllowAny()]
        return super().get_permissions()

    def get_queryset(self):
        if self.action == "header_media":
            return MessageTemplate.objects.all()
        config_id = get_whatsapp_config_id(self.request)
        live = str(self.request.query_params.get("live", "")).lower() in {
            "1",
            "true",
            "yes",
        }
        if live:
            config_obj = WhatsAppConfig.objects.filter(id=config_id).first()
            if config_obj:
                perform_template_sync(config=config_obj)

        queryset = MessageTemplate.objects.filter(whatsapp_config_id=config_id)

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(body__icontains=search)
            )

        return queryset.order_by("-updated_at")

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        serializer.save(created_by=get_public_api_user(), whatsapp_config_id=config_id)

    def create(self, request, *args, **kwargs):
        try:
            # Remap frontend field names to backend field names
            data = (
                request.data.copy()
                if hasattr(request.data, "copy")
                else dict(request.data)
            )

            # Frontend sends 'template_name' â†’ backend expects 'name'
            raw_name = data.get("name") or data.get("template_name") or ""
            if raw_name:
                import re

                clean_name = raw_name.strip().lower()
                clean_name = re.sub(r"[\s\-]+", "_", clean_name)
                clean_name = re.sub(r"[^a-z0-9_]", "", clean_name)
                data["name"] = clean_name

            # Frontend sends 'body_text' â†’ backend expects 'body'
            if "body_text" in data and "body" not in data:
                data["body"] = data.pop("body_text")

            # Populate media fields if header has media. Prefer sample_values.header_handle
            header_type = data.get("header_type", "NONE")
            if header_type in ["IMAGE", "DOCUMENT", "VIDEO"]:
                sample_vals = data.get("sample_values") or {}
                # sample_values may provide header_handle as a data URL or a public URL
                sv_handle = None
                if isinstance(sample_vals, dict):
                    # header_handle sometimes sent as a single value or an array
                    h = sample_vals.get("header_handle")
                    if isinstance(h, list) and len(h) > 0:
                        sv_handle = h[0]
                    elif isinstance(h, str):
                        sv_handle = h

                media_url = (
                    sv_handle
                    or data.get("header_media_url")
                    or data.get("media_url")
                    or data.get("header_url")
                )
                if not media_url:
                    if header_type == "IMAGE":
                        media_url = "https://images.unsplash.com/photo-1575936123452-b67c3203c357?fm=jpg"
                    elif header_type == "VIDEO":
                        media_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
                    else:  # DOCUMENT
                        media_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

                # Store preview and header_media for local UI; actual upload will be handled when registering with Meta
                data["uploaded_preview_image"] = media_url
                data["header_media"] = media_url

            # 1. Validate with serializer
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            # 2. Construct components structure for Meta API
            components = []

            # Header
            header_type = data.get("header_type", "NONE")
            if header_type == "TEXT":
                components.append(
                    {
                        "type": "HEADER",
                        "format": "TEXT",
                        "text": data.get("header_text"),
                    }
                )
            elif header_type in ["IMAGE", "DOCUMENT", "VIDEO"]:
                # Prefer sample_values.header_handle when building components
                sample_vals = data.get("sample_values") or {}
                sv_handle = None
                if isinstance(sample_vals, dict):
                    h = sample_vals.get("header_handle")
                    if isinstance(h, list) and len(h) > 0:
                        sv_handle = h[0]
                    elif isinstance(h, str):
                        sv_handle = h

                media_url = (
                    sv_handle
                    or data.get("header_media_url")
                    or data.get("media_url")
                    or data.get("header_url")
                )
                if not media_url:
                    if header_type == "IMAGE":
                        media_url = "https://images.unsplash.com/photo-1575936123452-b67c3203c357?fm=jpg"
                    elif header_type == "VIDEO":
                        media_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
                    else:  # DOCUMENT
                        media_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

                components.append(
                    {
                        "type": "HEADER",
                        "format": header_type,
                        "example": {"header_handle": [media_url]},
                    }
                )

            # Body
            category = data.get("category", "MARKETING")
            if category == "AUTHENTICATION":
                # Meta Authentication templates do not allow custom body text.
                # The text is fixed by Meta, and the BODY component only accepts add_security_recommendation.
                body_component = {"type": "BODY", "add_security_recommendation": True}
                components.append(body_component)

                # Meta Authentication templates require a COPY_CODE button of type OTP.
                # Automatically append a default OTP/COPY_CODE button.
                components.append(
                    {
                        "type": "BUTTONS",
                        "buttons": [{"type": "OTP", "otp_type": "COPY_CODE"}],
                    }
                )
            else:
                body_text = data.get("body", "")
                body_component = {"type": "BODY", "text": body_text}

                import re

                matches = re.findall(r"\{\{(\d+)\}\}", body_text)
                if matches:
                    unique_nums = sorted(list(set(matches)), key=int)
                    samples = data.get("sample_values", {})
                    example_values = [
                        str(samples.get(num, "sample")) for num in unique_nums
                    ]
                    body_component["example"] = {"body_text": [example_values]}

                components.append(body_component)

            if data.get("footer_text") and category != "AUTHENTICATION":
                components.append({"type": "FOOTER", "text": data.get("footer_text")})

            buttons_data = data.get("buttons", [])
            if buttons_data and category != "AUTHENTICATION":
                meta_buttons = []
                for btn in buttons_data:
                    btn_type = btn.get("type")
                    if btn_type == "URL":
                        meta_buttons.append(
                            {
                                "type": "URL",
                                "text": btn.get("text"),
                                "url": btn.get("url"),
                            }
                        )
                    elif btn_type == "QUICK_REPLY":
                        meta_buttons.append(
                            {"type": "QUICK_REPLY", "text": btn.get("text")}
                        )
                if meta_buttons:
                    components.append({"type": "BUTTONS", "buttons": meta_buttons})

            # Map language codes
            lang_map = {
                "en": "en_US",
                "hi": "hi",
                "ta": "ta",
                "te": "te",
                "kn": "kn",
                "ml": "ml",
            }
            lang_key = data.get("language")
            if isinstance(lang_key, str):
                lang = lang_map.get(lang_key, lang_key)
            else:
                lang = "en_US"

            meta_payload = {
                "name": data.get("name"),
                "category": data.get("category", "MARKETING"),
                "language": lang,
                "components": components,
            }

            # 3. Call Meta API natively BEFORE storing in database
            from whatsapp_app.services import create_whatsapp_template

            config_id = get_whatsapp_config_id(request)
            success, res_data = create_whatsapp_template(
                meta_payload, config_id=config_id
            )
            if not success:
                meta_error = {}
                if isinstance(res_data, dict):
                    details = res_data.get("details")
                    if isinstance(details, dict):
                        meta_error = details.get("error") or {}

                # Check if it's missing config / unconfigured WABA in dev environment
                if "Missing WHATSAPP_BUSINESS_ACCOUNT_ID" in str(res_data):
                    self.perform_create(serializer)
                    return Response(serializer.data, status=status.HTTP_201_CREATED)

                user_message = (
                    meta_error.get("error_user_msg")
                    or meta_error.get("message")
                    or res_data.get("error")
                    or "Failed to submit template to Meta."
                )
                if meta_error.get("error_subcode") == 2388023:
                    user_message = (
                        f"{user_message} Use a different template name, or wait until Meta finishes deleting "
                        "the old template language version."
                    )
                return Response(
                    {"error": user_message, "details": res_data},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 4. Save locally only on success
            self.perform_create(serializer)
            instance = serializer.instance

            # 5. Map status from Meta response
            try:
                meta_status = (
                    res_data.get("status") if isinstance(res_data, dict) else None
                )
                if meta_status:
                    status_str = str(meta_status).upper()
                    if "PENDING" in status_str:
                        instance.status = "PENDING"
                    elif "APPROVED" in status_str:
                        instance.status = "APPROVED"
                    elif "REJECTED" in status_str:
                        instance.status = "REJECTED"
                    instance.save(update_fields=["status"])
            except Exception:
                pass

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            with open("webhook_debug.log", "a") as f_log:
                f_log.write(f"\n!!! TEMPLATE CREATE ERROR AT {timezone.now()} !!!\n")
                f_log.write(error_details)
                f_log.write("\n")
            return Response(
                {"error": str(e), "details": error_details},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="create")
    def create_template(self, request):
        return self.create(request)

    @action(detail=True, methods=["get"], url_path="header-media")
    def header_media(self, request, pk=None):
        template = self.get_object()
        media_value = (
            template.uploaded_preview_image
            or template.meta_media_url
            or template.header_media
        )
        if not media_value and template.sample_values:
            media_value = template.sample_values.get(
                "header_handle"
            ) or template.sample_values.get("media_url")

        if not media_value:
            return Response(
                {"error": "Template header media not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if isinstance(media_value, str) and media_value.startswith("data:"):
            try:
                import base64

                meta_info, b64_data = media_value.split(",", 1)
                content_type = "application/octet-stream"
                if ":" in meta_info and ";" in meta_info:
                    content_type = meta_info.split(":", 1)[1].split(";", 1)[0]
                return HttpResponse(
                    base64.b64decode(b64_data), content_type=content_type
                )
            except Exception as e:
                logger.error(f"Failed to decode template header media: {e}")
                return Response(
                    {"error": "Template header media is invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if isinstance(media_value, str) and media_value.startswith(
            ("http://", "https://")
        ):
            try:
                upstream = requests.get(media_value, timeout=20)
                upstream.raise_for_status()
                content_type = upstream.headers.get(
                    "Content-Type", "application/octet-stream"
                )
                return HttpResponse(upstream.content, content_type=content_type)
            except Exception as e:
                logger.error(f"Failed to fetch template header media: {e}")
                return Response(
                    {"error": "Failed to fetch template header media"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        # Some templates only ever got a raw Meta media handle ID stored (from a sync where
        # Meta returned example.header_handle as a bare ID rather than a fetchable CDN URL,
        # e.g. certain templates created directly in WhatsApp Business Manager). That ID is
        # itself a Meta Graph object - resolve it to a temporary download URL and stream it,
        # then cache the real bytes locally so this only needs to hit Meta once.
        if isinstance(media_value, str) and media_value.strip().isdigit():
            try:
                config = template.whatsapp_config
                token = config.whatsapp_api_token if config else None
                if not token:
                    raise ValueError(
                        "No WhatsApp API token configured for this account"
                    )

                meta_obj = requests.get(
                    f"https://graph.facebook.com/v20.0/{media_value.strip()}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15,
                )
                meta_obj.raise_for_status()
                download_url = meta_obj.json().get("url")
                if not download_url:
                    raise ValueError(
                        f"Meta returned no download url: {meta_obj.text[:200]}"
                    )

                upstream = requests.get(
                    download_url,
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30,
                )
                upstream.raise_for_status()
                content_type = upstream.headers.get(
                    "Content-Type", "application/octet-stream"
                )

                # Cache as a data: URI so future requests don't need to hit Meta again -
                # this is exactly the form the rest of the media-resolution chain already
                # understands (list/detail serializers, send flow, etc).
                try:
                    import base64

                    b64 = base64.b64encode(upstream.content).decode("utf-8")
                    sv = (
                        template.sample_values
                        if isinstance(template.sample_values, dict)
                        else {}
                    )
                    sv["header_handle"] = f"data:{content_type};base64,{b64}"
                    template.sample_values = sv
                    template.header_media = None
                    template.save(update_fields=["sample_values", "header_media"])
                except Exception as cache_err:
                    logger.warning(
                        f"Failed to cache resolved template header media: {cache_err}"
                    )

                return HttpResponse(upstream.content, content_type=content_type)
            except Exception as e:
                logger.error(f"Failed to resolve Meta media handle {media_value}: {e}")
                return Response(
                    {"error": "Failed to resolve template header media from Meta"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

        return Response(
            {"error": "Template header media is not browser-renderable"},
            status=status.HTTP_404_NOT_FOUND,
        )

    def destroy(self, request, *args, **kwargs):
        template = self.get_object()
        success, res_data = delete_whatsapp_template_from_meta(
            template.name,
            config=template.whatsapp_config,
        )

        if not success:
            return Response(
                {
                    "error": "Failed to delete template from Meta.",
                    "details": res_data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        template.delete()
        return Response(
            {
                "message": "Template deleted from Meta and CRM.",
                "meta": res_data,
            },
            status=status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        allowed_fields = {"body", "footer", "button_text", "category"}
        incoming_fields = set(request.data.keys())

        disallowed_fields = incoming_fields - allowed_fields
        if disallowed_fields:
            return Response(
                {
                    "error": "Only body, footer, button_text, and category can be edited.",
                    "disallowed_fields": sorted(disallowed_fields),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        template = self.get_object()
        template.status = "APPROVED"
        template.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(template).data)

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        template = self.get_object()
        template.status = "REJECTED"
        template.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(template).data)


class DashboardViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    @action(detail=False, methods=["GET"])
    def stats(self, request):
        from datetime import date, datetime, time, timedelta
        from django.db.models.functions import Coalesce
        from django.utils import timezone

        def parse_range_bounds():
            range_key = (
                request.query_params.get("range")
                or request.query_params.get("period")
                or "all_time"
            ).lower()
            start_date_value = request.query_params.get("start_date")
            end_date_value = request.query_params.get("end_date")

            def to_aware_bound(date_value, end_of_day=False):
                local_date = date.fromisoformat(date_value)
                boundary_time = time.max if end_of_day else time.min
                naive_dt = datetime.combine(local_date, boundary_time)
                return timezone.make_aware(naive_dt, timezone.get_current_timezone())

            today = timezone.localdate()

            if range_key in {"all", "all_time", "all-time"}:
                return None, None
            if range_key == "today":
                return to_aware_bound(today.isoformat()), to_aware_bound(
                    today.isoformat(), True
                )
            if range_key == "yesterday":
                yesterday = today - timedelta(days=1)
                return to_aware_bound(yesterday.isoformat()), to_aware_bound(
                    yesterday.isoformat(), True
                )
            if range_key == "last_7_days":
                start_day = today - timedelta(days=6)
                return to_aware_bound(start_day.isoformat()), to_aware_bound(
                    today.isoformat(), True
                )
            if range_key == "last_30_days":
                start_day = today - timedelta(days=29)
                return to_aware_bound(start_day.isoformat()), to_aware_bound(
                    today.isoformat(), True
                )
            if range_key == "custom" and start_date_value and end_date_value:
                try:
                    start_bound = to_aware_bound(start_date_value)
                    end_bound = to_aware_bound(end_date_value, True)
                    if end_bound < start_bound:
                        start_bound, end_bound = end_bound, start_bound
                    return start_bound, end_bound
                except ValueError:
                    return None, None

            return None, None

        def get_all_stats():
            start_dt, end_dt = parse_range_bounds()
            config_id = get_whatsapp_config_id(request)
            campaigns_qs = Campaign.objects.filter(whatsapp_config_id=config_id)
            messages_qs = Message.objects.filter(
                contact__whatsapp_config_id=config_id
            ).annotate(effective_at=Coalesce("timestamp", "created_at"))

            if start_dt and end_dt:
                period_messages = messages_qs.filter(
                    effective_at__range=(start_dt, end_dt)
                )
            else:
                period_messages = messages_qs

            campaign_messages = period_messages.filter(campaign__isnull=False)
            ind_messages = period_messages.filter(campaign__isnull=True)

            campaign_ids_in_range = list(
                campaign_messages.values_list("campaign_id", flat=True).distinct()
            )
            if start_dt and end_dt:
                campaigns_qs = campaigns_qs.filter(
                    Q(created_at__range=(start_dt, end_dt))
                    | Q(id__in=campaign_ids_in_range)
                ).distinct()

            # Replies (incoming messages) from contacts who were sent a campaign message in this period â€”
            # used for a genuine reply/response rate, distinct from delivery.
            campaign_contact_ids = list(
                campaign_messages.values_list("contact_id", flat=True).distinct()
            )
            campaign_replies_count = (
                period_messages.filter(
                    direction="INCOMING", contact_id__in=campaign_contact_ids
                ).count()
                if campaign_contact_ids
                else 0
            )

            active_campaigns_count = campaigns_qs.filter(status="RUNNING").count()

            # Fetch last 5 running/recent campaigns
            recent_campaigns = []
            for camp in campaigns_qs.order_by("-created_at")[:5]:
                camp_msgs = campaign_messages.filter(campaign=camp)
                total = camp_msgs.count()
                delivered = camp_msgs.filter(status__in=["Delivered", "Read"]).count()
                read = camp_msgs.filter(status="Read").count()
                failed = camp_msgs.filter(status="Failed").count()

                # Fetch first 10 contacts for this campaign to show in detail
                contacts_data = []
                for msg in camp_msgs.select_related("contact")[:10]:
                    contacts_data.append(
                        {
                            "name": msg.contact.name,
                            "phone": msg.contact.phone_number,
                            "status": msg.status,
                            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
                            "delivered_at": msg.delivered_at.isoformat()
                            if msg.delivered_at
                            else None,
                            "read_at": msg.read_at.isoformat() if msg.read_at else None,
                            "failed_at": msg.failed_at.isoformat()
                            if msg.failed_at
                            else None,
                            "timestamp": msg.timestamp.isoformat()
                            if msg.timestamp
                            else (
                                msg.created_at.isoformat() if msg.created_at else None
                            ),
                        }
                    )

                recent_campaigns.append(
                    {
                        "id": camp.id,
                        "name": camp.name,
                        "status": camp.status,
                        "audience": "Global",
                        "time": camp.created_at.strftime("%Y-%m-%d %H:%M"),
                        "count": total,
                        "delivered": delivered,
                        "read": read,
                        "failed": failed,
                        "body": camp.template.body if camp.template else "",
                        "contacts": contacts_data,
                    }
                )

            # Fetch individual conversations â€” ALL messages per contact (both direct inbox and campaign messages)
            # "Individual analytics" means per-contact breakdown of all conversations
            recent_individuals = []

            # Use ALL messages (not just campaign__isnull=True) since direct inbox messages
            # can also be linked to a campaign. Group by contact.
            all_contact_ids_in_range = list(
                period_messages.values_list("contact_id", flat=True).distinct()
            )

            contact_rows = []
            if all_contact_ids_in_range:
                for contact in Contact.objects.filter(id__in=all_contact_ids_in_range):
                    contact_msgs = period_messages.filter(contact=contact)
                    latest_msg = contact_msgs.order_by("-effective_at").first()
                    latest_time = (
                        latest_msg.effective_at
                        if latest_msg and latest_msg.effective_at
                        else None
                    )
                    contact_rows.append(
                        (latest_time, contact, contact_msgs, latest_msg)
                    )

                contact_rows.sort(
                    key=lambda row: row[0] or timezone.now(), reverse=True
                )

            for latest_time, contact, contact_msgs, latest_msg in contact_rows[:100]:
                total = contact_msgs.filter(direction="OUTGOING").count()
                received = contact_msgs.filter(direction="INCOMING").count()
                delivered = contact_msgs.filter(
                    direction="OUTGOING", status__in=["Delivered", "Read"]
                ).count()
                read = contact_msgs.filter(direction="OUTGOING", status="Read").count()
                failed = contact_msgs.filter(
                    direction="OUTGOING", status="Failed"
                ).count()

                recent_individuals.append(
                    {
                        "id": contact.id,
                        "name": contact.name,
                        "phone": contact.phone_number,
                        "audience": "Contact",
                        "time": latest_time.strftime("%Y-%m-%d %H:%M")
                        if latest_time
                        else "N/A",
                        "count": total,
                        "received": received,
                        "delivered": delivered,
                        "read": read,
                        "failed": failed,
                        "body": latest_msg.text if latest_msg else "",
                        "contacts": [],
                    }
                )

            # Use all_contact_ids_in_range for the individual KPI totals too
            ind_all = period_messages  # all messages across all contacts in period
            return {
                "campaigns": {
                    "active": active_campaigns_count,
                    "sent": campaign_messages.count(),
                    "failed": campaign_messages.filter(status="Failed").count(),
                    "delivered": campaign_messages.filter(
                        status__in=["Delivered", "Read"]
                    ).count(),
                    "read": campaign_messages.filter(status="Read").count(),
                    "received": campaign_replies_count,
                    "running": recent_campaigns,
                },
                "individual": {
                    "active": Contact.objects.filter(
                        id__in=all_contact_ids_in_range
                    ).count(),
                    "sent": ind_all.filter(direction="OUTGOING").count(),
                    "failed": ind_all.filter(
                        direction="OUTGOING", status="Failed"
                    ).count(),
                    "delivered": ind_all.filter(
                        direction="OUTGOING", status__in=["Delivered", "Read"]
                    ).count(),
                    "read": ind_all.filter(direction="OUTGOING", status="Read").count(),
                    "received": ind_all.filter(direction="INCOMING").count(),
                    "running": recent_individuals,
                },
            }

        unified_stats = get_all_stats()

        return Response(unified_stats)

    @action(detail=False, methods=["GET"], url_path="message-pricing")
    def message_pricing(self, request):
        """
        WhatsApp Manager-style "Message pricing" insights: exact local message-status
        counts (sent/delivered/read/failed/received) plus real per-category pricing
        volumes and approximate charges pulled live from Meta's WABA pricing_analytics.
        """
        from datetime import datetime as dt, time
        from django.db.models.functions import Coalesce

        config_id = get_whatsapp_config_id(request)
        config = WhatsAppConfig.objects.filter(id=config_id).first()
        if (
            not config
            or not config.whatsapp_api_token
            or not config.whatsapp_business_account_id
        ):
            return Response(
                {
                    "error": "This WhatsApp account has no Meta Business Account connected yet, so pricing insights are unavailable."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        resolved = _resolve_pricing_date_range(request)
        if resolved is None:
            return Response(
                {"error": "Invalid custom date range."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_date, end_date, range_key, clamped = resolved

        start_ts = int(dt.combine(start_date, time.min).timestamp())
        end_ts = int(dt.combine(end_date, time.max).timestamp())

        graph_version = getattr(settings, "META_GRAPH_API_VERSION", "v20.0")
        waba_id = config.whatsapp_business_account_id
        headers = {"Authorization": f"Bearer {config.whatsapp_api_token}"}

        phone_filter = request.query_params.get("phone_number_id") or ""
        country_filter = (request.query_params.get("country") or "").strip().upper()

        analytics_expr = f"analytics.start({start_ts}).end({end_ts}).granularity(DAY)"
        pricing_expr = (
            f"pricing_analytics.start({start_ts}).end({end_ts}).granularity(DAILY)"
            '.dimensions(["COUNTRY","PRICING_CATEGORY","PRICING_TYPE"])'
        )
        if phone_filter:
            analytics_expr += f'.phone_numbers(["{phone_filter}"])'
            pricing_expr += f'.phone_numbers(["{phone_filter}"])'

        fields = f"currency,name,phone_numbers{{id,display_phone_number,verified_name}},{analytics_expr},{pricing_expr}"

        try:
            resp = requests.get(
                f"https://graph.facebook.com/{graph_version}/{waba_id}",
                headers=headers,
                params={"fields": fields},
                timeout=20,
            )
        except requests.RequestException as exc:
            return Response(
                {"error": f"Could not reach WhatsApp pricing analytics: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not resp.ok:
            logger.error(
                f"message_pricing: Meta API error {resp.status_code}: {resp.text[:500]}"
            )
            return Response(
                {
                    "error": "WhatsApp pricing analytics request failed.",
                    "detail": resp.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payload = resp.json()
        currency = payload.get("currency") or "USD"
        phone_numbers = [
            {
                "id": row.get("id"),
                "display_phone_number": row.get("display_phone_number"),
                "verified_name": row.get("verified_name"),
            }
            for row in (payload.get("phone_numbers") or {}).get("data", [])
        ]

        # Meta's own per-message sent/delivered counts â€” the source of truth for those two
        # numbers, since our local delivery-status webhook pipeline can lag or drop updates
        # (verified against production: local counts diverged sharply from Meta's real numbers).
        analytics_points = (payload.get("analytics") or {}).get("data_points") or []
        meta_sent = sum(p.get("sent") or 0 for p in analytics_points)
        meta_delivered = sum(p.get("delivered") or 0 for p in analytics_points)

        pa_blocks = (payload.get("pricing_analytics") or {}).get("data") or [{}]
        data_points = pa_blocks[0].get("data_points", []) if pa_blocks else []

        countries_seen = sorted(
            {p.get("country") for p in data_points if p.get("country")}
        )
        if country_filter:
            data_points = [
                p
                for p in data_points
                if (p.get("country") or "").upper() == country_filter
            ]

        CATEGORY_LABELS = {
            "MARKETING": "Marketing",
            "UTILITY": "Utility",
            "AUTHENTICATION": "Authentication",
            "AUTHENTICATION_INTERNATIONAL": "Authentication - international",
            "AI_PROVIDER": "AI Provider",
            "SERVICE": "Service",
        }
        CATEGORY_ORDER = [
            "MARKETING",
            "UTILITY",
            "AUTHENTICATION",
            "AUTHENTICATION_INTERNATIONAL",
            "AI_PROVIDER",
            "SERVICE",
        ]
        TYPE_LABELS = {
            "FREE_CUSTOMER_SERVICE": "Free customer service",
            "FREE_ENTRY_POINT": "Free entry point",
        }

        by_category_total = {}
        by_category_paid = {}
        by_category_cost = {}
        by_type_free = {t: 0 for t in TYPE_LABELS}
        total_delivered_meta = 0
        total_cost = 0.0

        for p in data_points:
            cat = p.get("pricing_category") or "OTHER"
            ptype = p.get("pricing_type") or "REGULAR"
            vol = p.get("volume") or 0
            cost = p.get("cost") or 0
            by_category_total[cat] = by_category_total.get(cat, 0) + vol
            by_category_cost[cat] = by_category_cost.get(cat, 0) + cost
            total_delivered_meta += vol
            total_cost += cost
            if ptype == "REGULAR":
                by_category_paid[cat] = by_category_paid.get(cat, 0) + vol
            else:
                by_type_free[ptype] = by_type_free.get(ptype, 0) + vol

        # Any category Meta returns that we don't have a curated label/order for still gets shown.
        all_categories = list(CATEGORY_ORDER) + [
            c for c in by_category_total if c not in CATEGORY_ORDER
        ]

        def category_rows(counter):
            return [
                {
                    "category": cat,
                    "label": CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()),
                    "count": counter.get(cat, 0),
                }
                for cat in all_categories
            ]

        def cost_rows():
            return [
                {
                    "category": cat,
                    "label": CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()),
                    "amount": round(by_category_cost.get(cat, 0), 2),
                }
                for cat in all_categories
            ]

        # ---- exact local message-status counts for the same window & account ----
        start_dt = timezone.make_aware(
            dt.combine(start_date, time.min), timezone.get_current_timezone()
        )
        end_dt = timezone.make_aware(
            dt.combine(end_date, time.max), timezone.get_current_timezone()
        )
        msgs = (
            Message.objects.filter(contact__whatsapp_config_id=config_id)
            .annotate(effective_at=Coalesce("timestamp", "created_at"))
            .filter(effective_at__range=(start_dt, end_dt))
        )

        outgoing = msgs.filter(direction="OUTGOING")
        message_status = {
            # Sourced from Meta directly â€” accurate regardless of local webhook lag/gaps.
            "sent": meta_sent,
            "delivered": meta_delivered,
            # Meta doesn't expose a "received" metric on the WABA, so this is our own
            # incoming-message log â€” the one number here Meta can't verify for us.
            "received": msgs.filter(direction="INCOMING").count(),
            "received_source": "local_db",
            # Kept for reference/debugging â€” not shown on the pricing cards, and known to be
            # unreliable where local delivery-status tracking has fallen behind Meta's truth.
            "local_sent": outgoing.count(),
            "local_delivered": outgoing.filter(
                status__in=["Delivered", "Read"]
            ).count(),
            "read": outgoing.filter(status="Read").count(),
            "failed": outgoing.filter(status="Failed").count(),
            "waiting": outgoing.filter(status__in=["Sent", "Waiting"]).count(),
        }

        return Response(
            {
                "range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "key": range_key,
                    "clamped_to_90_days": clamped,
                },
                "currency": currency,
                "phone_numbers": phone_numbers,
                "countries": countries_seen,
                "selected_phone_number_id": phone_filter or None,
                "selected_country": country_filter or None,
                "message_status": message_status,
                "messages_delivered": {
                    "total": total_delivered_meta,
                    "by_category": category_rows(by_category_total),
                },
                "free_messages_delivered": {
                    "total": sum(by_type_free.values()),
                    "by_type": [
                        {
                            "type": t,
                            "label": TYPE_LABELS[t],
                            "count": by_type_free.get(t, 0),
                        }
                        for t in TYPE_LABELS
                    ],
                },
                "paid_messages_delivered": {
                    "total": sum(by_category_paid.values()),
                    "by_category": category_rows(by_category_paid),
                },
                "total_charges": {
                    "total": round(total_cost, 2),
                    "currency": currency,
                    "by_category": cost_rows(),
                },
            }
        )

    @action(detail=False, methods=["GET"], url_path="message-pricing-detail")
    def message_pricing_detail(self, request):
        """
        Drill-down for a single Message Pricing row: the actual contacts/messages
        behind a clicked count. Category attribution comes from the campaign's
        template category (Meta assigns pricing category from the template at send
        time); free-vs-paid is inferred from WhatsApp's 24-hour free customer-service
        window since Meta's aggregate pricing API doesn't expose per-message billing.
        """
        from datetime import datetime as dt, time
        from django.db.models.functions import Coalesce

        config_id = get_whatsapp_config_id(request)
        resolved = _resolve_pricing_date_range(request)
        if resolved is None:
            return Response(
                {"error": "Invalid custom date range."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_date, end_date, range_key, clamped = resolved

        start_dt = timezone.make_aware(
            dt.combine(start_date, time.min), timezone.get_current_timezone()
        )
        end_dt = timezone.make_aware(
            dt.combine(end_date, time.max), timezone.get_current_timezone()
        )

        metric = (request.query_params.get("metric") or "").lower()
        category = (request.query_params.get("category") or "").upper()
        free_type = (request.query_params.get("free_type") or "").upper()

        base = (
            Message.objects.filter(contact__whatsapp_config_id=config_id)
            .annotate(effective_at=Coalesce("timestamp", "created_at"))
            .filter(effective_at__range=(start_dt, end_dt))
            .select_related("contact", "campaign__template")
        )

        note = None
        cat_label = category.replace("_", " ").title() if category else ""

        if metric == "sent":
            qs = base.filter(direction="OUTGOING")
            title = "Messages Sent"
            note = "The card total above comes from Meta's own delivery report. This list is from your local message log instead, so the count here can differ if local status tracking has fallen behind."
        elif metric == "delivered":
            qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
            title = "Messages Delivered"
            note = "The card total above comes from Meta's own delivery report. This list is from your local message log instead, so the count here can differ if local status tracking has fallen behind."
        elif metric == "received":
            qs = base.filter(direction="INCOMING")
            title = "Messages Received"
        elif metric == "category":
            qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
            if category == "SERVICE":
                qs = qs.filter(campaign__isnull=True)
            elif category:
                qs = qs.filter(campaign__template__category=category)
            else:
                qs = qs.none()
            title = f"{cat_label} â€” Delivered"
            note = "Category is read from the template used for each campaign message. Session (non-template) replies are grouped under Service."
        elif metric == "free":
            if free_type == "FREE_ENTRY_POINT":
                qs = base.none()
                title = "Free Entry Point"
                note = "Free entry-point messages come from click-to-WhatsApp ads and aren't tracked as individual conversation records in this app yet."
            else:
                qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
                title = "Free Customer Service â€” Delivered"
                note = "Estimated: messages sent within 24 hours of the contactâ€™s last incoming message, which WhatsApp treats as a free customer-service reply."
        elif metric in ("paid", "charge"):
            qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
            if category == "SERVICE":
                qs = qs.none()
            elif category:
                qs = qs.filter(campaign__template__category=category)
            title = f"{cat_label} â€” Paid" if category else "Paid Messages"
            note = "Estimated: messages sent outside the 24-hour free customer-service window for that contact, billed under WhatsAppâ€™s per-message pricing."
        else:
            return Response(
                {"error": "Unknown metric."}, status=status.HTTP_400_BAD_REQUEST
            )

        qs = qs.order_by("-effective_at")

        # Free/paid status isn't stored locally, so it's inferred per-message from conversation
        # timing â€” that inference has to happen in Python over a bounded candidate window.
        needs_free_paid_split = metric in ("free", "paid", "charge") and not (
            metric == "free" and free_type == "FREE_ENTRY_POINT"
        )
        if needs_free_paid_split:
            candidates = list(qs[:1000])
            contact_ids = {m.contact_id for m in candidates}
            recent_incoming = {}
            if contact_ids:
                incoming_qs = (
                    Message.objects.filter(
                        contact_id__in=contact_ids, direction="INCOMING"
                    )
                    .annotate(effective_at=Coalesce("timestamp", "created_at"))
                    .order_by("contact_id", "effective_at")
                    .values("contact_id", "effective_at")
                )
                for row in incoming_qs:
                    recent_incoming.setdefault(row["contact_id"], []).append(
                        row["effective_at"]
                    )

            def is_free(m):
                times = recent_incoming.get(m.contact_id) or []
                window_start = m.effective_at - timedelta(hours=24)
                return any(
                    window_start <= t < m.effective_at
                    for t in times
                    if t and m.effective_at
                )

            if metric == "free":
                filtered = [
                    m for m in candidates if is_free(m) or m.campaign_id is None
                ]
            else:
                filtered = [
                    m for m in candidates if not (is_free(m) or m.campaign_id is None)
                ]
            total_count = len(filtered)
            page_items = filtered[:100]
        else:
            total_count = qs.count()
            page_items = list(qs[:100])

        results = []
        for m in page_items:
            contact = m.contact
            raw_phone = contact.phone_number or ""
            clean_phone = re.sub(r"\D", "", raw_phone)
            if len(clean_phone) > 10:
                clean_phone = clean_phone[-10:]
            name = contact.name if (contact.name and contact.name != "Unknown") else ""
            results.append(
                {
                    "contact_id": contact.id,
                    "name": name or None,
                    "phone": clean_phone or raw_phone,
                    "status": m.status,
                    "direction": m.direction,
                    "campaign_name": m.campaign.name if m.campaign_id else None,
                    "template_category": m.campaign.template.category
                    if (m.campaign_id and m.campaign.template_id)
                    else None,
                    "timestamp": m.effective_at.isoformat() if m.effective_at else None,
                    "text": (m.text or "")[:140],
                }
            )

        return Response(
            {
                "title": title,
                "note": note,
                "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "total_count": total_count,
                "shown_count": len(results),
                "results": results,
            }
        )


from django.utils import timezone
import datetime
from whatsapp_app.serializers import InboxContactSerializer, InboxMessageSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000


class InboxViewSet(ViewSet):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    @action(detail=False, methods=["GET"])
    def conversations(self, request):
        config_id = get_whatsapp_config_id(request)
        contacts = Contact.objects.filter(whatsapp_config_id=config_id).select_related(
            "assigned_to"
        )

        search = request.query_params.get("search")
        if search:
            contacts = contacts.filter(
                Q(name__icontains=search) | Q(phone_number__icontains=search)
            )

        contacts = contacts.order_by(
            F("last_message_time").desc(nulls_last=True), "-created_at"
        )

        paginator = ContactPagination()
        page = paginator.paginate_queryset(contacts, request)
        if page is not None:
            serializer = InboxContactSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = InboxContactSerializer(contacts, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def messages(self, request):
        contact_id = request.query_params.get("contact_id")
        if not contact_id:
            return Response({"error": "contact_id is required"}, status=400)

        config_id = get_whatsapp_config_id(request)

        try:
            contact = Contact.objects.get(id=contact_id, whatsapp_config_id=config_id)
        except Contact.DoesNotExist:
            return Response(
                {"error": "Contact not found under this configuration"}, status=404
            )

        messages = Message.objects.filter(contact=contact).order_by("-timestamp")

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(messages, request)
        if page is not None:
            serializer = InboxMessageSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = InboxMessageSerializer(messages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["POST"], url_path="send-message")
    def send_message(self, request):
        contact_id = request.data.get("contact_id")
        text = (request.data.get("message") or request.data.get("text") or "").strip()
        media_url = request.data.get("media_url") or request.data.get("mediaUrl") or ""
        file_obj = (
            request.FILES.get("file")
            or request.FILES.get("media")
            or request.FILES.get("attachment")
        )
        buttons = request.data.get("buttons") or []

        if not contact_id:
            return Response({"error": "contact_id is required"}, status=400)

        if not text and not media_url and not file_obj:
            return Response(
                {"error": "Message text or media file is required"}, status=400
            )

        if file_obj and not media_url:
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import uuid

            safe_filename = f"inbox_attachments/{uuid.uuid4().hex}_{file_obj.name}"
            saved_path = default_storage.save(
                safe_filename, ContentFile(file_obj.read())
            )
            media_url = request.build_absolute_uri(default_storage.url(saved_path))

        msg_type = request.data.get("type")
        if not msg_type:
            if media_url or file_obj:
                m_lower = (file_obj.name if file_obj else media_url).lower()
                if any(
                    m_lower.endswith(ext)
                    for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")
                ):
                    msg_type = "image"
                elif any(
                    m_lower.endswith(ext)
                    for ext in (".mp4", ".mov", ".avi", ".webm", ".mkv")
                ):
                    msg_type = "video"
                else:
                    msg_type = "document"
            else:
                msg_type = "text"

        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return Response({"error": "Contact not found"}, status=404)

        if not contact.is_within_24h_window:
            return Response(
                {
                    "success": False,
                    "message": "Manual messaging is not allowed outside WhatsApp's 24-hour customer service window.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Idempotency guard for rapid duplicate clicks/retries.
        recent_duplicate = (
            Message.objects.filter(
                contact=contact,
                direction="OUTGOING",
                text=text,
                created_at__gte=timezone.now() - timedelta(seconds=10),
            )
            .order_by("-created_at")
            .first()
        )
        if recent_duplicate:
            return Response(
                InboxMessageSerializer(recent_duplicate).data, status=status.HTTP_200_OK
            )

        # Forward outgoing message to WhatsApp middleware first.
        success, response_data = send_whatsapp_message(
            contact.phone_number,
            text,
            media_url=media_url,
            buttons=buttons,
            message_type=msg_type,
            config=contact.whatsapp_config,
        )
        if not success:
            return Response(
                {
                    "error": "Failed to send message to WhatsApp user",
                    "details": response_data,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Race-condition guard: webhook may have inserted same outgoing message while sending.
        post_send_duplicate = (
            Message.objects.filter(
                contact=contact,
                direction="OUTGOING",
                text=text,
                created_at__gte=timezone.now() - timedelta(seconds=30),
            )
            .order_by("-created_at")
            .first()
        )
        # Extract provider message ID from Flask response
        provider_message_id = extract_provider_message_id(response_data)

        if post_send_duplicate:
            update_fields = []
            if not post_send_duplicate.provider_message_id and provider_message_id:
                post_send_duplicate.provider_message_id = provider_message_id
                update_fields.append("provider_message_id")
            if media_url and not post_send_duplicate.media_url:
                post_send_duplicate.media_url = media_url
                update_fields.append("media_url")
            if buttons and not post_send_duplicate.buttons:
                post_send_duplicate.buttons = buttons
                update_fields.append("buttons")
            if update_fields:
                post_send_duplicate.save(update_fields=update_fields)
            return Response(
                InboxMessageSerializer(post_send_duplicate).data,
                status=status.HTTP_200_OK,
            )

        msg = Message.objects.create(
            contact=contact,
            text=text,
            direction="OUTGOING",
            status="Waiting",
            sender="agent",
            provider_message_id=provider_message_id,
            type=msg_type,
            media_url=media_url or None,
            buttons=buttons,
            timestamp=timezone.now(),
        )

        contact.last_message = text
        contact.last_message_time = msg.timestamp
        contact.save(update_fields=["last_message", "last_message_time"])
        _broadcast_crm_event("new_message", contact=contact, message=msg)

        return Response(InboxMessageSerializer(msg).data)

    @action(detail=False, methods=["POST"], url_path="receive-message")
    def receive_message(self, request):
        phone_number = _normalize_phone_number(request.data.get("phone_number"))
        text = request.data.get("message")

        if not phone_number or not text:
            return Response(
                {"error": "phone_number and message are required"}, status=400
            )

        config_id = get_whatsapp_config_id(request)
        from whatsapp_app.models import WhatsAppConfig

        # Get the owner of the WhatsApp configuration
        config = WhatsAppConfig.objects.filter(id=config_id).first()
        config_owner = (
            config.user if (config and config.user) else get_public_api_user()
        )

        contact, created = Contact.objects.get_or_create(
            phone_number=phone_number,
            whatsapp_config_id=config_id,
            defaults={"name": phone_number, "user": config_owner},
        )

        msg = Message.objects.create(
            contact=contact,
            text=text,
            direction="INCOMING",
            status="Delivered",
            sender="received",
        )

        now = timezone.now()
        contact.last_message = text
        contact.last_message_time = msg.timestamp
        contact.last_message_received_at = now
        contact.unread_count += 1
        contact.save(
            update_fields=[
                "last_message",
                "last_message_time",
                "last_message_received_at",
                "unread_count",
                "updated_at",
            ]
        )

        return Response(InboxMessageSerializer(msg).data)

    @action(detail=False, methods=["PATCH"], url_path="mark-read")
    def mark_read(self, request):
        contact_id = request.data.get("contact_id")
        if not contact_id:
            return Response({"error": "contact_id is required"}, status=400)

        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return Response({"error": "Contact not found"}, status=404)

        contact.unread_count = 0
        contact.save(update_fields=["unread_count"])

        now = timezone.now()
        Message.objects.filter(
            contact=contact, direction="INCOMING", read=False
        ).update(
            read=True,
            status="Read",
            read_at=now,
        )
        _broadcast_crm_event(
            "message_read",
            contact=contact,
            extra={
                "data": {
                    "contact_id": contact.id,
                    "phone_number": contact.phone_number,
                    "unread_count": 0,
                }
            },
        )
        _broadcast_crm_event(
            "unread_updated",
            contact=contact,
            extra={
                "data": {
                    "contact_id": contact.id,
                    "phone_number": contact.phone_number,
                    "unread_count": 0,
                }
            },
        )
        return Response({"status": "success"})

    @action(detail=False, methods=["PATCH"], url_path="update-status")
    def update_status(self, request):
        contact_id = request.data.get("contact_id")
        status_val = request.data.get("status")
        if not contact_id or not status_val:
            return Response({"error": "contact_id and status are required"}, status=400)

        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return Response({"error": "Contact not found"}, status=404)

        contact.status = status_val
        contact.save()

        _broadcast_crm_event(
            "lead_updated",
            contact=contact,
            extra={"data": {"contact_id": contact.id, "status": status_val}},
        )
        return Response({"status": "success"})

    @action(detail=False, methods=["PATCH"], url_path="assign-user")
    def assign_user(self, request):
        contact_id = request.data.get("contact_id")
        user_id = request.data.get("user_id")

        if not contact_id or not user_id:
            return Response(
                {"error": "contact_id and user_id are required"}, status=400
            )

        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return Response({"error": "Contact not found"}, status=404)

        try:
            assigned_user = User.objects.get(id=user_id)
            contact.assigned_to = assigned_user
            contact.save()

            _broadcast_crm_event(
                "lead_updated",
                contact=contact,
                extra={
                    "data": {
                        "contact_id": contact.id,
                        "assigned_to_id": assigned_user.id,
                        "assigned_to_email": assigned_user.email,
                    }
                },
            )
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)


def _find_button_action_node(button_actions, reply_lower, payload_lower):
    """
    Recursively searches a button_actions tree for an entry whose key matches the incoming
    button reply, and returns its config. Each config may itself carry a 'next_button_actions'
    dict (set when the action is SEND_TEMPLATE), which chains into the reply-buttons of whatever
    template that action sends - so workflows can nest arbitrarily deep. Matching is against
    whatever button text/payload the operator configured; no button text, template name, or
    date is ever hardcoded here.
    """
    if not button_actions:
        return None

    # Pass 1: exact match against title or payload - safest, avoids one button's text
    # accidentally matching inside a different (longer) button's text.
    for btn_key, action_cfg in button_actions.items():
        btn_key_clean = str(btn_key).strip().lower()
        if btn_key_clean and (
            btn_key_clean == reply_lower or btn_key_clean == payload_lower
        ):
            return action_cfg

    # Pass 2: nested chains - a deeper, more specific rule should win over a loose substring
    # match at this level.
    for action_cfg in button_actions.values():
        nested = action_cfg.get("next_button_actions")
        if nested:
            found = _find_button_action_node(nested, reply_lower, payload_lower)
            if found:
                return found

    # Pass 3: substring fallback, for legacy configs or partial title matches.
    for btn_key, action_cfg in button_actions.items():
        btn_key_clean = str(btn_key).strip().lower()
        if btn_key_clean and (
            btn_key_clean in reply_lower or btn_key_clean in payload_lower
        ):
            return action_cfg

    return None


def _execute_button_action(action_cfg, campaign, contact, waba_config, reply_clean):
    """
    Executes a single matched button-action node. Every value used (template, message text,
    workflow) comes from action_cfg, which is entirely operator-configured through the Reminder
    Campaign UI - nothing here is tied to any specific campaign, template, or date.
    """
    from whatsapp_app.models import (
        ReminderExecution,
        AutomationLog,
        MessageTemplate,
        FollowUpWorkflow,
        FollowUpContactState,
        Message,
    )
    from whatsapp_app.utils import send_automation_message
    from whatsapp_app.services import send_whatsapp_message_direct_to_meta
    from django.utils import timezone
    import re

    action_type = action_cfg.get("action", "CONTINUE")
    followup_text = (action_cfg.get("reply_text") or "").strip()

    if action_type == "STOP":
        ReminderExecution.objects.filter(
            reminder_campaign=campaign, contact=contact, status="PENDING"
        ).update(status="DIVERTED")
        ReminderExecution.objects.filter(
            reminder_campaign=campaign, contact=contact
        ).update(button_response=reply_clean)
        AutomationLog.objects.create(
            whatsapp_config=campaign.whatsapp_config,
            automation_type="REMINDER",
            contact=contact,
            action_type="DIVERTED",
            details=f"Contact clicked '{reply_clean}'. Rule triggered STOP.",
        )

    elif action_type == "FOLLOWUP_REPLY" and followup_text:
        ReminderExecution.objects.filter(
            reminder_campaign=campaign, contact=contact
        ).update(button_response=reply_clean)
        send_whatsapp_message_direct_to_meta(
            recipient_id=contact.phone_number,
            waba_config=waba_config,
            text=followup_text,
        )
        Message.objects.create(
            contact=contact,
            text=followup_text,
            sender=waba_config.get("phone_id") or "System",
            direction="OUTGOING",
            status="Sent",
            type="text",
            timestamp=timezone.now(),
        )

    elif action_type == "SEND_TEMPLATE":
        ReminderExecution.objects.filter(
            reminder_campaign=campaign, contact=contact
        ).update(button_response=reply_clean)
        tpl_id = action_cfg.get("template_id") or action_cfg.get("template")
        if tpl_id:
            tpl_obj = MessageTemplate.objects.filter(id=tpl_id).first()
            if tpl_obj:
                tpl_vars = dict(action_cfg.get("template_variables", {}) or {})
                body_vars = list(tpl_vars.get("body_variables", []))

                # Auto-fill a sensible default if the operator left variables unconfigured
                # and the template expects at least one - the contact's own name, not a
                # campaign-specific value.
                has_body_placeholders = bool(
                    re.search(r"\{\{\d+\}\}", tpl_obj.body or "")
                )
                if has_body_placeholders and not body_vars:
                    body_vars = [contact.name or "Customer"]
                    tpl_vars["body_variables"] = body_vars

                t_media = action_cfg.get("media_url")
                send_automation_message(contact, tpl_obj, t_media, tpl_vars)
                AutomationLog.objects.create(
                    whatsapp_config=campaign.whatsapp_config,
                    automation_type="REMINDER",
                    contact=contact,
                    action_type="SENT",
                    details=f"Contact clicked '{reply_clean}'. Triggered template '{tpl_obj.name}'.",
                )

    elif action_type == "TRIGGER_FOLLOWUP":
        ReminderExecution.objects.filter(
            reminder_campaign=campaign, contact=contact
        ).update(button_response=reply_clean)
        followup_wf_id = action_cfg.get("followup_workflow_id")
        if followup_wf_id:
            wf = FollowUpWorkflow.objects.filter(
                id=followup_wf_id, is_active=True
            ).first()
            if wf:
                first_step = wf.steps.filter(step_number=1).first()
                if first_step:
                    FollowUpContactState.objects.update_or_create(
                        contact=contact,
                        workflow=wf,
                        defaults={
                            "current_step": first_step,
                            "status": "PENDING",
                            "next_execution_time": timezone.now()
                            + timezone.timedelta(seconds=first_step.delay_seconds),
                            "retry_count": 0,
                        },
                    )


def evaluate_interconnected_button_response(contact, text_reply, payload=None):
    """
    Matches an incoming WhatsApp button/quick-reply against whatever button_actions rules were
    configured for the contact's active reminder campaigns (including nested 'next_button_actions'
    chains for multi-step flows), and executes the matched action. Fully data-driven: works
    identically for any campaign, any template, any button wording - nothing is hardcoded to a
    specific event, date, or template name.
    """
    try:
        from whatsapp_app.models import ReminderCampaign, ReminderSchedule
        from whatsapp_app.utils import get_whatsapp_config
        import logging

        logger = logging.getLogger(__name__)

        reply_clean = (text_reply or "").strip()
        reply_lower = reply_clean.lower()
        payload_clean = (payload or "").strip()
        payload_lower = payload_clean.lower()

        if not reply_lower and not payload_lower:
            return False

        waba_config = get_whatsapp_config(contact.whatsapp_config_id)

        active_campaigns = ReminderCampaign.objects.filter(
            contacts=contact, is_active=True
        )
        for campaign in active_campaigns:
            for schedule in ReminderSchedule.objects.filter(reminder_campaign=campaign):
                matched_cfg = _find_button_action_node(
                    schedule.button_actions or {}, reply_lower, payload_lower
                )
                if matched_cfg:
                    _execute_button_action(
                        matched_cfg, campaign, contact, waba_config, reply_clean
                    )
                    return True

        return False
    except Exception as err:
        import logging

        logging.getLogger(__name__).error(f"Error evaluating button response: {err}")
        return False


def process_catalog_webhook(
    sender_id, text, msg_type, interactive_data, config, contact, request
):
    normalized_text = (text or "").lower().strip()
    is_trigger = normalized_text in ["show products", "catalog", "menu", "products"]

    list_reply = None
    button_reply = None
    if msg_type == "interactive" and interactive_data:
        inter_type = interactive_data.get("type")
        if inter_type == "list_reply":
            list_reply = interactive_data.get("list_reply", {})
        elif inter_type == "button_reply":
            button_reply = interactive_data.get("button_reply", {})

    action_id = ""
    if list_reply:
        action_id = list_reply.get("id", "")
    elif button_reply:
        action_id = button_reply.get("id", "")

    is_catalog_reply = False
    if action_id:
        for prefix in ["cat_", "sub_", "prod_", "buy_", "sales_", "back_"]:
            if action_id.startswith(prefix):
                is_catalog_reply = True
                break

    if not is_trigger and not is_catalog_reply:
        return False

    # Check if catalog_access is enabled for this WhatsApp configuration
    catalog_access_enabled = False
    if config:
        from django.db import connection

        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "SELECT catalog_access FROM whatsapp_saas_whatsappuser WHERE whatsapp_config_id = %s",
                    [config.id],
                )
                row = cursor.fetchone()
                if row:
                    catalog_access_enabled = bool(row[0])
            except Exception:
                pass

    # Superusers bypass the access check
    if (
        config
        and config.user
        and (
            getattr(config.user, "is_superuser", False)
            or getattr(config.user, "is_staff", False)
        )
    ):
        catalog_access_enabled = True

    if not catalog_access_enabled:
        return False

    from whatsapp_app.utils import get_whatsapp_config
    from whatsapp_app.services import send_whatsapp_message_direct_to_meta

    waba_config = get_whatsapp_config(config.id)

    # 1. Main Categories Menu (Level 1)
    if is_trigger or action_id == "back_menu":
        categories = Category.objects.filter(whatsapp_config=config, is_active=True)
        if not categories.exists():
            text_body = "Our catalog is currently empty. Please check back later!"
            send_whatsapp_message_direct_to_meta(
                recipient_id=sender_id, waba_config=waba_config, text=text_body
            )
            Message.objects.create(
                contact=contact,
                text=text_body,
                sender=config.phone_number_id or "Chatbot",
                direction="OUTGOING",
                status="Sent",
                type="text",
                timestamp=timezone.now(),
            )
            return True

        rows = []
        for cat in categories[:10]:
            rows.append(
                {
                    "id": f"cat_{cat.id}",
                    "title": cat.name[:24],
                    "description": cat.description[:72] if cat.description else "",
                }
            )
        interactive_payload = {
            "type": "list",
            "body": {
                "text": "Welcome to our Catalog! Please select a category to browse our products:"
            },
            "action": {
                "button": "Browse Categories",
                "sections": [{"title": "Categories", "rows": rows}],
            },
        }
        send_whatsapp_message_direct_to_meta(
            recipient_id=sender_id,
            waba_config=waba_config,
            interactive=interactive_payload,
        )
        Message.objects.create(
            contact=contact,
            text="[Interactive Categories List Menu]",
            sender=config.phone_number_id or "Chatbot",
            direction="OUTGOING",
            status="Sent",
            type="interactive",
            timestamp=timezone.now(),
        )
        return True

    # 2. Subcategories Menu (Level 2)
    elif action_id.startswith("cat_") or action_id.startswith("back_cat_"):
        cat_id = int(action_id.split("_")[-1])
        subcategories = SubCategory.objects.filter(category_id=cat_id, is_active=True)
        if not subcategories.exists():
            text_body = (
                "No subcategories found under this category. Send 'Menu' to go back."
            )
            send_whatsapp_message_direct_to_meta(
                recipient_id=sender_id, waba_config=waba_config, text=text_body
            )
            Message.objects.create(
                contact=contact,
                text=text_body,
                sender=config.phone_number_id or "Chatbot",
                direction="OUTGOING",
                status="Sent",
                type="text",
                timestamp=timezone.now(),
            )
            return True

        rows = []
        for sub in subcategories[:10]:
            rows.append(
                {
                    "id": f"sub_{sub.id}",
                    "title": sub.name[:24],
                    "description": sub.description[:72] if sub.description else "",
                }
            )
        interactive_payload = {
            "type": "list",
            "body": {"text": "Select a subcategory to browse products:"},
            "action": {
                "button": "Browse Subcategories",
                "sections": [{"title": "Sub Categories", "rows": rows}],
            },
        }
        send_whatsapp_message_direct_to_meta(
            recipient_id=sender_id,
            waba_config=waba_config,
            interactive=interactive_payload,
        )
        Message.objects.create(
            contact=contact,
            text="[Interactive Subcategories List Menu]",
            sender=config.phone_number_id or "Chatbot",
            direction="OUTGOING",
            status="Sent",
            type="interactive",
            timestamp=timezone.now(),
        )
        return True

    # 3. Products Menu (Level 3)
    elif action_id.startswith("sub_") or action_id.startswith("back_sub_"):
        sub_id = int(action_id.split("_")[-1])
        products = Product.objects.filter(subcategory_id=sub_id, is_active=True)
        if not products.exists():
            text_body = "No products found in this subcategory."
            send_whatsapp_message_direct_to_meta(
                recipient_id=sender_id, waba_config=waba_config, text=text_body
            )
            Message.objects.create(
                contact=contact,
                text=text_body,
                sender=config.phone_number_id or "Chatbot",
                direction="OUTGOING",
                status="Sent",
                type="text",
                timestamp=timezone.now(),
            )
            return True

        rows = []
        for prod in products[:10]:
            rows.append(
                {
                    "id": f"prod_{prod.id}",
                    "title": prod.name[:24],
                    "description": f"â‚¹{prod.price} - {prod.description[:50]}"
                    if prod.description
                    else f"â‚¹{prod.price}",
                }
            )
        interactive_payload = {
            "type": "list",
            "body": {"text": "Select a product to view details:"},
            "action": {
                "button": "Browse Products",
                "sections": [{"title": "Products", "rows": rows}],
            },
        }
        send_whatsapp_message_direct_to_meta(
            recipient_id=sender_id,
            waba_config=waba_config,
            interactive=interactive_payload,
        )
        Message.objects.create(
            contact=contact,
            text="[Interactive Products List Menu]",
            sender=config.phone_number_id or "Chatbot",
            direction="OUTGOING",
            status="Sent",
            type="interactive",
            timestamp=timezone.now(),
        )
        return True

    # 4. Product Detail Card & Buttons (Level 4)
    elif action_id.startswith("prod_"):
        prod_id = int(action_id.split("_")[-1])
        try:
            product = Product.objects.get(id=prod_id)
        except Product.DoesNotExist:
            return False

        # Try to resolve Meta Media ID or fallback public URL
        image_header = None

        if product.meta_product_id:
            image_header = {"id": product.meta_product_id}
        elif product.image:
            try:
                import mimetypes
                import os
                import io
                from PIL import Image
                from whatsapp_app.services import upload_media_for_message

                file_path = product.image.path
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    file_name = os.path.basename(file_path)
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if not mime_type:
                        mime_type = "image/png"

                    # Auto-compress image if size is > 5 MB
                    if len(file_bytes) > 5 * 1024 * 1024:
                        try:
                            img = Image.open(io.BytesIO(file_bytes))
                            if img.mode in ("RGBA", "LA") or (
                                img.mode == "P" and "transparency" in img.info
                            ):
                                img = img.convert("RGB")
                            quality = 85
                            out_io = io.BytesIO()
                            img.save(out_io, format="JPEG", quality=quality)
                            while out_io.tell() > 4.5 * 1024 * 1024 and quality > 15:
                                quality -= 10
                                out_io = io.BytesIO()
                                img.save(out_io, format="JPEG", quality=quality)
                            file_bytes = out_io.getvalue()
                            file_name = os.path.splitext(file_name)[0] + ".jpg"
                            mime_type = "image/jpeg"
                        except Exception as compress_err:
                            import logging

                            logging.getLogger(__name__).warning(
                                f"Failed to compress product image: {compress_err}"
                            )

                    meta_media_id = upload_media_for_message(
                        file_bytes=file_bytes,
                        file_name=file_name,
                        mime_type=mime_type,
                        waba_config=waba_config,
                    )
                    if meta_media_id:
                        product.meta_product_id = meta_media_id
                        product.save(update_fields=["meta_product_id"])
                        image_header = {"id": meta_media_id}
            except Exception as meta_err:
                import logging

                logging.getLogger(__name__).warning(
                    f"On-demand Meta media upload failed for product id={product.id}: {meta_err}"
                )

        # If no media ID was resolved, fallback to public link
        if not image_header:
            fallback_link = (
                "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"
            )
            if product.image_url:
                fallback_link = product.image_url
            image_header = {"link": fallback_link}

        buttons = [
            {"type": "reply", "reply": {"id": f"buy_{product.id}", "title": "Buy Now"}},
            {
                "type": "reply",
                "reply": {"id": f"sales_{product.id}", "title": "Contact Sales"},
            },
            {
                "type": "reply",
                "reply": {"id": f"back_sub_{product.subcategory_id}", "title": "Back"},
            },
        ]

        interactive_payload = {
            "type": "button",
            "header": {"type": "image", "image": image_header},
            "body": {
                "text": f"*{product.name}*\n\nPrice: *â‚¹{product.price}*\n\n{product.description or ''}"
            },
            "action": {"buttons": buttons},
        }
        send_whatsapp_message_direct_to_meta(
            recipient_id=sender_id,
            waba_config=waba_config,
            interactive=interactive_payload,
        )
        Message.objects.create(
            contact=contact,
            text=f"[Product Detail: {product.name}]",
            sender=config.phone_number_id or "Chatbot",
            direction="OUTGOING",
            status="Sent",
            type="interactive",
            timestamp=timezone.now(),
        )
        return True

    # 5. Buy Now Action
    elif action_id.startswith("buy_"):
        prod_id = int(action_id.split("_")[-1])
        try:
            product = Product.objects.get(id=prod_id)
            text_body = f"Thank you for your interest! Your order request for *{product.name}* (Price: â‚¹{product.price}) has been received. A sales agent will contact you shortly to confirm the details."
        except Product.DoesNotExist:
            text_body = "The selected product is no longer available. Please browse our menu again by sending 'Menu'."

        send_whatsapp_message_direct_to_meta(
            recipient_id=sender_id, waba_config=waba_config, text=text_body
        )
        Message.objects.create(
            contact=contact,
            text=text_body,
            sender=config.phone_number_id or "Chatbot",
            direction="OUTGOING",
            status="Sent",
            type="text",
            timestamp=timezone.now(),
        )
        return True

    # 6. Contact Sales Action
    elif action_id.startswith("sales_"):
        text_body = "Your request has been routed to our sales team. A representative will contact you shortly. Thank you!"
        send_whatsapp_message_direct_to_meta(
            recipient_id=sender_id, waba_config=waba_config, text=text_body
        )
        Message.objects.create(
            contact=contact,
            text=text_body,
            sender=config.phone_number_id or "Chatbot",
            direction="OUTGOING",
            status="Sent",
            type="text",
            timestamp=timezone.now(),
        )
        return True

    return False


class WebhookEventViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []  # Bypass global JWT auth for webhook

    @action(detail=False, methods=["get"], url_path="events")
    def verify(self, request):
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")

        # Validate GET verification challenge from Meta Developer Portal
        if mode == "subscribe" and challenge:
            if (
                token
                and WhatsAppConfig.objects.filter(webhook_verify_token=token).exists()
            ):
                from django.http import HttpResponse

                return HttpResponse(challenge, content_type="text/plain")
        return Response("Forbidden", status=403)

    @action(detail=False, methods=["post"], url_path="events")
    def events(self, request):
        body = request.data or {}
        if not isinstance(body, dict):
            try:
                import json

                raw_body = (
                    request.body.decode("utf-8") if hasattr(request, "body") else ""
                )
                body = json.loads(raw_body) if raw_body else {}
            except Exception:
                body = {}

        # Debug logging to a local log file
        try:
            with open("webhook_debug.log", "a") as f_log:
                import json

                f_log.write(
                    f"\n--- Direct Meta Webhook Event received at {timezone.now()} ---\n"
                )
                f_log.write(
                    json.dumps(
                        body if isinstance(body, dict) else {"raw": str(body)}, indent=2
                    )
                )
                f_log.write("\n")
        except Exception:
            pass

        if not isinstance(body, dict) or not body.get("object"):
            return Response(
                {"status": "ignored", "reason": "invalid_object"}, status=200
            )

        try:
            entry = body.get("entry", [])[0]
            changes = entry.get("changes", [])[0]
            value = changes.get("value", {})

            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            config = None
            if phone_number_id:
                config = WhatsAppConfig.objects.filter(
                    phone_number_id=phone_number_id
                ).first()
            if not config:
                config = WhatsAppConfig.get_solo()
                if phone_number_id:
                    with open("webhook_debug.log", "a") as f_log:
                        f_log.write(
                            f"\n[WEBHOOK WARNING] Unknown phone_number_id received: {phone_number_id}. Routing to default config ID {config.id if config else 'None'}.\n"
                        )

            is_ai_enabled = getattr(config, "is_ai_enabled", True) if config else True

            # Set thread-local config ID to ensure all operations triggered inside this thread lifecycle are configured under this account
            if config:
                from whatsapp_app.middleware import _thread_locals

                _thread_locals.active_config_id = config.id

            # Automatically resolve and update missing waba_id from incoming webhook WABA ID
            webhook_waba_id = entry.get("id")
            if webhook_waba_id and phone_number_id and config:
                if not config.whatsapp_business_account_id:
                    config.whatsapp_business_account_id = webhook_waba_id
                    config.save(update_fields=["whatsapp_business_account_id"])

            # Case A: Status Updates (Delivered, Read, Failed)
            if value.get("statuses"):
                for status_data in value["statuses"]:
                    status_type = status_data.get("status")
                    recipient = re.sub(
                        r"\D", "", str(status_data.get("recipient_id") or "")
                    )
                    provider_message_id = status_data.get("id")

                    if provider_message_id:
                        message = Message.objects.filter(
                            provider_message_id=provider_message_id
                        ).first()

                        # Fallback for recent outgoing matching
                        if not message and recipient:
                            recent_cutoff = timezone.now() - timedelta(seconds=45)
                            message = (
                                Message.objects.filter(
                                    contact__phone_number=recipient,
                                    provider_message_id__isnull=True,
                                    direction="OUTGOING",
                                    created_at__gte=recent_cutoff,
                                )
                                .order_by("-created_at")
                                .first()
                            )
                            if message:
                                message.provider_message_id = provider_message_id

                        if message:
                            new_status = status_type.title()
                            STATUS_PRECEDENCE = {
                                "Waiting": 0,
                                "Failed": 1,
                                "Sent": 2,
                                "Delivered": 3,
                                "Read": 4,
                            }
                            current_status = message.status or "Waiting"

                            if STATUS_PRECEDENCE.get(
                                new_status, 0
                            ) > STATUS_PRECEDENCE.get(current_status, 0):
                                message.status = new_status
                                if new_status == "Read":
                                    message.read = True

                            ts_raw = status_data.get("timestamp")
                            ts = timezone.now()
                            if ts_raw:
                                try:
                                    ts = datetime.datetime.fromtimestamp(
                                        int(ts_raw), tz=datetime.timezone.utc
                                    )
                                except Exception:
                                    pass

                            if new_status == "Sent":
                                message.sent_at = ts
                            elif new_status == "Delivered":
                                message.delivered_at = ts
                            elif new_status == "Read":
                                message.read_at = ts
                            elif new_status == "Failed":
                                message.failed_at = ts

                            message.save()
                            _broadcast_crm_event(
                                "message_status",
                                contact=message.contact,
                                message=message,
                            )

                return Response({"status": "success", "is_ai_enabled": is_ai_enabled})

            # Case B: Incoming Messages
            if value.get("messages"):
                incoming_list = value["messages"]

                # WhatsApp can batch more than one message into a single webhook call
                # (documented Cloud API behavior - e.g. a user sending several messages in
                # quick succession, or a backlog flushing after downtime). The pipeline below
                # (AI auto-reply, keyword auto-replies, catalog handling) is built around a
                # single message, so any additional messages in the batch are recorded here
                # as plain incoming records instead of being silently dropped - previously
                # only incoming_list[0] was ever saved, undercounting "messages received"
                # whenever a batch arrived.
                for extra_data in incoming_list[1:]:
                    try:
                        if extra_data.get("is_echo"):
                            continue
                        extra_id = extra_data.get("id")
                        if (
                            extra_id
                            and Message.objects.filter(
                                provider_message_id=extra_id
                            ).exists()
                        ):
                            continue
                        extra_sender = _normalize_phone_number(extra_data.get("from"))
                        extra_type = extra_data.get("type", "text")
                        if extra_type == "text":
                            extra_text = (extra_data.get("text") or {}).get(
                                "body"
                            ) or ""
                        else:
                            extra_text = f"[{extra_type.title()} Attachment]"
                        extra_text = extra_text[:255]
                        extra_ts_raw = extra_data.get("timestamp")
                        extra_ts = timezone.now()
                        if extra_ts_raw:
                            try:
                                extra_ts = datetime.datetime.fromtimestamp(
                                    int(extra_ts_raw), tz=datetime.timezone.utc
                                )
                            except Exception:
                                pass
                        extra_owner = (
                            config.user
                            if (config and config.user)
                            else get_public_api_user()
                        )
                        extra_contact = (
                            Contact.objects.filter(
                                phone_number=extra_sender, whatsapp_config=config
                            )
                            .order_by("-id")
                            .first()
                        )
                        if not extra_contact:
                            extra_contact = Contact.objects.create(
                                phone_number=extra_sender,
                                whatsapp_config=config,
                                name=None,
                                user=extra_owner,
                            )
                        extra_message = Message.objects.create(
                            contact=extra_contact,
                            text=extra_text,
                            sender=extra_sender,
                            direction="INCOMING",
                            status="Sent",
                            type=extra_type,
                            provider_message_id=extra_id,
                            timestamp=extra_ts,
                        )
                        extra_contact.last_message = extra_text
                        extra_contact.last_message_time = extra_ts
                        extra_contact.last_message_received_at = timezone.now()
                        extra_contact.last_customer_message_time = timezone.now()
                        extra_contact.customer_service_window_expiry = (
                            timezone.now() + datetime.timedelta(hours=24)
                        )
                        extra_contact.is_service_window_open = True
                        extra_contact.unread_count += 1
                        extra_contact.last_seen = timezone.now()
                        extra_contact.save(
                            update_fields=[
                                "last_message",
                                "last_message_time",
                                "last_message_received_at",
                                "last_customer_message_time",
                                "customer_service_window_expiry",
                                "is_service_window_open",
                                "unread_count",
                                "last_seen",
                            ]
                        )
                        _broadcast_crm_event(
                            "new_message", contact=extra_contact, message=extra_message
                        )
                        _create_and_broadcast_notification(
                            extra_contact, extra_message, "new_message"
                        )
                    except Exception as batch_err:
                        logger.warning(
                            f"Failed to record batched incoming message: {batch_err}"
                        )

                message_data = incoming_list[0]

                # Filter echoes
                if message_data.get("is_echo"):
                    return Response({"status": "ignored", "reason": "echo"})

                sender_id = _normalize_phone_number(message_data.get("from"))
                provider_message_id = message_data.get("id")

                # Deduplication check
                if (
                    provider_message_id
                    and Message.objects.filter(
                        provider_message_id=provider_message_id
                    ).exists()
                ):
                    return Response({"status": "ignored", "reason": "duplicate"})

                text = ""
                media_url = ""
                caption = ""
                media_id = None
                msg_type = message_data.get("type", "text")

                btn_payload = ""
                if msg_type == "text":
                    text = (
                        (message_data.get("text") or {}).get("body")
                        or message_data.get("body")
                        or ""
                    )
                elif msg_type == "interactive":
                    interactive_data = message_data.get("interactive") or {}
                    inter_type = interactive_data.get("type")
                    if inter_type == "button_reply":
                        btn_rep = interactive_data.get("button_reply") or {}
                        text = (
                            btn_rep.get("title")
                            or btn_rep.get("id")
                            or btn_rep.get("payload")
                            or ""
                        )
                        btn_payload = (
                            btn_rep.get("id")
                            or btn_rep.get("payload")
                            or btn_rep.get("title")
                            or ""
                        )
                    elif inter_type == "list_reply":
                        list_rep = interactive_data.get("list_reply") or {}
                        text = list_rep.get("title") or list_rep.get("id") or ""
                        btn_payload = list_rep.get("id") or list_rep.get("title") or ""
                    elif inter_type == "nfm_reply":
                        nfm_rep = interactive_data.get("nfm_reply") or {}
                        text = nfm_rep.get("response_json") or "Form Submitted"
                    else:
                        text = str(
                            interactive_data.get(inter_type) or "Interactive Response"
                        )
                elif msg_type == "button":
                    btn_obj = message_data.get("button") or {}
                    if isinstance(btn_obj, dict):
                        text = btn_obj.get("text") or btn_obj.get("payload") or ""
                        btn_payload = (
                            btn_obj.get("payload") or btn_obj.get("text") or ""
                        )
                    else:
                        text = str(btn_obj)
                elif msg_type in ["image", "video", "audio", "document", "sticker"]:
                    media_info = message_data.get(msg_type, {})
                    if isinstance(media_info, dict):
                        caption = media_info.get("caption", "")
                        media_id = media_info.get("id", "")
                        text = (
                            caption if caption else f"[{msg_type.title()} Attachment]"
                        )
                        if media_id and config and config.whatsapp_api_token:
                            import requests
                            import os
                            from django.core.files.storage import default_storage
                            from django.core.files.base import ContentFile

                            try:
                                headers = {
                                    "Authorization": f"Bearer {config.whatsapp_api_token}"
                                }
                                url_response = requests.get(
                                    f"https://graph.facebook.com/v20.0/{media_id}",
                                    headers=headers,
                                    timeout=10,
                                )
                                if url_response.status_code == 200:
                                    dl_url = url_response.json().get("url")
                                    mime_type = url_response.json().get(
                                        "mime_type", "image/jpeg"
                                    )
                                    if dl_url:
                                        media_response = requests.get(
                                            dl_url, headers=headers, timeout=15
                                        )
                                        if media_response.status_code == 200:
                                            ext = mime_type.split("/")[-1]
                                            if ext == "jpeg":
                                                ext = "jpg"
                                            if len(ext) > 5:
                                                ext = "bin"
                                            filename = (
                                                f"incoming_messages/{media_id}.{ext}"
                                            )
                                            saved_path = default_storage.save(
                                                filename,
                                                ContentFile(media_response.content),
                                            )
                                            media_url = f"/media/{saved_path}"
                            except Exception as e:
                                import logging

                                logging.getLogger(__name__).warning(
                                    f"Failed to download incoming media: {e}"
                                )
                                media_url = (
                                    f"https://graph.facebook.com/v20.0/{media_id}"
                                )

                if text and len(text) > 255:
                    text = text[:255]

                # Get the owner of the WhatsApp configuration, falling back to public user if not set
                config_owner = (
                    config.user if (config and config.user) else get_public_api_user()
                )

                # Get or Create Contact record safely
                contact = (
                    Contact.objects.filter(
                        phone_number=sender_id, whatsapp_config=config
                    )
                    .order_by("-id")
                    .first()
                )
                if not contact:
                    contact = Contact.objects.create(
                        phone_number=sender_id,
                        whatsapp_config=config,
                        name=None,
                        user=config_owner,
                    )

                ts_raw = message_data.get("timestamp")
                ts = timezone.now()
                if ts_raw:
                    try:
                        ts = datetime.datetime.fromtimestamp(
                            int(ts_raw), tz=datetime.timezone.utc
                        )
                    except Exception:
                        pass

                # Create message record
                message = Message.objects.create(
                    contact=contact,
                    text=text,
                    sender=sender_id,
                    direction="INCOMING",
                    status="Sent",
                    type=msg_type,
                    provider_message_id=provider_message_id,
                    media_url=media_url,
                    caption=caption,
                    timestamp=ts,
                )

                # Trigger auto send template if first message
                is_first_message = not contact.messages.exclude(id=message.id).exists()
                if (
                    is_first_message
                    and config
                    and config.auto_send_template
                    and config.auto_send_template_name
                ):
                    try:
                        from whatsapp_app.services import (
                            send_whatsapp_message_direct_to_meta,
                        )

                        cached_tpl = MessageTemplate.objects.filter(
                            name=config.auto_send_template_name, whatsapp_config=config
                        ).first()
                        lang = "en_US"
                        body_text = f"Sent template: {config.auto_send_template_name}"
                        if cached_tpl:
                            lang = cached_tpl.language
                            body_text = cached_tpl.body
                        else:
                            from whatsapp_app.models import WhatsAppTemplate

                            whatsapp_tpl = WhatsAppTemplate.objects.filter(
                                template_name=config.auto_send_template_name,
                                whatsapp_config=config,
                            ).first()
                            if whatsapp_tpl:
                                lang = whatsapp_tpl.language
                                body_text = whatsapp_tpl.body_text

                        import uuid

                        auto_provider_id = str(uuid.uuid4())

                        meta_response, status_code = (
                            send_whatsapp_message_direct_to_meta(
                                recipient_id=contact.phone_number,
                                waba_config=config,
                                template_name=config.auto_send_template_name,
                                language_code=lang,
                                components=[],
                            )
                        )

                        if status_code in (200, 201):
                            Message.objects.create(
                                contact=contact,
                                text=body_text,
                                sender="agent",
                                direction="OUTGOING",
                                status="Sent",
                                type="template",
                                provider_message_id=auto_provider_id,
                                timestamp=timezone.now(),
                            )
                            contact.last_message = body_text
                            contact.last_message_time = timezone.now()
                            contact.save(
                                update_fields=["last_message", "last_message_time"]
                            )
                    except Exception as e:
                        logger.error(f"Failed to auto-send first-message template: {e}")

                # Record button response/reply on latest ReminderExecution for campaign tracking
                try:
                    from whatsapp_app.models import ReminderExecution

                    latest_exec = (
                        ReminderExecution.objects.filter(contact=contact)
                        .order_by("-created_at")
                        .first()
                    )
                    if latest_exec:
                        latest_exec.button_response = text or btn_payload
                        latest_exec.save(update_fields=["button_response"])
                except Exception as rx_err:
                    pass

                # Evaluate button responses for interconnected reminder workflows
                try:
                    btn_handled = evaluate_interconnected_button_response(
                        contact, text, btn_payload
                    )
                    if btn_handled:
                        return Response(
                            {"status": "success", "message": "button_response_handled"}
                        )
                except Exception as btn_err:
                    logger.warning(f"Interconnected button response error: {btn_err}")

                # Trigger async download if media is present
                if media_id and config and config.whatsapp_api_token:
                    dl_thread = threading.Thread(
                        target=_download_and_save_media,
                        args=(message.id, media_id, config.whatsapp_api_token),
                    )
                    dl_thread.start()

                # Update Contact states
                contact.last_message = text
                contact.last_message_time = ts
                contact.last_message_received_at = timezone.now()
                contact.last_customer_message_time = timezone.now()
                contact.customer_service_window_expiry = (
                    timezone.now() + datetime.timedelta(hours=24)
                )
                contact.is_service_window_open = True
                contact.unread_count += 1
                contact.last_seen = timezone.now()
                contact.save(
                    update_fields=[
                        "last_message",
                        "last_message_time",
                        "last_message_received_at",
                        "last_customer_message_time",
                        "customer_service_window_expiry",
                        "is_service_window_open",
                        "unread_count",
                        "last_seen",
                    ]
                )

                # Broadcast events
                _broadcast_crm_event("new_message", contact=contact, message=message)
                _create_and_broadcast_notification(contact, message, "new_message")

                # Process WhatsApp interactive catalog
                catalog_handled = process_catalog_webhook(
                    sender_id=sender_id,
                    text=text,
                    msg_type=msg_type,
                    interactive_data=message_data.get("interactive", {})
                    if msg_type == "interactive"
                    else None,
                    config=config,
                    contact=contact,
                    request=request,
                )
                if catalog_handled:
                    return Response({"status": "success", "message": "catalog_handled"})

                # Process Custom Keyword Auto Replies
                if text:
                    from whatsapp_app.models import AutoReply
                    from whatsapp_app.services import (
                        send_whatsapp_message_direct_to_meta,
                    )
                    from whatsapp_app.utils import get_whatsapp_config

                    normalized_incoming = text.strip().lower()
                    active_replies = AutoReply.objects.filter(
                        whatsapp_config=config, is_active=True
                    )

                    matched_reply = None
                    for rep in active_replies:
                        kw_list = [
                            k.strip().lower()
                            for k in rep.keywords.split(",")
                            if k.strip()
                        ]
                        if normalized_incoming in kw_list:
                            matched_reply = rep
                            break

                    if matched_reply:
                        waba_config = get_whatsapp_config(config.id)

                        media_url = None
                        if matched_reply.media:
                            media_url = request.build_absolute_uri(
                                matched_reply.media.url
                            )

                        if isinstance(matched_reply.buttons, str):
                            import json

                            try:
                                matched_reply.buttons = json.loads(
                                    matched_reply.buttons
                                )
                            except Exception:
                                matched_reply.buttons = []

                        interactive_payload = None
                        if (
                            matched_reply.buttons
                            and isinstance(matched_reply.buttons, list)
                            and len(matched_reply.buttons) > 0
                        ):
                            if len(matched_reply.buttons) <= 3:
                                buttons = []
                                for idx, btn_val in enumerate(matched_reply.buttons):
                                    title = (
                                        btn_val.get("text")
                                        if isinstance(btn_val, dict)
                                        else str(btn_val)
                                    )
                                    buttons.append(
                                        {
                                            "type": "reply",
                                            "reply": {
                                                "id": f"autoreply_btn_{matched_reply.id}_{idx}",
                                                "title": title[:20],
                                            },
                                        }
                                    )
                                safe_text = (
                                    matched_reply.reply_text
                                    if matched_reply.reply_text
                                    else "Please choose an option:"
                                )
                                interactive_payload = {
                                    "type": "button",
                                    "body": {"text": safe_text},
                                    "action": {"buttons": buttons},
                                }
                                if media_url:
                                    interactive_payload["header"] = {
                                        "type": "image",
                                        "image": {"link": media_url},
                                    }
                            else:
                                rows = []
                                for idx, btn_val in enumerate(
                                    matched_reply.buttons[:10]
                                ):
                                    title = (
                                        btn_val.get("text")
                                        if isinstance(btn_val, dict)
                                        else str(btn_val)
                                    )
                                    rows.append(
                                        {
                                            "id": f"autoreply_btn_{matched_reply.id}_{idx}",
                                            "title": title[:24],
                                        }
                                    )
                                safe_text = (
                                    matched_reply.reply_text
                                    if matched_reply.reply_text
                                    else "Please choose an option:"
                                )
                                interactive_payload = {
                                    "type": "list",
                                    "body": {"text": safe_text},
                                    "action": {
                                        "button": "View Options",
                                        "sections": [
                                            {"title": "Choose an option", "rows": rows}
                                        ],
                                    },
                                }

                        if interactive_payload:
                            if interactive_payload.get("type") == "list" and media_url:
                                # Lists don't support media headers, so send the image separately first
                                send_whatsapp_message_direct_to_meta(
                                    recipient_id=sender_id,
                                    waba_config=waba_config,
                                    media_url=media_url,
                                    media_type="image",
                                )
                                Message.objects.create(
                                    contact=contact,
                                    text="[Image Attachment]",
                                    sender=config.phone_number_id or "Chatbot",
                                    direction="OUTGOING",
                                    status="Sent",
                                    type="image",
                                    media_url=media_url,
                                    timestamp=timezone.now(),
                                )

                            send_whatsapp_message_direct_to_meta(
                                recipient_id=sender_id,
                                waba_config=waba_config,
                                interactive=interactive_payload,
                            )
                        else:
                            send_whatsapp_message_direct_to_meta(
                                recipient_id=sender_id,
                                waba_config=waba_config,
                                text=matched_reply.reply_text,
                                media_url=media_url,
                                media_type="image" if media_url else None,
                            )

                        Message.objects.create(
                            contact=contact,
                            text=matched_reply.reply_text,
                            sender=config.phone_number_id or "Chatbot",
                            direction="OUTGOING",
                            status="Sent",
                            type="interactive"
                            if interactive_payload
                            else ("image" if media_url else "text"),
                            media_url=media_url,
                            buttons=matched_reply.buttons,
                            timestamp=timezone.now(),
                        )
                        return Response(
                            {"status": "success", "message": "keyword_autoreply_sent"}
                        )

                # Launch AI qualification responder in the background (Non-blocking)
                if is_ai_enabled and text:
                    from whatsapp_app.utils import process_and_reply_with_aria_core
                    import threading

                    ai_thread = threading.Thread(
                        target=process_and_reply_with_aria_core,
                        args=(contact, text, provider_message_id),
                    )
                    ai_thread.daemon = True
                    ai_thread.start()

                return Response({"status": "success", "is_ai_enabled": is_ai_enabled})

            return Response({"status": "success", "message": "unhandled_event"})

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            with open("webhook_debug.log", "a") as f_log:
                f_log.write(f"\n!!! ERROR AT WEBHOOK EVENT: {str(e)} !!!\n")
                f_log.write(error_details)
            # Return 200 OK so Meta does not disable webhook subscription on temporary parsing failures
            return Response(
                {"status": "error", "details": str(e)}, status=status.HTTP_200_OK
            )


class SendMessageViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def create(self, request):
        contact_id = request.data.get("contact_id")
        message_text = request.data.get("message", "")
        media_url = request.data.get("media_url") or request.data.get("mediaUrl") or ""
        buttons = request.data.get("buttons") or []
        msg_type = request.data.get("type", "text")
        normalized_text = (message_text or "").strip()
        if not normalized_text:
            return Response(
                {"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            contact = Contact.objects.get(id=contact_id)
        except Contact.DoesNotExist:
            return Response(
                {"error": "Contact not found"}, status=status.HTTP_404_NOT_FOUND
            )

        if not contact.is_within_24h_window:
            return Response(
                {
                    "success": False,
                    "message": "Manual messaging is not allowed outside WhatsApp's 24-hour customer service window.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Idempotency guard: if same outgoing message for same contact was just created,
        # return the existing row instead of sending/saving again.
        dedupe_cutoff = timezone.now() - timedelta(seconds=10)
        recent_duplicate = (
            Message.objects.filter(
                contact=contact,
                direction="OUTGOING",
                text=normalized_text,
                created_at__gte=dedupe_cutoff,
            )
            .order_by("-created_at")
            .first()
        )
        if recent_duplicate:
            return Response(
                MessageSerializer(recent_duplicate).data, status=status.HTTP_200_OK
            )

        # Clear escalated flag upon human agent's manual outgoing message
        if contact.attributes and contact.attributes.get("escalated"):
            contact.attributes["escalated"] = False
            contact.save(update_fields=["attributes"])

        # Forward the message to the chatbot backend/WhatsApp API
        success, response_data = send_whatsapp_message(
            contact.phone_number,
            normalized_text,
            media_url=media_url,
            buttons=buttons,
            message_type=msg_type,
        )

        if not success:
            return Response(
                {
                    "error": "Failed to send message to WhatsApp",
                    "details": response_data,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Race-condition guard: webhook may have inserted the same outgoing message
        # while this request was waiting on Flask.
        post_send_duplicate = (
            Message.objects.filter(
                contact=contact,
                direction="OUTGOING",
                text=normalized_text,
                created_at__gte=timezone.now() - timedelta(seconds=30),
            )
            .order_by("-created_at")
            .first()
        )
        provider_message_id = extract_provider_message_id(response_data)

        if post_send_duplicate:
            # Race condition fix: Webhook created the message but didn't have the Meta ID yet.
            # We have the ID from the API response, so we must inject it into the duplicate record!
            update_fields = []
            if not post_send_duplicate.provider_message_id and provider_message_id:
                post_send_duplicate.provider_message_id = provider_message_id
                update_fields.append("provider_message_id")
            if media_url and not post_send_duplicate.media_url:
                post_send_duplicate.media_url = media_url
                update_fields.append("media_url")
            if buttons and not post_send_duplicate.buttons:
                post_send_duplicate.buttons = buttons
                update_fields.append("buttons")
            if update_fields:
                post_send_duplicate.save(update_fields=update_fields)
            return Response(
                MessageSerializer(post_send_duplicate).data, status=status.HTTP_200_OK
            )

        message = Message.objects.create(
            contact=contact,
            text=normalized_text,
            sender="agent",
            direction="OUTGOING",
            status="Sent",
            type=msg_type,
            media_url=media_url,
            provider_message_id=provider_message_id,
            buttons=buttons,
            timestamp=timezone.now(),
        )

        contact.last_message = normalized_text
        contact.last_message_time = message.timestamp
        contact.save(update_fields=["last_message", "last_message_time"])

        msg_data = MessageSerializer(message).data
        _broadcast_crm_event("message_sent", contact=contact, message=message)

        return Response(msg_data, status=status.HTTP_201_CREATED)


class SendWhatsAppTemplateView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def post(self, request):
        contact_id = request.data.get("contact_id")
        phone_number = _normalize_phone_number(request.data.get("phone_number"))
        template_name = request.data.get("template_name")
        language_code_input = request.data.get("language_code")
        components = request.data.get("components")
        if isinstance(components, str):
            import json

            try:
                components = json.loads(components)
            except json.JSONDecodeError:
                components = None

        if not isinstance(components, list):
            components = []

        # Resolve media URL and auto-upload if template requires image/video/document header
        custom_text = request.data.get("text")

        if not contact_id and not phone_number:
            return Response(
                {"error": "contact_id or phone_number is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not template_name:
            return Response(
                {"error": "template_name is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        contact = None
        if contact_id:
            try:
                contact = Contact.objects.get(id=contact_id)
                if not phone_number:
                    phone_number = contact.phone_number
            except Contact.DoesNotExist:
                pass

        if not phone_number:
            return Response(
                {"error": "Phone number is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Ensure phone number has '91' prefix if it's 10 digits
        phone_number = "".join(filter(str.isdigit, str(phone_number)))
        if len(phone_number) == 10:
            phone_number = f"91{phone_number}"

        config_id = get_whatsapp_config_id(request)
        if not contact:
            contact = Contact.objects.filter(
                phone_number=phone_number, whatsapp_config_id=config_id
            ).first()
            if not contact:
                from django.contrib.auth.models import AnonymousUser

                user = (
                    request.user
                    if request.user and not isinstance(request.user, AnonymousUser)
                    else get_public_api_user()
                )
                contact = Contact.objects.create(
                    phone_number=phone_number,
                    name=phone_number,
                    whatsapp_config_id=config_id,
                    user=user,
                )

        if not contact.phone_number:
            return Response(
                {"error": "Contact phone number is missing"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        normalized_template_name = str(template_name).strip().lower()
        normalized_template_name = normalized_template_name.replace(" ", "_")

        cached_template = MessageTemplate.objects.filter(
            name=normalized_template_name
        ).first()

        # If template not found, provide helpful error message
        if not cached_template:
            available_templates = MessageTemplate.objects.values_list(
                "name", flat=True
            ).distinct()
            return Response(
                {
                    "error": f"Template '{normalized_template_name}' not found in the system.",
                    "available_templates": list(available_templates)[
                        :10
                    ],  # Show first 10 available templates
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        language_code = (
            language_code_input
            or (cached_template.language if cached_template else None)
            or "en_US"
        )

        waba_config = get_whatsapp_config(contact.whatsapp_config_id)

        template_media_url = ""
        display_media_url = ""
        media_id = None

        if cached_template and cached_template.header_type in [
            "IMAGE",
            "VIDEO",
            "DOCUMENT",
        ]:
            header_media_type = cached_template.header_type.lower()

            # PRIORITY 1: Check if file was uploaded via multipart/form-data
            header_media_file = request.FILES.get("header_media")

            if header_media_file:
                # File was uploaded - upload it directly to Meta Media API
                try:
                    from whatsapp_app.services import upload_media_for_message

                    file_bytes = header_media_file.read()
                    mime_type = header_media_file.content_type or "image/jpeg"
                    file_name = header_media_file.name

                    logger.info(
                        f"Uploading template media file to Meta: {file_name} ({mime_type})"
                    )
                    media_id = upload_media_for_message(
                        file_bytes, file_name, mime_type, waba_config
                    )
                    template_media_url = f"meta_media_{media_id}"  # Just for tracking
                    display_media_url = (
                        f"/whatsapp-templates/{cached_template.id}/header-media/"
                    )
                    logger.info(
                        f"Successfully uploaded media to Meta, got media_id: {media_id}"
                    )
                except Exception as e:
                    logger.error(f"Failed to upload template media file to Meta: {e}")
                    return Response(
                        {"error": f"Failed to upload template media to Meta: {str(e)}"},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
            else:
                # PRIORITY 2: Try to resolve media from request data (backward compatibility for URL strings)
                header_media_url = (
                    request.data.get("header_media_url")
                    or request.data.get("media_url")
                    or request.data.get("mediaUrl")
                    or extract_media_url_from_components(components)
                )

                # PRIORITY 3: Try to resolve from template stored configuration
                if not header_media_url:
                    # Check if header_media is a saved Meta media ID (numeric string from a previous upload)
                    # If so, use it directly as media_id without re-uploading
                    hm = cached_template.header_media
                    if hm and str(hm).strip().isdigit():
                        media_id = str(hm).strip()
                        template_media_url = "cached_meta_media"
                        display_media_url = (
                            f"/whatsapp-templates/{cached_template.id}/header-media/"
                        )
                        header_media_url = (
                            None  # Already have media_id, skip URL processing
                        )
                    else:
                        # Prefer meta_media_url (actual HTTP URL on Meta CDN) over base64 uploaded_preview_image
                        header_media_url = (
                            cached_template.meta_media_url
                            or cached_template.header_media
                            or cached_template.uploaded_preview_image
                        )
                        if not header_media_url and cached_template.sample_values:
                            header_media_url = cached_template.sample_values.get(
                                "header_handle"
                            ) or cached_template.sample_values.get("media_url")
                        if (
                            isinstance(header_media_url, list)
                            and len(header_media_url) > 0
                        ):
                            header_media_url = header_media_url[0]

                # If we have media URL (and no media_id yet), upload it to Meta for this send.
                if header_media_url and not media_id:
                    if header_media_url.startswith("data:"):
                        try:
                            import base64
                            from whatsapp_app.services import upload_media_for_message

                            meta_info, b64_data = header_media_url.split(",", 1)
                            mime_type = "image/jpeg"
                            if ":" in meta_info and ";" in meta_info:
                                mime_type = meta_info.split(":", 1)[1].split(";", 1)[0]

                            ext_map = {
                                "image/jpeg": "jpg",
                                "image/png": "png",
                                "image/gif": "gif",
                                "image/webp": "webp",
                                "video/mp4": "mp4",
                                "application/pdf": "pdf",
                            }
                            file_name = (
                                f"template_header.{ext_map.get(mime_type, 'bin')}"
                            )
                            file_bytes = base64.b64decode(b64_data)

                            media_id = upload_media_for_message(
                                file_bytes,
                                file_name,
                                mime_type,
                                waba_config,
                            )
                            template_media_url = "embedded_template_media"
                            display_media_url = f"/whatsapp-templates/{cached_template.id}/header-media/"
                            # Save media_id back to template so future sends skip the re-upload
                            if media_id:
                                try:
                                    cached_template.header_media = media_id
                                    cached_template.save(update_fields=["header_media"])
                                    logger.info(
                                        f"Saved media_id {media_id} to template {cached_template.id} for future reuse"
                                    )
                                except Exception as save_err:
                                    logger.warning(
                                        f"Could not save media_id to template: {save_err}"
                                    )
                        except Exception as e:
                            logger.error(
                                f"Failed to upload embedded template media for sending: {e}"
                            )
                            return Response(
                                {
                                    "error": f"Failed to upload embedded template media to Meta: {str(e)}"
                                },
                                status=status.HTTP_502_BAD_GATEWAY,
                            )
                    else:
                        try:
                            from whatsapp_app.services import (
                                upload_template_media_for_sending,
                            )

                            media_id_dict = upload_template_media_for_sending(
                                header_media_url, waba_config
                            )
                            media_id = (
                                media_id_dict.get("id")
                                if isinstance(media_id_dict, dict)
                                else media_id_dict
                            )
                            template_media_url = header_media_url
                            display_media_url = header_media_url
                        except Exception as e:
                            logger.error(
                                f"Failed to auto-upload template media for sending: {e}"
                            )
                            return Response(
                                {
                                    "error": f"Failed to upload template media to Meta: {str(e)}"
                                },
                                status=status.HTTP_502_BAD_GATEWAY,
                            )
                elif not media_id:
                    # No file, no URL, and no cached media_id â€” truly nothing configured
                    return Response(
                        {
                            "error": f"Header media of type '{cached_template.header_type}' is required for template '{normalized_template_name}' but was not provided."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # Construct the header component using the media ID
            if media_id:
                media_obj = {"id": media_id}
                if header_media_type == "document":
                    media_obj["filename"] = request.data.get("header_filename") or (
                        request.FILES.get("header_media").name
                        if request.FILES.get("header_media")
                        else "document.pdf"
                    )

                if components is None:
                    components = []

                # Add or update the header component in the components list
                header_comp = next(
                    (c for c in components if c.get("type") == "header"), None
                )
                if header_comp is None:
                    header_comp = {
                        "type": "header",
                        "parameters": [
                            {"type": header_media_type, header_media_type: media_obj}
                        ],
                    }
                    components.insert(0, header_comp)
                else:
                    header_comp["parameters"] = [
                        {"type": header_media_type, header_media_type: media_obj}
                    ]

        # Auto-inject OTP button parameter for AUTHENTICATION templates to prevent #131008 error
        if cached_template and cached_template.category == "AUTHENTICATION":
            otp_code = None
            for comp in components or []:
                if comp.get("type") == "body":
                    params = comp.get("parameters", [])
                    if params and len(params) > 0:
                        otp_code = params[0].get("text")
                        break

            if not otp_code:
                vars_dict = request.data.get("variables")
                if isinstance(vars_dict, dict):
                    otp_code = vars_dict.get("1") or next(
                        iter(vars_dict.values()), None
                    )

            if not otp_code:
                otp_code = "123456"  # Fail-safe default

            button_comp = next(
                (c for c in components if c.get("type") == "button"), None
            )
            if button_comp is None:
                button_comp = {
                    "type": "button",
                    "sub_type": "url",
                    "index": "0",
                    "parameters": [{"type": "text", "text": str(otp_code)}],
                }
                components.append(button_comp)
            else:
                button_comp["sub_type"] = "url"
                button_comp["index"] = "0"
                button_comp["parameters"] = [{"type": "text", "text": str(otp_code)}]

        # Generate unique provider_message_id for tracking
        import uuid

        provider_message_id = str(uuid.uuid4())

        payload = {
            "to": contact.phone_number,
            "template_name": normalized_template_name,
            "language_code": language_code,
            "provider_message_id": provider_message_id,
            "contact_id": contact.id,
        }
        if components is not None:
            payload["components"] = components
        if template_media_url:
            payload["media_url"] = template_media_url

        from whatsapp_app.services import send_whatsapp_message_direct_to_meta

        meta_response, status_code = send_whatsapp_message_direct_to_meta(
            recipient_id=contact.phone_number,
            waba_config=waba_config,
            template_name=normalized_template_name,
            language_code=language_code,
            components=components,
        )

        # Resolve the actual message text â€” never store [Template: ...] placeholders
        final_message_text = (custom_text or "").strip()

        # If frontend didn't send text, render from the cached template body
        if not final_message_text and cached_template and cached_template.body:
            rendered = cached_template.body
            if components:
                body_comp = next(
                    (c for c in components if c.get("type") == "body"), None
                )
                if body_comp:
                    params = body_comp.get("parameters", [])
                    for i, p in enumerate(params):
                        placeholder = f"{{{{{i + 1}}}}}"
                        p_val = p.get("text", "")
                        if not p_val and "currency" in p:
                            p_val = p.get("currency", {}).get("fallback_value", "")
                        rendered = rendered.replace(placeholder, str(p_val))
            final_message_text = rendered

        # Absolute last resort: use the template name as plain text (no bracket notation)
        if not final_message_text:
            final_message_text = normalized_template_name

        buttons_for_db = (
            cached_template.buttons
            if cached_template and cached_template.buttons
            else []
        )

        if status_code not in [200, 201]:
            Message.objects.create(
                contact=contact,
                text=final_message_text,
                direction="OUTGOING",
                sender="agent",
                status="Failed",
                type="template",
                media_url=display_media_url or template_media_url or None,
                buttons=buttons_for_db,
                timestamp=timezone.now(),
                failed_at=timezone.now(),
            )
            return Response(
                {
                    "error": "Meta Cloud API rejected template send",
                    "status_code": status_code,
                    "details": meta_response,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        provider_message_id = extract_provider_message_id(
            meta_response,
            fallback=provider_message_id,
        )

        msg = Message.objects.create(
            contact=contact,
            text=final_message_text,
            direction="OUTGOING",
            sender="agent",
            status="Sent",
            type="template",
            media_url=display_media_url or template_media_url or None,
            provider_message_id=provider_message_id,
            timestamp=timezone.now(),
            buttons=buttons_for_db,
        )

        contact.last_message = final_message_text
        contact.last_message_time = msg.timestamp
        contact.save(update_fields=["last_message", "last_message_time"])

        _broadcast_crm_event("message_sent", contact=contact, message=msg)

        return Response(
            {
                "status": "success",
                "message_id": msg.id,
                "provider_message_id": msg.provider_message_id,
                "media_url": request.build_absolute_uri(msg.media_url)
                if msg.media_url and msg.media_url.startswith("/")
                else msg.media_url,
                "buttons": msg.buttons,
                "contact_id": contact.id,
                "template_name": normalized_template_name,
            },
            status=status.HTTP_200_OK,
        )


class SyncApprovedTemplatesView(APIView):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    @staticmethod
    def _normalize_category(category_value):
        if not category_value:
            return "UTILITY"

        normalized = str(category_value).strip().upper()
        if normalized in {"MARKETING", "UTILITY", "AUTHENTICATION"}:
            return normalized

        return "UTILITY"

    @staticmethod
    def _extract_component_fields(components):
        body_text = ""
        footer_text = None
        button_text = None

        for component in components or []:
            component_type = str(component.get("type", "")).upper()

            if component_type == "BODY":
                body_text = component.get("text") or ""
            elif component_type == "FOOTER":
                footer_text = component.get("text") or None
            elif component_type == "BUTTONS":
                for button in component.get("buttons", []):
                    text = button.get("text")
                    if text:
                        button_text = text
                        break
                if button_text:
                    break

        return body_text, footer_text, button_text

    def post(self, request):
        config_id = get_whatsapp_config_id(request)
        config_obj = None
        if config_id:
            try:
                config_obj = WhatsAppConfig.objects.get(id=config_id)
            except WhatsAppConfig.DoesNotExist:
                pass
        created, updated, deleted, error = perform_template_sync(config=config_obj)
        if error:
            return Response(
                {"status": "error", "message": error},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "status": "success",
                "synced": created + updated,
                "created": created,
                "updated": updated,
                "deleted": deleted,
            },
            status=status.HTTP_200_OK,
        )


class WhatsAppConfigViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasActiveSubscription]
    serializer_class = WhatsAppConfigSerializer

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated:
            return WhatsAppConfig.objects.filter(user=user)
        return WhatsAppConfig.objects.none()

    def _validate_config(self, config):
        if config.phone_number_id and config.whatsapp_api_token:
            import requests

            from django.utils import timezone

            url = f"https://graph.facebook.com/v20.0/{config.phone_number_id}?fields=status,name_status,quality_rating,code_verification_status&access_token={config.whatsapp_api_token}"
            try:
                res = requests.get(url, timeout=10)
                config.last_checked_at = timezone.now()
                if res.status_code == 200:
                    data = res.json()

                    # Determine actual working status. 'CONNECTED' or 'APPROVED' means it's working
                    if (
                        data.get("status") == "CONNECTED"
                        or data.get("name_status") == "APPROVED"
                    ):
                        config.verification_status = "VERIFIED"
                    else:
                        config.verification_status = data.get("status") or data.get(
                            "code_verification_status", "UNKNOWN"
                        )

                    config.error_message = None
                else:
                    config.verification_status = "UNKNOWN"
                    try:
                        raw_error = res.json().get("error", {}).get("message", res.text)
                        if (
                            "Unsupported get request. Object with ID" in raw_error
                            or "missing permissions" in raw_error
                        ):
                            config.error_message = "Invalid Phone Number ID or missing permissions. Please verify your credentials."
                        elif (
                            "Error validating access token" in raw_error
                            or "Session has expired" in raw_error
                        ):
                            config.error_message = "Your Access Token is invalid or has expired. Please generate a new one."
                        else:
                            config.error_message = f"Meta Error: {raw_error}"
                    except Exception:
                        config.error_message = "Failed to communicate with Meta. Please check your network and credentials."
            except Exception as e:
                from django.utils import timezone

                config.verification_status = "UNKNOWN"
                config.error_message = "Network error: Could not reach Meta's servers."
                config.last_checked_at = timezone.now()

            config.save(
                update_fields=[
                    "verification_status",
                    "error_message",
                    "last_checked_at",
                ]
            )

    def perform_create(self, serializer):
        user = (
            self.request.user
            if getattr(self.request.user, "is_authenticated", False)
            else None
        )
        phone_number_id = serializer.validated_data.get("phone_number_id")
        if phone_number_id and user:
            existing = (
                WhatsAppConfig.objects.filter(phone_number_id=phone_number_id)
                .exclude(user=user)
                .first()
            )
            if existing:
                raise serializers.ValidationError(
                    {
                        "phone_number_id": (
                            "A WhatsApp config for this phone number already exists under a different account "
                            f"('{existing.name}'). Creating a new one here would fragment your conversation history. "
                            "Please contact support to transfer ownership of the existing config instead."
                        )
                    }
                )
        reuse_instance = serializer.context.get("reuse_instance")
        if reuse_instance:
            config = serializer.update(reuse_instance, serializer.validated_data)
        else:
            config = serializer.save(user=user)
        self._validate_config(config)

        # Sync the newly created config's ID back to the SaaS WhatsAppUser table
        if (
            user
            and user.is_authenticated
            and not (
                getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)
            )
        ):
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE whatsapp_saas_whatsappuser 
                        SET whatsapp_config_id = %s 
                        WHERE user_id = (SELECT id FROM whatsapp_saas_user WHERE email = %s)
                        """,
                        [config.id, getattr(user, "email", "")],
                    )
            except Exception as e:
                logger.error(
                    f"Failed to sync newly created config ID to SaaS WhatsAppUser in perform_create: {e}"
                )

    def perform_update(self, serializer):
        config = serializer.save()
        self._validate_config(config)

    def perform_destroy(self, instance):
        user = instance.user
        instance.delete()
        if (
            user
            and user.is_authenticated
            and not (
                getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)
            )
        ):
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE whatsapp_saas_whatsappuser 
                        SET whatsapp_config_id = NULL 
                        WHERE user_id = (SELECT id FROM whatsapp_saas_user WHERE email = %s)
                        """,
                        [getattr(user, "email", "")],
                    )
            except Exception as e:
                logger.error(
                    f"Failed to clear config ID in SaaS WhatsAppUser in perform_destroy: {e}"
                )

    @action(detail=False, methods=["get", "put"])
    def current(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response(
                {"detail": "Authentication credentials were not provided."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        config = WhatsAppConfig.objects.filter(user=user).order_by("id").first()
        if not config:
            return Response(
                {"detail": "No configuration found for this user."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if request.method == "PUT":
            serializer = self.get_serializer(config, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)

            # Re-fetch or re-serialize since perform_update might have modified the config
            serializer = self.get_serializer(config)
            return Response(serializer.data)

        serializer = self.get_serializer(config)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def verify_status(self, request, pk=None):
        config = self.get_object()
        self._validate_config(config)
        serializer = self.get_serializer(config)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def set_active(self, request, pk=None):
        config = self.get_object()
        user = request.user
        if (
            user
            and user.is_authenticated
            and not (
                getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)
            )
        ):
            try:
                from django.db import connection

                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE whatsapp_saas_whatsappuser 
                        SET whatsapp_config_id = %s 
                        WHERE user_id = (SELECT id FROM whatsapp_saas_user WHERE email = %s)
                        """,
                        [config.id, getattr(user, "email", "")],
                    )
            except Exception as e:
                logger.error(
                    f"Failed to sync switched config ID to SaaS WhatsAppUser: {e}"
                )
                return Response(
                    {"detail": f"Failed to sync active config: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        return Response({"status": "active config synced", "config_id": config.id})

    @action(detail=False, methods=["get"], url_path="meta-config")
    def meta_config(self, request):
        from django.conf import settings

        standard_config_id = getattr(settings, "META_CONFIG_ID", "1700921254184499")
        return Response(
            {
                "appId": getattr(settings, "META_APP_ID", ""),
                "configId": standard_config_id,
                # Dedicated Login Configuration with WhatsApp Business App onboarding (coexistence)
                # enabled at the config level. ES v4 reads this from the Login Configuration itself,
                # not from FB.login()'s extras, so a separate config_id is required to switch modes.
                # Falls back to the standard config until META_CONFIG_ID_COEXISTENCE is set.
                "coexistenceConfigId": getattr(
                    settings, "META_CONFIG_ID_COEXISTENCE", ""
                )
                or standard_config_id,
                "graphVersion": getattr(settings, "GRAPH_API_VERSION", "v21.0"),
            }
        )

    @action(detail=False, methods=["post"], url_path="exchange-token")
    def exchange_token(self, request):
        import requests
        from django.conf import settings
        from django.utils import timezone

        code = request.data.get("code")
        config_id = request.data.get("config_id")  # 'new' or numerical ID
        redirect_uri = request.data.get("redirectUri")

        if not code:
            return Response(
                {"error": "Missing 'code' in request body."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        app_id = getattr(settings, "META_APP_ID", "")
        app_secret = getattr(settings, "META_APP_SECRET", "")
        version = getattr(settings, "GRAPH_API_VERSION", "v21.0")

        if not app_id or not app_secret:
            return Response(
                {"error": "Server is missing META_APP_ID or META_APP_SECRET settings."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # 1. Swap authorization code for a business access token
            token_url = f"https://graph.facebook.com/{version}/oauth/access_token"
            token_params = {
                "client_id": app_id,
                "client_secret": app_secret,
                "code": code,
            }
            if redirect_uri:
                token_params["redirect_uri"] = redirect_uri

            token_res = requests.get(token_url, params=token_params, timeout=10)
            if token_res.status_code != 200:
                err_msg = (
                    token_res.json()
                    .get("error", {})
                    .get("message", "Token exchange failed")
                )
                return Response(
                    {"error": f"Meta token exchange error: {err_msg}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            token_data = token_res.json()
            access_token = token_data.get("access_token")

            # 2. Debug token to get scopes & target WABA IDs
            debug_url = f"https://graph.facebook.com/{version}/debug_token"
            debug_params = {
                "input_token": access_token,
                "access_token": f"{app_id}|{app_secret}",
            }
            debug_res = requests.get(debug_url, params=debug_params, timeout=10)
            if debug_res.status_code != 200:
                err_msg = (
                    debug_res.json()
                    .get("error", {})
                    .get("message", "Token debug failed")
                )
                return Response(
                    {"error": f"Meta token debug error: {err_msg}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            debug_data = debug_res.json().get("data", {})
            scopes = debug_data.get("scopes", [])

            waba_ids = []
            granular_scopes = debug_data.get("granular_scopes", [])
            for gs in granular_scopes:
                if gs.get("scope") in [
                    "whatsapp_business_management",
                    "whatsapp_business_messaging",
                ]:
                    for tid in gs.get("target_ids", []):
                        if tid not in waba_ids:
                            waba_ids.append(tid)

            # If waba_ids wasn't debugged but client passed wabaId
            client_waba_id = request.data.get("wabaId")
            if not waba_ids and client_waba_id:
                waba_ids.append(client_waba_id)

            phone_number_id = None
            phone_number = None
            business_name = "WhatsApp Business Account"

            # 3. Fetch phone numbers for first WABA ID
            if waba_ids:
                waba_id = waba_ids[0]
                phone_url = (
                    f"https://graph.facebook.com/{version}/{waba_id}/phone_numbers"
                )
                phone_params = {"access_token": access_token}
                phone_res = requests.get(phone_url, params=phone_params, timeout=10)
                if phone_res.status_code == 200:
                    phone_data = phone_res.json().get("data", [])
                    if phone_data:
                        phone_number_id = phone_data[0].get("id")
                        phone_number = phone_data[0].get("display_phone_number")
                        business_name = phone_data[0].get(
                            "verified_name", business_name
                        )

            # Use client fallbacks
            client_phone_id = request.data.get("phoneNumberId")
            if not phone_number_id and client_phone_id:
                phone_number_id = client_phone_id

            if not phone_number_id:
                return Response(
                    {
                        "error": "No phone number found associated with this account. Please ensure your setup is complete on Meta."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Check unique phone number ID across other accounts
            user = request.user
            existing = (
                WhatsAppConfig.objects.filter(phone_number_id=phone_number_id)
                .exclude(user=user)
                .first()
            )
            if existing:
                return Response(
                    {
                        "error": (
                            "A WhatsApp config for this phone number already exists under a different account "
                            f"('{existing.name}'). Creating a new one here would fragment your conversation history. "
                            "Please contact support to transfer ownership of the existing config instead."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 4. Save to config
            config = None
            is_new = False
            if config_id and config_id != "new":
                try:
                    config = WhatsAppConfig.objects.get(id=config_id, user=user)
                except WhatsAppConfig.DoesNotExist:
                    return Response(
                        {"error": f"Config with ID {config_id} not found."},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            else:
                config = WhatsAppConfig(user=user)
                is_new = True

            config.whatsapp_api_token = access_token
            config.phone_number_id = phone_number_id
            config.whatsapp_business_account_id = waba_ids[0] if waba_ids else None
            config.whatsapp_app_id = app_id
            if business_name:
                config.whatsapp_app_name = business_name
            if phone_number:
                config.name = f"WhatsApp - {phone_number}"
            elif business_name:
                config.name = business_name

            # Setup defaults for webhook if new
            if is_new:
                config.webhook_verify_token = "my_secret_token_123"
                runserver_addr = getattr(
                    settings, "DJANGO_RUNSERVER_ADDR", "http://localhost:8001"
                )
                config.crm_webhook_url = f"{runserver_addr}/whatsapp/events/"
                config.crm_api_token = "super_secret_crm_token_123"
                config.is_ai_enabled = False
                config.verification_status = "NOT_VERIFIED"
            else:
                # Update status
                config.verification_status = "NOT_VERIFIED"

            config.save()

            # Sync new config ID back to SaaS WhatsAppUser table
            if (
                is_new
                and user
                and user.is_authenticated
                and not (
                    getattr(user, "is_superuser", False)
                    or getattr(user, "is_staff", False)
                )
            ):
                try:
                    from django.db import connection

                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE whatsapp_saas_whatsappuser 
                            SET whatsapp_config_id = %s 
                            WHERE user_id = (SELECT id FROM whatsapp_saas_user WHERE email = %s)
                            """,
                            [config.id, getattr(user, "email", "")],
                        )
                except Exception as e:
                    logger.error(
                        f"Failed to sync newly created config ID to SaaS WhatsAppUser in exchange_token: {e}"
                    )

            serializer = self.get_serializer(config)
            return Response(
                {
                    "success": True,
                    "config": serializer.data,
                    "wabaIds": waba_ids,
                    "phoneNumberId": phone_number_id,
                    "phoneNumber": phone_number,
                    "businessName": business_name,
                    "scopes": scopes,
                }
            )

        except Exception as e:
            logger.error(f"Error exchanging meta token: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to exchange token: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["post"], url_path="register-phone")
    def register_phone(self, request):
        import requests
        from django.conf import settings
        from django.utils import timezone

        config_id = request.data.get("config_id")
        pin = request.data.get("pin")

        if not config_id or not pin:
            return Response(
                {"error": "Missing 'config_id' or 'pin' (6 digits)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not str(pin).isdigit() or len(str(pin)) != 6:
            return Response(
                {"error": "PIN must be exactly 6 digits."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            config = WhatsAppConfig.objects.get(id=config_id, user=request.user)
        except WhatsAppConfig.DoesNotExist:
            return Response(
                {"error": f"Config with ID {config_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        phone_number_id = config.phone_number_id
        access_token = config.whatsapp_api_token

        if not phone_number_id or not access_token:
            return Response(
                {
                    "error": "Config is missing Phone Number ID or WhatsApp Access Token. Swap token first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        version = getattr(settings, "GRAPH_API_VERSION", "v21.0")
        url = f"https://graph.facebook.com/{version}/{phone_number_id}/register"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }
        payload = {"messaging_product": "whatsapp", "pin": str(pin)}

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            data = res.json()
            if res.status_code == 200 and data.get("success"):
                config.verification_status = "VERIFIED"
                config.last_checked_at = timezone.now()
                config.error_message = None
                config.save(
                    update_fields=[
                        "verification_status",
                        "last_checked_at",
                        "error_message",
                    ]
                )
                return Response(
                    {
                        "success": True,
                        "message": "Phone number registered successfully.",
                    }
                )
            else:
                err_msg = data.get("error", {}).get(
                    "message", "Phone registration failed"
                )
                config.error_message = f"Meta registration error: {err_msg}"
                config.save(update_fields=["error_message"])
                return Response({"error": err_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error registering phone: {e}", exc_info=True)
            return Response(
                {"error": f"Failed to register phone: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LoginSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = LoginSessionSerializer

    def get_queryset(self):
        return LoginSession.objects.filter(
            user=self.request.user, is_active=True
        ).order_by("-last_active")

    def list(self, request):
        sessions = self.get_queryset()

        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        current_jti = None
        if token:
            try:
                from rest_framework_simplejwt.authentication import JWTAuthentication

                authenticator = JWTAuthentication()
                validated_token = authenticator.get_validated_token(token)
                current_jti = validated_token.get("refresh_jti") or validated_token.get(
                    "jti"
                )
            except Exception:
                pass

        if current_jti:
            current_session = sessions.filter(jti=current_jti).first()
            other_sessions = sessions.exclude(jti=current_jti)
        else:
            current_session = sessions.filter(is_current=True).first()
            other_sessions = sessions.filter(is_current=False)

        return Response(
            {
                "current_device": self.get_serializer(current_session).data
                if current_session
                else None,
                "other_devices": self.get_serializer(other_sessions, many=True).data,
            }
        )

    @action(detail=True, methods=["post"], url_path="logout")
    def logout_session(self, request, pk=None):
        session = self.get_object()
        session.is_active = False
        session.is_current = False
        session.save()

        # If no active sessions remain, set user offline
        if not LoginSession.objects.filter(user=session.user, is_active=True).exists():
            session.user.is_online = False
            session.user.save(update_fields=["is_online"])

        return Response({"message": "Session deactivated"})

    @action(detail=False, methods=["post"], url_path="logout-others")
    def logout_others(self, request):
        # Find current session JTI from token
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "")
        authenticator = JWTAuthentication()
        validated_token = authenticator.get_validated_token(token)
        current_jti = validated_token.get("jti")

        # Deactivate all other sessions
        sessions = LoginSession.objects.filter(
            user=request.user, is_active=True
        ).exclude(jti=current_jti)
        count = sessions.count()
        sessions.update(is_active=False, is_current=False)

        return Response({"message": f"Logged out of {count} other sessions"})


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Notification ViewSet
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "notification_type",
            "title",
            "message",
            "contact_phone",
            "contact_name",
            "message_id",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class NotificationViewSet(viewsets.ViewSet):
    """
    REST endpoints for the notification system.

    GET  /api/notifications/           â€” list last 50 notifications
    GET  /api/notifications/unread-count/ â€” {count: N}
    PATCH /api/notifications/<id>/read/ â€” mark single as read
    PATCH /api/notifications/read-all/  â€” mark all as read
    """

    permission_classes = [IsAuthenticated, HasActiveSubscription]

    def list(self, request):
        config_id = get_whatsapp_config_id(request)
        qs = Notification.objects.filter(whatsapp_config_id=config_id)[:50]
        return Response(NotificationSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"], url_path="unread-count")
    def unread_count(self, request):
        config_id = get_whatsapp_config_id(request)
        count = Notification.objects.filter(
            whatsapp_config_id=config_id, is_read=False
        ).count()
        return Response({"count": count})

    @action(detail=True, methods=["patch"], url_path="read")
    def mark_read(self, request, pk=None):
        try:
            notif = Notification.objects.get(pk=pk)
        except Notification.DoesNotExist:
            return Response({"error": "Not found"}, status=status.HTTP_404_NOT_FOUND)

        notif.is_read = True
        notif.save(update_fields=["is_read"])

        # Broadcast updated unread count
        _broadcast_unread_count(config_id=notif.whatsapp_config_id)
        return Response({"id": notif.id, "is_read": True})

    @action(detail=False, methods=["patch"], url_path="read-all")
    def mark_all_read(self, request):
        config_id = get_whatsapp_config_id(request)
        Notification.objects.filter(whatsapp_config_id=config_id, is_read=False).update(
            is_read=True
        )
        _broadcast_unread_count(config_id=config_id)
        return Response({"status": "all read"})


def _broadcast_unread_count(config_id=None):
    """Push the current unread count to all notification WebSocket clients."""
    try:
        from whatsapp_app.consumers import NOTIFICATIONS_GROUP

        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        if config_id:
            count = Notification.objects.filter(
                whatsapp_config_id=config_id, is_read=False
            ).count()
        else:
            count = Notification.objects.filter(is_read=False).count()
        async_to_sync(channel_layer.group_send)(
            NOTIFICATIONS_GROUP,
            {
                "type": "notification_event",
                "data": {
                    "event": "unread_count_update",
                    "count": count,
                    "whatsapp_config_id": config_id,
                },
            },
        )
    except Exception:
        pass


from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        # Before calling super(), ensure the user exists in our whatsapp_user table.
        # When users arrive via SSO from saas_backend, their token was issued against
        # whatsapp_saas_user. We auto-provision them in whatsapp_user if needed so the
        # standard refresh machinery doesn't crash with DoesNotExist.
        try:
            refresh_token = RefreshToken(attrs["refresh"])
            user_id = refresh_token.get("user_id")
            if user_id:
                from whatsapp_app.models import User as WhatsappUser

                if not WhatsappUser.objects.filter(id=user_id).exists():
                    # Try to pull profile data from the shared saas user table
                    try:
                        from django.db import connection

                        with connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT id, email, first_name, last_name, is_active, is_staff, is_superuser "
                                "FROM whatsapp_saas_user WHERE id = %s",
                                [user_id],
                            )
                            row = cursor.fetchone()

                            is_whatsapp_user = False
                            if row:
                                cursor.execute(
                                    "SELECT 1 FROM whatsapp_saas_whatsappuser WHERE user_id = %s",
                                    [user_id],
                                )
                                is_whatsapp_user = bool(cursor.fetchone())

                        if row:
                            (
                                saas_id,
                                email,
                                first_name,
                                last_name,
                                is_active,
                                is_staff,
                                is_superuser,
                            ) = row
                            full_name = (
                                f"{first_name or ''} {last_name or ''}".strip() or email
                            )
                            is_admin = bool(
                                is_staff or is_superuser or is_whatsapp_user
                            )
                            # whatsapp.User uses email as USERNAME_FIELD, has a 'name' field, no 'username'
                            user_obj, created = WhatsappUser.objects.get_or_create(
                                id=saas_id,
                                defaults={
                                    "email": email or "",
                                    "name": full_name,
                                    "is_active": bool(is_active),
                                    "is_staff": bool(is_staff or is_superuser),
                                    "role": "ADMIN" if is_admin else "EMPLOYEE",
                                },
                            )
                            if not created:
                                new_role = "ADMIN" if is_admin else "EMPLOYEE"
                                if user_obj.role != new_role:
                                    user_obj.role = new_role
                                    user_obj.save(update_fields=["role"])
                            if created:
                                user_obj.set_unusable_password()
                                user_obj.save(update_fields=["password"])
                                import logging

                                logging.getLogger(__name__).info(
                                    f"SSO auto-provisioned whatsapp user id={saas_id} email={email}"
                                )
                    except Exception as provision_err:
                        import logging

                        logging.getLogger(__name__).warning(
                            f"SSO auto-provision failed for user_id={user_id}: {provision_err}"
                        )
        except Exception:
            pass  # Let super() handle any token format errors normally

        data = super().validate(attrs)

        try:
            refresh = RefreshToken(attrs["refresh"])
            refresh_jti = refresh.get("jti")

            # Add refresh_jti claim to the new access token so middleware can track sessions
            access_token = AccessToken(data["access"])
            access_token["refresh_jti"] = refresh_jti
            data["access"] = str(access_token)
        except Exception:
            pass

        return data


class CustomTokenRefreshView(TokenRefreshView):
    serializer_class = CustomTokenRefreshSerializer


from whatsapp_app.models import Category, SubCategory, Product
from whatsapp_app.serializers import (
    CategorySerializer,
    SubCategorySerializer,
    ProductSerializer,
)
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        if not config_id:
            return Category.objects.none()
        return Category.objects.filter(whatsapp_config_id=config_id)

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        serializer.save(whatsapp_config_id=config_id)


class SubCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        if not config_id:
            return SubCategory.objects.none()
        category_id = self.request.query_params.get("category")
        qs = SubCategory.objects.filter(category__whatsapp_config_id=config_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        return qs


class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        if not config_id:
            return Product.objects.none()
        subcategory_id = self.request.query_params.get("subcategory")
        qs = Product.objects.filter(subcategory__category__whatsapp_config_id=config_id)
        if subcategory_id:
            qs = qs.filter(subcategory_id=subcategory_id)
        return qs

    def perform_update(self, serializer):
        # Clear meta_product_id if a new image file is uploaded so it forces a re-upload to Meta
        if "image" in self.request.FILES:
            serializer.save(meta_product_id=None)
        else:
            serializer.save()


from whatsapp_app.models import AutoReply
from whatsapp_app.serializers import AutoReplySerializer


class AutoReplyViewSet(viewsets.ModelViewSet):
    serializer_class = AutoReplySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        if not config_id:
            return AutoReply.objects.none()
        return AutoReply.objects.filter(whatsapp_config_id=config_id)

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        serializer.save(whatsapp_config_id=config_id)


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from whatsapp_app.models import AIConfig
from whatsapp_app.serializers import AIConfigSerializer


class AIConfigView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tenant_param = (
            request.GET.get("tenant")
            or request.GET.get("tenant_id")
            or request.GET.get("username")
        )
        config_id = None

        if tenant_param:
            user_obj = (
                User.objects.filter(email__iexact=tenant_param).first()
                or User.objects.filter(email__icontains=tenant_param).first()
                or User.objects.filter(name__icontains=tenant_param).first()
            )
            if not user_obj and tenant_param.isdigit():
                user_obj = User.objects.filter(id=int(tenant_param)).first()
            if user_obj:
                wa_cfg = (
                    WhatsAppConfig.objects.filter(user=user_obj).order_by("id").first()
                )
                if wa_cfg:
                    config_id = wa_cfg.id

        if not config_id:
            config_id = get_whatsapp_config_id(request)

        if not config_id:
            first_cfg = WhatsAppConfig.objects.order_by("id").first()
            if first_cfg:
                config_id = first_cfg.id
            else:
                return Response(
                    {"error": "WhatsApp config not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        user_name = "Merida HR"
        if getattr(request, "user", None) and request.user.is_authenticated:
            user_name = (
                getattr(request.user, "name", "")
                or request.user.email.split("@")[0].title()
            )

        business_display = (
            f"{user_name} HR"
            if "hr" in user_name.lower() or "merida" in user_name.lower()
            else f"{user_name} Business"
        )

        default_prompt = f"You are Aria, an intelligent AI HR & Customer Support assistant for {business_display}. Your goal is to assist candidates, employees, and clients with inquiries, services, hiring solutions, and support politely, clearly, and professionally."

        default_behaviours = [
            {
                "id": 1,
                "name": "Greeting Message",
                "desc": "Send a proactive greeting when chat opens",
                "active": True,
            },
            {
                "id": 2,
                "name": "Suggested Replies",
                "desc": "Show quick reply buttons to users",
                "active": True,
            },
            {
                "id": 3,
                "name": "Typing Indicator",
                "desc": "Simulate human typing delay",
                "active": True,
            },
            {
                "id": 4,
                "name": "Emoji Usage",
                "desc": "Allow AI to use emojis naturally",
                "active": True,
            },
        ]
        default_lead_collection = [
            {"id": 1, "name": "Collect Name", "active": True},
            {"id": 2, "name": "Collect Phone", "active": True},
            {"id": 3, "name": "Collect Email", "active": True},
            {"id": 4, "name": "Collect Company", "active": True},
        ]
        default_auto_replies = [
            {
                "id": 1,
                "keyword": "Pricing",
                "reply": f"Our services and consulting plans at {business_display} are tailored to your needs. Please share your email for details.",
                "active": True,
            },
            {
                "id": 2,
                "keyword": "Jobs",
                "reply": f"We have exciting job openings at {business_display}. Visit our careers portal or submit your resume here!",
                "active": True,
            },
        ]
        default_websites = [{"id": 1, "url": "https://meridatechminds.com"}]
        default_faqs = [
            {
                "id": 1,
                "q": "What are your working hours?",
                "a": "Our support team is available Monday through Friday, 9 AM to 6 PM.",
            }
        ]

        ai_config, created = AIConfig.objects.get_or_create(
            whatsapp_config_id=config_id,
            defaults={
                "assistant_name": "Aria",
                "business_name": business_display,
                "personality": "Support",
                "tone": "friendly",
                "prompt": default_prompt,
                "conversation_behaviours": default_behaviours,
                "lead_collection": default_lead_collection,
                "auto_replies": default_auto_replies,
                "websites": default_websites,
                "faqs": default_faqs,
            },
        )

        # Fill defaults if any fields were empty in existing record
        updated = False
        if not ai_config.prompt:
            ai_config.prompt = default_prompt
            updated = True
        if not ai_config.conversation_behaviours:
            ai_config.conversation_behaviours = default_behaviours
            updated = True
        if not ai_config.lead_collection:
            ai_config.lead_collection = default_lead_collection
            updated = True
        if not ai_config.auto_replies:
            ai_config.auto_replies = default_auto_replies
            updated = True
        if not ai_config.websites:
            ai_config.websites = default_websites
            updated = True
        if not ai_config.faqs:
            ai_config.faqs = default_faqs
            updated = True
        if not ai_config.assistant_name or ai_config.assistant_name == "AI Assistant":
            ai_config.assistant_name = "Aria"
            updated = True
        if not ai_config.business_name or ai_config.business_name == "My Business":
            ai_config.business_name = business_display
            updated = True

        if updated:
            ai_config.save()

        serializer = AIConfigSerializer(ai_config)
        return Response(serializer.data)

    def post(self, request):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        config_id = get_whatsapp_config_id(request)
        if not config_id:
            return Response(
                {"error": "WhatsApp config not found"}, status=status.HTTP_404_NOT_FOUND
            )

        ai_config, created = AIConfig.objects.get_or_create(
            whatsapp_config_id=config_id
        )
        serializer = AIConfigSerializer(ai_config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AIConfigTestConnectionView(APIView):
    """
    Validates a provider + model + API key combination with a minimal, direct completion
    request - independent of the chatbot microservice's own generate/retry pipeline, which
    swallows every failure (invalid key, unknown model, etc.) into a generic canned reply
    with no visible error anywhere. Lets an admin confirm a key/model actually works before
    relying on it, and get a specific reason immediately if it doesn't.
    """

    permission_classes = [IsAuthenticated]

    PROVIDER_BASE_URLS = {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "groq": "https://api.groq.com/openai/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    }

    def post(self, request):
        provider = (request.data.get("llm_provider") or "").strip().lower()
        model_name = (request.data.get("model_name") or "").strip()
        api_key = (request.data.get("api_key") or "").strip()

        # Any field left blank falls back to what's already saved, so this works both to
        # test unsaved form changes and to re-check the live config as-is.
        if not (provider and model_name and api_key):
            config_id = get_whatsapp_config_id(request)
            ai_conf = AIConfig.objects.filter(whatsapp_config_id=config_id).first()
            if ai_conf:
                provider = provider or (ai_conf.llm_provider or "").strip().lower()
                model_name = model_name or (ai_conf.model_name or "").strip()
                api_key = api_key or (ai_conf.api_key or "").strip()

        if not api_key:
            return Response(
                {"success": False, "error": "No API key to test - enter one first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not model_name:
            return Response(
                {"success": False, "error": "No model name to test - enter one first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        base_url = self.PROVIDER_BASE_URLS.get(
            provider, self.PROVIDER_BASE_URLS["openai"]
        )
        provider_label = provider or "the provider"

        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model_name,
                    "messages": [{"role": "user", "content": "ping"}],
                    "max_tokens": 5,
                },
                timeout=15,
            )
        except requests.Timeout:
            return Response(
                {
                    "success": False,
                    "error": f"{provider_label} did not respond in time. Try again in a moment.",
                }
            )
        except requests.RequestException as e:
            return Response(
                {"success": False, "error": f"Could not reach {provider_label}: {e}"}
            )

        if resp.status_code == 200:
            return Response(
                {"success": True, "provider": provider, "model": model_name}
            )

        if resp.status_code == 429:
            # Authentication succeeded - it's only rate-limited/out of quota - so the
            # key itself is confirmed valid and working.
            return Response(
                {
                    "success": True,
                    "provider": provider,
                    "model": model_name,
                    "warning": "Key is valid, but the account is currently rate-limited or out of quota.",
                }
            )

        detail = None
        try:
            body = resp.json()
            err = body.get("error")
            detail = err.get("message") if isinstance(err, dict) else err
        except Exception:
            detail = resp.text[:200] if resp.text else None

        if resp.status_code == 401:
            friendly = f"Invalid API key for {provider_label}."
        elif resp.status_code == 404:
            friendly = f"Model '{model_name}' was not found on {provider_label} - it may be deprecated, renamed, or misspelled."
        else:
            friendly = f"{provider_label} returned an error ({resp.status_code})."

        if detail:
            friendly = f"{friendly} {detail}"

        return Response({"success": False, "error": friendly})


class AITestMessageView(APIView):
    """Live 'Test AI' preview: runs a real message through the tenant's own
    AI Config (provider/model/api_key/system prompt) via Aria Core and
    returns the actual generated answer. Uses a throwaway session id scoped
    to the config, so it never touches real contact/lead data."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from chatbot_app.services import send_aria_message, ChatbotServiceError

        message = (request.data.get("message") or "").strip()
        if not message:
            return Response(
                {"error": "message is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        config_id = get_whatsapp_config_id(request)
        if not config_id:
            return Response(
                {"error": "WhatsApp config not found"}, status=status.HTTP_404_NOT_FOUND
            )

        try:
            ai_conf = AIConfig.objects.get(whatsapp_config_id=config_id)
        except AIConfig.DoesNotExist:
            return Response(
                {"error": "Set up and save your AI Config first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        raw = AIConfigSerializer(ai_conf).data
        ai_config_data = {
            "assistant_name": raw.get("assistant_name") or "Assistant",
            "business_name": raw.get("business_name") or "Company",
            "personality": raw.get("personality") or "Support",
            "tone": raw.get("tone") or "friendly",
            "primary_language": raw.get("primary_language") or "en",
            "prompt": raw.get("prompt") or "",
            "system_prompt": raw.get("system_prompt") or raw.get("prompt") or "",
            "llm_provider": raw.get("llm_provider") or "openai",
            "model_name": raw.get("model_name") or "gpt-4o-mini",
            "api_key": raw.get("api_key") or None,
        }

        try:
            result = send_aria_message(
                channel="test_preview",
                channel_session_id=f"test-preview-config-{config_id}",
                message=message,
                identity={"name": "Test Preview"},
                ai_config=ai_config_data,
            )
        except ChatbotServiceError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({"answer": result.get("answer") or ""})


from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import viewsets
from whatsapp_app.models import KnowledgeDocument
from whatsapp_app.serializers import KnowledgeDocumentSerializer


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        if not config_id:
            return KnowledgeDocument.objects.none()
        return KnowledgeDocument.objects.filter(whatsapp_config_id=config_id)

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        serializer.save(whatsapp_config_id=config_id)


class GeneratePromptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import requests
        from django.conf import settings

        business_name = request.data.get("business_name", "your business")
        tone = request.data.get("tone", "friendly")

        chatbot_url = getattr(
            settings, "CHATBOT_SERVICE_URL", "http://localhost:8002"
        ).rstrip("/")
        try:
            response = requests.post(
                f"{chatbot_url}/ai-prompt/generate",
                json={"business_name": business_name, "tone": tone},
                timeout=15,
            )
            if response.status_code == 200:
                return Response(response.json())
        except Exception as exc:
            pass

        # Fallback template
        generated_prompt = f"You are the official AI Assistant for {business_name}. Your tone is {tone}. Answer politely and concisely."
        return Response({"generated_prompt": generated_prompt})


class ImprovePromptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import requests
        from django.conf import settings

        current_prompt = request.data.get("prompt", "")

        chatbot_url = getattr(
            settings, "CHATBOT_SERVICE_URL", "http://localhost:8002"
        ).rstrip("/")
        try:
            response = requests.post(
                f"{chatbot_url}/ai-prompt/improve",
                json={"prompt": current_prompt},
                timeout=15,
            )
            if response.status_code == 200:
                return Response(response.json())
        except Exception as exc:
            pass

        # Fallback template
        improved_prompt = (
            current_prompt
            + "\n\n(Improved: Ensure you never deviate from the persona and always remain helpful.)"
        )
        return Response({"improved_prompt": improved_prompt})


class KnowledgeRebuildView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import requests
        from django.conf import settings

        file_obj = request.FILES.get("file")
        url = request.data.get("url")
        faq_q = request.data.get("faq_q")
        faq_a = request.data.get("faq_a")

        chatbot_url = getattr(
            settings, "CHATBOT_SERVICE_URL", "http://localhost:8002"
        ).rstrip("/")

        files = None
        data = {}

        if file_obj:
            files = {"file": (file_obj.name, file_obj.read(), file_obj.content_type)}

        if url:
            data["url"] = url
        if faq_q:
            data["faq_q"] = faq_q
        if faq_a:
            data["faq_a"] = faq_a

        try:
            headers = {}
            ingestion_token = getattr(settings, "INGESTION_API_TOKEN", None) or getattr(
                settings, "CHATBOT_INGESTION_TOKEN", None
            )
            if ingestion_token:
                headers["X-Ingestion-Token"] = ingestion_token

            response = requests.post(
                f"{chatbot_url}/knowledge/rebuild",
                headers=headers,
                files=files,
                data=data,
                timeout=60,
            )
            if response.status_code == 200:
                return Response(response.json())
            return Response(response.json(), status=response.status_code)
        except Exception as exc:
            return Response(
                {
                    "status": "failed",
                    "message": f"Proxy request failed: {exc}",
                    "crawl_website": False,
                    "knowledge_file": "",
                    "file_size_bytes": 0,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


import uuid as _uuid


class VideoCallInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        phone_number = request.data.get("phone_number", "").strip()
        if not phone_number:
            return Response({"error": "phone_number is required"}, status=400)

        short_id = str(_uuid.uuid4()).replace("-", "")[:10].upper()
        room_name = f"MeridaSession{short_id}"
        room_url = f"https://meet.jit.si/{room_name}"

        message_text = (
            f"Video call session ready! Join here: {room_url} (valid 30 mins)."
        )

        try:
            config_id = get_whatsapp_config_id(request)
            if config_id:
                waba_config = get_whatsapp_config(config_id)
                from whatsapp_app.services import send_whatsapp_message_direct_to_meta

                send_whatsapp_message_direct_to_meta(
                    recipient_id=phone_number,
                    waba_config=waba_config,
                    text=message_text,
                )
        except Exception as e:
            logger.warning(f"[VideoCall] Failed to send WhatsApp link: {e}")

        return Response({"room_url": room_url, "room_name": room_name})


from whatsapp_app.models import (
    FollowUpWorkflow,
    FollowUpStep,
    FollowUpContactState,
    ReminderCampaign,
    ReminderSchedule,
    ReminderExecution,
    AutomationLog,
)
from whatsapp_app.serializers import (
    FollowUpWorkflowSerializer,
    FollowUpContactStateSerializer,
    ReminderCampaignSerializer,
    ReminderExecutionSerializer,
    AutomationLogSerializer,
)


class FollowUpWorkflowViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = FollowUpWorkflowSerializer

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        return FollowUpWorkflow.objects.filter(whatsapp_config_id=config_id)

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        serializer.save(whatsapp_config_id=config_id, created_by=self.request.user)

    @action(detail=True, methods=["POST"])
    def duplicate(self, request, pk=None):
        workflow = self.get_object()
        new_workflow = FollowUpWorkflow.objects.create(
            name=f"{workflow.name} (Copy)",
            whatsapp_config=workflow.whatsapp_config,
            is_active=workflow.is_active,
            created_by=request.user,
        )
        for step in workflow.steps.all():
            FollowUpStep.objects.create(
                workflow=new_workflow,
                step_number=step.step_number,
                delay_seconds=step.delay_seconds,
                template=step.template,
                media_url=step.media_url,
            )
        return Response(
            FollowUpWorkflowSerializer(new_workflow).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["GET"])
    def history(self, request):
        config_id = get_whatsapp_config_id(request)
        states = FollowUpContactState.objects.filter(
            contact__whatsapp_config_id=config_id
        )

        # Search filter
        search = request.query_params.get("search")
        if search:
            states = states.filter(
                Q(contact__name__icontains=search)
                | Q(contact__phone_number__icontains=search)
                | Q(workflow__name__icontains=search)
            )

        page = self.paginate_queryset(states)
        if page is not None:
            serializer = FollowUpContactStateSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = FollowUpContactStateSerializer(states, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def logs(self, request):
        config_id = get_whatsapp_config_id(request)
        logs = AutomationLog.objects.filter(
            whatsapp_config_id=config_id, automation_type="FOLLOW_UP"
        )

        search = request.query_params.get("search")
        if search:
            logs = logs.filter(
                Q(contact__name__icontains=search)
                | Q(contact__phone_number__icontains=search)
                | Q(details__icontains=search)
            )

        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = AutomationLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AutomationLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def analytics(self, request):
        config_id = get_whatsapp_config_id(request)
        states = FollowUpContactState.objects.filter(
            contact__whatsapp_config_id=config_id
        )

        total_scheduled = states.filter(status="PENDING").count()
        total_sent = states.filter(status__in=["SENT", "COMPLETED"]).count()
        total_completed = states.filter(status="COMPLETED").count()
        total_cancelled = states.filter(status="CANCELLED").count()
        total_failed = states.filter(status="FAILED").count()

        response_rate = 0.0
        if total_sent > 0:
            response_rate = round((total_completed / total_sent) * 100, 2)

        avg_response_time = 180.0

        return Response(
            {
                "total_scheduled": total_scheduled,
                "total_sent": total_sent,
                "response_rate": response_rate,
                "conversion_rate": response_rate,
                "avg_response_time": avg_response_time,
                "total_failed": total_failed,
                "total_completed": total_completed,
                "total_cancelled": total_cancelled,
            }
        )


class ReminderCampaignViewSet(viewsets.ModelViewSet):
    permission_classes = [AllowAny]
    authentication_classes = []  # Bypass global JWT auth for campaign analytics
    serializer_class = ReminderCampaignSerializer

    def get_queryset(self):
        config_id = get_whatsapp_config_id(self.request)
        if config_id:
            return ReminderCampaign.objects.filter(whatsapp_config_id=config_id)
        return ReminderCampaign.objects.none()

    def perform_create(self, serializer):
        config_id = get_whatsapp_config_id(self.request)
        if not config_id:
            config = WhatsAppConfig.get_solo()
            config_id = config.id if config else None

        user = (
            self.request.user
            if (self.request.user and self.request.user.is_authenticated)
            else get_public_api_user()
        )
        serializer.save(whatsapp_config_id=config_id, created_by=user)

    @action(detail=True, methods=["POST"])
    def duplicate(self, request, pk=None):
        campaign = self.get_object()
        new_campaign = ReminderCampaign.objects.create(
            name=f"{campaign.name} (Copy)",
            whatsapp_config=campaign.whatsapp_config,
            event_type=campaign.event_type,
            event_title=campaign.event_title,
            event_date_time=campaign.event_date_time,
            time_zone=campaign.time_zone,
            is_active=campaign.is_active,
            created_by=request.user,
        )
        new_campaign.contacts.set(campaign.contacts.all())
        for schedule in campaign.schedules.all():
            ReminderSchedule.objects.create(
                reminder_campaign=new_campaign,
                timing_type=schedule.timing_type,
                custom_minutes_before=schedule.custom_minutes_before,
                template=schedule.template,
                media_url=schedule.media_url,
            )
        return Response(
            ReminderCampaignSerializer(new_campaign).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["GET"])
    def history(self, request):
        config_id = get_whatsapp_config_id(request)
        executions = ReminderExecution.objects.filter(
            reminder_campaign__whatsapp_config_id=config_id
        )

        search = request.query_params.get("search")
        if search:
            executions = executions.filter(
                Q(contact__name__icontains=search)
                | Q(contact__phone_number__icontains=search)
                | Q(reminder_campaign__name__icontains=search)
            )

        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = ReminderExecutionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ReminderExecutionSerializer(executions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def logs(self, request):
        config_id = get_whatsapp_config_id(request)
        logs = AutomationLog.objects.filter(
            whatsapp_config_id=config_id, automation_type="REMINDER"
        )

        search = request.query_params.get("search")
        if search:
            logs = logs.filter(
                Q(contact__name__icontains=search)
                | Q(contact__phone_number__icontains=search)
                | Q(details__icontains=search)
            )

        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = AutomationLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = AutomationLogSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["GET"])
    def analytics(self, request):
        try:
            from whatsapp_app.models import Message

            config_id = get_whatsapp_config_id(request)
            campaign_id = request.query_params.get("campaign_id")

            campaigns = ReminderCampaign.objects.all()
            if campaign_id:
                campaigns = campaigns.filter(id=campaign_id)
            elif config_id and campaigns.filter(whatsapp_config_id=config_id).exists():
                campaigns = campaigns.filter(whatsapp_config_id=config_id)

            executions = ReminderExecution.objects.filter(
                reminder_campaign__in=campaigns
            )

            total_scheduled = executions.filter(status="PENDING").count()
            total_sent = executions.filter(status="SENT").count()
            total_diverted = executions.filter(status="DIVERTED").count()
            total_failed = executions.filter(status="FAILED").count()

            if total_sent + total_failed > 0:
                delivery_rate = round(
                    (total_sent / (total_sent + total_failed)) * 100, 1
                )
            else:
                delivery_rate = 100.0 if total_sent > 0 else 0.0

            contact_breakdown = []
            interested_count = 0
            later_dates_count = 0
            not_interested_count = 0
            no_response_count = 0

            for camp in campaigns:
                camp_m2m = set(camp.contacts.values_list("id", flat=True))
                camp_execs = set(
                    executions.filter(reminder_campaign=camp).values_list(
                        "contact_id", flat=True
                    )
                )
                all_contact_ids = list(camp_m2m.union(camp_execs))
                contacts_qs = Contact.objects.filter(id__in=all_contact_ids)

                for contact in contacts_qs:
                    c_executions = executions.filter(
                        reminder_campaign=camp, contact=contact
                    )
                    last_exec = c_executions.order_by("-execution_time").first()

                    log_filter = {
                        "automation_type": "REMINDER",
                        "contact": contact,
                        "whatsapp_config": camp.whatsapp_config,
                    }
                    log = (
                        AutomationLog.objects.filter(**log_filter)
                        .order_by("-created_at")
                        .first()
                    )

                    btn_resp = (
                        last_exec.button_response
                        if (last_exec and last_exec.button_response)
                        else None
                    )
                    if not btn_resp:
                        # Only count a reply that actually came after we sent this reminder â€”
                        # otherwise an unrelated older message gets misread as a response to it.
                        sent_after = (
                            last_exec.sent_at or last_exec.execution_time
                            if last_exec
                            else None
                        )
                        if sent_after:
                            inc_msg = (
                                Message.objects.filter(
                                    contact=contact,
                                    direction="INCOMING",
                                    created_at__gte=sent_after,
                                )
                                .order_by("-created_at")
                                .first()
                            )
                            if inc_msg:
                                btn_resp = inc_msg.text

                    action_type = log.action_type if log else None

                    btn_str = (btn_resp or "").strip().lower()

                    if action_type == "DIVERTED" or (
                        btn_str
                        and any(
                            kw in btn_str
                            for kw in [
                                "not interested",
                                "no thanks",
                                "unsubscribe",
                                "stop",
                                "decline",
                                "not attending",
                                "cancel",
                                "don't want",
                            ]
                        )
                    ):
                        category = "NOT_INTERESTED"
                        category_label = "ðŸ”´ Not Interested"
                        not_interested_count += 1
                    elif action_type in [
                        "FOLLOWUP_TRIGGERED",
                        "FOLLOWUP_SENT",
                        "ALTERNATE_DATES",
                    ] or (
                        btn_str
                        and any(
                            kw in btn_str
                            for kw in [
                                "reschedule",
                                "later",
                                "next time",
                                "other dates",
                                "not this time",
                                "maybe later",
                                "may be later",
                                "different date",
                                "postpone",
                            ]
                        )
                    ):
                        category = "LATER_DATES"
                        category_label = "ðŸ“… Interested for Later Dates"
                        later_dates_count += 1
                    elif action_type in ["CONFIRMED"] or (
                        btn_str
                        and any(
                            kw in btn_str
                            for kw in [
                                "confirm",
                                "yes",
                                "attend",
                                "register",
                                "interested",
                                "attending",
                                "joining",
                                "count me in",
                                "book",
                            ]
                        )
                    ):
                        category = "INTERESTED"
                        category_label = "ðŸŸ¢ Interested / Attending"
                        interested_count += 1
                    elif btn_str:
                        category = "INTERESTED"
                        category_label = "ðŸŸ¢ Interested / Attending"
                        interested_count += 1
                    else:
                        category = "NO_RESPONSE"
                        category_label = "â³ No Replies"
                        no_response_count += 1

                    contact_breakdown.append(
                        {
                            "contact_id": contact.id,
                            "contact_name": contact.name or contact.phone_number,
                            "phone_number": contact.phone_number,
                            "campaign_id": camp.id,
                            "campaign_name": camp.name,
                            "category": category,
                            "category_label": category_label,
                            "button_response": btn_resp or "No reply yet",
                            "action_triggered": action_type
                            or (last_exec.status if last_exec else "PENDING"),
                            "last_updated": (
                                last_exec.sent_at
                                or last_exec.execution_time
                                or last_exec.updated_at
                            ).isoformat()
                            if last_exec
                            else camp.created_at.isoformat(),
                        }
                    )

            total_contacts = len(contact_breakdown)
            responded_total = (
                interested_count + later_dates_count + not_interested_count
            )

            response_rate = (
                round((responded_total / total_contacts * 100), 1)
                if total_contacts > 0
                else 0.0
            )
            attendance_rate = (
                round((interested_count / total_contacts * 100), 1)
                if total_contacts > 0
                else 0.0
            )

            return Response(
                {
                    "total_contacts": total_contacts,
                    "total_scheduled": total_scheduled,
                    "total_sent": total_sent,
                    "total_diverted": total_diverted,
                    "total_failed": total_failed,
                    "delivery_rate": delivery_rate,
                    "response_rate": response_rate,
                    "attendance_rate": attendance_rate,
                    "counts": {
                        "interested": interested_count,
                        "later_dates": later_dates_count,
                        "not_interested": not_interested_count,
                        "no_response": no_response_count,
                    },
                    "contacts": contact_breakdown,
                }
            )
        except Exception as err:
            logger.error(f"Error in analytics method: {err}")
            return Response(
                {
                    "total_contacts": 0,
                    "total_scheduled": 0,
                    "total_sent": 0,
                    "total_diverted": 0,
                    "total_failed": 0,
                    "delivery_rate": 0.0,
                    "response_rate": 0.0,
                    "attendance_rate": 0.0,
                    "counts": {
                        "interested": 0,
                        "later_dates": 0,
                        "not_interested": 0,
                        "no_response": 0,
                    },
                    "contacts": [],
                    "error": str(err),
                }
            )


class PublicCampaignDetailView(APIView):
    """Publicly accessible view to retrieve reminder campaign metadata for public registration pages."""

    permission_classes = [AllowAny]

    def get(self, request, user_name, campaign_name):
        from django.utils.text import slugify
        import urllib.parse

        user_name_clean = urllib.parse.unquote(user_name or "").strip()
        campaign_name_clean = urllib.parse.unquote(campaign_name or "").strip()

        user_name_decoded = user_name_clean.replace("-", " ").strip()
        campaign_name_decoded = campaign_name_clean.replace("-", " ").strip()

        # 1. Resolve User
        user = User.objects.filter(
            Q(name__iexact=user_name_clean)
            | Q(name__iexact=user_name_decoded)
            | Q(email__istartswith=user_name_clean)
        ).first()

        if not user:
            all_users = User.objects.filter(is_active=True)
            for u in all_users:
                u_name = u.name or u.email.split("@")[0]
                if slugify(u_name) == slugify(user_name_clean):
                    user = u
                    break

        # 1b. Newer links use the campaign's stable ID instead of its (mutable) name, so a
        # rename after the link was already shared can't break it. Try that first.
        reminder_campaign = None
        campaign = None
        if campaign_name_clean.isdigit():
            reminder_campaign = ReminderCampaign.objects.filter(
                id=int(campaign_name_clean)
            ).first()
            if not reminder_campaign:
                campaign = Campaign.objects.filter(id=int(campaign_name_clean)).first()

        # 2. Prioritize ReminderCampaign resolution (name-based, for links generated before
        # the ID-based scheme above - skipped entirely if step 1b already found a match)
        reminder_qs = ReminderCampaign.objects.all()
        if user:
            reminder_qs_user = reminder_qs.filter(created_by=user)
            if reminder_qs_user.exists():
                reminder_qs = reminder_qs_user

        if not reminder_campaign and not campaign:
            reminder_campaign = (
                reminder_qs.filter(
                    Q(name__iexact=campaign_name_clean)
                    | Q(name__iexact=campaign_name_decoded)
                    | Q(event_title__iexact=campaign_name_clean)
                    | Q(event_title__iexact=campaign_name_decoded)
                )
                .order_by("-created_at")
                .first()
            )

        if not reminder_campaign and not campaign:
            for rc in reminder_qs:
                if slugify(rc.name) == slugify(campaign_name_clean) or slugify(
                    rc.event_title or ""
                ) == slugify(campaign_name_clean):
                    reminder_campaign = rc
                    break

        # Fallback to standard Campaign if ReminderCampaign not found
        if not reminder_campaign and not campaign:
            camp_qs = Campaign.objects.all()
            if user:
                camp_qs_user = camp_qs.filter(created_by=user)
                if camp_qs_user.exists():
                    camp_qs = camp_qs_user

            campaign = (
                camp_qs.filter(
                    Q(name__iexact=campaign_name_clean)
                    | Q(name__iexact=campaign_name_decoded)
                )
                .order_by("-created_at")
                .first()
            )

            if not campaign:
                for c in camp_qs:
                    if slugify(c.name) == slugify(campaign_name_clean):
                        campaign = c
                        break

        if not reminder_campaign and not campaign:
            reminder_campaign = ReminderCampaign.objects.order_by("-updated_at").first()
            if not reminder_campaign:
                campaign = Campaign.objects.order_by("-created_at").first()

        if not reminder_campaign and not campaign:
            return Response(
                {"error": f"Reminder campaign '{campaign_name}' not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        template_obj = None
        campaign_id_val = None
        campaign_title = campaign_name
        campaign_vars = {}

        if reminder_campaign:
            campaign_id_val = reminder_campaign.id
            campaign_title = reminder_campaign.name
            first_schedule = reminder_campaign.schedules.filter(
                template__isnull=False
            ).first()
            if first_schedule:
                template_obj = first_schedule.template
                campaign_vars = first_schedule.template_variables or {}
        elif campaign:
            campaign_id_val = campaign.id
            campaign_title = campaign.name
            template_obj = campaign.template
            campaign_vars = campaign.variables or {}

        template_data = None
        if template_obj:
            t = template_obj
            body_text = (t.body or "").strip()
            if not body_text and isinstance(t.sample_values, dict):
                body_text = (
                    t.sample_values.get("body") or t.sample_values.get("text") or ""
                )

            # header_media can resolve to a full base64-encoded image/video (tens of MB,
            # cached from Meta's CDN), a raw Meta media handle (a bare numeric ID, not a
            # fetchable URL), or nothing yet-resolved at all. This is a *public*,
            # unauthenticated endpoint hit by every lead who opens the campaign link -
            # rather than re-deriving all of that here, always point at the
            # /header-media/ endpoint (same one used everywhere else), which already
            # knows how to lazily resolve any of those forms on demand.
            header_media = None
            if t.header_type in ("IMAGE", "VIDEO", "DOCUMENT"):
                has_media_source = bool(
                    t.header_media
                    or t.uploaded_preview_image
                    or t.meta_media_url
                    or (
                        isinstance(t.sample_values, dict)
                        and (
                            t.sample_values.get("header_handle")
                            or t.sample_values.get("media_url")
                        )
                    )
                )
                if has_media_source:
                    header_media = request.build_absolute_uri(
                        f"/templates/{t.id}/header-media/?type={t.header_type.lower()}"
                    )

            template_data = {
                "id": t.id,
                "name": t.name,
                "language": t.language,
                "category": t.category,
                "header_type": t.header_type,
                "header_text": t.header_text,
                "header_media": header_media,
                "body": body_text,
                "footer_text": t.footer_text,
                "buttons": t.buttons or [],
                "variables": t.variables or [],
            }

        # The actual dialable WhatsApp Business number (not the internal phone_number_id
        # used for API calls) - resolved from Meta and cached, since it's a public page
        # hit by every lead and shouldn't call out to Meta on every load.
        business_phone = None
        whatsapp_config = (
            reminder_campaign.whatsapp_config
            if reminder_campaign
            else (campaign.whatsapp_config if campaign else None)
        )
        if whatsapp_config and whatsapp_config.phone_number_id:
            from django.core.cache import cache

            cache_key = f"wa_display_phone_{whatsapp_config.id}"
            business_phone = cache.get(cache_key)
            if not business_phone and whatsapp_config.whatsapp_api_token:
                try:
                    import requests as _req

                    res = _req.get(
                        f"https://graph.facebook.com/v20.0/{whatsapp_config.phone_number_id}",
                        params={"fields": "display_phone_number"},
                        headers={
                            "Authorization": f"Bearer {whatsapp_config.whatsapp_api_token}"
                        },
                        timeout=5,
                    )
                    if res.status_code == 200:
                        business_phone = res.json().get("display_phone_number")
                        if business_phone:
                            cache.set(cache_key, business_phone, 60 * 60 * 24)
                except Exception:
                    business_phone = None

        return Response(
            {
                "campaign_id": campaign_id_val,
                "id": campaign_id_val,
                "campaign_name": campaign_title,
                "user_name": (user.name if user else None) or user_name_clean,
                "company_name": (getattr(user, "name", "") if user else None)
                or "WhatsApp Reminder Campaign",
                "business_phone": business_phone,
                "template": template_data,
                "variables": campaign_vars,
            }
        )


class PublicCampaignSubmitLeadView(APIView):
    """Public view to register a new lead for a campaign and automatically activate Reminder Campaigns."""

    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data
        if isinstance(data, str):
            import json

            try:
                data = json.loads(data)
            except Exception:
                data = {}

        campaign_id = data.get("campaign_id") or data.get("id")
        name = (data.get("name") or "").strip()
        phone_number_raw = data.get("phone_number") or data.get("phone")
        # When set, this came from a visitor clicking one of the template's own reply
        # buttons (e.g. "Yes, I'm Interested") on the public page rather than filling a
        # generic form - the resulting action should be identical to a real WhatsApp
        # button reply, not the default "send the initial invite" path below.
        button_text = (data.get("button_text") or "").strip()

        if not name or not phone_number_raw:
            return Response(
                {"error": "name and phone_number are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reminder_campaign = None
        if campaign_id:
            reminder_campaign = ReminderCampaign.objects.filter(id=campaign_id).first()

        campaign = None
        if campaign_id:
            campaign = Campaign.objects.filter(id=campaign_id).first()

        if not reminder_campaign and not campaign:
            reminder_campaign = ReminderCampaign.objects.order_by("-updated_at").first()
            if not reminder_campaign:
                campaign = Campaign.objects.order_by("-created_at").first()

        target_user = (
            (reminder_campaign.created_by if reminder_campaign else None)
            or (campaign.created_by if campaign else None)
            or get_public_api_user()
        )
        config_id = None
        if reminder_campaign and reminder_campaign.whatsapp_config_id:
            config_id = reminder_campaign.whatsapp_config_id
        elif campaign and campaign.whatsapp_config_id:
            config_id = campaign.whatsapp_config_id
        else:
            config = (
                WhatsAppConfig.objects.filter(user=target_user).first()
                or WhatsAppConfig.get_solo()
            )
            config_id = config.id if config else None

        phone_number = _normalize_phone_number(phone_number_raw)
        if not phone_number:
            return Response(
                {
                    "error": "Invalid phone number format. Please provide a valid phone number with country code."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            contact, created = Contact.objects.get_or_create(
                phone_number=phone_number,
                whatsapp_config_id=config_id,
                user=target_user,
                defaults={"name": name},
            )
            if not created and name and contact.name != name:
                contact.name = name
                contact.save(update_fields=["name"])

            if campaign:
                campaign.contacts.add(contact)
                campaign.total_contacts = campaign.contacts.count()
                campaign.save(update_fields=["total_contacts"])

            # Automatically associate & activate Reminder Campaigns for this registered lead
            rc_targets = []
            if reminder_campaign:
                rc_targets.append(reminder_campaign)

            # Find any active ReminderCampaigns matching the user or campaign name
            c_name = (
                campaign.name
                if campaign
                else (reminder_campaign.name if reminder_campaign else "")
            )
            if c_name:
                extra_rcs = ReminderCampaign.objects.filter(
                    created_by=target_user, is_active=True
                ).filter(Q(name__iexact=c_name) | Q(event_title__iexact=c_name))
                for er in extra_rcs:
                    if er not in rc_targets:
                        rc_targets.append(er)

            if not rc_targets:
                # Fallback to most recent active ReminderCampaign for this user
                fallback_rc = (
                    ReminderCampaign.objects.filter(
                        created_by=target_user, is_active=True
                    )
                    .order_by("-created_at")
                    .first()
                )
                if fallback_rc:
                    rc_targets.append(fallback_rc)

            queued_executions = []
            for rc in rc_targets:
                rc.contacts.add(contact)
                # Activate reminder executions for each schedule in the reminder campaign
                for schedule in rc.schedules.all():
                    exec_obj, _ = ReminderExecution.objects.get_or_create(
                        reminder_campaign=rc,
                        contact=contact,
                        schedule=schedule,
                        defaults={
                            "status": "PENDING",
                            "execution_time": timezone.now(),
                        },
                    )
                    queued_executions.append(exec_obj)

        message_sent = False
        button_action_handled = False

        # A visitor clicked one of the template's own reply buttons - run it through the
        # exact same matching/execution used for a real incoming WhatsApp button reply
        # (see evaluate_interconnected_button_response, used by the webhook handler above),
        # so "Yes, I'm Interested" here behaves identically to tapping it in WhatsApp.
        #
        # Guard against re-sending: unlike a real WhatsApp button (which can only be
        # tapped once), nothing stops a visitor from reopening this page and tapping the
        # same reply again - a page refresh, a second visit, or just double-tapping. If
        # they already have this exact response recorded for this campaign, treat it as
        # already handled rather than firing another real WhatsApp send for it.
        already_responded = False
        if button_text and rc_targets:
            already_responded = ReminderExecution.objects.filter(
                contact=contact,
                reminder_campaign__in=rc_targets,
                button_response__iexact=button_text,
            ).exists()

        if already_responded:
            button_action_handled = True
        elif button_text and reminder_campaign:
            try:
                button_action_handled = evaluate_interconnected_button_response(
                    contact, button_text, button_text
                )
            except Exception as e:
                logger.error(
                    f"Failed to process public campaign button interaction for contact {contact.id}: {e}"
                )
                button_action_handled = False

        if button_action_handled:
            message_sent = True
            # The button-action already sent the real, specific reply for what they clicked -
            # divert the just-queued "generic invite" executions so the background engine
            # doesn't also send that a few seconds later (they've already seen/read it here).
            ReminderExecution.objects.filter(
                id__in=[e.id for e in queued_executions], status="PENDING"
            ).update(status="DIVERTED")
        else:
            # No matching button_actions rule was found (not a ReminderCampaign, no
            # button_text at all, or the button-action lookup itself failed) - the
            # ReminderExecution rows queued above (execution_time=now()) will be picked
            # up and sent by the background automation engine within seconds; only do a
            # direct send here when there's nothing queued to handle it (plain-Campaign case).
            send_template_obj = None
            send_vars = {}
            already_queued_via_reminder_engine = bool(queued_executions)

            if rc_targets:
                first_sch = (
                    rc_targets[0].schedules.filter(template__isnull=False).first()
                )
                if first_sch:
                    send_template_obj = first_sch.template
                    send_vars = first_sch.template_variables or {}

            if not send_template_obj and campaign:
                send_template_obj = campaign.template
                send_vars = campaign.variables or {}

            if send_template_obj and already_queued_via_reminder_engine:
                # Will be sent momentarily by the reminder automation engine.
                message_sent = True
            elif send_template_obj:
                try:
                    from whatsapp_app.utils import send_automation_message

                    send_automation_message(
                        contact, send_template_obj, template_variables=send_vars
                    )
                    message_sent = True
                except Exception as e:
                    logger.error(
                        f"Failed to send template message for public campaign lead {contact.id}: {e}"
                    )

        return Response(
            {
                "success": True,
                "message": "Lead registered successfully and Reminder Campaign activated!",
                "whatsapp_sent": message_sent,
                "contact_id": contact.id,
            },
            status=status.HTTP_201_CREATED,
        )


class CandidateRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = request.data
        name = data.get("name")
        phone_number_raw = data.get("phone_number") or data.get("phone")
        email = data.get("email")
        domain = data.get("domain")
        experience_level = data.get("experience_level")
        current_salary = data.get("current_salary")
        expected_salary = data.get("expected_salary")

        if not name or not phone_number_raw or not email:
            return Response(
                {"error": "name, phone_number, and email are required"}, status=400
            )

        phone_number = _normalize_phone_number(phone_number_raw)
        if not phone_number:
            return Response({"error": "Invalid phone number format"}, status=400)

        config = WhatsAppConfig.get_solo()
        target_user = config.user or get_public_api_user()

        # Get or create contact
        contact, created = Contact.objects.get_or_create(
            phone_number=phone_number,
            whatsapp_config=config,
            user=target_user,
            defaults={"name": name, "email": email},
        )
        if not created:
            contact.name = name
            contact.email = email

        # Save candidate attributes
        contact.attributes = contact.attributes or {}
        contact.attributes.update(
            {
                "domain": domain,
                "experience_level": experience_level,
                "current_salary": current_salary,
                "expected_salary": expected_salary,
            }
        )
        contact.save()

        # Send WhatsApp template message if configured
        message_sent = False
        template_name = "hello_world"  # Fallback
        if config.auto_send_template and config.auto_send_template_name:
            template_name = config.auto_send_template_name

        try:
            from whatsapp_app.services import send_whatsapp_message_direct_to_meta

            cached_tpl = MessageTemplate.objects.filter(
                name=template_name, whatsapp_config=config
            ).first()
            lang = "en_US"
            body_text = f"Sent template: {template_name}"
            if cached_tpl:
                lang = cached_tpl.language
                body_text = cached_tpl.body
            else:
                from whatsapp_app.models import WhatsAppTemplate

                whatsapp_tpl = WhatsAppTemplate.objects.filter(
                    template_name=template_name, whatsapp_config=config
                ).first()
                if whatsapp_tpl:
                    lang = whatsapp_tpl.language
                    body_text = whatsapp_tpl.body_text

            import uuid

            provider_message_id = str(uuid.uuid4())

            meta_response, status_code = send_whatsapp_message_direct_to_meta(
                recipient_id=contact.phone_number,
                waba_config=config,
                template_name=template_name,
                language_code=lang,
                components=[],
            )

            if status_code in (200, 201):
                Message.objects.create(
                    contact=contact,
                    text=body_text,
                    sender="agent",
                    direction="OUTGOING",
                    status="Sent",
                    type="template",
                    provider_message_id=provider_message_id,
                    timestamp=timezone.now(),
                )
                contact.last_message = body_text
                contact.last_message_time = timezone.now()
                contact.save(update_fields=["last_message", "last_message_time"])
                message_sent = True
        except Exception as e:
            logger.error(f"Failed to auto-send candidate registration template: {e}")

        return Response(
            {
                "success": True,
                "message": "Candidate details stored successfully",
                "contact_id": contact.id,
                "whatsapp_sent": message_sent,
            },
            status=201,
        )


# =============================================================================
# Leads → WhatsApp Bulk Send (HRM Integration)
# =============================================================================
class LeadsBulkWhatsAppSendView(APIView):
    """
    Called from HRM Leads page when HR/recruiter selects multiple candidates
    and clicks "Send WhatsApp".

    Expected payload:
    {
        "config_id": 1,
        "template_name": "merida_1",
        "template_language": "en_US",
        "leads": [
            {"name": "Ranjeeta", "phone": "9739580814", "email": "r@g.com"},
            ...
        ]
    }

    For each lead:
    1. Auto-creates a Contact if not already present (phone + config unique key)
    2. Sends WhatsApp template message via Meta Cloud API
    3. Stores an outgoing Message record in the DB

    Candidate replies hit the existing webhook (whatsapp/events/) which finds
    the Contact by phone and stores the INCOMING message — it then appears
    in the HRM Inbox automatically.
    """

    permission_classes = []  # Open — HRM auth via X-HRM-Employee-ID header

    def post(self, request):
        from whatsapp_app.models import WhatsAppConfig, Contact, Message
        from django.utils import timezone

        config_id = request.data.get("config_id")
        template_name = request.data.get("template_name", "").strip()
        template_language = request.data.get("template_language", "en_US")
        leads = request.data.get("leads", [])

        if not leads:
            return Response({"error": "leads list is required"}, status=400)
        if not template_name:
            return Response({"error": "template_name is required"}, status=400)

        # Resolve WhatsApp config
        try:
            if config_id:
                wa_config = WhatsAppConfig.objects.get(id=config_id)
            else:
                wa_config = WhatsAppConfig.get_solo()
        except WhatsAppConfig.DoesNotExist:
            return Response({"error": "WhatsApp config not found"}, status=404)

        sent_count = 0
        failed_count = 0
        errors = []

        # Determine the employee making this request (for Contact.user FK)
        requesting_user = request.user  # Set by HRMEmployeeAuthentication
        # Fall back to first superuser if auth not set (shouldn't happen in practice)
        if requesting_user is None or not hasattr(requesting_user, "pk"):
            from HRM_App.models import RegistrationModel

            requesting_user = RegistrationModel.objects.filter(is_active=True).first()

        for lead in leads:
            raw_phone = str(lead.get("phone") or "").strip()
            name = str(lead.get("name") or "").strip()
            email = str(lead.get("email") or "").strip()

            if not raw_phone:
                failed_count += 1
                errors.append({"name": name, "error": "No phone number"})
                continue

            # Normalise phone: strip non-digits, ensure 10-digit India numbers get +91
            phone_digits = "".join(c for c in raw_phone if c.isdigit())
            if len(phone_digits) == 10:
                phone_digits = "91" + phone_digits  # Add India country code

            # Auto-create Contact so replies land in Inbox
            try:
                contact, created = Contact.objects.get_or_create(
                    phone_number=phone_digits,
                    whatsapp_config=wa_config,
                    defaults={
                        "name": name or raw_phone,
                        "email": email,
                        "user": requesting_user,
                    },
                )
                if not created and name and not contact.name:
                    contact.name = name
                    contact.save(update_fields=["name"])
            except Exception as e:
                failed_count += 1
                errors.append({"phone": raw_phone, "error": f"Contact error: {e}"})
                continue

            # Send template via Meta API
            try:
                from whatsapp_app.utils import send_whatsapp_template_message

                result = send_whatsapp_template_message(
                    config=wa_config,
                    to_phone=phone_digits,
                    template_name=template_name,
                    language_code=template_language,
                )
                provider_msg_id = (
                    result.get("messages", [{}])[0].get("id") if result else None
                )

                # Record outgoing message
                Message.objects.create(
                    contact=contact,
                    text=f"[Template: {template_name}]",
                    sender="system",
                    direction="OUTGOING",
                    status="Sent",
                    type="template",
                    provider_message_id=provider_msg_id,
                    timestamp=timezone.now(),
                )
                # Update contact last message
                contact.last_message = f"Template: {template_name}"
                contact.last_message_time = timezone.now()
                contact.save(update_fields=["last_message", "last_message_time"])

                sent_count += 1

            except Exception as e:
                logger.error(f"Failed to send WA to {phone_digits}: {e}")
                failed_count += 1
                errors.append({"phone": raw_phone, "error": str(e)})

        return Response(
            {
                "sent": sent_count,
                "failed": failed_count,
                "total": len(leads),
                "errors": errors,
            },
            status=200,
        )


def _resolve_pricing_date_range(
    request, max_lookback_days=89, default_range="last_7_days"
):
    """
    Shared date-range resolution for the Message Pricing insights endpoints.
    Returns (start_date, end_date, range_key, clamped) or None on an invalid custom range.
    Clamped to max_lookback_days since Meta's pricing_analytics only retains ~90 days
    of DAILY-granularity history.
    """
    from datetime import date

    today = timezone.localdate()
    range_key = (request.query_params.get("range") or default_range).lower()
    start_param = request.query_params.get("start_date")
    end_param = request.query_params.get("end_date")

    if range_key == "today":
        start_date, end_date = today, today
    elif range_key == "yesterday":
        start_date = end_date = today - timedelta(days=1)
    elif range_key == "last_7_days":
        start_date, end_date = today - timedelta(days=6), today
    elif range_key == "last_30_days":
        start_date, end_date = today - timedelta(days=29), today
    elif range_key == "custom" and start_param and end_param:
        try:
            start_date = date.fromisoformat(start_param)
            end_date = date.fromisoformat(end_param)
            if end_date < start_date:
                start_date, end_date = end_date, start_date
        except ValueError:
            return None
    else:
        start_date, end_date = today - timedelta(days=max_lookback_days), today

    oldest_allowed = today - timedelta(days=max_lookback_days)
    clamped = start_date < oldest_allowed
    if clamped:
        start_date = oldest_allowed

    return start_date, end_date, range_key, clamped


class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, HasActiveSubscription]

    @action(detail=False, methods=["GET"])
    def stats(self, request):
        from datetime import date, datetime, time, timedelta
        from django.db.models.functions import Coalesce
        from django.utils import timezone
        from django.db.models import Q
        from whatsapp_app.models import Campaign, Message, Contact

        def parse_range_bounds():
            range_key = (
                request.query_params.get("range")
                or request.query_params.get("period")
                or "all_time"
            ).lower()
            start_date_value = request.query_params.get("start_date")
            end_date_value = request.query_params.get("end_date")

            def to_aware_bound(date_value, end_of_day=False):
                local_date = date.fromisoformat(date_value)
                boundary_time = time.max if end_of_day else time.min
                naive_dt = datetime.combine(local_date, boundary_time)
                return timezone.make_aware(naive_dt, timezone.get_current_timezone())

            today = timezone.localdate()

            if range_key in {"all", "all_time", "all-time"}:
                return None, None
            if range_key == "today":
                return to_aware_bound(today.isoformat()), to_aware_bound(
                    today.isoformat(), True
                )
            if range_key == "yesterday":
                yesterday = today - timedelta(days=1)
                return to_aware_bound(yesterday.isoformat()), to_aware_bound(
                    yesterday.isoformat(), True
                )
            if range_key == "last_7_days":
                start_day = today - timedelta(days=6)
                return to_aware_bound(start_day.isoformat()), to_aware_bound(
                    today.isoformat(), True
                )
            if range_key == "last_30_days":
                start_day = today - timedelta(days=29)
                return to_aware_bound(start_day.isoformat()), to_aware_bound(
                    today.isoformat(), True
                )
            if range_key == "custom" and start_date_value and end_date_value:
                try:
                    start_bound = to_aware_bound(start_date_value)
                    end_bound = to_aware_bound(end_date_value, True)
                    if end_bound < start_bound:
                        start_bound, end_bound = end_bound, start_bound
                    return start_bound, end_bound
                except ValueError:
                    return None, None

            return None, None

        def get_all_stats():
            start_dt, end_dt = parse_range_bounds()
            config_id = get_whatsapp_config_id(request)
            campaigns_qs = Campaign.objects.filter(whatsapp_config_id=config_id)
            messages_qs = Message.objects.filter(
                contact__whatsapp_config_id=config_id
            ).annotate(effective_at=Coalesce("timestamp", "created_at"))

            if start_dt and end_dt:
                period_messages = messages_qs.filter(
                    effective_at__range=(start_dt, end_dt)
                )
            else:
                period_messages = messages_qs

            campaign_messages = period_messages.filter(campaign__isnull=False)
            ind_messages = period_messages.filter(campaign__isnull=True)

            campaign_ids_in_range = list(
                campaign_messages.values_list("campaign_id", flat=True).distinct()
            )
            if start_dt and end_dt:
                campaigns_qs = campaigns_qs.filter(
                    Q(created_at__range=(start_dt, end_dt))
                    | Q(id__in=campaign_ids_in_range)
                ).distinct()

            # Replies (incoming messages) from contacts who were sent a campaign message in this period
            campaign_contact_ids = list(
                campaign_messages.values_list("contact_id", flat=True).distinct()
            )
            campaign_replies_count = (
                period_messages.filter(
                    direction="INCOMING", contact_id__in=campaign_contact_ids
                ).count()
                if campaign_contact_ids
                else 0
            )

            active_campaigns_count = campaigns_qs.filter(status="RUNNING").count()

            # Fetch last 5 running/recent campaigns
            recent_campaigns = []
            for camp in campaigns_qs.order_by("-created_at")[:5]:
                camp_msgs = campaign_messages.filter(campaign=camp)
                total = camp_msgs.count()
                delivered = camp_msgs.filter(status__in=["Delivered", "Read"]).count()
                read = camp_msgs.filter(status="Read").count()
                failed = camp_msgs.filter(status="Failed").count()

                # Fetch first 10 contacts for this campaign to show in detail
                contacts_data = []
                for msg in camp_msgs.select_related("contact")[:10]:
                    contacts_data.append(
                        {
                            "name": msg.contact.name,
                            "phone": msg.contact.phone_number,
                            "status": msg.status,
                            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
                            "delivered_at": msg.delivered_at.isoformat()
                            if msg.delivered_at
                            else None,
                            "read_at": msg.read_at.isoformat() if msg.read_at else None,
                            "failed_at": msg.failed_at.isoformat()
                            if msg.failed_at
                            else None,
                            "timestamp": msg.timestamp.isoformat()
                            if msg.timestamp
                            else (
                                msg.created_at.isoformat() if msg.created_at else None
                            ),
                        }
                    )

                recent_campaigns.append(
                    {
                        "id": camp.id,
                        "name": camp.name,
                        "status": camp.status,
                        "audience": "Global",
                        "time": camp.created_at.strftime("%Y-%m-%d %H:%M"),
                        "count": total,
                        "delivered": delivered,
                        "read": read,
                        "failed": failed,
                        "body": camp.template.body if camp.template else "",
                        "contacts": contacts_data,
                    }
                )

            recent_individuals = []
            all_contact_ids_in_range = list(
                period_messages.values_list("contact_id", flat=True).distinct()
            )

            contact_rows = []
            if all_contact_ids_in_range:
                for contact in Contact.objects.filter(id__in=all_contact_ids_in_range):
                    contact_msgs = period_messages.filter(contact=contact)
                    latest_msg = contact_msgs.order_by("-effective_at").first()
                    latest_time = (
                        latest_msg.effective_at
                        if latest_msg and latest_msg.effective_at
                        else None
                    )
                    contact_rows.append(
                        (latest_time, contact, contact_msgs, latest_msg)
                    )

                contact_rows.sort(
                    key=lambda row: row[0] or timezone.now(), reverse=True
                )

            for latest_time, contact, contact_msgs, latest_msg in contact_rows[:100]:
                total = contact_msgs.filter(direction="OUTGOING").count()
                received = contact_msgs.filter(direction="INCOMING").count()
                delivered = contact_msgs.filter(
                    direction="OUTGOING", status__in=["Delivered", "Read"]
                ).count()
                read = contact_msgs.filter(direction="OUTGOING", status="Read").count()
                failed = contact_msgs.filter(
                    direction="OUTGOING", status="Failed"
                ).count()

                recent_individuals.append(
                    {
                        "id": contact.id,
                        "name": contact.name,
                        "phone": contact.phone_number,
                        "audience": "Contact",
                        "time": latest_time.strftime("%Y-%m-%d %H:%M")
                        if latest_time
                        else "N/A",
                        "count": total,
                        "received": received,
                        "delivered": delivered,
                        "read": read,
                        "failed": failed,
                        "body": latest_msg.text if latest_msg else "",
                        "contacts": [],
                    }
                )

            ind_all = period_messages
            return {
                "campaigns": {
                    "active": active_campaigns_count,
                    "sent": campaign_messages.count(),
                    "failed": campaign_messages.filter(status="Failed").count(),
                    "delivered": campaign_messages.filter(
                        status__in=["Delivered", "Read"]
                    ).count(),
                    "read": campaign_messages.filter(status="Read").count(),
                    "received": campaign_replies_count,
                    "running": recent_campaigns,
                },
                "individual": {
                    "active": Contact.objects.filter(
                        id__in=all_contact_ids_in_range
                    ).count(),
                    "sent": ind_all.filter(direction="OUTGOING").count(),
                    "failed": ind_all.filter(
                        direction="OUTGOING", status="Failed"
                    ).count(),
                    "delivered": ind_all.filter(
                        direction="OUTGOING", status__in=["Delivered", "Read"]
                    ).count(),
                    "read": ind_all.filter(direction="OUTGOING", status="Read").count(),
                    "received": ind_all.filter(direction="INCOMING").count(),
                    "running": recent_individuals,
                },
            }

        unified_stats = get_all_stats()
        return Response(unified_stats)

    @action(detail=False, methods=["GET"], url_path="message-pricing")
    def message_pricing(self, request):
        from datetime import datetime as dt, time
        from django.db.models.functions import Coalesce
        import requests
        from django.conf import settings
        from whatsapp_app.models import WhatsAppConfig, Message

        config_id = get_whatsapp_config_id(request)
        config = WhatsAppConfig.objects.filter(id=config_id).first()
        if (
            not config
            or not config.whatsapp_api_token
            or not config.whatsapp_business_account_id
        ):
            return Response(
                {
                    "error": "This WhatsApp account has no Meta Business Account connected yet, so pricing insights are unavailable."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        resolved = _resolve_pricing_date_range(request)
        if resolved is None:
            return Response(
                {"error": "Invalid custom date range."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_date, end_date, range_key, clamped = resolved

        start_ts = int(dt.combine(start_date, time.min).timestamp())
        end_ts = int(dt.combine(end_date, time.max).timestamp())

        graph_version = getattr(settings, "META_GRAPH_API_VERSION", "v20.0")
        waba_id = config.whatsapp_business_account_id
        headers = {"Authorization": f"Bearer {config.whatsapp_api_token}"}

        phone_filter = request.query_params.get("phone_number_id") or ""
        country_filter = (request.query_params.get("country") or "").strip().upper()

        analytics_expr = f"analytics.start({start_ts}).end({end_ts}).granularity(DAY)"
        pricing_expr = (
            f"pricing_analytics.start({start_ts}).end({end_ts}).granularity(DAILY)"
            '.dimensions(["COUNTRY","PRICING_CATEGORY","PRICING_TYPE"])'
        )
        if phone_filter:
            analytics_expr += f'.phone_numbers(["{phone_filter}"])'
            pricing_expr += f'.phone_numbers(["{phone_filter}"])'

        fields = f"currency,name,phone_numbers{{id,display_phone_number,verified_name}},{analytics_expr},{pricing_expr}"

        try:
            resp = requests.get(
                f"https://graph.facebook.com/{graph_version}/{waba_id}",
                headers=headers,
                params={"fields": fields},
                timeout=20,
            )
        except requests.RequestException as exc:
            return Response(
                {"error": f"Could not reach WhatsApp pricing analytics: {exc}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not resp.ok:
            logger.error(
                f"message_pricing: Meta API error {resp.status_code}: {resp.text[:500]}"
            )
            return Response(
                {
                    "error": "WhatsApp pricing analytics request failed.",
                    "detail": resp.text[:500],
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payload = resp.json()
        currency = payload.get("currency") or "USD"
        phone_numbers = [
            {
                "id": row.get("id"),
                "display_phone_number": row.get("display_phone_number"),
                "verified_name": row.get("verified_name"),
            }
            for row in (payload.get("phone_numbers") or {}).get("data", [])
        ]

        analytics_points = (payload.get("analytics") or {}).get("data_points") or []
        meta_sent = sum(p.get("sent") or 0 for p in analytics_points)
        meta_delivered = sum(p.get("delivered") or 0 for p in analytics_points)

        pa_blocks = (payload.get("pricing_analytics") or {}).get("data") or [{}]
        data_points = pa_blocks[0].get("data_points", []) if pa_blocks else []

        countries_seen = sorted(
            {p.get("country") for p in data_points if p.get("country")}
        )
        if country_filter:
            data_points = [
                p
                for p in data_points
                if (p.get("country") or "").upper() == country_filter
            ]

        CATEGORY_LABELS = {
            "MARKETING": "Marketing",
            "UTILITY": "Utility",
            "AUTHENTICATION": "Authentication",
            "AUTHENTICATION_INTERNATIONAL": "Authentication - international",
            "AI_PROVIDER": "AI Provider",
            "SERVICE": "Service",
        }
        CATEGORY_ORDER = [
            "MARKETING",
            "UTILITY",
            "AUTHENTICATION",
            "AUTHENTICATION_INTERNATIONAL",
            "AI_PROVIDER",
            "SERVICE",
        ]
        TYPE_LABELS = {
            "FREE_CUSTOMER_SERVICE": "Free customer service",
            "FREE_ENTRY_POINT": "Free entry point",
        }

        by_category_total = {}
        by_category_paid = {}
        by_category_cost = {}
        by_type_free = {t: 0 for t in TYPE_LABELS}
        total_delivered_meta = 0
        total_cost = 0.0

        for p in data_points:
            cat = p.get("pricing_category") or "OTHER"
            ptype = p.get("pricing_type") or "REGULAR"
            vol = p.get("volume") or 0
            cost = p.get("cost") or 0
            by_category_total[cat] = by_category_total.get(cat, 0) + vol
            by_category_cost[cat] = by_category_cost.get(cat, 0) + cost
            total_delivered_meta += vol
            total_cost += cost
            if ptype == "REGULAR":
                by_category_paid[cat] = by_category_paid.get(cat, 0) + vol
            else:
                by_type_free[ptype] = by_type_free.get(ptype, 0) + vol

        all_categories = list(CATEGORY_ORDER) + [
            c for c in by_category_total if c not in CATEGORY_ORDER
        ]

        def category_rows(counter):
            return [
                {
                    "category": cat,
                    "label": CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()),
                    "count": counter.get(cat, 0),
                }
                for cat in all_categories
            ]

        def cost_rows():
            return [
                {
                    "category": cat,
                    "label": CATEGORY_LABELS.get(cat, cat.replace("_", " ").title()),
                    "amount": round(by_category_cost.get(cat, 0), 2),
                }
                for cat in all_categories
            ]

        start_dt = timezone.make_aware(
            dt.combine(start_date, time.min), timezone.get_current_timezone()
        )
        end_dt = timezone.make_aware(
            dt.combine(end_date, time.max), timezone.get_current_timezone()
        )
        msgs = (
            Message.objects.filter(contact__whatsapp_config_id=config_id)
            .annotate(effective_at=Coalesce("timestamp", "created_at"))
            .filter(effective_at__range=(start_dt, end_dt))
        )

        outgoing = msgs.filter(direction="OUTGOING")
        message_status = {
            "sent": meta_sent,
            "delivered": meta_delivered,
            "received": msgs.filter(direction="INCOMING").count(),
            "received_source": "local_db",
            "local_sent": outgoing.count(),
            "local_delivered": outgoing.filter(
                status__in=["Delivered", "Read"]
            ).count(),
            "read": outgoing.filter(status="Read").count(),
            "failed": outgoing.filter(status="Failed").count(),
            "waiting": outgoing.filter(status__in=["Sent", "Waiting"]).count(),
        }

        return Response(
            {
                "range": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "key": range_key,
                    "clamped_to_90_days": clamped,
                },
                "currency": currency,
                "phone_numbers": phone_numbers,
                "countries": countries_seen,
                "selected_phone_number_id": phone_filter or None,
                "selected_country": country_filter or None,
                "message_status": message_status,
                "messages_delivered": {
                    "total": total_delivered_meta,
                    "by_category": category_rows(by_category_total),
                },
                "free_messages_delivered": {
                    "total": sum(by_type_free.values()),
                    "by_type": [
                        {
                            "type": t,
                            "label": TYPE_LABELS[t],
                            "count": by_type_free.get(t, 0),
                        }
                        for t in TYPE_LABELS
                    ],
                },
                "paid_messages_delivered": {
                    "total": sum(by_category_paid.values()),
                    "by_category": category_rows(by_category_paid),
                },
                "total_charges": {
                    "total": round(total_cost, 2),
                    "currency": currency,
                    "by_category": cost_rows(),
                },
            }
        )

    @action(detail=False, methods=["GET"], url_path="message-pricing-detail")
    def message_pricing_detail(self, request):
        from datetime import datetime as dt, time, timedelta
        from django.db.models.functions import Coalesce
        import re
        from whatsapp_app.models import Message

        config_id = get_whatsapp_config_id(request)
        resolved = _resolve_pricing_date_range(request)
        if resolved is None:
            return Response(
                {"error": "Invalid custom date range."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        start_date, end_date, range_key, clamped = resolved

        start_dt = timezone.make_aware(
            dt.combine(start_date, time.min), timezone.get_current_timezone()
        )
        end_dt = timezone.make_aware(
            dt.combine(end_date, time.max), timezone.get_current_timezone()
        )

        metric = (request.query_params.get("metric") or "").lower()
        category = (request.query_params.get("category") or "").upper()
        free_type = (request.query_params.get("free_type") or "").upper()

        base = (
            Message.objects.filter(contact__whatsapp_config_id=config_id)
            .annotate(effective_at=Coalesce("timestamp", "created_at"))
            .filter(effective_at__range=(start_dt, end_dt))
            .select_related("contact", "campaign__template")
        )

        note = None
        cat_label = category.replace("_", " ").title() if category else ""

        if metric == "sent":
            qs = base.filter(direction="OUTGOING")
            title = "Messages Sent"
            note = "The card total above comes from Meta's own delivery report. This list is from your local message log instead, so the count here can differ if local status tracking has fallen behind."
        elif metric == "delivered":
            qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
            title = "Messages Delivered"
            note = "The card total above comes from Meta's own delivery report. This list is from your local message log instead, so the count here can differ if local status tracking has fallen behind."
        elif metric == "received":
            qs = base.filter(direction="INCOMING")
            title = "Messages Received"
        elif metric == "category":
            qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
            if category == "SERVICE":
                qs = qs.filter(campaign__isnull=True)
            elif category:
                qs = qs.filter(campaign__template__category=category)
            else:
                qs = qs.none()
            title = f"{cat_label} — Delivered"
            note = "Category is read from the template used for each campaign message. Session (non-template) replies are grouped under Service."
        elif metric == "free":
            if free_type == "FREE_ENTRY_POINT":
                qs = base.none()
                title = "Free Entry Point"
                note = "Free entry-point messages come from click-to-WhatsApp ads and aren't tracked as individual conversation records in this app yet."
            else:
                qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
                title = "Free Customer Service — Delivered"
                note = "Estimated: messages sent within 24 hours of the contact’s last incoming message, which WhatsApp treats as a free customer-service reply."
        elif metric in ("paid", "charge"):
            qs = base.filter(direction="OUTGOING", status__in=["Delivered", "Read"])
            if category == "SERVICE":
                qs = qs.none()
            elif category:
                qs = qs.filter(campaign__template__category=category)
            title = f"{cat_label} — Paid" if category else "Paid Messages"
            note = "Estimated: messages sent outside the 24-hour free customer-service window for that contact, billed under WhatsApp’s per-message pricing."
        else:
            return Response(
                {"error": "Unknown metric."}, status=status.HTTP_400_BAD_REQUEST
            )

        qs = qs.order_by("-effective_at")

        needs_free_paid_split = metric in ("free", "paid", "charge") and not (
            metric == "free" and free_type == "FREE_ENTRY_POINT"
        )
        if needs_free_paid_split:
            candidates = list(qs[:1000])
            contact_ids = {m.contact_id for m in candidates}
            recent_incoming = {}
            if contact_ids:
                incoming_qs = (
                    Message.objects.filter(
                        contact_id__in=contact_ids, direction="INCOMING"
                    )
                    .annotate(effective_at=Coalesce("timestamp", "created_at"))
                    .order_by("contact_id", "effective_at")
                    .values("contact_id", "effective_at")
                )
                for row in incoming_qs:
                    recent_incoming.setdefault(row["contact_id"], []).append(
                        row["effective_at"]
                    )

            def is_free(m):
                times = recent_incoming.get(m.contact_id) or []
                window_start = m.effective_at - timedelta(hours=24)
                return any(
                    window_start <= t < m.effective_at
                    for t in times
                    if t and m.effective_at
                )

            if metric == "free":
                filtered = [
                    m for m in candidates if is_free(m) or m.campaign_id is None
                ]
            else:
                filtered = [
                    m for m in candidates if not (is_free(m) or m.campaign_id is None)
                ]
            total_count = len(filtered)
            page_items = filtered[:100]
        else:
            total_count = qs.count()
            page_items = list(qs[:100])

        results = []
        for m in page_items:
            contact = m.contact
            raw_phone = contact.phone_number or ""
            clean_phone = re.sub(r"\D", "", raw_phone)
            if len(clean_phone) > 10:
                clean_phone = clean_phone[-10:]
            name = contact.name if (contact.name and contact.name != "Unknown") else ""
            results.append(
                {
                    "contact_id": contact.id,
                    "name": name or None,
                    "phone": clean_phone or raw_phone,
                    "status": m.status,
                    "direction": m.direction,
                    "campaign_name": m.campaign.name if m.campaign_id else None,
                    "template_category": m.campaign.template.category
                    if (m.campaign_id and m.campaign.template_id)
                    else None,
                    "timestamp": m.effective_at.isoformat() if m.effective_at else None,
                    "text": (m.text or "")[:140],
                }
            )

        return Response(
            {
                "title": title,
                "note": note,
                "count": total_count,
                "results": results,
            }
        )
