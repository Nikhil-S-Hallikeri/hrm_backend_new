from rest_framework import serializers
from rest_framework.validators import UniqueValidator
import re
from urllib.parse import urlparse
from whatsapp_app.models import (
    User, Contact, ContactGroup, Template, Campaign, Message,
    MessageTemplate, WhatsAppTemplate, WhatsAppConfig, LoginSession,
    AIConfig, Category, SubCategory, Product, AutoReply, KnowledgeDocument
)

from django.contrib.auth import authenticate
from whatsapp_app.utils import extract_variables

def mask_value(value, visible_chars=4):
    if not value:
        return ""
    value_str = str(value)
    
    # Handle webhook URLs
    if value_str.startswith('http://') or value_str.startswith('https://'):
        try:
            parsed = urlparse(value_str)
            if parsed.netloc:
                masked_netloc = "*" * len(parsed.netloc)
                return value_str.replace(parsed.netloc, masked_netloc)
        except Exception:
            pass

    if len(value_str) <= visible_chars:
        return "*" * len(value_str)

    return "*" * max(0, len(value_str) - visible_chars) + value_str[-visible_chars:]




class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    team_lead_email = serializers.EmailField(source='team_lead.email', read_only=True, allow_null=True)
    team_lead_name = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'role', 'team_lead', 'team_lead_email', 'team_lead_name', 'is_active', 'phone_number', 'theme_preference', 'password', 'is_online', 'last_seen']
        read_only_fields = ['id', 'is_online', 'last_seen']
    
    def get_team_lead_name(self, obj):
        if obj.team_lead:
            return obj.team_lead.email.split('@')[0]
        return None

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class UserCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new User directly (Admin action)"""
    password = serializers.CharField(write_only=True, required=True, min_length=6)
    name = serializers.CharField(required=True, allow_blank=False)
    phone_number = serializers.CharField(required=True, allow_blank=False)
    
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'password', 'role', 'is_active', 'phone_number']
        read_only_fields = ['id']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserPreferenceSerializer(serializers.Serializer):
    """Serializer for updating user preferences"""
    theme_preference = serializers.ChoiceField(
        choices=['light', 'dark', 'auto'],
        required=True
    )


class SignupWithOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=[('ADMIN', 'Admin'), ('EMPLOYEE', 'Employee'), ('MANAGER', 'Manager')], default='EMPLOYEE')
    
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists")
        return value

class VerifySignupOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    
class LoginSerializers(serializers.Serializer):
      email = serializers.EmailField()
      password = serializers.CharField(write_only=True)


      def validate(self, attrs):
         email = attrs.get("email")
         password = attrs.get("password")
         
         if not User.objects.filter(email=email).exists():
             raise serializers.ValidationError("No user found with this email address")
             
         user = authenticate(email=email, password=password)
         if not user:
            raise serializers.ValidationError("Invalid password")
            
         attrs["user"] = user
         return attrs
      
class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email does not exist")
        return value


class LoginSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoginSession
        fields = [
            'id', 'device_name', 'browser', 'os', 'ip_address', 
            'location_city', 'location_country', 'is_current', 
            'is_active', 'logged_in_at', 'last_active'
        ]
        read_only_fields = fields


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
    confirm_password = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "New passwords do not match."})
        return attrs


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=6)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=True)



def resolve_template_placeholder(text):
    if not text:
        return text
    text_str = str(text).strip()
    match = re.match(r'^\[(?:System Sent )?Template:\s*([^\]]+)\]$', text_str, re.IGNORECASE)
    if match:
        template_name = match.group(1).strip().lower()
        from whatsapp_app.models import WhatsAppTemplate, MessageTemplate
        wt = WhatsAppTemplate.objects.filter(template_name=template_name).first()
        if wt and wt.body_text:
            return wt.body_text
        mt = MessageTemplate.objects.filter(name=template_name).first()
        if mt and mt.body:
            return mt.body
        return f"Template: {template_name}"
    
    match2 = re.match(r'^Template:\s*([^\s]+)$', text_str, re.IGNORECASE)
    if match2:
        template_name = match2.group(1).strip().lower()
        from whatsapp_app.models import WhatsAppTemplate, MessageTemplate
        wt = WhatsAppTemplate.objects.filter(template_name=template_name).first()
        if wt and wt.body_text:
            return wt.body_text
        mt = MessageTemplate.objects.filter(name=template_name).first()
        if mt and mt.body:
            return mt.body

    return text


# Contact Group Serializer
class ContactGroupSerializer(serializers.ModelSerializer):
    contact_count = serializers.SerializerMethodField()

    class Meta:
        model = ContactGroup
        fields = ['id', 'name', 'color', 'contact_count', 'created_at']
        read_only_fields = ['id', 'contact_count', 'created_at']

    def get_contact_count(self, obj):
        return obj.contacts.count()


# Contact Serializer
class ContactSerializer(serializers.ModelSerializer):
    is_within_24h_window = serializers.BooleanField(read_only=True)
    groups = ContactGroupSerializer(many=True, read_only=True)
    group_ids = serializers.PrimaryKeyRelatedField(
        source='groups', many=True, queryset=ContactGroup.objects.all(), required=False, write_only=True
    )

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if 'last_message' in ret and ret['last_message']:
            ret['last_message'] = resolve_template_placeholder(ret['last_message'])
        return ret

    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'phone_number', 'email', 'language', 'attributes',
            'broadcast', 'sms', 'created_at', 'updated_at',
            'last_message', 'last_message_time', 'last_message_received_at',
            'is_within_24h_window', 'unread_count',
            'assigned_to', 'status', 'whatsapp_config',
            'last_customer_message_time', 'customer_service_window_expiry', 'is_service_window_open',
            'aria_user_id', 'aria_journey_stage', 'aria_last_synced_at',
            'groups', 'group_ids',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'last_message_received_at',
            'is_within_24h_window', 'aria_user_id', 'aria_journey_stage',
            'aria_last_synced_at',
        ]

    def validate_phone_number(self, value):
        from whatsapp_app.utils import _normalize_phone_number
        normalized_value = _normalize_phone_number(value)
        if not normalized_value:
            raise serializers.ValidationError('phone_number must contain digits.')

        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            user = None

        queryset = Contact.objects.filter(phone_number=normalized_value)
        
        # If user is not authenticated, we assume they are targeting the default public user
        # This prevents global uniqueness check which is too restrictive for bulk uploads
        if user:
            queryset = queryset.filter(user=user)
        else:
            from whatsapp_app.utils import get_public_api_user
            target_user = get_public_api_user()
            queryset = queryset.filter(user=target_user)

        # Resolve config ID from payload, request headers, or context fallback.
        # initial_data is only a per-item dict for single create/update - when this
        # serializer runs as a many=True list's child (bulk upload), self.initial_data
        # is the whole list instead, so .get() would blow up. Guard for that shape.
        config_id = None
        if hasattr(self, 'initial_data') and isinstance(self.initial_data, dict):
            config_id = self.initial_data.get('whatsapp_config')
        if not config_id and request:
            from whatsapp_app.views import get_whatsapp_config_id
            config_id = get_whatsapp_config_id(request)

        if config_id:
            queryset = queryset.filter(whatsapp_config_id=config_id)
        elif self.instance and self.instance.whatsapp_config_id:
            queryset = queryset.filter(whatsapp_config_id=self.instance.whatsapp_config_id)

        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError('phone_number must be unique per user.')

        return normalized_value






# Template Serializer
class TemplateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    
    class Meta:
        model = Template
        fields = ['id', 'name', 'body', 'category', 'status', 'created_by', 'created_by_email', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


# Campaign Serializer
class CampaignListSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'template', 'template_name', 'status', 'created_by',
            'created_by_email', 'total_contacts', 'total_sent', 'total_failed',
            'scheduled_at', 'started_at', 'completed_at', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

class CampaignDetailSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    contact_list = ContactSerializer(source='contacts', many=True, read_only=True)
    contacts = serializers.SlugRelatedField(many=True, read_only=True, slug_field='phone_number')
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'template', 'template_name', 'status', 'created_by',
            'created_by_email', 'contacts', 'contact_list', 'variables',
            'total_contacts', 'total_sent', 'total_failed',
            'scheduled_at', 'started_at', 'completed_at', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']



class CampaignHistorySerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'status', 'template', 'template_name',
            'created_by', 'created_by_email', 'total_contacts',
            'total_sent', 'total_failed', 'started_at', 'completed_at', 'created_at',
        ]


class CampaignScheduledSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'status', 'template', 'template_name',
            'created_by', 'created_by_email', 'total_contacts', 'scheduled_at', 'created_at',
        ]

class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    template_id = serializers.IntegerField(required=False, allow_null=True)
    whatsapp_template_id = serializers.IntegerField(required=False, allow_null=True)
    contact_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=True, default=list
    )
    variables = serializers.DictField(default=dict, required=False)


# Message Serializer
class MessageSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone_number', read_only=True)
    contact_whatsapp_config = serializers.IntegerField(source='contact.whatsapp_config_id', read_only=True)
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if ret.get('media_url') and ret['media_url'].startswith('/'):
            request = self.context.get('request')
            if request:
                ret['media_url'] = request.build_absolute_uri(ret['media_url'])
        buttons = ret.get('buttons')
        if isinstance(buttons, str):
            try:
                import json
                ret['buttons'] = json.loads(buttons)
            except Exception:
                ret['buttons'] = []
        return ret
    
    class Meta:
        model = Message
        fields = [
            'id', 'contact', 'contact_name', 'contact_phone', 'contact_whatsapp_config',
            'campaign', 'text', 'sender', 'direction', 'status', 'type', 'media_url',
            'caption', 'buttons', 'read', 'created_at', 'timestamp', 'sent_at',
            'delivered_at', 'read_at', 'failed_at'
        ]
        read_only_fields = ['id', 'created_at']



# MessageTemplate Serializer
class MessageTemplateSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    language = serializers.CharField(required=False, default='en')
    header_type = serializers.CharField(required=False, default='NONE')
    header_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    footer_text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    buttons = serializers.JSONField(required=False, default=list)
    name = serializers.RegexField(
        regex=r'^[a-z0-9_]+$',
        validators=[UniqueValidator(queryset=MessageTemplate.objects.all(), message="A template with this name already exists.")],
        error_messages={'invalid': 'Template name must be lowercase with underscores only'},
    )

    uploaded_preview_image = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    meta_media_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    header_media = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    class Meta:
        model = MessageTemplate
        fields = [
            'id', 'name', 'category', 'language', 'header_type', 'header_text', 'body', 'sample_values', 'footer_text', 'buttons',
            'variables', 'variables_count', 'status',
            'uploaded_preview_image', 'meta_media_url', 'header_media',
            'created_by', 'created_by_email', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'variables', 'variables_count', 'status', 'created_by', 'created_at', 'updated_at']

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not ret.get('header_media'):
            fallback = None
            if instance.uploaded_preview_image:
                fallback = instance.uploaded_preview_image
            elif instance.meta_media_url:
                fallback = instance.meta_media_url
            elif instance.sample_values and isinstance(instance.sample_values, dict):
                fallback = instance.sample_values.get('header_handle') or instance.sample_values.get('media_url')
            ret['header_media'] = fallback

        # header_media can resolve to a full base64-encoded image/video (cached from
        # Meta's CDN, up to tens of MB). Embedding that inline - even for a single
        # template fetch, e.g. when opening the template picker in the inbox - is what
        # made the tab hang/go blank for contacts whose config has large cached media.
        # Point at the existing lazily-fetched /header-media/ endpoint instead; the
        # <img>/<video> tag can pull the real bytes as a normal HTTP request.
        if isinstance(ret.get('header_media'), str) and ret['header_media'].startswith('data:'):
            request = self.context.get('request')
            path = f'/templates/{instance.id}/header-media/'
            ret['header_media'] = request.build_absolute_uri(path) if request else path

        return ret

    def _extract_and_validate_variables(self, body):
        if re.search(r"(?<!\{)\{(?!\{)", body or ""):
            raise serializers.ValidationError("Use double curly braces {{1}} format for variables")

        raw_tokens = re.findall(r"\{\{([^{}]+)\}\}", body or "")
        invalid_tokens = [token for token in raw_tokens if not token.isdigit()]
        if invalid_tokens:
            raise serializers.ValidationError("Invalid variable format. Use {{1}}, {{2}}, ...")

        extracted = re.findall(r"\{\{(\d+)\}\}", body or "")
        if len(extracted) != len(set(extracted)):
            raise serializers.ValidationError("Duplicate variables are not allowed.")

        variables = extract_variables(body or "")
        expected = [str(i) for i in range(1, len(variables) + 1)]

        if variables != expected:
            raise serializers.ValidationError("Variables must be sequential like {{1}}, {{2}}, {{3}}")

        return variables

    def validate_body(self, value):
        self._extract_and_validate_variables(value)
        return value

    def validate(self, attrs):
        category = attrs.get('category')
        if category is None and self.instance:
            category = self.instance.category

        if category == 'AUTHENTICATION':
            header_type = attrs.get('header_type')
            if header_type is None and self.instance:
                header_type = self.instance.header_type
            
            if header_type and header_type != 'NONE':
                raise serializers.ValidationError({
                    "header_type": "Authentication templates cannot contain a header component."
                })

            buttons = attrs.get('buttons')
            if buttons is None and self.instance:
                buttons = self.instance.buttons

            if buttons:
                raise serializers.ValidationError({
                    "buttons": "Authentication templates cannot contain custom CTA or Quick Reply buttons."
                })

        return attrs

    def create(self, validated_data):
        body = validated_data.get('body', '')
        variables = self._extract_and_validate_variables(body)
        validated_data.pop('variables', None)
        validated_data['language'] = validated_data.get('language') or 'en'
        validated_data['variables'] = variables
        validated_data['variables_count'] = len(variables)
        validated_data['status'] = 'PENDING'
        return super().create(validated_data)

    def update(self, instance, validated_data):
        body = validated_data.get('body', instance.body)
        variables = self._extract_and_validate_variables(body)
        validated_data.pop('variables', None)
        validated_data['variables'] = variables
        validated_data['variables_count'] = len(variables)
        validated_data['status'] = 'PENDING'
        return super().update(instance, validated_data)


class MessageTemplateListSerializer(MessageTemplateSerializer):
    """
    Same as MessageTemplateSerializer, but additionally drops the raw `sample_values`
    field for list responses - its `header_handle` is redundant with `header_media`'s
    fallback (both base classes already swap a base64 blob there for a lightweight
    /header-media/ URL), so including it again in every row of a template list is pure
    duplication. This is what previously blew list payloads up to 100MB+.
    """

    class Meta(MessageTemplateSerializer.Meta):
        fields = [f for f in MessageTemplateSerializer.Meta.fields if f != 'sample_values']


class CampaignSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True, allow_null=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    contacts_count = serializers.SerializerMethodField()
    contacts = serializers.SlugRelatedField(many=True, read_only=True, slug_field='phone_number')
    
    class Meta:
        model = Campaign
        fields = [
            'id', 'name', 'template', 'template_name',
            'contacts', 'contacts_count', 'status', 'variables', 'total_contacts', 'total_sent', 'total_failed',
            'started_at', 'completed_at', 'scheduled_at', 'created_by', 'created_by_email', 'created_at'
        ]
        read_only_fields = [
            'id', 'total_contacts', 'total_sent', 'total_failed',
            'started_at', 'completed_at', 'created_by', 'created_by_email', 'created_at'
        ]
    
    def get_contacts_count(self, obj):
        return obj.contacts.count()


# InboxContact Serializer
class InboxContactSerializer(serializers.ModelSerializer):
    is_within_24h_window = serializers.BooleanField(read_only=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if 'last_message' in ret and ret['last_message']:
            ret['last_message'] = resolve_template_placeholder(ret['last_message'])
        return ret

    class Meta:
        model = Contact
        fields = [
            'id', 'name', 'phone_number',
            'last_message', 'last_message_time', 'last_message_received_at',
            'is_within_24h_window', 'unread_count', 'status',
            'assigned_to', 'created_at', 'whatsapp_config',
            'last_customer_message_time', 'customer_service_window_expiry', 'is_service_window_open',
            'attributes',
        ]



class InboxMessageSerializer(serializers.ModelSerializer):
    contact_whatsapp_config = serializers.IntegerField(source='contact.whatsapp_config_id', read_only=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if 'text' in ret and ret['text']:
            ret['text'] = resolve_template_placeholder(ret['text'])
        buttons = ret.get('buttons')
        if isinstance(buttons, str):
            try:
                import json
                ret['buttons'] = json.loads(buttons)
            except Exception:
                ret['buttons'] = []
        return ret

    class Meta:
        model = Message
        fields = [
            'id', 'contact', 'contact_whatsapp_config', 'text', 'sender', 'direction', 'status', 'type', 
            'media_url', 'caption', 'buttons', 'timestamp', 'created_at',
            'sent_at', 'delivered_at', 'read_at', 'failed_at'
        ]


class WebhookEventSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_blank=True, allow_null=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    message = serializers.CharField(allow_blank=True, required=False, allow_null=True)
    sender = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    timestamp = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    type = serializers.CharField(max_length=20, default='text')
    status = serializers.CharField(max_length=20, default='sent', required=False, allow_blank=True, allow_null=True)
    provider_message_id = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    classification = serializers.CharField(max_length=50, required=False, allow_blank=True)
    mediaUrl = serializers.URLField(max_length=1000, required=False, allow_blank=True)
    caption = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        return attrs


class WhatsAppTemplateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='template_name', read_only=True)
    body = serializers.CharField(source='body_text', read_only=True)
    created_at = serializers.DateTimeField(source='last_synced_at', read_only=True)
    updated_at = serializers.DateTimeField(source='last_synced_at', read_only=True)

    uploaded_preview_image = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    meta_media_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    header_media = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not ret.get('header_media'):
            fallback = None
            if instance.uploaded_preview_image:
                fallback = instance.uploaded_preview_image
            elif instance.meta_media_url:
                fallback = instance.meta_media_url
            elif instance.sample_values and isinstance(instance.sample_values, dict):
                fallback = instance.sample_values.get('header_handle') or instance.sample_values.get('media_url')
            ret['header_media'] = fallback
        return ret

    class Meta:
        model = WhatsAppTemplate
        fields = [
            'id',
            'name',
            'template_name',
            'language',
            'category',
            'header_type',
            'header_text',
            'body',
            'body_text',
            'sample_values',
            'footer_text',
            'buttons',
            'status',
            'rejection_reason',
            'uploaded_preview_image',
            'meta_media_url',
            'header_media',
            'created_at',
            'updated_at',
            'last_synced_at',
        ]


class WhatsAppConfigSerializer(serializers.ModelSerializer):
    chatbot_access = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WhatsAppConfig
        fields = [
            'id', 'name', 'crm_webhook_url', 'crm_api_token',
            'whatsapp_api_token', 'whatsapp_api_token_start_date', 'whatsapp_api_token_expire_date',
            'phone_number_id', 'whatsapp_business_account_id', 
            'whatsapp_app_id', 'whatsapp_app_name', 'webhook_verify_token', 
            'gemini_api_key', 'is_ai_enabled', 'auto_send_template', 'auto_send_template_name',
            'chatbot_access', 'updated_at',
            'verification_status', 'last_checked_at', 'error_message'
        ]
        read_only_fields = ['id', 'updated_at', 'verification_status', 'last_checked_at', 'error_message']

    def get_chatbot_access(self, obj):
        from django.db import connection, DatabaseError
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        obj_id = getattr(obj, 'id', None) or (obj.get('id') if isinstance(obj, dict) else None)
        if not obj_id:
            return False
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT chatbot_access FROM whatsapp_saas_whatsappuser WHERE whatsapp_config_id = %s OR user_id = %s",
                    [obj_id, user.id]
                )
                row = cursor.fetchone()
                if row:
                    return bool(row[0])
        except DatabaseError:
            pass
        return False

    def validate(self, attrs):
        if 'is_ai_enabled' not in attrs:
            attrs['is_ai_enabled'] = True

        if not self.instance:
            from django.db import connection
            user = self.context['request'].user
            limit = 1
            if user and user.is_authenticated:
                if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
                    limit = 9999
                else:
                    with connection.cursor() as cursor:
                        try:
                            cursor.execute("SELECT app_limit FROM whatsapp_saas_whatsappuser WHERE user_id = %s", [user.id])
                            row = cursor.fetchone()
                            if row:
                                limit = int(row[0])
                        except Exception:
                            pass
            existing_configs = WhatsAppConfig.objects.filter(user=user) if user and user.is_authenticated else WhatsAppConfig.objects.none()
            count = existing_configs.count()
            if count >= limit:
                first_cfg = existing_configs.first()
                if first_cfg:
                    self.context['reuse_instance'] = first_cfg
                else:
                    raise serializers.ValidationError(f"Limit exceeded. You have access to create {limit} app(s).")
        return attrs


    def to_representation(self, instance):
        ret = super().to_representation(instance)
        
        sensitive_fields = [
            'whatsapp_api_token', 'crm_api_token', 'gemini_api_key', 
            'webhook_verify_token', 'phone_number_id', 
            'whatsapp_business_account_id', 'whatsapp_app_id', 
            'crm_webhook_url'
        ]
        
        for field in sensitive_fields:
            if ret.get(field):
                ret[field] = mask_value(ret[field])
                
        return ret

    def to_internal_value(self, data):
        mutable_data = data.copy() if hasattr(data, 'copy') else dict(data)
        
        sensitive_fields = [
            'whatsapp_api_token', 'crm_api_token', 'gemini_api_key', 
            'webhook_verify_token', 'phone_number_id', 
            'whatsapp_business_account_id', 'whatsapp_app_id', 
            'crm_webhook_url'
        ]
        
        if self.instance:
            for field in sensitive_fields:
                if field in mutable_data:
                    val = mutable_data[field]
                    if isinstance(val, str) and '***' in val:
                        mutable_data[field] = getattr(self.instance, field)
                        
        return super().to_internal_value(mutable_data)




class ProductSerializer(serializers.ModelSerializer):
    subcategory_name = serializers.CharField(source='subcategory.name', read_only=True)
    category_name = serializers.CharField(source='subcategory.category.name', read_only=True)
    category_id = serializers.IntegerField(source='subcategory.category.id', read_only=True)

    class Meta:
        model = Product
        fields = [
            'id', 'subcategory', 'subcategory_name', 'category_id', 'category_name',
            'name', 'description', 'price', 'image', 'image_url', 'is_active',
            'meta_product_id', 'sync_status', 'last_sync_time', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'sync_status', 'last_sync_time']


class SubCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    products_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SubCategory
        fields = [
            'id', 'category', 'category_name', 'name', 'description', 'is_active',
            'products_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_products_count(self, obj):
        return obj.products.count()


class CategorySerializer(serializers.ModelSerializer):
    subcategories_count = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Category
        fields = [
            'id', 'whatsapp_config', 'name', 'description', 'is_active',
            'subcategories_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'whatsapp_config', 'created_at', 'updated_at']

    def get_subcategories_count(self, obj):
        return obj.subcategories.count()




class AutoReplySerializer(serializers.ModelSerializer):
    remove_media = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = AutoReply
        fields = [
            'id', 'whatsapp_config', 'keywords', 'reply_text', 'media', 'buttons', 'is_active',
            'created_at', 'updated_at', 'remove_media'
        ]
        read_only_fields = ['id', 'whatsapp_config', 'created_at', 'updated_at']

    def to_internal_value(self, data):
        ret = super().to_internal_value(data)
        buttons = ret.get('buttons')
        if isinstance(buttons, str):
            try:
                import json
                ret['buttons'] = json.loads(buttons)
            except Exception:
                pass
        return ret

    def create(self, validated_data):
        validated_data.pop('remove_media', None)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        remove_media = validated_data.pop('remove_media', False)
        if remove_media:
            instance.media = None
        return super().update(instance, validated_data)

class AIConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIConfig
        fields = [
            'id', 'whatsapp_config', 'assistant_name', 'business_name', 'personality', 'tone', 'primary_language',
            'prompt', 'system_prompt', 'conversation_behaviours', 'lead_collection', 'auto_replies',
            'websites', 'faqs',
            'context_window_size', 'fallback_rule', 'confidence_threshold', 'human_handoff_alert',
            'primary_color', 'widget_position',
            'llm_provider', 'model_name', 'api_key',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'whatsapp_config', 'created_at', 'updated_at']

    def validate_api_key(self, value):
        # A stray leading/trailing space or newline from copy-pasting a key is invisible
        # in a text input but makes the provider reject it outright (401) with no hint
        # why - trim it here so a "valid-looking" paste can't silently save as garbage.
        return value.strip() if isinstance(value, str) else value

    def validate_model_name(self, value):
        return value.strip() if isinstance(value, str) else value

    def validate_llm_provider(self, value):
        return value.strip().lower() if isinstance(value, str) else value

class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = '__all__'
        read_only_fields = ['whatsapp_config']


from whatsapp_app.models import (
    FollowUpWorkflow, FollowUpStep, FollowUpContactState,
    ReminderCampaign, ReminderSchedule, ReminderExecution, AutomationLog
)

class FollowUpStepSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = FollowUpStep
        fields = ['id', 'step_number', 'delay_seconds', 'template', 'template_name', 'media_url', 'template_variables']
        read_only_fields = ['id']

class FollowUpWorkflowSerializer(serializers.ModelSerializer):
    steps = FollowUpStepSerializer(many=True, required=False)

    class Meta:
        model = FollowUpWorkflow
        fields = ['id', 'name', 'whatsapp_config', 'is_active', 'created_by', 'created_at', 'updated_at', 'steps']
        read_only_fields = ['id', 'whatsapp_config', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        steps_data = validated_data.pop('steps', [])
        workflow = FollowUpWorkflow.objects.create(**validated_data)
        for step_data in steps_data:
            FollowUpStep.objects.create(workflow=workflow, **step_data)
        return workflow

    def update(self, instance, validated_data):
        steps_data = validated_data.pop('steps', None)
        instance.name = validated_data.get('name', instance.name)
        instance.is_active = validated_data.get('is_active', instance.is_active)
        instance.save()

        if steps_data is not None:
            # Delete old steps and recreate
            instance.steps.all().delete()
            for step_data in steps_data:
                FollowUpStep.objects.create(workflow=instance, **step_data)
        return instance

class FollowUpContactStateSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone_number', read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    current_step_number = serializers.IntegerField(source='current_step.step_number', read_only=True)

    class Meta:
        model = FollowUpContactState
        fields = [
            'id', 'contact', 'contact_name', 'contact_phone', 'workflow', 'workflow_name',
            'current_step', 'current_step_number', 'status', 'next_execution_time', 'retry_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class ReminderScheduleSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    media_url = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    timing_type = serializers.CharField(required=False, default='1_HOUR_BEFORE')

    class Meta:
        model = ReminderSchedule
        fields = ['id', 'timing_type', 'custom_minutes_before', 'template', 'template_name', 'media_url', 'template_variables', 'button_actions']

class ReminderCampaignSerializer(serializers.ModelSerializer):
    schedules = ReminderScheduleSerializer(many=True, required=False)
    contacts = serializers.PrimaryKeyRelatedField(many=True, queryset=Contact.objects.all(), required=False)
    contacts_count = serializers.SerializerMethodField()

    class Meta:
        model = ReminderCampaign
        fields = [
            'id', 'name', 'whatsapp_config', 'event_type', 'event_title', 'event_date_time',
            'time_zone', 'is_active', 'is_interconnected', 'alternate_dates', 'conditional_rules',
            'created_by', 'created_at', 'updated_at', 'schedules',
            'contacts', 'contacts_count'
        ]
        read_only_fields = ['id', 'whatsapp_config', 'created_by', 'created_at', 'updated_at']

    def get_contacts_count(self, obj):
        return obj.contacts.count()

    def create(self, validated_data):
        schedules_data = validated_data.pop('schedules', [])
        contacts = validated_data.pop('contacts', [])
        if 'created_by' not in validated_data or not validated_data['created_by']:
            from whatsapp_app.utils import get_public_api_user
            validated_data['created_by'] = get_public_api_user()
        if 'whatsapp_config' not in validated_data or not validated_data['whatsapp_config']:
            from whatsapp_app.models import WhatsAppConfig
            validated_data['whatsapp_config'] = WhatsAppConfig.get_solo()
        if 'settings' not in validated_data or validated_data['settings'] is None:
            validated_data['settings'] = {}
        if 'workflow_type' not in validated_data or not validated_data['workflow_type']:
            validated_data['workflow_type'] = 'STANDARD'
        if 'alternate_dates' not in validated_data or validated_data['alternate_dates'] is None:
            validated_data['alternate_dates'] = []
        if 'conditional_rules' not in validated_data or validated_data['conditional_rules'] is None:
            validated_data['conditional_rules'] = {}

        campaign = ReminderCampaign.objects.create(**validated_data)
        if contacts:
            campaign.contacts.set(contacts)
        for schedule_data in schedules_data:
            schedule_data.pop('id', None)
            ReminderSchedule.objects.create(reminder_campaign=campaign, **schedule_data)
        return campaign

    def update(self, instance, validated_data):
        schedules_data = validated_data.pop('schedules', None)
        contacts = validated_data.pop('contacts', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if contacts is not None:
            instance.contacts.set(contacts)

        if schedules_data is not None:
            existing_schedules = {s.id: s for s in instance.schedules.all()}
            kept_schedule_ids = set()

            for schedule_data in schedules_data:
                sched_id = schedule_data.pop('id', None)
                if sched_id and sched_id in existing_schedules:
                    sched_obj = existing_schedules[sched_id]
                    for attr, value in schedule_data.items():
                        setattr(sched_obj, attr, value)
                    sched_obj.save()
                    kept_schedule_ids.add(sched_id)
                else:
                    new_sched = ReminderSchedule.objects.create(reminder_campaign=instance, **schedule_data)
                    kept_schedule_ids.add(new_sched.id)

            for sched_id, sched_obj in existing_schedules.items():
                if sched_id not in kept_schedule_ids:
                    sched_obj.delete()

        return instance

class ReminderExecutionSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone_number', read_only=True)
    campaign_name = serializers.CharField(source='reminder_campaign.name', read_only=True)
    timing_type = serializers.CharField(source='schedule.timing_type', read_only=True)

    class Meta:
        model = ReminderExecution
        fields = [
            'id', 'reminder_campaign', 'campaign_name', 'contact', 'contact_name', 'contact_phone',
            'schedule', 'timing_type', 'status', 'button_response', 'retry_count', 'execution_time', 'sent_at',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class AutomationLogSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source='contact.name', read_only=True)
    contact_phone = serializers.CharField(source='contact.phone_number', read_only=True)

    class Meta:
        model = AutomationLog
        fields = ['id', 'whatsapp_config', 'automation_type', 'contact', 'contact_name', 'contact_phone', 'action_type', 'details', 'created_at']
        read_only_fields = ['id', 'created_at']

