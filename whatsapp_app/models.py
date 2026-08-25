from django.db import models
from django.utils import timezone
from datetime import timedelta
from cryptography.fernet import Fernet
import base64
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

# ─── HRM User Bridge ─────────────────────────────────────────────────────────
# Instead of the SaaS custom User model, we use HRM's RegistrationModel as the
# user identity throughout the WhatsApp module. The alias 'User' keeps all
# downstream FK references working without any further code changes.
from HRM_App.models import RegistrationModel as User
# ─────────────────────────────────────────────────────────────────────────────


def get_fernet():
    # Use SECRET_KEY to derive a 32-byte base64 encoded key
    key = settings.SECRET_KEY.encode('utf-8')
    key = base64.urlsafe_b64encode(key.ljust(32, b'0')[:32])
    return Fernet(key)


class EncryptedTextField(models.TextField):
    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except Exception:
            logger.error(
                "Failed to decrypt %s.%s: stored value is not decryptable with the current SECRET_KEY. "
                "Returning raw stored value; downstream use of this field will likely fail.",
                self.model.__name__ if self.model else '?', self.name
            )
            return value

    def get_prep_value(self, value):
        if not value:
            return value
        try:
            return get_fernet().encrypt(value.encode()).decode()
        except Exception:
            return value


class EncryptedCharField(models.CharField):
    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return get_fernet().decrypt(value.encode()).decode()
        except Exception:
            logger.error(
                "Failed to decrypt %s.%s: stored value is not decryptable with the current SECRET_KEY. "
                "Returning raw stored value; downstream use of this field will likely fail.",
                self.model.__name__ if self.model else '?', self.name
            )
            return value

    def get_prep_value(self, value):
        if not value:
            return value
        try:
            return get_fernet().encrypt(value.encode()).decode()
        except Exception:
            return value


# LoginSession tracks active WA module sessions (kept for audit, optional)
class LoginSession(models.Model):
    user = models.ForeignKey(
        'HRM_App.RegistrationModel',
        on_delete=models.CASCADE,
        related_name='wa_login_sessions'
    )
    jti = models.UUIDField(unique=True)
    ip_address = models.GenericIPAddressField(null=True)
    device_name = models.CharField(max_length=255, blank=True)
    browser = models.CharField(max_length=255, blank=True)
    os = models.CharField(max_length=255, blank=True)
    location_city = models.CharField(max_length=255, blank=True)
    location_country = models.CharField(max_length=255, blank=True)
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    logged_in_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.device_name} ({self.logged_in_at})"



class ContactGroup(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='contact_groups')
    name = models.CharField(max_length=100)
    color = models.CharField(max_length=20, blank=True, default='')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_contact_groups')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['whatsapp_config', 'name'], name='unique_contact_group_name_per_config'),
        ]

    def __str__(self):
        return self.name


class Contact(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, null=True, blank=True, related_name='contacts')
    name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=10, default='en')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    groups = models.ManyToManyField(ContactGroup, related_name='contacts', blank=True)
    broadcast = models.BooleanField(default=True)
    sms = models.BooleanField(default=True)
    attributes = models.JSONField(default=dict, blank=True)
    aria_user_id = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    aria_journey_stage = models.CharField(max_length=64, blank=True, null=True)
    aria_last_synced_at = models.DateTimeField(null=True, blank=True)
    assigned_to = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='assigned_contacts')
    status = models.CharField(max_length=20, choices=[('OPEN', 'Open'), ('PENDING', 'Pending'), ('SOLVED', 'Solved')], default='OPEN')
    last_message = models.TextField(null=True, blank=True)
    last_message_time = models.DateTimeField(null=True, blank=True)
    last_message_received_at = models.DateTimeField(null=True, blank=True)
    last_customer_message_time = models.DateTimeField(null=True, blank=True)
    customer_service_window_expiry = models.DateTimeField(null=True, blank=True)
    is_service_window_open = models.BooleanField(default=False)
    last_seen = models.DateTimeField(null=True, blank=True)
    unread_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'contact'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'phone_number', 'whatsapp_config'], name='unique_contact_phone_config_per_user'),
        ]
        indexes = [
            models.Index(fields=['user', 'phone_number', 'whatsapp_config']),
        ]
    
    def __str__(self):
        name = self.name or "Unnamed"
        return f"{name} ({self.phone_number})"

    @property
    def is_within_24h_window(self):
        if not self.last_customer_message_time:
            return False
        from django.utils import timezone
        import datetime
        now = timezone.now()
        is_open = now <= self.last_customer_message_time + datetime.timedelta(hours=24)
        if self.is_service_window_open != is_open:
            # Sync back to database field to ensure consistency
            Contact.objects.filter(id=self.id).update(is_service_window_open=is_open)
            self.is_service_window_open = is_open
        return is_open



