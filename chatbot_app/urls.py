from django.urls import path
from . import views

app_name = "chatbot"

urlpatterns = [
    path("chat/", views.ChatView.as_view(), name="chat"),
    path("chat/end/", views.EndChatView.as_view(), name="end-chat"),
    path("sessions/", views.SessionListView.as_view(), name="session-list"),
    path("sessions/<str:session_id>/transcript/", views.TranscriptView.as_view(), name="transcript"),
]