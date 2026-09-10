import json
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from whatsapp_app.models import User

NOTIFICATIONS_GROUP = 'notifications_all'


class CRMConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_names = {'crm_updates'}

        phone_number = self.scope.get('url_route', {}).get('kwargs', {}).get('phone')
        if phone_number:
            normalized_phone = re.sub(r'\D', '', str(phone_number))
            if normalized_phone:
                self.room_group_names.add(f'crm_chat_{normalized_phone}')

        for room_group_name in self.room_group_names:
            await self.channel_layer.group_add(room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        for room_group_name in getattr(self, 'room_group_names', set()):
            await self.channel_layer.group_discard(room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            payload = json.loads(text_data)
        except Exception:
            return

        if payload.get('type') == 'ping':
            await self.send(text_data=json.dumps({'event': 'pong'}))

    async def crm_event(self, event):
        message = event['message']
        await self.send(text_data=json.dumps(message))


class StatusConsumer(AsyncWebsocketConsumer):
    # Class-level dictionary to track active connections per user
    active_connections = {}

    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs'].get('user_id')
        self.group_name = 'user_status'
        
        # Join group
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        if self.user_id:
            # Increment connection count
            count = StatusConsumer.active_connections.get(self.user_id, 0) + 1
            StatusConsumer.active_connections[self.user_id] = count
            
            # Only broadcast and update DB if this is the first connection
            if count == 1:
                verified_status = await self.update_user_status(self.user_id, True)
                await self.broadcast_status(self.user_id, verified_status)

    async def disconnect(self, close_code):
        if hasattr(self, 'user_id') and self.user_id:
            # Decrement connection count
            count = StatusConsumer.active_connections.get(self.user_id, 1) - 1
            if count <= 0:
                if self.user_id in StatusConsumer.active_connections:
                    del StatusConsumer.active_connections[self.user_id]
                
                # NOTE: We no longer set is_online=False on disconnect.
                # This ensures the indicator stays green until the user explicitly logs out,
                # as requested. We still broadcast a 'ping' or similar if needed, 
                # but we keep the online status persistent.
                pass
            else:
                StatusConsumer.active_connections[self.user_id] = count
            
        # Leave group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def update_user_status(self, user_id, is_online):
        try:
            from whatsapp_app.models import LoginSession
            # If we are trying to set them online, check if they have at least one active session
            if is_online:
                has_active_session = LoginSession.objects.filter(user_id=user_id, is_active=True).exists()
                if not has_active_session:
                    is_online = False
            
            User.objects.filter(id=user_id).update(
                is_online=is_online,
                last_seen=timezone.now()
            )
            return is_online
        except Exception:
            return is_online

    async def broadcast_status(self, user_id, is_online):
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'status_update',
                'message': {
                    'user_id': int(user_id),
                    'is_online': is_online,
                    'last_seen': timezone.now().isoformat()
                }
            }
        )

    async def status_update(self, event):
        # This sends the message to the client
        await self.send(text_data=json.dumps(event['message']))


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Per-agent WebSocket consumer for real-time notifications.
    Agents join a scoped group 'notifications_config_<id>' so that
    they only receive notifications for their active WhatsApp config.
    """

    async def connect(self):
        self.config_id = self.scope.get('url_route', {}).get('kwargs', {}).get('config_id')
        if not self.config_id:
            await self.close()
            return
            
        self.group_name = f'notifications_config_{self.config_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial unread count so the badge is correct immediately on connect
        unread_count = await self.get_unread_count(self.config_id)
        await self.send(text_data=json.dumps({
            'event': 'unread_count_update',
            'count': unread_count,
            'whatsapp_config_id': self.config_id
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle pings from the frontend keepalive."""
        try:
            payload = json.loads(text_data)
        except Exception:
            return
        if payload.get('type') == 'ping':
            await self.send(text_data=json.dumps({'event': 'pong'}))

    # â”€â”€ Channel layer event handlers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    async def notification_event(self, event):
        """Relay any notification event directly to the WebSocket client."""
        await self.send(text_data=json.dumps(event['data']))

    # â”€â”€ DB helpers â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    @database_sync_to_async
    def get_unread_count(self, config_id):
        from whatsapp_app.models import Notification
        return Notification.objects.filter(whatsapp_config_id=config_id, is_read=False).count()

