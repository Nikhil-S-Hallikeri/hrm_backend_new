from django.contrib import admin
from .models import (
    User, Contact, Template, Campaign, Message, 
    MessageTemplate, 
    WhatsAppConfig
)

# User (RegistrationModel) is already registered in HRM_App admin.
# We do not register it again here to avoid exceptions.
# @admin.register(User)
# class UserAdmin(admin.ModelAdmin):
#     list_display = ('email', 'role', 'is_staff', 'is_active')
#     search_fields = ('email',)
#     list_filter = ('role', 'is_staff', 'is_active')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'status')
    search_fields = ('name', 'phone_number', 'email')
    list_filter = ('status',)

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('contact', 'direction', 'status', 'type', 'timestamp')
    list_filter = ('direction', 'status', 'type')
    search_fields = ('contact__name', 'text')

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'total_sent', 'created_at')
    list_filter = ('status',)

@admin.register(WhatsAppConfig)
class WhatsAppConfigAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'phone_number_id',
        'is_ai_enabled',
        'updated_at',
    )

# Register other models with default interface
admin.site.register(Template)
admin.site.register(MessageTemplate)