class Template(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    
    name = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return str(self.name)


class Campaign(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('SCHEDULED', 'Scheduled'),
        ('RUNNING', 'Running'),
        ('SENDING', 'Sending'),
        ('SENT', 'Sent'),
        ('STOPPED', 'Stopped'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )
    
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, null=True, blank=True, related_name='campaigns')
    name = models.CharField(max_length=255)
    template = models.ForeignKey('MessageTemplate', on_delete=models.CASCADE, related_name='campaigns', null=True, blank=True)
    contacts = models.ManyToManyField(Contact, related_name='campaigns')
    variables = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    total_contacts = models.IntegerField(default=0)
    total_sent = models.IntegerField(default=0)
    total_failed = models.IntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return str(self.name)


class Message(models.Model):
    DIRECTION_CHOICES = [('INCOMING', 'Incoming'), ('OUTGOING', 'Outgoing')]
    STATUS_CHOICES = [('Sent', 'Sent'), ('Delivered', 'Delivered'), ('Read', 'Read'), ('Failed', 'Failed'), ('Waiting', 'Waiting')]
    TYPE_CHOICES = [('text', 'Text'), ('image', 'Image'), ('audio', 'Audio'), ('video', 'Video'), ('document', 'Document'), ('template', 'Template')]

    
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='messages')
    campaign = models.ForeignKey(Campaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    text = models.TextField()
    sender = models.CharField(max_length=50)
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='OUTGOING')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Waiting')
    provider_message_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='text')
    media_url = models.URLField(max_length=1000, null=True, blank=True)
    caption = models.TextField(null=True, blank=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    timestamp = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    buttons = models.JSONField(null=True, blank=True)
    button_actions = models.JSONField(default=dict, blank=True)

    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.contact.name} - {self.direction}"




class MessageTemplate(models.Model):
    CATEGORY_CHOICES = (
        ('MARKETING', 'Marketing'),
        ('UTILITY', 'Utility'),
        ('AUTHENTICATION', 'Authentication'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )

    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, null=True, blank=True, related_name='message_templates')
    name = models.CharField(max_length=255)
    language = models.CharField(max_length=20, default='en_US')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    header_type = models.CharField(max_length=20, default='NONE')
    header_text = models.CharField(max_length=60, blank=True, null=True)
    body = models.TextField()
    sample_values = models.JSONField(default=dict, blank=True)
    uploaded_preview_image = models.URLField(max_length=1000, blank=True, null=True)
    meta_media_url = models.URLField(max_length=1000, blank=True, null=True)
    header_media = models.URLField(max_length=1000, blank=True, null=True)
    footer_text = models.CharField(max_length=60, blank=True, null=True)
    buttons = models.JSONField(default=list, blank=True)
    variables = models.JSONField(default=list, blank=True)
    variables_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='message_templates', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['name', 'whatsapp_config'], name='unique_messagetemplate_name_per_config'),
        ]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['category']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return str(self.name)



