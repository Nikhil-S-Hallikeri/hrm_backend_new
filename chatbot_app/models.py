from django.db import models

# Create your models here.
from django.conf import settings


class ChatSession(models.Model):
    """Links a Django user to a FastAPI chatbot session."""

    STATUS_CHOICES = [
        ("active", "Active"),
        ("ended", "Ended"),
    ]
    LEAD_TYPE_CHOICES = [
        ("Hot", "Hot"),
        ("Warm", "Warm"),
        ("Cold", "Cold"),
        ("Dead", "Dead"),
    ]

    # Link to Django user (null = anonymous visitor)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="chat_sessions",
    )

    # The session_id used by FastAPI — this is the bridge
    fastapi_session_id = models.CharField(max_length=64, unique=True, db_index=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    lead_type = models.CharField(max_length=10, choices=LEAD_TYPE_CHOICES, default="Cold")
    lead_score = models.IntegerField(default=0)
    summary = models.TextField(blank=True)

    # Captured lead fields (mirrored from FastAPI for quick Django queries)
    lead_name = models.CharField(max_length=120, blank=True)
    lead_email = models.EmailField(blank=True)
    lead_phone = models.CharField(max_length=15, blank=True)
    lead_interest = models.CharField(max_length=200, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session {self.fastapi_session_id} — {self.lead_type}"


class ChatMessage(models.Model):
    """Optional: mirror messages in Django DB for admin visibility."""

    ROLE_CHOICES = [("user", "User"), ("assistant", "Assistant")]

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]