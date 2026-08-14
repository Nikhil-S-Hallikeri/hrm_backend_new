from django.urls import re_path
from whatsapp_app import consumers

websocket_urlpatterns = [
    re_path(r'^ws/crm/$', consumers.CRMConsumer.as_asgi()),
    re_path(r'^ws/chat/(?P<phone>[^/]+)/$', consumers.CRMConsumer.as_asgi()),
    re_path(r'^ws/status/(?P<user_id>\d+)/$', consumers.StatusConsumer.as_asgi()),
    re_path(r'^ws/notifications/(?P<config_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
]