class WhatsAppConfig(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='whatsapp_configs', null=True, blank=True)
    # Name or Identifier
    name = models.CharField(max_length=255, default="Default WhatsApp")

    # Flask Proxy Bot URLs & Security
    flask_bot_url = models.URLField(max_length=500, default="http://localhost:5000")
    flask_server_url = models.URLField(max_length=500, blank=True, null=True) # Legacy alias field
    flask_auth_token = models.CharField(max_length=255, default="super_secret_flask_token_123")
    flask_text_send_path = models.CharField(max_length=255, default='/send-message')
    
    # Django Webhook Receiver credentials
    crm_webhook_url = models.URLField(max_length=500, blank=True, null=True)
    crm_api_token = models.CharField(max_length=255, blank=True, null=True)
    
    # Meta Developer Portal Credentials
    whatsapp_api_token = EncryptedTextField(blank=True, null=True)
    whatsapp_api_token_start_date = models.DateField(blank=True, null=True)
    whatsapp_api_token_expire_date = models.DateField(blank=True, null=True)
    phone_number_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_business_account_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_app_id = models.CharField(max_length=100, blank=True, null=True)
    whatsapp_app_name = models.CharField(max_length=100, blank=True, null=True)
    webhook_verify_token = models.CharField(max_length=100, default="my_secret_token_123")
    
    # Google AI Assistant Engine Settings
    gemini_api_key = EncryptedCharField(max_length=255, blank=True, null=True)
    is_ai_enabled = models.BooleanField(default=True)

    # Auto-send template settings
    auto_send_template = models.BooleanField(default=False)
    auto_send_template_name = models.CharField(max_length=255, blank=True, null=True)
    
    # Meta Verification Status
    verification_status = models.CharField(
        max_length=20,
        choices=[('VERIFIED', 'Verified'), ('NOT_VERIFIED', 'Not Verified'), ('UNKNOWN', 'Unknown')],
        default='UNKNOWN'
    )
    last_checked_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'WhatsApp Configuration'
        verbose_name_plural = 'WhatsApp Configurations'

    @classmethod
    def get_solo(cls):
        """
        Singleton retrieval method. Returns first config or gets/creates id=1.
        """
        obj = cls.objects.order_by('id').first()
        if not obj:
            obj, created = cls.objects.get_or_create(id=1, defaults={'name': 'Default WhatsApp'})
        return obj

    def save(self, *args, **kwargs):
        """
        Sync flask_server_url legacy field with flask_bot_url.
        """
        if self.flask_bot_url and not self.flask_server_url:
            self.flask_server_url = self.flask_bot_url
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.name)



