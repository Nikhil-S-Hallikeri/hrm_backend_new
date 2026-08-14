import requests
import logging
import uuid
import re
from typing import Any
from django.conf import settings
from whatsapp_app.utils import get_whatsapp_config, get_whatsapp_headers

logger = logging.getLogger(__name__)

def upload_bytes_to_meta(file_bytes, file_name, mime_type, waba_config):
    """
    Directly uploads raw file bytes to Meta's Resumable Upload API.
    Returns the h: handle string on success.
    """
    file_size = len(file_bytes)
    app_id = waba_config.get('config_obj').whatsapp_app_id if waba_config.get('config_obj') else None
    whatsapp_token = waba_config.get('whatsapp_token')

    if not app_id or app_id == "your_app_id_here":
        raise ValueError(
            "WHATSAPP_APP_ID is not configured. Please register the App ID in your WhatsApp Configuration panel."
        )

    # Step 1: Initiate upload session with Meta
    session_url = f"https://graph.facebook.com/v20.0/{app_id}/uploads"
    session_resp = requests.post(
        session_url,
        headers={"Authorization": f"Bearer {whatsapp_token}"},
        params={
            "file_length": file_size,
            "file_type": mime_type,
            "file_name": file_name
        },
        timeout=15
    )
    if not session_resp.ok:
        raise ValueError(f"Meta Upload Session failed ({session_resp.status_code}): {session_resp.text}")
    
    session_id = session_resp.json().get("id")
    if not session_id:
        raise ValueError("Meta did not return an upload session ID.")

    # Step 2: Upload the file bytes
    upload_url = f"https://graph.facebook.com/v20.0/{session_id}"
    upload_resp = requests.post(
        upload_url,
        headers={
            "Authorization": f"OAuth {whatsapp_token}",
            "file_offset": "0",
            "Content-Type": mime_type
        },
        data=file_bytes,
        timeout=60
    )
    upload_resp.raise_for_status()
    handle = upload_resp.json().get("h")
    if not handle:
        raise ValueError("Meta did not return a media upload handle.")

    return handle

def upload_media_to_meta(media_url, mime_type="image/jpeg", waba_config=None):
    """
    Downloads media from a public URL then uploads it natively to Meta.
    Returns the h: handle string.
    """
    file_response = requests.get(media_url, timeout=30)
    file_response.raise_for_status()
    file_bytes = file_response.content

    file_name = media_url.split("/")[-1].split("?")[0] or "media_upload"
    if "." not in file_name:
        ext_map = {
            "image/jpeg": "jpg", "image/png": "png",
            "video/mp4": "mp4", "application/pdf": "pdf"
        }
        file_name = f"upload.{ext_map.get(mime_type, 'bin')}"

    return upload_bytes_to_meta(file_bytes, file_name, mime_type, waba_config)

def upload_media_for_message(file_bytes, file_name, mime_type, waba_config):
    """
    Uploads a file to Meta's Media API and returns the media ID.
    Used for sending messages/templates with media from a local server.
    """
    phone_number_id = waba_config.get('phone_id')
    whatsapp_token = waba_config.get('whatsapp_token')

    if not phone_number_id or not whatsapp_token:
        raise ValueError("Missing phone_number_id or whatsapp_token in WhatsApp Config.")

    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/media"
    
    files = {
        'file': (file_name, file_bytes, mime_type)
    }
    data = {
        'messaging_product': 'whatsapp'
    }
    headers = {
        "Authorization": f"Bearer {whatsapp_token}"
    }
    
    response = requests.post(url, headers=headers, data=data, files=files, timeout=30)
    
    if not response.ok:
        logger.error(f"Meta Media Upload Failed: {response.status_code} {response.text}")
        response.raise_for_status()
        
    media_id = response.json().get("id")
    if not media_id:
        raise ValueError("Meta did not return a media ID.")
        
    return media_id

