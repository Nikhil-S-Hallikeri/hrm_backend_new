from django.contrib import admin

# Register your models here.
from .models import ChatSession, ChatMessage


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ["fastapi_session_id", "lead_name", "lead_phone", "lead_interest", "lead_type", "lead_score", "status", "created_at"]
    list_filter = ["lead_type", "status"]
    search_fields = ["lead_name", "lead_phone", "lead_email", "fastapi_session_id"]
    readonly_fields = ["fastapi_session_id", "created_at", "updated_at"]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ["session", "role", "content", "created_at"]
    list_filter = ["role"]