STATUS_CHOICES = [
    ('PENDING_REVIEW', 'Pending Review'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
    ('PAUSED', 'Paused'),
    ('DISABLED', 'Disabled'),
]

class WhatsAppTemplate(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, null=True, blank=True, related_name='whatsapp_templates')
    template_name = models.CharField(max_length=255)
    language = models.CharField(max_length=20, default='en')
    category = models.CharField(max_length=50, blank=True, default='MARKETING')
    
    header_type = models.CharField(max_length=20, default='NONE')
    header_text = models.CharField(max_length=60, blank=True, null=True)
    body_text = models.TextField()
    sample_values = models.JSONField(default=dict, blank=True)
    uploaded_preview_image = models.URLField(max_length=1000, blank=True, null=True)
    meta_media_url = models.URLField(max_length=1000, blank=True, null=True)
    header_media = models.URLField(max_length=1000, blank=True, null=True)
    footer_text = models.CharField(max_length=60, blank=True, null=True)
    
    # Buttons (Stored as JSON)
    buttons = models.JSONField(default=list, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    rejection_reason = models.TextField(blank=True, null=True)
    
    last_synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_synced_at']
        constraints = [
            models.UniqueConstraint(fields=['template_name', 'whatsapp_config'], name='unique_whatsapptemplate_name_per_config'),
        ]
        indexes = [
            models.Index(fields=['template_name']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.template_name} ({self.language}) - {self.status}"


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = (
        ('new_message', 'New Message'),
        ('unread_message', 'Unread Message'),
        ('message_read', 'Message Read'),
        ('system_alert', 'System Alert'),
        ('agent_assigned', 'Agent Assigned'),
    )

    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='notifications',
        null=True, blank=True,
        help_text='Null means broadcast to all agents'
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPE_CHOICES, default='new_message')
    title = models.CharField(max_length=255)
    message = models.TextField()
    contact_phone = models.CharField(max_length=30, blank=True, null=True)
    contact_name = models.CharField(max_length=255, blank=True, null=True)
    message_id = models.CharField(max_length=255, blank=True, null=True, help_text='Provider message ID for deduplication')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_read', 'created_at']),
            models.Index(fields=['contact_phone']),
            models.Index(fields=['message_id']),
        ]
        # Prevent duplicate notifications for the same message event
        constraints = [
            models.UniqueConstraint(
                fields=['message_id', 'notification_type'],
                condition=models.Q(message_id__isnull=False),
                name='unique_notification_per_message'
            )
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} â€” {self.created_at:%Y-%m-%d %H:%M}"


class Category(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Config: {self.whatsapp_config_id})"


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Sub Categories"
        ordering = ['name']

    def __str__(self):
        return f"{self.category.name} -> {self.name}"


class Product(models.Model):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image_url = models.URLField(max_length=1000, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    meta_product_id = models.CharField(max_length=255, blank=True, null=True)
    sync_status = models.CharField(max_length=50, choices=[('pending', 'Pending'), ('synced', 'Synced'), ('failed', 'Failed')], default='pending')
    last_sync_time = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class AutoReply(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='autoreplies')
    keywords = models.TextField(help_text="Comma-separated list of keywords")
    reply_text = models.TextField()
    media = models.FileField(upload_to='autoreplies/', blank=True, null=True, help_text="Optional media (e.g. PDF, image) to send with the auto-reply")
    buttons = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Auto Replies"
        ordering = ['-created_at']

    def __str__(self):
        return f"Keywords: {self.keywords[:30]}... (Active: {self.is_active})"

class AIConfig(models.Model):
    whatsapp_config = models.OneToOneField('WhatsAppConfig', on_delete=models.CASCADE, related_name='ai_config')
    assistant_name = models.CharField(max_length=100, default='AI Assistant')
    business_name = models.CharField(max_length=100, default='My Business')
    personality = models.CharField(max_length=100, default='Support')
    tone = models.CharField(max_length=100, default='Friendly')
    primary_language = models.CharField(max_length=20, default='en')
    
    prompt = models.TextField(blank=True, null=True)
    system_prompt = models.TextField(blank=True, null=True)
    
    conversation_behaviours = models.JSONField(default=list, blank=True)
    lead_collection = models.JSONField(default=list, blank=True)
    auto_replies = models.JSONField(default=list, blank=True)
    websites = models.JSONField(default=list, blank=True)
    faqs = models.JSONField(default=list, blank=True)
    
    context_window_size = models.IntegerField(default=15)
    fallback_rule = models.CharField(max_length=50, default='transfer')
    confidence_threshold = models.IntegerField(default=70)
    human_handoff_alert = models.BooleanField(default=True)
    
    primary_color = models.CharField(max_length=20, default='#6366f1')
    widget_position = models.CharField(max_length=20, default='right')
    
    # User Freedom LLM Configuration
    llm_provider = models.CharField(max_length=50, default='openai')
    model_name = models.CharField(max_length=100, default='gpt-4o-mini')
    api_key = models.CharField(max_length=255, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "AI Configurations"

    def __str__(self):
        return f"AI Config for {self.whatsapp_config}"

class KnowledgeDocument(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='knowledge_documents')
    file = models.FileField(upload_to='knowledge_docs/')
    file_name = models.CharField(max_length=255)
    is_processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name


class FollowUpWorkflow(models.Model):
    name = models.CharField(max_length=255)
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='follow_up_workflows')
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follow_up_workflows')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class FollowUpStep(models.Model):
    workflow = models.ForeignKey(FollowUpWorkflow, on_delete=models.CASCADE, related_name='steps')
    step_number = models.IntegerField()
    delay_seconds = models.IntegerField()
    template = models.ForeignKey('MessageTemplate', on_delete=models.CASCADE, related_name='follow_up_steps')
    media_url = models.URLField(max_length=1000, null=True, blank=True)
    template_variables = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['step_number']

    def __str__(self):
        return f"{self.workflow.name} - Step {self.step_number}"


class FollowUpContactState(models.Model):
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='follow_up_states')
    workflow = models.ForeignKey(FollowUpWorkflow, on_delete=models.CASCADE, related_name='contact_states')
    current_step = models.ForeignKey(FollowUpStep, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('COMPLETED', 'Completed'), ('CANCELLED', 'Cancelled'), ('FAILED', 'Failed')], 
        default='PENDING'
    )
    next_execution_time = models.DateTimeField()
    retry_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class ReminderCampaign(models.Model):
    name = models.CharField(max_length=255)
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='reminder_campaigns')
    event_type = models.CharField(
        max_length=20, 
        choices=[('WEBINAR', 'Webinar'), ('EVENT', 'Event'), ('MEETING', 'Meeting'), ('APPOINTMENT', 'Appointment'), ('DEMO', 'Demo'), ('CUSTOM', 'Custom')]
    )
    event_title = models.CharField(max_length=255)
    event_date_time = models.DateTimeField()
    time_zone = models.CharField(max_length=50, default='UTC')
    contacts = models.ManyToManyField(Contact, related_name='reminder_campaigns')
    is_active = models.BooleanField(default=True)
    is_interconnected = models.BooleanField(default=False)
    alternate_dates = models.JSONField(default=list, blank=True)
    conditional_rules = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    workflow_type = models.CharField(max_length=50, default='STANDARD', blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminder_campaigns')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ReminderSchedule(models.Model):
    reminder_campaign = models.ForeignKey(ReminderCampaign, on_delete=models.CASCADE, related_name='schedules')
    timing_type = models.CharField(
        max_length=50, 
        choices=[
            ('7_DAYS_BEFORE', '7 days before'),
            ('5_DAYS_BEFORE', '5 days before'),
            ('3_DAYS_BEFORE', '3 days before'),
            ('2_DAYS_BEFORE', '2 days before'),
            ('1_DAY_BEFORE', '1 day before'),
            ('6_HOURS_BEFORE', '6 hours before'),
            ('1_HOUR_BEFORE', '1 hour before'),
            ('AT_EVENT_TIME', 'At Event Date & Time'),
            ('SPECIFIC_DATETIME', 'Specific Date & Time'),
            ('CUSTOM', 'Custom timing')
        ],
        default='1_HOUR_BEFORE'
    )
    custom_minutes_before = models.IntegerField(null=True, blank=True)
    template = models.ForeignKey('MessageTemplate', on_delete=models.CASCADE, related_name='reminder_schedules', null=True, blank=True)
    media_url = models.URLField(max_length=1000, null=True, blank=True)
    template_variables = models.JSONField(default=dict, blank=True)
    button_actions = models.JSONField(default=dict, blank=True)
    message_type = models.CharField(max_length=30, default='TEMPLATE', blank=True)
    actions = models.JSONField(default=dict, blank=True)
    stage_name = models.CharField(max_length=255, default='Stage 1', blank=True)
    stage_order = models.IntegerField(default=1, blank=True)
    timeout_rule = models.JSONField(default=dict, blank=True)
    transitions = models.JSONField(default=list, blank=True)
    trigger_type = models.CharField(max_length=50, default='TIME_BEFORE', blank=True)

    def __str__(self):
        return f"{self.reminder_campaign.name} - {self.timing_type}"


class ReminderExecution(models.Model):
    reminder_campaign = models.ForeignKey(ReminderCampaign, on_delete=models.CASCADE, related_name='executions')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='reminder_executions')
    schedule = models.ForeignKey(ReminderSchedule, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(
        max_length=20, 
        choices=[('PENDING', 'Pending'), ('SENT', 'Sent'), ('FAILED', 'Failed'), ('CANCELLED', 'Cancelled'), ('DIVERTED', 'Diverted')], 
        default='PENDING'
    )
    button_response = models.CharField(max_length=255, null=True, blank=True)
    retry_count = models.IntegerField(default=0)
    execution_time = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    context_data = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=50, default='PENDING', blank=True)
    selected_event_date = models.DateTimeField(null=True, blank=True)
    timeout_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']


class AutomationLog(models.Model):
    whatsapp_config = models.ForeignKey('WhatsAppConfig', on_delete=models.CASCADE, related_name='automation_logs')
    automation_type = models.CharField(max_length=20, choices=[('FOLLOW_UP', 'Follow-up'), ('REMINDER', 'Reminder')])
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, related_name='automation_logs')
    action_type = models.CharField(max_length=20)
    details = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