def upload_template_media_for_sending(media_url, waba_config):
    """
    Downloads media from a template's media URL (preview image, stored media, etc.)
    and uploads it to Meta's Media API to get a media_id.
    
    IMPORTANT: This function only accepts HTTP(S) URLs. Data URLs and blob URLs are not supported.
    Use upload_bytes_to_meta() for file uploads instead.
    """
    # Prevent processing data: URLs (they should never reach here)
    if media_url.startswith('data:'):
        raise ValueError(
            "Data URLs are not supported for media upload. "
            "Please use the file upload interface instead of Data URLs."
        )
    
    if not media_url.startswith('http://') and not media_url.startswith('https://'):
        raise ValueError(
            f"Invalid media URL scheme. Only HTTP(S) URLs are supported, got: {media_url[:30]}"
        )
    
    logger.info(f"Downloading template media from URL: {media_url}")
    try:
        file_response = requests.get(media_url, timeout=30)
        file_response.raise_for_status()
        file_bytes = file_response.content
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to download media from URL: {e}")
        raise ValueError(f"Failed to download media: {str(e)}")

    # Get MIME type from headers or fallback
    mime_type = file_response.headers.get("Content-Type")
    if not mime_type or ";" in mime_type:
        mime_type = mime_type.split(";")[0].strip() if mime_type else "image/jpeg"

    # Determine filename
    file_name = media_url.split("/")[-1].split("?")[0] or "media_upload"
    if "." not in file_name:
        ext_map = {
            "image/jpeg": "jpg", 
            "image/png": "png",
            "image/gif": "gif",
            "image/webp": "webp",
            "video/mp4": "mp4", 
            "application/pdf": "pdf",
            "application/msword": "doc",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx"
        }
        ext = ext_map.get(mime_type)
        if not ext:
            import mimetypes
            ext = mimetypes.guess_extension(mime_type) or ".bin"
            ext = ext.lstrip(".")
        file_name = f"upload.{ext}"

    logger.info(f"Uploading downloaded template media to Meta. Filename: {file_name}, Mime-type: {mime_type}")
    return upload_media_for_message(file_bytes, file_name, mime_type, waba_config)

def send_whatsapp_message_direct_to_meta(recipient_id, waba_config, text=None, template_name=None, language_code="en_US", components=None, media_url=None, media_type=None, filename=None, interactive=None):
    """
    Constructs and dispatches payload directly to Meta Graph API.
    Handles self-healing retries for Meta button index mismatches.
    In local development mode (DEBUG=True), simulates successful responses.
    """
    recipient_id = re.sub(r'\D', '', str(recipient_id).strip())
    if len(recipient_id) == 10:
        recipient_id = f"91{recipient_id}"
        
    phone_number_id = waba_config.get('phone_id')
    whatsapp_token = waba_config.get('whatsapp_token')
    
    # Check if running in DEBUG mode (local development)
    is_debug = getattr(settings, 'DEBUG', False)

    if not phone_number_id or not whatsapp_token:
        logger.warning(f"Missing WhatsApp credentials (Phone ID: {phone_number_id}, Token: {'*' * 4 if whatsapp_token else 'None'})")
        
        # In local development mode, simulate a successful Meta API response
        if is_debug:
            logger.info(f"[LOCAL DEV MODE] Simulating successful template send to {recipient_id}")
            return {
                "messages": [
                    {
                        "id": f"wamid.{str(uuid.uuid4())[:16]}",
                        "message_status": "accepted"
                    }
                ],
                "contacts": [{"input": recipient_id, "wa_id": recipient_id.replace("+", "")}]
            }, 200
        
        logger.error("Missing phone_number_id or whatsapp_token in WhatsApp Config.")
        return {"error": "Missing essential Meta credentials. Please configure WhatsApp API credentials in the admin panel."}, 400

    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {whatsapp_token}",
        "Content-Type": "application/json"
    }

    # Base payload structure
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": recipient_id
    }

    # Format 1: Template Message
    if template_name:
        template_payload = {
            "name": template_name,
            "language": {"code": language_code}
        }
        if components:
            sanitized_components = []
            for comp in components:
                if not isinstance(comp, dict):
                    continue
                comp_type = str(comp.get("type", "")).lower()
                if comp_type not in ["header", "body", "button", "buttons", "footer"]:
                    continue
                
                # Singular normalization
                if comp.get("type") == "buttons":
                    comp["type"] = "button"
                if "buttons" in comp and "parameters" not in comp:
                    comp["parameters"] = comp.pop("buttons")

                # Filter out components with no parameters (Meta rejects empty parameter lists)
                params = comp.get("parameters")
                if not params or not isinstance(params, list) or len(params) == 0:
                    continue

                sanitized_components.append(comp)
            if sanitized_components:
                template_payload["components"] = sanitized_components
        payload["type"] = "template"
        payload["template"] = template_payload

    # Format 2: Dynamic Interactive Buttons/Lists
    elif interactive:
        payload["type"] = "interactive"
        payload["interactive"] = interactive

    # Format 3: Rich Media Link Attachments
    elif media_url and media_type in ["image", "video", "document"]:
        payload["type"] = media_type
        media_payload = {"link": media_url}
        if text:
            media_payload["caption"] = text
        if media_type == "document" and filename:
            media_payload["filename"] = filename
        payload[media_type] = media_payload

    # Format 4: Standard Plain Text Message
    else:
        payload["type"] = "text"
        payload["text"] = {"preview_url": False, "body": text or ""}

    try:
        try:
            from django.utils import timezone
            import json
            with open('webhook_debug.log', 'a') as f_log:
                f_log.write(f"\n--- Direct Meta Send Request at {timezone.now()} ---\n")
                f_log.write(f"URL: {url}\n")
                f_log.write(f"Payload: {json.dumps(payload, indent=2)}\n")
        except Exception:
            pass

        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response_json = response.json() if response.content else {}

        try:
            import json
            with open('webhook_debug.log', 'a') as f_log:
                f_log.write(f"Response ({response.status_code}): {json.dumps(response_json, indent=2)}\n")
        except Exception:
            pass

        # Self-healing retry for template button index errors (Meta Error 132018)
        if response.status_code == 400 and template_name and components:
            error_info = response_json.get("error", {})
            err_msg = error_info.get("message", "")
            err_data = error_info.get("error_data", {})
            details = err_data.get("details", "") if isinstance(err_data, dict) else ""
            
            if "does not require parameters" in details or "does not require parameters" in err_msg:
                match = re.search(r"Button at index (\d+)", details or err_msg, re.IGNORECASE)
                cleaned_components = []
                removed_any = False
                active_components = payload["template"].get("components", [])
                
                if match:
                    target_idx = int(match.group(1))
                    for comp in active_components:
                        if comp.get("type") == "button" and str(comp.get("index")) == str(target_idx):
                            removed_any = True
                            continue
                        cleaned_components.append(comp)
                else:
                    for comp in active_components:
                        if comp.get("type") == "button":
                            removed_any = True
                            continue
                        cleaned_components.append(comp)

                if removed_any:
                    payload["template"]["components"] = cleaned_components
                    response = requests.post(url, headers=headers, json=payload, timeout=15)
                    response_json = response.json() if response.content else {}

        return response_json, response.status_code
    except Exception as e:
        logger.error(f"Failed to post native message event: {e}")
        return {"error": "Connection timed out", "details": str(e)}, 500


