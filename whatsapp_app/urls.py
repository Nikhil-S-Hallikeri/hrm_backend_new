from django.urls import path
from rest_framework.routers import DefaultRouter

from whatsapp_app.views import (
    LoginViewSet,
    SignupViewSet,
    VerifySignupViewSet,
    ForgotPasswordViewSet,
    ResetPasswordViewSet,
    ChangePasswordViewSet,
    LogoutViewSet,
    UserPreferencesViewSet,
    LoginSessionViewSet,
    ContactViewSet,
    ContactGroupViewSet,
    TemplateViewSet,
    CampaignViewSet,
    MessageViewSet,
    MessageTemplateViewSet,
    DashboardViewSet,
    InboxViewSet,
    WebhookEventViewSet,
    SendMessageViewSet,
    SendWhatsAppTemplateView,
    SyncApprovedTemplatesView,
    WhatsAppConfigViewSet,
    NotificationViewSet,
    CategoryViewSet,
    SubCategoryViewSet,
    AutoReplyViewSet,
    ProductViewSet,
    KnowledgeDocumentViewSet,
    GeneratePromptView,
    ImprovePromptView,
    AIConfigView,
    AITestMessageView,
    AIConfigTestConnectionView,
    KnowledgeRebuildView,
    VideoCallInitiateView,
    FollowUpWorkflowViewSet,
    ReminderCampaignViewSet,
    PublicCampaignDetailView,
    PublicCampaignSubmitLeadView,
    CandidateRegistrationView,
    LeadsBulkWhatsAppSendView,   # HRM Leads → WhatsApp bulk send (NEW)
)


router = DefaultRouter()
router.register('dashboard', DashboardViewSet, basename='dashboard')
router.register('inbox', InboxViewSet, basename='inbox')
router.register('users', UserPreferencesViewSet, basename='users')
router.register('auth/change-password', ChangePasswordViewSet, basename='auth-change-password')
router.register('auth/sessions', LoginSessionViewSet, basename='auth-sessions')
router.register('contacts', ContactViewSet, basename='contacts')
router.register('contact-groups', ContactGroupViewSet, basename='contact-groups')

router.register('templates', MessageTemplateViewSet, basename='templates')
router.register('whatsapp-templates', MessageTemplateViewSet, basename='whatsapp-templates')
router.register('legacy-templates', TemplateViewSet, basename='legacy-templates')
router.register('campaigns', CampaignViewSet, basename='campaigns')
router.register('messages', MessageViewSet, basename='messages')
router.register('whatsapp/config', WhatsAppConfigViewSet, basename='whatsapp-config')
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('categories', CategoryViewSet, basename='categories')
router.register('subcategories', SubCategoryViewSet, basename='subcategories')
router.register('products', ProductViewSet, basename='products')
router.register('autoreplies', AutoReplyViewSet, basename='autoreplies')
router.register('knowledge-documents', KnowledgeDocumentViewSet, basename='knowledge-documents')
router.register('follow-ups', FollowUpWorkflowViewSet, basename='follow-ups')
router.register('reminders', ReminderCampaignViewSet, basename='reminders')

urlpatterns = [
    path('public/campaign/<str:user_name>/<str:campaign_name>/', PublicCampaignDetailView.as_view(), name='public-campaign-detail'),
    path('public/campaign/submit-lead/', PublicCampaignSubmitLeadView.as_view(), name='public-campaign-submit-lead'),
    path('whatsapp/candidate-registration/', CandidateRegistrationView.as_view(), name='candidate-registration'),
    path('create/draft/', CampaignViewSet.as_view({'post': 'create_draft'}), name='campaigns-create-draft'),
    path('create/crm_launch/', CampaignViewSet.as_view({'post': 'crm_launch'}), name='campaigns-crm-launch'),
    path('auth/login/', LoginViewSet.as_view({'post': 'create'}), name='auth-login'),
    path('auth/logout/', LogoutViewSet.as_view({'post': 'create'}), name='auth-logout'),
    path('auth/signup/', SignupViewSet.as_view({'post': 'create'}), name='auth-signup'),
    path('auth/signup/verify/', VerifySignupViewSet.as_view({'post': 'create'}), name='auth-signup-verify'),
    path('auth/forgot-password/', ForgotPasswordViewSet.as_view({'post': 'create'}), name='auth-forgot-password'),
    path('auth/reset-password/', ResetPasswordViewSet.as_view({'post': 'create'}), name='auth-reset-password'),
    path('whatsapp/events/', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'}), name='whatsapp-webhook-events'),
    path('whatsapp/events', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'})),
    path('api/whatsapp/events/', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'}), name='api-whatsapp-webhook-events'),
    path('api/whatsapp/events', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'})),
    path('whatsapp/webhook/', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'}), name='whatsapp-webhook-legacy'),
    path('whatsapp/webhook', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'})),
    path('api/whatsapp/webhook/', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'})),
    path('api/whatsapp/webhook', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'})),
    path('webhook/', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'}), name='whatsapp-webhook-root'),
    path('webhook', WebhookEventViewSet.as_view({'get': 'verify', 'post': 'events'})),
    path('whatsapp/webhook/messages/', WebhookEventViewSet.as_view({'post': 'create'}), name='webhook-event'),
    path('whatsapp/webhook/messages', WebhookEventViewSet.as_view({'post': 'create'})),
    path('whatsapp/send-message/', SendMessageViewSet.as_view({'post': 'create'}), name='send-message'),
    path('whatsapp/send-template/', SendWhatsAppTemplateView.as_view(), name='send-template'),
    path('whatsapp/templates/sync/', SyncApprovedTemplatesView.as_view(), name='sync-templates'),
    # Aliases from source project
    path('send-message/', SendMessageViewSet.as_view({'post': 'create'}), name='send-message-alias'),
    path('send-template/', SendWhatsAppTemplateView.as_view(), name='send-template-alias'),
    path('whatsapp/sync-templates/', SyncApprovedTemplatesView.as_view(), name='whatsapp-sync-templates-alias'),
    path('whatsapp/ai-config/', AIConfigView.as_view(), name='ai-config'),
    path('whatsapp/ai-config/test-message/', AITestMessageView.as_view(), name='ai-config-test-message'),
    path('whatsapp/ai-config/test-connection/', AIConfigTestConnectionView.as_view(), name='ai-config-test-connection'),
    path('whatsapp/ai-prompt/generate/', GeneratePromptView.as_view(), name='ai-prompt-generate'),
    path('whatsapp/ai-prompt/improve/', ImprovePromptView.as_view(), name='ai-prompt-improve'),
    path('whatsapp/knowledge/rebuild/', KnowledgeRebuildView.as_view(), name='knowledge-rebuild'),
    path('messages/<str:phone>/', MessageViewSet.as_view({'get': 'by_phone'}), name='messages-by-phone'),
    path('video-call/initiate/', VideoCallInitiateView.as_view(), name='video-call-initiate'),
    path('api/reminders/', ReminderCampaignViewSet.as_view({'get': 'list', 'post': 'create'}), name='api-reminders-list'),
    path('api/reminders/<int:pk>/', ReminderCampaignViewSet.as_view({'get': 'retrieve', 'put': 'update', 'patch': 'partial_update', 'delete': 'destroy'}), name='api-reminders-detail'),

    # ── HRM Leads → WhatsApp Bulk Send (NEW) ─────────────────────────────────
    path('leads/send-whatsapp/', LeadsBulkWhatsAppSendView.as_view(), name='leads-bulk-wa-send'),
    # ──────────────────────────────────────────────────────────────
]

urlpatterns += router.urls

