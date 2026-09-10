import re
import threading
import requests
import logging
import os
from django.db import transaction
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.conf import settings
from whatsapp_app.models import Contact, Message, Notification
from whatsapp_app.utils import get_whatsapp_headers

logger = logging.getLogger(__name__)

def _async_send_campaign(phone, name):
    headers, flask_url = get_whatsapp_headers()
    endpoint = f"{flask_url}/api/campaigns/send"
    
    import uuid
    provider_message_id = str(uuid.uuid4())

    payload = {
        "phone": phone,
        "template_name": "welcome_message",
        "language_code": "en_US",
        "provider_message_id": provider_message_id,
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": name}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=15)
        if response.status_code in [200, 201]:
            # If Flask returns provider_message_id or other data, log it for traceability
            try:
                resp_json = response.json()
                returned_id = resp_json.get('provider_message_id') or resp_json.get('message_id') or resp_json.get('id')
                logger.info(f"Successfully triggered async welcome campaign for contact: {name} ({phone}), provider_id={returned_id}")
            except Exception:
                logger.info(f"Successfully triggered async welcome campaign for contact: {name} ({phone})")
        else:
            logger.error(f"Flask bot campaign endpoint returned status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        logger.error(f"Failed to connect to Flask bot campaign endpoint for async contact welcomer: {str(e)}")

# Disabled welcome templates automation based on WARM/HOT lead status - not needed for this project
# @receiver(post_save, sender=Contact)
# def trigger_warm_hot_lead_campaign(sender, instance, created, **kwargs):
#     status_upper = str(instance.status).upper()
#     
#     should_trigger = False
#     
#     if created:
#         if status_upper in ['WARM', 'HOT']:
#             should_trigger = True
#     else:
#         # Check if status has transitioned to HOT
#         # We fetch the original state from DB to compare
#         try:
#             original = Contact.objects.get(pk=instance.pk)
#             if original.status.upper() != 'HOT' and status_upper == 'HOT':
#                 should_trigger = True
#         except Contact.DoesNotExist:
#             pass
# 
#     if should_trigger and instance.phone_number:
#         # 1. Strip non-numeric characters for Meta compliance
#         clean_phone = re.sub(r'\D', '', str(instance.phone_number))
#         if not clean_phone:
#             return
# 
#         # Handle Indian prefixing or basic length formatting
#         if len(clean_phone) == 10:
#             clean_phone = f"91{clean_phone}"
#         elif clean_phone.startswith('0') and len(clean_phone) == 11:
#             clean_phone = f"91{clean_phone[1:]}"
#         
#         # 2. Trigger asynchronously in a separate Thread to prevent blocking
#         threading.Thread(
#             target=_async_send_campaign,
#             args=(clean_phone, instance.name),
#             daemon=True
#         ).start()


@receiver(post_save, sender=Contact)
def sync_new_contact_to_crm(sender, instance, created, **kwargs):
    if created:
        def _sync_after_commit():
            try:
                from whatsapp_app.utils import _broadcast_crm_event
                _broadcast_crm_event('new_contact', contact=instance)
            except Exception as e:
                logger.error(f"Failed to broadcast new_contact event for CRM: {str(e)}")

        # Deferred to transaction.on_commit: bulk uploads and campaign draft/launch
        # creates wrap Contact creation in transaction.atomic(). Firing the webhook
        # synchronously here (pre-commit) meant a later row failing/rolling back the
        # same transaction still left CRM believing already-broadcast contacts exist,
        # even though they were never actually persisted. on_commit runs immediately
        # when there's no open transaction, so single-add behavior is unchanged.
        transaction.on_commit(_sync_after_commit)


@receiver(post_save, sender=Message)
def log_message_activity(sender, instance, created, **kwargs):
    """
    Signal receiver to log all WhatsApp message activities (INCOMING and OUTGOING)
    to a dedicated 'whatsapp_messages.log' file.
    """
    try:
        log_file_path = os.path.join(str(settings.BASE_DIR), 'whatsapp_messages.log')
        
        # Extract details
        msg_id = instance.id
        direction = instance.direction
        msg_type = instance.type
        status = instance.status
        provider_id = instance.provider_message_id or "N/A"
        from django.utils import timezone
        timestamp = instance.timestamp or instance.created_at or timezone.now()
        text = instance.text
        
        contact_name = instance.contact.name or "Unknown"
        contact_phone = instance.contact.phone_number
        
        if direction == 'INCOMING':
            sent_by = f"Customer: {contact_phone} ({contact_name})"
            recipient = f"System (Config ID: {instance.contact.whatsapp_config_id})"
        else:
            agent_sender = instance.sender or "agent"
            sent_by = f"Agent/System (Sender: '{agent_sender}')"
            recipient = f"Customer: {contact_phone} ({contact_name})"

        log_line = (
            f"========================================================================\n"
            f"TIMESTAMP: {timestamp}\n"
            f"EVENT: {'[NEW MESSAGE SAVED]' if created else '[MESSAGE STATUS UPDATED]'}\n"
            f"DIRECTION: {direction}\n"
            f"MESSAGE TYPE: {msg_type}\n"
            f"STATUS: {status}\n"
            f"PROVIDER ID: {provider_id}\n"
            f"DATABASE TABLE: whatsapp_message\n"
            f"RECORD ID: {msg_id}\n"
            f"SENT BY: {sent_by}\n"
            f"RECIPIENT: {recipient}\n"
            f"CONTENT: {text}\n"
        )
        if instance.media_url:
            log_line += f"MEDIA URL: {instance.media_url}\n"
        log_line += "========================================================================\n\n"

        with open(log_file_path, 'a', encoding='utf-8') as f:
            f.write(log_line)
    except Exception as e:
        logger.error(f"Error logging message activity in signal: {str(e)}")


@receiver(pre_delete, sender=Contact)
def on_contact_delete(sender, instance, **kwargs):
    """
    Pre-delete signal for Contact:
    Cleans up related notifications before the contact is deleted.
    """
    logger.info(f"Cleaning up notifications for contact ID {instance.id} (Phone: {instance.phone_number})")
    Notification.objects.filter(
        contact_phone=instance.phone_number,
        whatsapp_config=instance.whatsapp_config
    ).delete()