def send_whatsapp_message(phone, message, media_url=None, buttons=None, message_type='text', config=None):
    """
    Natively sends message to customer directly via Meta Cloud API, maintaining
    exact signature and return codes expected by CRM view modules.
    """
    try:
        if config:
            if isinstance(config, (int, str)):
                waba_config = get_whatsapp_config(config_id=config)
            else:
                waba_config = get_whatsapp_config(config_id=config.id)
        else:
            waba_config = get_whatsapp_config()
        provider_message_id = str(uuid.uuid4())

        # Determine structural payload
        interactive = None
        if message_type == 'interactive' and buttons:
            interactive = buttons
        elif buttons and isinstance(buttons, list) and len(buttons) > 0:
            # Reformat plain list into standard reply buttons for dynamic responses
            btn_array = []
            for idx, raw_val in enumerate(buttons):
                btn_array.append({
                    "type": "reply",
                    "reply": {"id": f"btn_opt_{idx}", "title": str(raw_val)[:20]}
                })
            interactive = {
                "type": "button",
                "body": {"text": message[:1024]},
                "action": {"buttons": btn_array}
            }

        # Determine media_type automatically if media_url is present
        effective_media_type = message_type if message_type in ['image', 'video', 'document'] else None
        filename = None
        if media_url and not effective_media_type:
            m_lower = media_url.lower()
            if any(m_lower.endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')):
                effective_media_type = 'image'
            elif any(m_lower.endswith(ext) for ext in ('.mp4', '.mov', '.avi', '.webm', '.mkv')):
                effective_media_type = 'video'
            else:
                effective_media_type = 'document'
                filename = media_url.split('/')[-1]

        resp_json, status_code = send_whatsapp_message_direct_to_meta(
            recipient_id=phone,
            waba_config=waba_config,
            text=message,
            media_url=media_url,
            media_type=effective_media_type,
            filename=filename,
            interactive=interactive
        )

        if status_code in [200, 201]:
            logger.info(f"Successfully sent native message to {phone}.")
            if isinstance(resp_json, dict):
                real_id = None
                if isinstance(resp_json.get('messages'), list) and resp_json['messages']:
                    real_id = resp_json['messages'][0].get('id')
                resp_json.setdefault('provider_message_id', real_id or provider_message_id)
            return True, resp_json
        else:
            logger.error(f"Meta rejected message. Code: {status_code}, Body: {resp_json}")
            return False, {"error": "Meta API Rejected", "details": resp_json}

    except Exception as e:
        logger.error(f"Error natively sending message: {e}")
        return False, {"error": "Internal direct send error", "details": str(e)}


def create_whatsapp_template(template_data, config_id=None):
    """
    Directly creates and registers a message template with Meta Cloud API.
    Matches the existing structure expected by message-template views.
    """
    try:
        waba_config = get_whatsapp_config(config_id)
        whatsapp_token = waba_config.get('whatsapp_token')
        waba_id = waba_config.get('config_obj').whatsapp_business_account_id if waba_config.get('config_obj') else None

        if not waba_id or waba_id == "your_waba_id_here":
            return False, {"error": "Missing WHATSAPP_BUSINESS_ACCOUNT_ID in config."}

        url = f"https://graph.facebook.com/v20.0/{waba_id}/message_templates"
        headers = {
            "Authorization": f"Bearer {whatsapp_token}",
            "Content-Type": "application/json"
        }

        # Resolve public media URLs inline
        MEDIA_FORMATS = {"IMAGE": "image/jpeg", "VIDEO": "video/mp4", "DOCUMENT": "application/pdf"}
        for component in template_data.get("components", []):
            if component.get("type", "").upper() != "HEADER":
                continue
            fmt = component.get("format", "").upper()
            if fmt not in MEDIA_FORMATS:
                continue

            example = component.get("example", {})
            handles = example.get("header_handle", [])
            handle_value = handles[0] if handles else ""
            is_url = isinstance(handle_value, str) and handle_value.startswith("http")
            is_data_url = isinstance(handle_value, str) and handle_value.startswith("data:")
            is_missing = not handle_value
            fallback_url = component.get("media_url", "")

            try:
                if is_data_url:
                    import base64
                    # data:[<mediatype>][;base64],<data>
                    header_parts = handle_value.split(',', 1)
                    if len(header_parts) != 2:
                        raise ValueError('Invalid data URL for header')
                    meta_info = header_parts[0]
                    b64_data = header_parts[1]
                    mime = 'image/jpeg'
                    if ':' in meta_info and ';' in meta_info:
                        mime = meta_info.split(':', 1)[1].split(';', 1)[0]
                    file_bytes = base64.b64decode(b64_data)
                    # Determine a reasonable extension
                    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/gif": "gif", "image/webp": "webp"}
                    ext = ext_map.get(mime, 'jpg')
                    file_name = f"upload_header.{ext}"
                    handle = upload_bytes_to_meta(file_bytes, file_name, mime, waba_config)
                    component["example"] = {"header_handle": [handle]}
                    component.pop("media_url", None)

                elif is_url or is_missing:
                    media_url = handle_value if is_url else fallback_url
                    if media_url:
                        mime_type = MEDIA_FORMATS[fmt]
                        handle = upload_media_to_meta(media_url, mime_type, waba_config)
                        component["example"] = {"header_handle": [handle]}
                        component.pop("media_url", None)
            except Exception as e:
                logger.error(f"Media upload during template creation failed: {e}")
                return False, {"error": "Media upload failed", "details": str(e)}

        response = requests.post(url, headers=headers, json=template_data, timeout=20)
        
        if response.status_code in [200, 201]:
            logger.info("Natively registered template with Meta.")
            return True, response.json()
        else:
            logger.error(f"Meta rejected template registration. Status: {response.status_code}, Body: {response.text}")
            return False, {"error": "Meta registration failed", "details": response.json()}

    except Exception as e:
        logger.error(f"Error natively creating template: {e}")
        return False, {"error": "Internal template registration error", "details": str(e)}


def delete_whatsapp_template_from_meta(template_name, config=None):
    """
    Deletes a WhatsApp message template from Meta by template name.
    Returns (success, response_data).
    """
    try:
        if config:
            waba_config = get_whatsapp_config(config_id=config.id if hasattr(config, 'id') else config)
        else:
            waba_config = get_whatsapp_config()

        config_obj = waba_config.get('config_obj')
        whatsapp_token = waba_config.get('whatsapp_token')
        waba_id = config_obj.whatsapp_business_account_id if config_obj else None

        if not template_name:
            return False, {"error": "Template name is required."}

        if not waba_id or waba_id == "your_waba_id_here":
            return False, {"error": "Missing WHATSAPP_BUSINESS_ACCOUNT_ID in config."}

        if not whatsapp_token:
            return False, {"error": "Missing WhatsApp API token in config."}

        graph_version = getattr(settings, 'META_GRAPH_API_VERSION', 'v20.0')
        url = f"https://graph.facebook.com/{graph_version}/{waba_id}/message_templates"
        headers = {"Authorization": f"Bearer {whatsapp_token}"}
        response = requests.delete(
            url,
            headers=headers,
            params={"name": template_name},
            timeout=20,
        )

        response_data = response.json() if response.content else {}
        if response.ok:
            logger.info("Deleted WhatsApp template '%s' from Meta.", template_name)
            return True, response_data

        logger.error(
            "Meta rejected template delete for '%s'. Status: %s, Body: %s",
            template_name,
            response.status_code,
            response.text,
        )
        return False, {"error": "Meta template deletion failed", "details": response_data}

    except Exception as e:
        logger.error(f"Error deleting template from Meta: {e}")
        return False, {"error": "Internal template deletion error", "details": str(e)}

