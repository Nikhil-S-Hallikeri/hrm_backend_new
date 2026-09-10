from django.core.mail import send_mail
from django.conf import settings
from whatsapp_app.models import Message
from django.utils import timezone
import random
import re
import requests
import time


def extract_provider_message_id(response_data, fallback=None):
    """Return the provider message id from common Flask/Meta response shapes."""
    provider_id = None
    if isinstance(response_data, dict):
        provider_id = (
            response_data.get('provider_message_id')
            or response_data.get('message_id')
            or response_data.get('id')
        )
        if not provider_id and isinstance(response_data.get('data'), dict):
            inner_data = response_data.get('data')
            provider_id = (
                inner_data.get('provider_message_id')
                or inner_data.get('message_id')
                or inner_data.get('id')
            )
        if (
            not provider_id
            and isinstance(response_data.get('messages'), list)
            and response_data['messages']
        ):
            provider_id = response_data['messages'][0].get('id')

    return provider_id or fallback


def extract_media_url_from_components(components):
    """Find a header media link in WhatsApp template components."""
    for component in components or []:
        if str(component.get('type', '')).lower() != 'header':
            continue
        for parameter in component.get('parameters', []) or []:
            param_type = str(parameter.get('type', '')).lower()
            if param_type in {'image', 'video', 'document'}:
                media_data = parameter.get(param_type) or {}
                if isinstance(media_data, dict) and media_data.get('link'):
                    return media_data.get('link')
    return None


def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))


def create_otp_record(email, otp_type, user_data=None):
    # Generate OTP
    otp = generate_otp()
    
    # Delete any previous OTP for this email and type
    OTPVerification.objects.filter(
        email=email,
        otp_type=otp_type
    ).delete()
    
    # Create new OTP record
    otp_record = OTPVerification.objects.create(
        email=email,
        otp=otp,
        otp_type=otp_type,
        user_data=user_data
    )
    
    return otp_record


def send_signup_otp_to_admin(email, role, otp):
    """
    Send signup OTP to admin email
    
    Args:
        email: User's email
        role: User's role
        otp: The generated OTP
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='New Signup Request',
            message=f"""
            New signup request received:
            
            Email: {email}
            Role: {role}
            
            OTP for approval: {otp}
            
            This OTP will expire in 10 minutes.
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.ADMIN_EMAIL],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"--- FAILED TO SEND ADMIN OTP EMAIL ---")
        print(f"Error: {str(e)}")
        print(f"OTP for admin is: {otp}")
        print(f"--------------------------------------")
        return False


def send_signup_otp_to_user(email, otp):
    """
    Send signup OTP to user's email
    
    Args:
        email: User's email
        otp: The generated OTP
    
    Returns:
        Boolean indicating success
    """
    try:
        subject = 'ðŸ” Your Signup OTP - Merida Tech Minds'
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 500px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                        <h1 style="color: white; margin: 0;">Merida Tech Minds</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd;">
                        <h2 style="color: #667eea;">Welcome to Merida Tech Minds!</h2>
                        <p>Thank you for signing up. To complete your registration, please use the following OTP:</p>
                        
                        <div style="background: white; border: 2px solid #667eea; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                            <p style="font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 5px; margin: 0;">{otp}</p>
                        </div>
                        
                        <p style="color: #666; font-size: 14px;"><strong>â±ï¸ Valid for:</strong> 10 minutes</p>
                        
                        <p style="margin-top: 30px; color: #666; font-size: 13px;">
                            If you didn't request this signup, please ignore this email or contact our support team.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            Â© 2026 Merida Tech Minds. All rights reserved.<br>
                            Do not share this OTP with anyone.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        send_mail(
            subject=subject,
            message=f'Your signup OTP is: {otp}\n\nValid for 10 minutes.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_message,
        )
        return True
    except Exception as e:
        print(f"--- FAILED TO SEND USER OTP EMAIL ---")
        print(f"Error: {str(e)}")
        print(f"OTP for {email} is: {otp}")
        print(f"-------------------------------------")
        return False


def send_account_approval_email(email):
    """
    Send account approval confirmation to user
    
    Args:
        email: User's email
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='Account Approved',
            message=f"""
            Dear User,
            
            Your account has been approved by the admin.
            You can now login with your email and password.
            
            Email: {email}
            
            Welcome to our platform!
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False


def send_password_reset_otp(email, otp):
    """
    Send password reset OTP to user's email
    
    Args:
        email: User's email
        otp: The generated OTP
    
    Returns:
        Boolean indicating success
    """
    try:
        subject = 'ðŸ”‘ Password Reset OTP - Merida Tech Minds'
        html_message = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 500px; margin: 0 auto; padding: 20px;">
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px 10px 0 0; text-align: center;">
                        <h1 style="color: white; margin: 0;">Merida Tech Minds</h1>
                    </div>
                    <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; border: 1px solid #ddd;">
                        <h2 style="color: #667eea;">Password Reset Request</h2>
                        <p>We received a request to reset your password. If this was you, use the following OTP to proceed:</p>
                        
                        <div style="background: white; border: 2px solid #667eea; padding: 20px; text-align: center; border-radius: 8px; margin: 20px 0;">
                            <p style="font-size: 32px; font-weight: bold; color: #667eea; letter-spacing: 5px; margin: 0;">{otp}</p>
                        </div>
                        
                        <p style="color: #666; font-size: 14px;"><strong>â±ï¸ Valid for:</strong> 10 minutes</p>
                        
                        <p style="margin-top: 30px; color: #666; font-size: 13px;">
                            <strong>âš ï¸ Security Notice:</strong> If you didn't request this, your account may be at risk. 
                            Please change your password immediately and contact our support team.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
                        <p style="color: #999; font-size: 12px; text-align: center;">
                            Â© 2026 Merida Tech Minds. All rights reserved.<br>
                            Never share your OTP with anyone.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        send_mail(
            subject=subject,
            message=f'Your password reset OTP is: {otp}\n\nValid for 10 minutes. Do not share this with anyone.',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_message,
        )
        return True
    except Exception as e:
        raise Exception(f"Failed to send password reset OTP email: {str(e)}")


def send_password_reset_confirmation(email):
    """
    Send password reset confirmation to user
    
    Args:
        email: User's email
    
    Returns:
        Boolean indicating success
    """
    try:
        send_mail(
            subject='Password Reset Successful',
            message=f"""
            Your password has been reset successfully.
            
            You can now login with your new password.
            
            If you didn't make this change, please contact support immediately.
            """,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Failed to send confirmation email: {e}")
        return False


def verify_otp(email, otp, otp_type):
    """
    Verify OTP and return the OTP record if valid
    
    Args:
        email: User's email
        otp: The OTP to verify
        otp_type: 'signup' or 'forgot_password'
    
    Returns:
        OTPVerification object if valid, None otherwise
    """
    try:
        otp_record = OTPVerification.objects.get(
            email=email,
            otp=otp,
            otp_type=otp_type,
            is_verified=False
        )
        
        if otp_record.is_valid():
            return otp_record
        else:
            return None
            
    except OTPVerification.DoesNotExist:
        return None


def extract_variables(text):
    """Extract unique placeholder indices from text, e.g. {{1}}, {{2}} -> ["1", "2"]."""
    return sorted(set(re.findall(r"\{\{(\d+)\}\}", text or "")), key=int)


def validate_sequential_variables(variables):
    """Ensure placeholders start from 1 and are continuous with no gaps."""
    if not variables:
        return True

    expected = [str(i) for i in range(1, len(variables) + 1)]
    return variables == expected


def render_template(template_body, variables):
    for key, value in variables.items():
        template_body = template_body.replace(f"{{{{{key}}}}}", value)
    return template_body

def render_template_body(body, values):
    """Render a template body by replacing placeholders with supplied variable values."""
    values = values or {}
    required = extract_variables(body)

    provided_keys = sorted(values.keys(), key=lambda item: int(item)) if values else []
    if provided_keys != required:
        raise ValueError("Provided variables do not match required placeholders.")

    rendered = body or ""
    for var_key in required:
        rendered = rendered.replace("{{" + var_key + "}}", str(values[var_key]))
    return rendered


def execute_campaign(campaign):
    """Execute campaign delivery and update campaign delivery metrics."""
    now = timezone.now()
    campaign.status = 'RUNNING'
    campaign.started_at = now

    contacts = list(campaign.contacts.all())
    campaign.total_contacts = len(contacts)
    
    # Save RUNNING status immediately so frontend sees it
    campaign.save(
        update_fields=[
            'status', 'started_at', 'total_contacts',
        ]
    )

    sent_count = 0
    sent_messages = []
    contacts_to_update = []
    failed_count = 0


    if not campaign.template:
        campaign.status = 'FAILED'
        campaign.completed_at = now
        campaign.total_contacts = len(contacts)
        campaign.total_sent = campaign.total_sent or 0
        campaign.total_failed = (campaign.total_failed or 0) + len(contacts)
        campaign.save(
            update_fields=[
                'status', 'started_at', 'completed_at',
                'total_contacts', 'total_sent', 'total_failed',
            ]
        )
        return {
            'total_sent': campaign.total_sent,
            'total_failed': campaign.total_failed,
            'status': campaign.status,
            'messages': [],
        }

    # Resolve waba_config early
    waba_config = get_whatsapp_config(campaign.whatsapp_config_id if campaign.whatsapp_config else None)

    # Pre-flight upload for template media
    pre_uploaded_media_id = None
    header_media_url = None
    if campaign.template and campaign.template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT']:
        # Priority 1: media_id pre-uploaded during launch via direct byte stream (solves local URL issues)
        pre_uploaded_media_id = campaign.variables.get('__header_media_id__') if campaign.variables else None
        
        header_media_url = campaign.variables.get('__header_media_url__') if campaign.variables else None
        if not header_media_url:
            # Check if header_media is a saved Meta media ID (numeric string from a previous upload)
            # If so, use it directly without re-uploading
            hm = campaign.template.header_media
            if hm and str(hm).strip().isdigit():
                pre_uploaded_media_id = str(hm).strip()
                header_media_url = None  # Already have media_id, no URL needed
            else:
                # Prefer meta_media_url (actual HTTP URL on Meta CDN) over base64 uploaded_preview_image
                # which can be very large and cause timeouts when re-uploading on every send
                header_media_url = (
                    campaign.template.meta_media_url
                    or campaign.template.header_media
                    or campaign.template.uploaded_preview_image
                )
                if not header_media_url and campaign.template.sample_values:
                    header_media_url = (
                        campaign.template.sample_values.get('header_handle')
                        or campaign.template.sample_values.get('media_url')
                    )
                if isinstance(header_media_url, list) and len(header_media_url) > 0:
                    header_media_url = header_media_url[0]

        # Make relative URLs absolute or read directly from disk if local
        if header_media_url and header_media_url.startswith('/'):
            # It's a local file, try to read from disk directly to avoid network loopback issues
            if header_media_url.startswith('/media/'):
                from django.conf import settings
                import os
                
                # Extract path after /media/
                relative_path = header_media_url[len('/media/'):]
                file_path = os.path.join(settings.MEDIA_ROOT or '', relative_path)
                
                if os.path.exists(file_path):
                    try:
                        from whatsapp_app.services import upload_media_for_message
                        import mimetypes
                        
                        mime_type, _ = mimetypes.guess_type(file_path)
                        mime_type = mime_type or 'application/octet-stream'
                        file_name = os.path.basename(file_path)
                        
                        with open(file_path, 'rb') as f:
                            file_bytes = f.read()
                            
                        pre_uploaded_media_id = upload_media_for_message(file_bytes, file_name, mime_type, waba_config)
                        print(f"Pre-flight campaign local upload successful. Media ID: {pre_uploaded_media_id}")
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Campaign pre-flight local media upload failed: {e}")
                        campaign.status = 'FAILED'
            
            # If still not uploaded (e.g. not a /media/ path or file missing), fallback to absolute URL
            if not pre_uploaded_media_id:
                from django.conf import settings
                domain = getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000').rstrip('/')
                header_media_url = f"{domain}{header_media_url}"

        # Handle Data URLs (base64)
        if header_media_url and header_media_url.startswith('data:') and not pre_uploaded_media_id:
            try:
                import base64
                from whatsapp_app.services import upload_media_for_message

                meta_info, b64_data = header_media_url.split(',', 1)
                mime_type = 'image/jpeg'
                if ':' in meta_info and ';' in meta_info:
                    mime_type = meta_info.split(':', 1)[1].split(';', 1)[0]

                ext_map = {
                    "image/jpeg": "jpg",
                    "image/png": "png",
                    "image/gif": "gif",
                    "image/webp": "webp",
                    "video/mp4": "mp4",
                    "application/pdf": "pdf",
                }
                file_name = f"template_header.{ext_map.get(mime_type, 'bin')}"
                file_bytes = base64.b64decode(b64_data)

                pre_uploaded_media_id = upload_media_for_message(
                    file_bytes,
                    file_name,
                    mime_type,
                    waba_config,
                )
                print(f"Pre-flight campaign base64 upload successful. Media ID: {pre_uploaded_media_id}")
                # Save the media ID back to the template so future sends don't re-upload
                if pre_uploaded_media_id and campaign.template:
                    try:
                        campaign.template.header_media = pre_uploaded_media_id
                        campaign.template.save(update_fields=['header_media'])
                        print(f"Saved media_id {pre_uploaded_media_id} to template {campaign.template.id} header_media for future reuse")
                    except Exception as save_err:
                        import logging
                        logging.getLogger(__name__).warning(f"Could not save media_id to template: {save_err}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Campaign pre-flight base64 media upload failed: {e}")
                campaign.status = 'FAILED'

        # Only attempt URL-based upload if we don't already have a media_id
        if header_media_url and not pre_uploaded_media_id and not header_media_url.startswith('data:'):
            try:
                from whatsapp_app.services import upload_template_media_for_sending
                print(f"Pre-flight uploading campaign template media: {header_media_url}")
                pre_uploaded_media_id = upload_template_media_for_sending(header_media_url, waba_config)
                print(f"Pre-flight campaign upload successful. Media ID: {pre_uploaded_media_id}")
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Campaign pre-flight media upload failed: {e}")
                campaign.status = 'FAILED'
                campaign.completed_at = timezone.now()
                campaign.total_contacts = len(contacts)
                campaign.total_sent = campaign.total_sent or 0
                campaign.total_failed = (campaign.total_failed or 0) + len(contacts)
                campaign.save(
                    update_fields=[
                        'status', 'completed_at',
                        'total_contacts', 'total_sent', 'total_failed',
                    ]
                )
                return {
                    'total_sent': campaign.total_sent,
                    'total_failed': campaign.total_failed,
                    'status': campaign.status,
                    'messages': [],
                }

    for contact in contacts:
        # Check if campaign was stopped mid-execution
        campaign.refresh_from_db()
        if campaign.status == 'COMPLETED':
            break
            
        # Avoid duplicate sends if contact has already been messaged in this campaign
        from whatsapp_app.models import Message
        if Message.objects.filter(contact=contact, campaign=campaign).exists():
            continue
            
        try:
            # Resolve message text robustly for campaign delivery
            template_body = campaign.template.body if (campaign.template and campaign.template.body) else ""
            
            # If body is empty but we have a template name, use that as a base
            if not template_body and campaign.template:
                template_body = campaign.template.name

            parsed_message = render_template(template_body, campaign.variables or {})
            # render_template only fills in placeholders explicitly present in
            # campaign.variables. Named placeholders like {{contact.name}} that
            # weren't saved as an explicit variable are resolved here instead.
            parsed_message = resolve_contact_variables(parsed_message, contact)

            # Final fallback if rendering resulted in empty string
            if not parsed_message and campaign.template:
                parsed_message = campaign.template.name

            # _normalize_phone_number already handles 10-digit -> 91XXXXXXXXXX conversion
            phone = _normalize_phone_number(contact.phone_number)
            
            payload = {
                "phone": phone,
                "template_name": campaign.template.name,
                "language_code": campaign.template.language or "en_US",
                "campaign_id": campaign.id,
                "contact_id": contact.id,
            }
            
            # Always build components dict (even for templates with no user variables)
            # so header media and url buttons are always included when applicable
            variables_dict = campaign.variables or {}
            components = []

            # Extract url_buttons from stored variables
            url_buttons = variables_dict.get('__url_buttons__', {})

            # 1. Header Media component
            if campaign.template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT']:
                header_type = campaign.template.header_type.lower()
                if pre_uploaded_media_id:
                    media_obj = {"id": pre_uploaded_media_id}
                    if header_type == 'document':
                        media_obj["filename"] = variables_dict.get('__header_filename__') or 'document.pdf'
                    components.append({
                        "type": "header",
                        "parameters": [
                            {
                                "type": header_type,
                                header_type: media_obj
                            }
                        ]
                    })
                elif header_media_url:
                    components.append({
                        "type": "header",
                        "parameters": [
                            {
                                "type": header_type,
                                header_type: {"link": header_media_url}
                            }
                        ]
                    })

            # 2. Body variable components
            import re
            placeholders = re.findall(r'\{\{(\w+)\}\}', campaign.template.body or '')
            body_keys = [
                k for k in variables_dict.keys()
                if not str(k).startswith('__') and not str(k).startswith('_')
            ]
            if body_keys:
                params = []
                for key in sorted(body_keys, key=lambda v: int(v) if str(v).isdigit() else v):
                    p_item = {"type": "text", "text": str(variables_dict[key])}
                    if not str(key).isdigit():
                        p_item["parameter_name"] = str(key)
                    params.append(p_item)
                components.append({
                    "type": "body",
                    "parameters": params
                })
            elif placeholders:
                params = []
                for p in placeholders:
                    val = "Saturday, Aug 15, 2026" if ("date" in str(p).lower() or "text" in str(p).lower()) else (contact.name or "Customer")
                    p_item = {"type": "text", "text": val}
                    if not str(p).isdigit():
                        p_item["parameter_name"] = str(p)
                    params.append(p_item)
                components.append({
                    "type": "body",
                    "parameters": params
                })

            # 3. URL Button components
            if url_buttons and isinstance(url_buttons, dict):
                template_buttons = campaign.template.buttons or []
                for btn_idx, btn in enumerate(template_buttons):
                    if btn.get('type') in ('URL', 'url') and btn.get('text') in url_buttons:
                        url_val = url_buttons[btn.get('text')]
                        components.append({
                            "type": "button",
                            "sub_type": "url",
                            "index": str(btn_idx),
                            "parameters": [
                                {"type": "text", "text": str(url_val)}
                            ]
                        })

            # Only attach components to payload if there are any
            if components:
                payload["components"] = components

            import uuid
            generated_provider_message_id = str(uuid.uuid4())
            media_url = header_media_url
            template_buttons = campaign.template.buttons or []
            
            from whatsapp_app.services import send_whatsapp_message_direct_to_meta
            
            try:
                meta_response, status_code = send_whatsapp_message_direct_to_meta(
                    recipient_id=phone,
                    waba_config=waba_config,
                    text=parsed_message,
                    template_name=campaign.template.name,
                    language_code=campaign.template.language or "en_US",
                    components=components,
                    media_url=media_url,
                    media_type=campaign.template.header_type.lower() if (campaign.template and campaign.template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT']) else None
                )
                
                if status_code not in [200, 201]:
                    print(f"Meta Request Failed ({status_code}): {meta_response}")
                    failed_count += 1
                    continue
                
                res_data = meta_response if isinstance(meta_response, dict) else {}
            except Exception as req_err:
                print(f"Meta Request Failed: {str(req_err)}")
                failed_count += 1
                continue

            provider_id = extract_provider_message_id(res_data, fallback=generated_provider_message_id)

            # Store our own lazily-resolvable media link for local display, independent of
            # whatever form (direct link vs Meta media_id) was used for the Meta send above -
            # header_media_url gets nulled whenever a media_id is used (the common case),
            # which would otherwise leave our own inbox with nothing to render even though
            # Meta delivered the media to the recipient fine.
            stored_media_url = media_url
            if campaign.template and campaign.template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT']:
                stored_media_url = f"/templates/{campaign.template.id}/header-media/?type={campaign.template.header_type.lower()}"

            msg = Message(
                contact=contact,
                campaign=campaign,
                text=parsed_message,
                sender='agent',
                direction='OUTGOING',
                status='Sent',
                type='template',
                provider_message_id=provider_id,
                media_url=stored_media_url,
                buttons=template_buttons,
                timestamp=now,
            )
            msg.save()
            sent_messages.append({
                'id': msg.id,
                'contact_id': contact.id,
                'phone': contact.phone_number,
                'provider_message_id': msg.provider_message_id,
                'media_url': msg.media_url,
                'buttons': msg.buttons,
            })
            contact.last_message = parsed_message
            contact.last_message_time = now
            contacts_to_update.append(contact)
            sent_count += 1
        except Exception as contact_err:
            import traceback
            import logging as _logging
            _logging.getLogger(__name__).error(
                f"Campaign {campaign.id} failed for contact {contact.phone_number}: {contact_err}\n{traceback.format_exc()}"
            )
            failed_count += 1

    if contacts_to_update:
        contact_model = contacts_to_update[0].__class__
        contact_model.objects.bulk_update(contacts_to_update, ['last_message', 'last_message_time'])

    campaign.total_sent = (campaign.total_sent or 0) + sent_count
    campaign.total_failed = (campaign.total_failed or 0) + failed_count
    
    # Re-check status â€” if it was stopped (COMPLETED) mid-loop, keep it
    current_status = campaign.__class__.objects.filter(pk=campaign.pk).values_list('status', flat=True).first()
    if current_status == 'COMPLETED':
        campaign.status = 'COMPLETED'
    else:
        # Keep as RUNNING â€” user must explicitly stop or it stays running
        campaign.status = 'RUNNING'
    
    campaign.save(
        update_fields=[
            'status', 'started_at',
            'total_contacts', 'total_sent', 'total_failed',
        ]
    )

    return {
        'total_sent': campaign.total_sent,
        'total_failed': campaign.total_failed,
        'status': campaign.status,
        'messages': sent_messages,
    }

def _normalize_phone_number(phone_number):
    """Normalize phone number by removing all non-digit characters and prepending 91 if 10 digits."""
    phone = re.sub(r'\D', '', str(phone_number or ''))
    if len(phone) == 10:
        phone = f"91{phone}"
    elif phone.startswith('0') and len(phone) == 11:
        phone = f"91{phone[1:]}"
    return phone


def _serialize_event_payload(event_type, contact=None, message=None, extra=None):
    from whatsapp_app.serializers import ContactSerializer, MessageSerializer
    payload = {'event': event_type}

    if contact is not None:
        payload['contact'] = ContactSerializer(contact).data if hasattr(contact, '_meta') else contact

    if message is not None:
        payload['message'] = MessageSerializer(message).data if hasattr(message, '_meta') else message

    if extra:
        payload.update(extra)

    return payload


def _send_crm_webhook_async(webhook_url, payload, api_token, tenant_email=None):
    import threading
    import requests
    SELF_HOSTS = ("backendwa.porchgeek.in", "localhost:8000", "127.0.0.1:8000")
    if not webhook_url or any(h in webhook_url for h in SELF_HOSTS):
        return
    def worker():
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + str(api_token or 'super_secret_crm_token_123')
            }
            if tenant_email:
                headers["X-Tenant-Email"] = tenant_email
            response = requests.post(webhook_url, json=payload, headers=headers, timeout=5)
            if response.status_code >= 400:
                raise requests.exceptions.RequestException("Status " + str(response.status_code))
            try:
                with open("webhook_debug.log", "a") as f_log:
                    f_log.write("\n[WEBHOOK PUSH] Sent to " + webhook_url + ", Status: " + str(response.status_code) + "\n")
            except:
                pass
        except Exception as e:
            try:
                with open("webhook_debug.log", "a") as f_log:
                    f_log.write("\n[WEBHOOK ERROR] Failed to send webhook to " + webhook_url + ": " + str(e) + "\n")
            except:
                pass
    threading.Thread(target=worker, daemon=True).start()


def _lookup_admin_crm_access(config_id, user_id):
    """
    crm_access lives on WhatsAppUser in the Admin SaaS backend, which runs as a separate
    service with its own database - not something this project's normal Django `connection`
    can query (they're different SQLite files, even in this same-host deployment). Open that
    database directly, read-only, instead.

    Defaults to True (i.e. keep forwarding) whenever the flag can't be determined - a lookup
    failure should never silently break the CRM push for tenants who do have it enabled.
    """
    if not config_id and not user_id:
        return True
    try:
        import sqlite3
        from django.conf import settings
        db_path = settings.BASE_DIR.parent / 'admin _saas_backend' / 'db.sqlite3'
        if not db_path.exists():
            return True
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True, timeout=2)
        try:
            cursor = conn.cursor()
            if config_id and user_id:
                cursor.execute(
                    "SELECT crm_access FROM whatsapp_saas_whatsappuser WHERE whatsapp_config_id = ? OR user_id = ?",
                    (config_id, user_id)
                )
            elif config_id:
                cursor.execute(
                    "SELECT crm_access FROM whatsapp_saas_whatsappuser WHERE whatsapp_config_id = ?",
                    (config_id,)
                )
            else:
                cursor.execute(
                    "SELECT crm_access FROM whatsapp_saas_whatsappuser WHERE user_id = ?",
                    (user_id,)
                )
            row = cursor.fetchone()
            return bool(row[0]) if row is not None else True
        finally:
            conn.close()
    except Exception:
        return True


def _broadcast_crm_event(event_type, contact=None, message=None, extra=None, phone_number=None):
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    payload = _serialize_event_payload(event_type, contact=contact, message=message, extra=extra)
    groups = {'crm_updates'}

    # Forward to Node/Express CRM Webhook
    try:
        config_id = contact.whatsapp_config_id if (contact and hasattr(contact, 'whatsapp_config_id')) else None
        config = get_whatsapp_config(config_id)
        webhook_url = config.get('crm_webhook_url')
        config_obj = config.get('config_obj')
        crm_api_token = config_obj.crm_api_token if (config_obj and config_obj.crm_api_token) else 'super_secret_crm_token_123'
        user_obj = config_obj.user if (config_obj and config_obj.user) else None
        tenant_email = None
        if user_obj:
            tenant_email = getattr(user_obj, 'email', None) or getattr(user_obj, 'Email', None)
        
        # Default fallback to Node/Express running on port 9003
        if (not webhook_url or
            'localhost:8000' in webhook_url or
            '127.0.0.1:8000' in webhook_url or
            'localhost:9956' in webhook_url or
            '127.0.0.1:9956' in webhook_url or
            'trycloudflare.com' in webhook_url):
            webhook_url = 'http://localhost:9003/api/whatsapp/events'

        user_id = config_obj.user.id if (config_obj and config_obj.user) else None
        config_id_val = config_obj.id if config_obj else None
        crm_access = _lookup_admin_crm_access(config_id_val, user_id)

        if webhook_url and crm_access:
            _send_crm_webhook_async(webhook_url, payload, crm_api_token, tenant_email=tenant_email)
    except Exception as e:
        try:
            with open('webhook_debug.log', 'a') as f_log:
                f_log.write(f"\n[WEBHOOK ERROR] Config resolution failed: {str(e)}\n")
        except:
            pass


    if contact is not None:
        groups.add(f'crm_contact_{contact.id}')
        normalized_phone = _normalize_phone_number(contact.phone_number)
        if normalized_phone:
            groups.add(f'crm_chat_{normalized_phone}')
    elif phone_number:
        normalized_phone = _normalize_phone_number(phone_number)
        if normalized_phone:
            groups.add(f'crm_chat_{normalized_phone}')

    # Debug logging
    try:
        with open('webhook_debug.log', 'a') as f_log:
            f_log.write(f"\n[BROADCAST] {event_type} to groups {list(groups)}\n")
    except:
        pass

    for group_name in groups:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'crm_event',
                'message': payload
            }
        )



PUBLIC_API_USER_EMAIL = 'public-api@example.local'


def get_public_api_user():
    """Get or create a default user for public API operations."""
    from whatsapp_app.models import User
    # RegistrationModel has 'Email' instead of 'email'
    user = User.objects.filter(Email=PUBLIC_API_USER_EMAIL).first()
    if user:
        return user

    # Fallback to the first existing employee
    user = User.objects.order_by('id').first()
    if user:
        return user

    # Create system API employee if none exist
    return User.objects.create(
        EmployeeId='SYSTEM_API',
        UserName='System API User',
        Email=PUBLIC_API_USER_EMAIL,
    )


def get_whatsapp_config(config_id=None):
    """
    Fetches the active WhatsAppConfig record from the database singleton or specified ID.
    Falls back gracefully to django.conf.settings if database values are missing.
    """
    from whatsapp_app.models import WhatsAppConfig
    from django.conf import settings
    from whatsapp_app.middleware import get_current_request_config_id
    
    if config_id is None:
        config_id = get_current_request_config_id()
    
    if config_id:
        try:
            config = WhatsAppConfig.objects.get(id=config_id)
        except (WhatsAppConfig.DoesNotExist, ValueError):
            config = WhatsAppConfig.get_solo()
    else:
        config = WhatsAppConfig.get_solo()
    
    flask_url = getattr(settings, 'FLASK_SERVER_URL', 'http://127.0.0.1:5000')
    flask_token = getattr(settings, 'FLASK_AUTH_TOKEN', 'super_secret_crm_token_123')
    whatsapp_token = getattr(settings, 'WHATSAPP_API_TOKEN', None)
    phone_id = getattr(settings, 'PHONE_NUMBER_ID', None)
    
    if config:
        if config.flask_bot_url:
            flask_url = config.flask_bot_url
        elif config.flask_server_url:
            flask_url = config.flask_server_url
            
        if config.flask_auth_token:
            flask_token = config.flask_auth_token
        if config.whatsapp_api_token:
            whatsapp_token = config.whatsapp_api_token
        if config.phone_number_id:
            phone_id = config.phone_number_id
            
    return {
        'flask_url': flask_url.rstrip('/'),
        'flask_token': flask_token,
        'whatsapp_token': whatsapp_token,
        'phone_id': phone_id,
        'waba_id': getattr(config, 'whatsapp_business_account_id', None) if config else None,
        'crm_webhook_url': config.crm_webhook_url if config else getattr(settings, 'CRM_WEBHOOK_URL', 'http://localhost:8000/api/whatsapp/events/'),
        'gemini_api_key': config.gemini_api_key if config else None,
        'webhook_verify_token': config.webhook_verify_token if config else 'my_secret_token_123',
        'config_obj': config
    }


def get_whatsapp_headers(config_id=None):
    """
    Constructs the exact HTTP headers dictionary required by the Flask bot
    according to the dynamic multi-tenant specifications.
    """
    config = get_whatsapp_config(config_id)
    
    headers = {
        "Authorization": f"Bearer {config['flask_token']}",
        "Content-Type": "application/json"
    }
    
    config_obj = config.get('config_obj')
    is_ai_enabled = config_obj.is_ai_enabled if config_obj else False
    
    headers["X-AI-Enabled"] = "true" if is_ai_enabled else "false"
    headers["X-Is-AI-Enabled"] = "true" if is_ai_enabled else "false"
    
    if config['whatsapp_token']:
        headers["X-Whatsapp-Token"] = config['whatsapp_token']
    if config['phone_id']:
        headers["X-Phone-Number-Id"] = config['phone_id']
    if config_obj and config_obj.whatsapp_business_account_id:
        headers["X-WhatsApp-Business-Account-Id"] = str(config_obj.whatsapp_business_account_id)
        headers["X-WABA-ID"] = str(config_obj.whatsapp_business_account_id)
    if config_obj and config_obj.whatsapp_app_id:
        headers["X-WhatsApp-App-Id"] = str(config_obj.whatsapp_app_id)
    if config['crm_webhook_url']:
        headers["X-CRM-Webhook-Url"] = config['crm_webhook_url']
    if config['gemini_api_key'] and is_ai_enabled:
        headers["X-Gemini-API-Key"] = config['gemini_api_key']
    if config['webhook_verify_token']:
        headers["X-Webhook-Verify-Token"] = config['webhook_verify_token']
        
    return headers, config['flask_url']


# =====================================================================
# NATIVE GEMINI AI qualification & LEAD SCORING FLOW (PORTED FROM FLASK)
# =====================================================================

QUESTIONS_CONFIG = {
    "Skill Enhancement": [
        {"options": ["Web Development", "Data Analytics", "Machine Learning", "UI/UX Design", "Other"]}, # Q4
        {"options": ["Complete Beginner", "Intermediate/Basics", "Advanced Level"]}, # Q5
        {"options": ["Right Away / Direct", "Within 30 Days", "Planning for Later"]}, # Q6
        {"options": ["Yes", "No"]}, # Q7
        {"options": ["Fully Dedicated", "Moderately Active", "Just Exploring"]}, # Q8
        {"options": ["Career Transition", "Upskillment", "Gain Experience"]}, # Q9
        {"options": ["Live Mentor-Guided", "Self-Paced Learning"]}, # Q10
        {"options": ["Yes", "No"]}, # Q11
        {"options": ["Yes", "No"]} # Q12
    ],
    "Trading Academy": [
        {"options": ["Yes", "No"]}, # Q4
        {"options": ["Complete Beginner", "Intermediate Level", "Advanced Level"]}, # Q5
        {"options": ["Premium Capital", "Standard Capital", "Starter Capital"]}, # Q6
        {"options": ["High Risk Growth", "Balanced/Moderate", "Low Risk Capital"]}, # Q7
        {"options": ["Full-time", "Casual", "Just Exploring"]}, # Q8
        {"options": ["Both Strategies", "Short-Term Focus", "Long-Term Focus"]}, # Q9
        {"options": ["Daily", "Sometimes", "Limited"]}, # Q10
        {"options": ["Yes", "No"]}, # Q11
        {"options": ["Yes", "No"]} # Q12
    ],
    "Jobs": [
        {"options": ["Software Engineer", "Data Analyst", "Product Manager", "Other"]}, # Q4
        {"options": ["5+ Years Experience", "3 to 5 Years", "1 to 3 Years", "Fresher / Graduate"]}, # Q5
        {"options": ["Immediate Joiner", "Within 1-2 Months", "Just Exploring"]}, # Q6
        {"options": ["Yes, actively", "No, not currently"]}, # Q7
        {"options": ["Fully Prepared", "Needs Preparation", "Not Ready Yet"]}, # Q8
        {"options": ["Entry Level", "Mid Level", "Senior"]}, # Q9
        {"options": ["Open to Relocate", "No, remote only"]}, # Q10
        {"options": ["Yes, fully skilled", "Most core skills", "Not skilled yet"]}, # Q11
        {"options": ["Yes", "No"]} # Q12
    ]
}

def parse_conversation_state(history):
    """
    Deterministically parses conversation history sequentially to calculate
    the exact step (1 to 14) and extracted metadata (name, phone, email, path, answers).
    """
    path = None
    name = None
    phone = None
    email = None
    answers = []

    opt_in_words = {
        "yes", "no", "hi", "hello", "start", "get started",
        "opt-in", "opt in", "yes, i'm interested", "interested"
    }
    restart_words = {"hi", "hello", "start", "restart", "get started", "menu", "reset"}

    for msg in history:
        if msg["role"] != "user":
            continue
        
        txt = msg["text"].strip()
        txt_lower = txt.lower()

        if txt_lower in restart_words:
            path = None
            name = None
            phone = None
            email = None
            answers = []
            continue

        # Step 1: Path Selection
        if path is None:
            is_email_or_url = "@" in txt or txt_lower.startswith("http") or (
                "." in txt and len(txt.split()) == 1 and len(txt) > 5
            )
            if not is_email_or_url:
                if re.search(r"\bskill|\bupskill", txt_lower):
                    path = "Skill Enhancement"
                elif re.search(r"\btrad", txt_lower) or re.search(r"\bfortune\b", txt_lower):
                    path = "Trading Academy"
                elif re.search(r"\bjob", txt_lower) or re.search(r"\bcareer", txt_lower):
                    path = "Jobs"
            if path is None and txt_lower in opt_in_words:
                continue
            if path is None:
                continue
            continue

        # Step 2: Name
        if name is None:
            name = txt
            continue

        # Step 3: Phone
        if phone is None:
            phone = txt
            continue

        # Step 4: Email
        if email is None:
            email = txt
            continue

        # Steps 5-13: Path-specific questions (Q5 to Q13)
        if (path in ["Skill Enhancement", "Jobs"] and 
            len(answers) == 1 and 
            answers[0].lower() == "other"):
            answers[0] = f"Other: {txt}"
            continue

        answers.append(txt)

    # Calculate step
    if path is None:
        step = 1
    elif name is None:
        step = 2
    elif phone is None:
        step = 3
    elif email is None:
        step = 4
    elif (path in ["Skill Enhancement", "Jobs"] and 
          len(answers) == 1 and 
          answers[0].lower() == "other"):
        step = 5
    else:
        step = min(5 + len(answers), 14)

    return {
        "name": name,
        "phone": phone,
        "email": email,
        "path": path,
        "answers": answers,
        "step": step
    }


def parse_database_conversation_history(contact):
    """
    Retrieves the chronological message history for a Contact directly from the database,
    enriching outgoing messages with origin tags (Campaign, Reminder Campaign, Human Agent, Auto-Reply)
    and attachment details (Document, Image, JD file) so the AI has 100% full awareness of all outbound communications.
    """
    from whatsapp_app.models import Message
    messages = Message.objects.filter(contact=contact).select_related('campaign').order_by('timestamp', 'created_at')
    history = []
    
    for msg in messages:
        if msg.direction == 'INCOMING':
            history.append({"role": "user", "text": msg.text or ""})
        else:
            # Determine outbound origin tag
            origin_tag = ""
            if msg.campaign:
                title = getattr(msg.campaign, 'title', None) or getattr(msg.campaign, 'name', '') or "Campaign"
                camp_type = "Reminder Campaign" if ("reminder" in title.lower() or "reminder" in (msg.sender or "").lower()) else "Campaign"
                origin_tag = f"[{camp_type}: \"{title}\"]"
            elif msg.sender in ("AutoReply", "Auto-Reply", "System"):
                origin_tag = "[Auto-Reply System]"
            elif msg.sender in ("Admin", "Human", "Agent", "HR", "Support") or (msg.sender and msg.sender != "AI" and not msg.sender.startswith("91")):
                origin_tag = f"[Human HR Agent ({msg.sender})]"
            else:
                origin_tag = "[AI Assistant]"

            # Determine attachment tag
            attachment_tag = ""
            if msg.type == 'document' or msg.media_url:
                file_name = ""
                if msg.media_url:
                    file_name = msg.media_url.split("/")[-1].split("?")[0]
                attachment_name = file_name if file_name else "Attached Document/File"
                attachment_tag = f" [Attachment: {attachment_name}]"
                if msg.caption:
                    attachment_tag += f" (Caption: \"{msg.caption}\")"
            elif msg.type == 'image':
                attachment_tag = " [Image Attachment]"
            elif msg.type == 'template':
                attachment_tag = " [Template Message]"

            full_text = f"{origin_tag}{attachment_tag} {msg.text or ''}".strip()
            history.append({"role": "bot", "text": full_text})
        
    return history


def generate_gemini_response(history, waba_config):
    """
    Natively calls Google Gemini, Groq, or OpenAI API to get the structured auto-reply text.
    """
    from whatsapp_app.models import AIConfig
    import json
    ai_conf = None
    config_obj = waba_config.get('config_obj')
    if config_obj:
        try:
            ai_conf = AIConfig.objects.get(whatsapp_config=config_obj)
        except AIConfig.DoesNotExist:
            pass

    provider = ai_conf.llm_provider.lower().strip() if ai_conf else 'gemini'
    model_name = ai_conf.model_name if (ai_conf and ai_conf.model_name) else None
    api_key = ai_conf.api_key if (ai_conf and ai_conf.api_key) else waba_config.get('gemini_api_key')

    api_key = api_key.split()[0].strip()
    history_text = "\n".join([
        f"{'User' if m['role'] == 'user' else 'Assistant'}: {m['text']}"
        for m in history
    ])
    
    custom_system_prompt = (ai_conf.system_prompt or "").strip() if ai_conf else ""
    custom_description = (ai_conf.prompt or "").strip() if ai_conf else ""
    business_name = (ai_conf.business_name or "Merida HR").strip() if ai_conf else "Merida HR"
    assistant_name = (ai_conf.assistant_name or "Aria").strip() if ai_conf else "Aria"
    
    system_instructions = custom_system_prompt if custom_system_prompt else (
        f"You are {assistant_name}, AI assistant for {business_name}.\n"
        "Role: Professional HR & Workforce Solutions Consultant. Sound professional, approachable, knowledgeable, empathetic, and trustworthy."
    )

    contact = waba_config.get('contact')
    contact_memory_text = ""
    if contact:
        c_name = contact.name if (contact.name and contact.name != "Unknown" and contact.name != contact.phone_number) else "Not provided yet"
        c_phone = contact.phone_number or "Unknown"
        c_email = contact.email or "Not provided yet"
        c_attrs = json.dumps(contact.attributes, ensure_ascii=False) if (contact.attributes and isinstance(contact.attributes, dict)) else "None"
        contact_memory_text = f"""
### KNOWN USER PROFILE & PERSISTENT SESSION MEMORY:
- Full Name: {c_name}
- Phone Number: {c_phone}
- Email Address: {c_email}
- Saved Attributes & Memory: {c_attrs}
"""

    prompt = f"""{system_instructions}

### COMPANY DESCRIPTION & BUSINESS CONTEXT:
{custom_description if custom_description else 'Merida HR is an AI-powered HR consulting and workforce solutions company offering Recruitment, Staffing, RPO, HR Outsourcing, and Payroll services.'}
{contact_memory_text}
### CONVERSATION HISTORY:
{history_text}

### RESPONSE RULES:
1. STRICT FACTUAL GROUNDING: Treat ONLY details explicitly provided by the user in this transcript or listed under KNOWN USER PROFILE & PERSISTENT SESSION MEMORY as absolute facts. NEVER fabricate, assume, guess, or invent candidate details (name, experience, company, salary, location) to please anyone.
2. OUTBOUND MESSAGES, CAMPAIGNS & ATTACHMENT AWARENESS:
   - Outbound messages in history are tagged with their origin: [Campaign: "..."], [Reminder Campaign: "..."], [Auto-Reply System], [Human HR Agent], or [AI Assistant]. Understand what has already been sent to the user from your organization's end.
   - ATTACHMENT POSITION (ABOVE VS. BELOW): If a document, JD file, image, or template was ALREADY sent in a prior message in history (above the current turn), refer to it as "in the attachment above" or "sent above". If an automated auto-reply or system rule is attaching a document/JD file alongside/after this message, refer to it as "in the attachment below".
   - CONFLICT & DUPLICATION PREVENTION: If a Human HR Agent or Auto-Reply System has ALREADY answered the user's request in history, do NOT repeat the same answer or send conflicting information. Acknowledge what was sent gracefully.
3. Speak naturally, warmly, and concisely (under 70 words unless explaining a service).
4. Ask only ONE question in each reply. Wait for the user to reply before asking another.
5. Do not send repetitive greetings or prefix responses with the user's name if it sounds unnatural.
6. WHATSAPP PHONE NUMBER RULE: The user is messaging over WhatsApp, so their phone number is ALREADY KNOWN. NEVER ask the user to provide, share, or confirm their phone number for recruiter calls or updates, as you already have their WhatsApp number.
7. USER NAME & MEMORY RULE: If the user asks for their name ("What's my name?"), email, or details, ALWAYS use the profile info under KNOWN USER PROFILE & PERSISTENT SESSION MEMORY. If Full Name is known (e.g. Ayush Srivastava), reply directly: "Your name is Ayush Srivastava." If a detail is missing, state clearly that it has not been recorded yet.
8. If you want to present quick-reply choices to the user, include them at the very end of your message using the tag format:
   ### OPTIONS: Option 1, Option 2, Option 3 ###
9. Never guarantee employment, interviews, candidate selection, or hiring timelines.
10. Never invent job openings, pricing, client names, or legal policies.

Now respond directly and naturally to the last user message."""

    if provider == 'groq':
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name or "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.5
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"Groq API error: {e}")

    elif provider == 'openai':
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name or "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.5
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenAI API error: {e}")

    elif provider == 'openrouter':
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": model_name or "openrouter/auto",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.5
            }
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"OpenRouter API error: {e}")

    models = [
        ("gemini-2.5-flash-lite", {}),
        ("gemini-2.5-flash", {}),
        ("gemini-flash-latest", {}),
        ("gemini-flash-lite-latest", {}),
        ("gemini-2.0-flash-lite", {}),
        ("gemini-2.0-flash", {}),
    ]
    for model_name_gem, extra in models:
        for attempt in range(2):
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name_gem}:generateContent?key={api_key}"
                headers = {"Content-Type": "application/json"}
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "maxOutputTokens": 500
                    }
                }
                payload.update(extra)
                response = requests.post(url, headers=headers, json=payload, timeout=12)
                if response.status_code == 503:
                    time.sleep(0.5)
                    continue
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                time.sleep(0.5)

    return "I'm a little busy right now, please try again in a moment!"


def process_and_reply_directly(contact, incoming_text):
    """
    Runs natively in a background thread: processes incoming text, computes
    AI qualification steps, queries Gemini, parses leads metadata, formats buttons,
    sends outbound Meta API call, and broadcasts results back to React.
    """
    try:
        import json
        import re
        from django.utils import timezone
        from whatsapp_app.models import Message
        
        # Load local singleton credentials
        waba_config = get_whatsapp_config()
        config_obj = waba_config.get('config_obj') if isinstance(waba_config, dict) else None
        
        # If config is missing or AI toggle is off, abort
        if not config_obj or not config_obj.is_ai_enabled:
            print(f"INFO: Native AI is disabled on this account. Skipping auto-reply.")
            return

        # Check if conversation has been escalated to human custody
        if contact.attributes and contact.attributes.get('escalated'):
            print(f"Skipping direct AI response for contact {contact.id} because conversation is escalated to human.")
            return

        # Fetch conversation history from DATABASE
        history = parse_database_conversation_history(contact)
        
        # Request Gemini to generate a response with full contact memory context
        waba_config['contact'] = contact
        reply_text = generate_gemini_response(history, waba_config)
        
        # Process qualification state
        state = parse_conversation_state(history)
        step = state["step"]
        
        clean_reply = reply_text
        lead_data = None
        option_strings = []
        
        # 0. Handle structured JSON output from LLM
        try:
            raw_text = (reply_text or "").strip()
            if raw_text.startswith("```"):
                raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.IGNORECASE).strip()
            if raw_text.startswith("{") and raw_text.endswith("}"):
                parsed_json = json.loads(raw_text)
                if isinstance(parsed_json, dict) and "answer" in parsed_json:
                    clean_reply = parsed_json["answer"]
                    if parsed_json.get("quick_replies") and isinstance(parsed_json["quick_replies"], list):
                        option_strings = [str(opt).strip() for opt in parsed_json["quick_replies"] if str(opt).strip()]

                    # Update contact profile & attributes from extracted structured data
                    extracted_fields = parsed_json.get("extracted") or {}
                    if isinstance(extracted_fields, dict):
                        if not contact.attributes or not isinstance(contact.attributes, dict):
                            contact.attributes = {}
                        attrs_updated = False
                        for k, v in extracted_fields.items():
                            if v and str(v).strip() and k not in ("name", "email", "phone"):
                                contact.attributes[k] = v
                                attrs_updated = True
                        if extracted_fields.get("name") and (not contact.name or contact.name == "Unknown"):
                            contact.name = extracted_fields["name"]
                            attrs_updated = True
                        if extracted_fields.get("email") and not contact.email:
                            contact.email = extracted_fields["email"]
                            attrs_updated = True
                        if attrs_updated:
                            contact.save(update_fields=['name', 'email', 'attributes'])
        except Exception:
            pass

        # 1. Check for Lead Metadata JSON exports at step 14
        if "### LEAD_METADATA ###" in reply_text:
            parts = reply_text.split("### LEAD_METADATA ###")
            clean_reply = parts[0].strip()
            clean_reply = re.sub(r"```(json)?\s*$", "", clean_reply).strip()
            
            metadata_str = parts[1].strip()
            metadata_str = re.sub(r"^```json|```$", "", metadata_str).strip()
            
            try:
                lead_data = json.loads(metadata_str)
                print(f"🔥 [NATIVE LEAD CAPTURED]: {lead_data}")
                
                # Write to local file for diagnostic purposes
                with open("leads_captured.txt", "a", encoding="utf-8") as f:
                    f.write(json.dumps(lead_data) + "\n")
                    
                # Natively update Lead fields in Django
                if lead_data.get("name") and contact.name == "Unknown":
                    contact.name = lead_data["name"]
                if lead_data.get("email"):
                    contact.email = lead_data["email"]
                    
                if not contact.attributes:
                    contact.attributes = {}
                    
                for key in lead_data:
                    if lead_data[key] and key not in ("name", "email", "phone"):
                        contact.attributes[key] = lead_data[key]
                        
                contact.save(update_fields=['name', 'email', 'attributes'])
            except Exception as e:
                print(f"Error parsing native lead metadata: {e}")

        # 2. Extract Dynamic UI Interactive Buttons from ### OPTIONS: ... ### tag if not already found from JSON
        interactive_payload = None
        if not option_strings:
            options_match = re.search(r"### OPTIONS:\s*(.*?)###", reply_text, re.DOTALL | re.IGNORECASE)
            if options_match:
                raw_opts = options_match.group(1).strip()
                option_strings = [opt.strip() for opt in raw_opts.split(",") if opt.strip()]
        
        # Clean standard option tags from text
        clean_reply = re.sub(r"### OPTIONS:.*?###", "", clean_reply, flags=re.DOTALL | re.IGNORECASE).strip()
        clean_reply = re.sub(r"[\ufe00-\ufe0f]", "", clean_reply)
        
        # Strip option bullet points from message text body
        if option_strings:
            for opt in option_strings:
                esc_opt = re.escape(opt)
                pattern = rf"(?mi)^\s*(?:<-|<=|->|=>|â†|â†©|[-*â€¢\u2190-\u21FF\u27A1\u2705]|\U0001F449|\U0001F44D)[\ufe00-\ufe0f]?\s*{esc_opt}\s*\r?\n?"
                clean_reply = re.sub(pattern, "", clean_reply)
                clean_reply = re.sub(rf"(?mi)^\s*{esc_opt}\s*\r?\n?", "", clean_reply)
            clean_reply = re.sub(r"\n{3,}", "\n\n", clean_reply).strip()
            
            # Format Interactive WhatsApp buttons or lists
            if 1 <= len(option_strings) <= 3:
                btn_array = []
                for idx, raw_val in enumerate(option_strings):
                    btn_array.append({
                        "type": "reply",
                        "reply": {"id": f"btn_opt_{idx}", "title": raw_val[:20]}
                    })
                interactive_payload = {
                    "type": "button",
                    "body": {"text": clean_reply[:1024]},
                    "action": {"buttons": btn_array}
                }
            elif 4 <= len(option_strings) <= 10:
                row_array = []
                for idx, raw_val in enumerate(option_strings):
                    row_array.append({
                        "id": f"lst_opt_{idx}",
                        "title": raw_val[:24]
                    })
                interactive_payload = {
                    "type": "list",
                    "body": {"text": clean_reply[:1024]},
                    "action": {
                        "button": "Make Selection",
                        "sections": [{
                            "title": "Available Choices",
                            "rows": row_array
                        }]
                    }
                }

        # 3. Create Outgoing Database Message
        msg_type = 'interactive' if interactive_payload else 'text'
        message = Message.objects.create(
            contact=contact,
            text=clean_reply,
            sender='bot',
            direction='OUTGOING',
            status='Waiting',
            type=msg_type,
            buttons=option_strings if option_strings else None,
            timestamp=timezone.now()
        )
        
        # Update Contact last message
        contact.last_message = clean_reply
        contact.last_message_time = message.timestamp
        contact.save(update_fields=['last_message', 'last_message_time'])
        
        # Broadcast standard sending message event to UI
        _broadcast_crm_event('message_sent', contact=contact, message=message)

        # 4. Dispatch natively to Meta APIs
        from whatsapp_app.services import send_whatsapp_message_direct_to_meta
        meta_response, status_code = send_whatsapp_message_direct_to_meta(
            recipient_id=contact.phone_number,
            waba_config=waba_config,
            text=clean_reply,
            interactive=interactive_payload
        )
        
        if status_code in [200, 201] and isinstance(meta_response, dict):
            provider_message_id = None
            if "messages" in meta_response and len(meta_response["messages"]) > 0:
                provider_message_id = meta_response["messages"][0].get("id")
            if provider_message_id:
                message.provider_message_id = provider_message_id
                message.status = 'Sent'
                message.save(update_fields=['provider_message_id', 'status'])
                _broadcast_crm_event('message_status', contact=contact, message=message)
                
    except Exception as e:
        print(f"CRITICAL ERROR in native process_and_reply_directly: {e}")


def process_and_reply_with_aria_core(contact, incoming_text, provider_message_id=None):
    """
    Channel-adapter worker for Aria Core.

    Django stores WhatsApp messages and handles Meta delivery. FastAPI Aria Core
    decides the response, shared user profile, journey state, and lead memory.
    """
    try:
        from django.utils import timezone
        from whatsapp_app.models import Message
        from whatsapp_app.services import send_whatsapp_message_direct_to_meta
        from chatbot_app.services import ChatbotServiceError, send_aria_message

        # Check if conversation has been escalated to human custody
        if contact.attributes and contact.attributes.get('escalated'):
            print(f"Skipping AI response for contact {contact.id} because conversation is escalated to human.")
            return

        # Gated check for Chatbot / AI access in channel and user profile
        if contact.whatsapp_config and not getattr(contact.whatsapp_config, 'is_ai_enabled', True):
            print(f"AI is disabled on WhatsAppConfig channel for contact {contact.id}")
            return

        has_chatbot_access = True
        if contact.whatsapp_config and contact.whatsapp_config.user:
            user_obj = contact.whatsapp_config.user
            from django.db import connection
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        "SELECT chatbot_access, ai_config_access FROM whatsapp_saas_whatsappuser WHERE user_id = %s OR whatsapp_config_id = %s",
                        [user_obj.id, contact.whatsapp_config_id]
                    )
                    row = cursor.fetchone()
                    if row:
                        has_chatbot_access = bool(row[0]) or bool(row[1])
                except Exception:
                    pass

        if not has_chatbot_access:
            print(f"Chatbot access is disabled in SaaS for WhatsApp contact {contact.id}")
            return

        identity = {
            "name": contact.name if contact.name and contact.name != contact.phone_number else None,
            "phone": contact.phone_number,
            "email": contact.email,
            "whatsapp_number": contact.phone_number,
        }
        from whatsapp_app.models import AIConfig
        from whatsapp_app.serializers import AIConfigSerializer
        ai_config_data = None
        try:
            ai_conf = AIConfig.objects.get(whatsapp_config_id=contact.whatsapp_config_id)
            raw_data = AIConfigSerializer(ai_conf).data
            
            behaviours = []
            for b in (raw_data.get("conversation_behaviours") or []):
                behaviours.append({
                    "rule": b.get("name") or b.get("rule") or "",
                    "is_active": b.get("active", b.get("is_active", True))
                })
            
            lead_fields = []
            for f in (raw_data.get("lead_collection") or []):
                lead_fields.append({
                    "field_name": f.get("name") or f.get("field_name") or "",
                    "is_active": f.get("active", f.get("is_active", True))
                })

            ai_config_data = {
                "assistant_name": raw_data.get("assistant_name") or "Assistant",
                "business_name": raw_data.get("business_name") or "Company",
                "personality": raw_data.get("personality") or "Support",
                "tone": raw_data.get("tone") or "friendly",
                "primary_language": raw_data.get("primary_language") or "en",
                "prompt": raw_data.get("prompt") or "",
                "system_prompt": raw_data.get("system_prompt") or raw_data.get("prompt") or "",
                "greeting_message": raw_data.get("greeting_message") or "Hi, how can I help you today?",
                "quick_replies": [r.get("keyword") for r in (raw_data.get("auto_replies") or []) if isinstance(r, dict)],
                "conversation_behaviours": behaviours,
                "lead_collection": lead_fields,
                "faqs": raw_data.get("faqs") or [],
                "websites": raw_data.get("websites") or [],
                "categories": raw_data.get("categories") or [],
                "domain_keywords": raw_data.get("domain_keywords") or {},
                "out_of_scope_message": raw_data.get("out_of_scope_message"),
                "registration_url_template": raw_data.get("registration_url_template"),
                "catalog_api_url": raw_data.get("catalog_api_url"),
                "llm_provider": raw_data.get("llm_provider") or "openai",
                "model_name": raw_data.get("model_name") or "gpt-4o-mini",
                "api_key": raw_data.get("api_key") or None,
            }
        except AIConfig.DoesNotExist:
            pass

        response = send_aria_message(
            channel="whatsapp",
            channel_session_id=str(contact.phone_number),
            message=incoming_text,
            identity=identity,
            metadata={
                "contact_id": contact.id,
                "provider_message_id": provider_message_id,
                "whatsapp_config_id": contact.whatsapp_config_id,
            },
            ai_config=ai_config_data,
        )

        profile = response.get("profile") or {}
        journey = response.get("journey_state") or {}
        answer = (response.get("answer") or "").strip()
        quick_replies = response.get("quick_replies") or []
        if not answer:
            return

        if quick_replies and isinstance(quick_replies, list) and not any(opt in answer for opt in quick_replies):
            formatted_options = "\n".join([f"â€¢ {opt}" for opt in quick_replies if isinstance(opt, str) and opt.strip()])
            if formatted_options:
                answer = f"{answer}\n\nðŸ“Œ *Options:*\n{formatted_options}"

        update_fields = []
        if response.get("aria_user_id") and contact.aria_user_id != response["aria_user_id"]:
            contact.aria_user_id = response["aria_user_id"]
            update_fields.append("aria_user_id")
        if journey.get("current_stage") and contact.aria_journey_stage != journey["current_stage"]:
            contact.aria_journey_stage = journey["current_stage"]
            update_fields.append("aria_journey_stage")
        if profile.get("name") and contact.name != profile["name"]:
            new_name = profile["name"].strip()
            # Do not accept greeting words like "There" or "Hello" as names
            if new_name.lower() not in ("there", "hello", "hi", "hey", "howyou", "how you doing", "unknown"):
                curr_words = len((contact.name or "").split())
                new_words = len(new_name.split())
                if not contact.name or contact.name == "Unknown" or new_words > curr_words:
                    contact.name = new_name
                    update_fields.append("name")
        if profile.get("email") and contact.email != profile["email"]:
            contact.email = profile["email"]
            update_fields.append("email")

        # Evaluate escalation conditions (transfer policy)
        fallback_rule = ai_config_data.get('fallback_rule', 'transfer') if ai_config_data else 'transfer'
        is_handoff_state = (
            journey.get("current_stage") == "CALLBACK_REQUEST"
            or profile.get("advisor_requested")
        )
        if is_handoff_state and fallback_rule == 'transfer':
            if not isinstance(contact.attributes, dict):
                contact.attributes = {}
            contact.attributes['escalated'] = True
            update_fields.append("attributes")

        contact.aria_last_synced_at = timezone.now()
        update_fields.append("aria_last_synced_at")
        if update_fields:
            contact.save(update_fields=list(dict.fromkeys(update_fields)))

        waba_config = get_whatsapp_config(contact.whatsapp_config_id)
        message = Message.objects.create(
            contact=contact,
            text=answer,
            sender="aria",
            direction="OUTGOING",
            status="Waiting",
            type="text",
            timestamp=timezone.now(),
        )
        contact.last_message = answer
        contact.last_message_time = message.timestamp
        contact.save(update_fields=["last_message", "last_message_time"])
        _broadcast_crm_event("message_sent", contact=contact, message=message)

        meta_response, status_code = send_whatsapp_message_direct_to_meta(
            recipient_id=contact.phone_number,
            waba_config=waba_config,
            text=answer,
        )
        if status_code in [200, 201] and isinstance(meta_response, dict):
            sent_id = None
            if meta_response.get("messages"):
                sent_id = meta_response["messages"][0].get("id")
            if sent_id:
                message.provider_message_id = sent_id
            message.status = "Sent"
            message.save(update_fields=["provider_message_id", "status"])
            _broadcast_crm_event("message_status", contact=contact, message=message)
        else:
            message.status = "Failed"
            message.failed_at = timezone.now()
            message.save(update_fields=["status", "failed_at"])
            _broadcast_crm_event("message_status", contact=contact, message=message)

    except ChatbotServiceError as exc:
        print(f"Aria Core unavailable for WhatsApp contact {contact.id}: {exc}. Falling back to native Gemini processing...")
        try:
            process_and_reply_directly(contact, incoming_text)
        except Exception as fallback_exc:
            print(f"Fallback direct processing also failed: {fallback_exc}")
    except Exception as exc:
        print(f"CRITICAL ERROR in process_and_reply_with_aria_core: {exc}")



def resolve_contact_variables(value, contact):
    """
    Dynamically substitutes tokens like {{contact.name}}, {{contact.city}}, {{phone}}, etc.
    with actual values from the Contact instance without hardcoded field lists.
    """
    if not value or not isinstance(value, str):
        return value

    import re
    val_str = str(value)

    def replacer(match):
        token = match.group(1).strip()
        attr_name = token.replace('contact.', '').lower()
        
        # Check exact attribute match on contact
        if hasattr(contact, attr_name):
            attr_val = getattr(contact, attr_name)
            if attr_val is not None and str(attr_val).strip():
                return str(attr_val).strip()

        # Check common field aliases dynamically
        if attr_name == 'name':
            return (getattr(contact, 'name', '') or getattr(contact, 'phone_number', '') or "Customer").strip()
        elif attr_name in ['phone', 'phone_number']:
            return (getattr(contact, 'phone_number', '') or "").strip()
        elif attr_name == 'email':
            return (getattr(contact, 'email', '') or "").strip()

        return match.group(0)

    return re.sub(r'\{\{?([a-zA-Z0-9_\.]+)\}?\}', replacer, val_str)


def send_automation_message(contact, template, media_url=None, template_variables=None):
    """
    Sends a template-based automation message (Follow-up or Reminder)
    directly to Meta, registers it in the database, and broadcasts updates.
    """
    from django.utils import timezone
    from whatsapp_app.models import Message
    from whatsapp_app.services import send_whatsapp_message_direct_to_meta
    import uuid
    import logging
    logger = logging.getLogger(__name__)

    waba_config = get_whatsapp_config(contact.whatsapp_config_id)
    components = []
    template_vars = template_variables or {}
    
    # Resolve template media URL or saved Meta media ID dynamically from schedule / template
    active_media_url = media_url or template_vars.get('media_url') or template_vars.get('header_media_url')
    if not active_media_url:
        active_media_url = template.header_media or template.uploaded_preview_image or template.meta_media_url
        if not active_media_url and template.sample_values and isinstance(template.sample_values, dict):
            active_media_url = template.sample_values.get('header_handle') or template.sample_values.get('media_url') or template.sample_values.get('url')

    # Ignore expired WhatsApp Graph CDN links
    # Do not pass scontent URLs as 'link' - they expire; backend will re-upload instead
    if active_media_url and ('scontent.whatsapp.net' in str(active_media_url) or 'fbcdn.net' in str(active_media_url)):
        active_media_url = None

    pre_uploaded_media_id = None

    # Data URLs (base64) can't be passed as a 'link' - Meta requires a real hosted URL or media_id.
    # Upload the bytes to Meta directly to obtain a stable media_id.
    if active_media_url and str(active_media_url).startswith('data:'):
        try:
            import base64
            from whatsapp_app.services import upload_media_for_message

            meta_info, b64_data = active_media_url.split(',', 1)
            mime_type = 'image/jpeg'
            if ':' in meta_info and ';' in meta_info:
                mime_type = meta_info.split(':', 1)[1].split(';', 1)[0]

            ext_map = {
                "image/jpeg": "jpg",
                "image/png": "png",
                "image/gif": "gif",
                "image/webp": "webp",
                "video/mp4": "mp4",
                "application/pdf": "pdf",
            }
            file_name = f"template_header.{ext_map.get(mime_type, 'bin')}"
            file_bytes = base64.b64decode(b64_data)

            pre_uploaded_media_id = upload_media_for_message(file_bytes, file_name, mime_type, waba_config)
            active_media_url = None

            # Save the media_id back to the template so future sends don't need to re-upload
            if pre_uploaded_media_id and template:
                try:
                    template.header_media = pre_uploaded_media_id
                    template.save(update_fields=['header_media'])
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Automation message base64 media upload failed: {e}")
            active_media_url = None
    if template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT']:
        header_type = template.header_type.lower()
        if not active_media_url:
            try:
                import requests as _req
                w_token = waba_config.get('whatsapp_token')
                w_waba_id = waba_config.get('waba_id')
                w_phone_id = waba_config.get('phone_id')
                if w_token and w_waba_id:
                    meta_tpl_url = f"https://graph.facebook.com/v20.0/{w_waba_id}/message_templates?name={template.name}"
                    res_tpl = _req.get(meta_tpl_url, headers={'Authorization': f'Bearer {w_token}'}, timeout=5)
                    if res_tpl.status_code == 200:
                        tpl_data = res_tpl.json().get('data', [])
                        if tpl_data:
                            for comp in tpl_data[0].get('components', []):
                                if comp.get('type') == 'HEADER':
                                    handles = comp.get('example', {}).get('header_handle', [])
                                    if handles and handles[0]:
                                        scontent_url = handles[0]
                                        # Download the video and re-upload to get a stable media_id
                                        try:
                                            mime_map = {'video': 'video/mp4', 'image': 'image/jpeg', 'document': 'application/pdf'}
                                            ext_map = {'video': 'video.mp4', 'image': 'image.jpg', 'document': 'doc.pdf'}
                                            r_dl = _req.get(scontent_url, timeout=30)
                                            if r_dl.status_code == 200 and w_phone_id:
                                                upload_url = f"https://graph.facebook.com/v20.0/{w_phone_id}/media"
                                                files = {'file': (ext_map.get(header_type, 'file'), r_dl.content, mime_map.get(header_type, 'application/octet-stream'))}
                                                upload_data = {'messaging_product': 'whatsapp', 'type': mime_map.get(header_type, 'video/mp4')}
                                                r_up = _req.post(upload_url, headers={'Authorization': f'Bearer {w_token}'}, files=files, data=upload_data, timeout=60)
                                                if r_up.status_code == 200:
                                                    pre_uploaded_media_id = r_up.json().get('id')
                                                    logger.info(f"Uploaded Meta template media to get stable media_id: {pre_uploaded_media_id}")
                                                    # Cache it on the template so every future send (and every other
                                                    # contact in the same bulk run) reuses this id instead of
                                                    # re-downloading and re-uploading the full video/image from
                                                    # Meta's CDN on every single message - this repeated download+
                                                    # reupload under ThreadPoolExecutor's 20 concurrent workers is
                                                    # what drove WaB to 1.4GB+ RSS during tonight's bulk reminder run.
                                                    if pre_uploaded_media_id and template:
                                                        try:
                                                            template.header_media = pre_uploaded_media_id
                                                            template.save(update_fields=['header_media'])
                                                        except Exception:
                                                            pass
                                                else:
                                                    logger.warning(f"Media re-upload failed: {r_up.status_code} {r_up.text[:200]}")
                                                    active_media_url = scontent_url  # fallback to link
                                            else:
                                                logger.warning(f"Could not download scontent media (status={r_dl.status_code}), falling back to link")
                                                active_media_url = scontent_url
                                        except Exception as up_err:
                                            logger.warning(f"Media re-upload error: {up_err}, falling back to link")
                                            active_media_url = scontent_url
                                        break
            except Exception as e:
                logger.warning(f"Could not fetch Meta header_handle: {e}")

        if not active_media_url:
            if header_type == 'image':
                active_media_url = 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800'
            elif header_type == 'video':
                active_media_url = 'https://www.w3schools.com/html/mov_bbb.mp4'
            elif header_type == 'document':
                active_media_url = 'https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf'

        if active_media_url and str(active_media_url).strip().isdigit():
            pre_uploaded_media_id = str(active_media_url).strip()
            active_media_url = None

        if pre_uploaded_media_id:
            media_obj = {"id": pre_uploaded_media_id}
            if header_type == 'document':
                media_obj["filename"] = 'document.pdf'
            components.append({
                "type": "header",
                "parameters": [
                    {
                        "type": header_type,
                        header_type: media_obj
                    }
                ]
            })
        elif active_media_url:
            components.append({
                "type": "header",
                "parameters": [
                    {
                        "type": header_type,
                        header_type: {"link": active_media_url}
                    }
                ]
            })
    elif template.header_type == 'TEXT':
        import re
        header_text_val = template.header_text or ''
        has_header_param = re.search(r'\{\{([^}]+)\}\}', header_text_val)
        if has_header_param:
            placeholder_name = has_header_param.group(1).strip()
            param_val = template_vars.get('header_text') or template_vars.get('header_1') or contact.name or "Customer"
            resolved_header = resolve_contact_variables(str(param_val), contact)
            
            param_obj = {
                "type": "text",
                "text": str(resolved_header)
            }
            if not placeholder_name.isdigit():
                param_obj["parameter_name"] = placeholder_name
                
            components.append({
                "type": "header",
                "parameters": [param_obj]
            })

    # Body variables {{1}}, {{2}}, or {{text}}, etc.
    import re
    body_text = template.body or ''
    all_placeholders = re.findall(r'\{\{([^}]+)\}\}', body_text)
    digit_placeholders = [int(m) for m in re.findall(r'\{\{(\d+)\}\}', body_text)] if re.findall(r'\{\{(\d+)\}\}', body_text) else []
    max_digit = max(digit_placeholders, default=0)

    raw_body_vars = template_vars.get('body_variables') if isinstance(template_vars, dict) else []
    raw_var_count = len(raw_body_vars) if isinstance(raw_body_vars, list) else 0

    actual_body_placeholders = max(len(all_placeholders), max_digit)
    num_placeholders = actual_body_placeholders if actual_body_placeholders > 0 else 0

    body_params = []
    if num_placeholders > 0:
        for i in range(1, num_placeholders + 1):
            val = None
            if isinstance(template_vars, dict):
                val = template_vars.get(str(i)) or template_vars.get(f'1_{i}') or template_vars.get(f'body_{i}') or template_vars.get(f'var_{i}')
            if not val and isinstance(raw_body_vars, list) and i - 1 < len(raw_body_vars):
                val = raw_body_vars[i - 1]
            if not val and isinstance(raw_body_vars, dict):
                val = raw_body_vars.get(str(i)) or raw_body_vars.get(f'1_{i}')
            
            # Smart fallbacks if user left field empty
            if not val:
                if i == 1:
                    val = contact.name or "Customer"
                elif i == 2:
                    val = "Appointment"
                else:
                    val = "Details"
            
            # Substitute any dynamic variables like {{contact.name}}, {{contact.phone}}, etc.
            val = resolve_contact_variables(val, contact)
            
            placeholder_token = all_placeholders[i - 1].strip() if (i - 1 < len(all_placeholders)) else None
            param_dict = {"type": "text", "text": str(val)}
            if placeholder_token and not placeholder_token.isdigit():
                param_dict["parameter_name"] = placeholder_token
                
            body_params.append(param_dict)

        if body_params:
            components.append({
                "type": "body",
                "parameters": body_params
            })

    # Button variables (dynamic URL suffixes / payloads)
    button_vars = template_vars.get('button_variables', []) if isinstance(template_vars, dict) else []
    if isinstance(button_vars, list) and len(button_vars) > 0:
        for idx, btn_val in enumerate(button_vars):
            components.append({
                "type": "button",
                "sub_type": "url",
                "index": str(idx),
                "parameters": [{"type": "payload", "payload": str(btn_val)}]
            })

    # Render body template for DB log message
    from whatsapp_app.utils import render_template
    vars_dict = {}
    if isinstance(raw_body_vars, list):
        for i, val in enumerate(raw_body_vars):
            vars_dict[str(i+1)] = str(val)
            # Also key by the placeholder's actual token (e.g. "text", "contact.name")
            # so named placeholders - not just {{1}}, {{2}}... - get filled in below.
            if i < len(all_placeholders):
                token = all_placeholders[i].strip()
                if token and not token.isdigit():
                    vars_dict[token] = str(val)
    parsed_message = render_template(template.body or template.name, vars_dict)
    # Final safety net for any remaining {{contact.*}} tokens not covered above
    # (e.g. left blank by the operator, or not in vars_dict at all).
    parsed_message = resolve_contact_variables(parsed_message, contact)

    phone = _normalize_phone_number(contact.phone_number)
    generated_provider_message_id = str(uuid.uuid4())

    meta_response, status_code = send_whatsapp_message_direct_to_meta(
        recipient_id=phone,
        waba_config=waba_config,
        text=parsed_message,
        template_name=template.name,
        language_code=template.language or "en_US",
        components=components,
        media_url=active_media_url,
        media_type=template.header_type.lower() if template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT'] else None
    )

    if status_code not in [200, 201]:
        raise Exception(f"Meta returned HTTP {status_code}: {meta_response}")

    res_data = meta_response if isinstance(meta_response, dict) else {}
    provider_id = extract_provider_message_id(res_data, fallback=generated_provider_message_id)

    # Store our own lazily-resolvable media link for local display, independent of whatever
    # form (direct link vs Meta media_id) was actually used for the Meta send above - that
    # step nulls out active_media_url whenever a media_id is used (the common case), which
    # would otherwise leave our own inbox with nothing to render even though Meta delivered
    # the media to the recipient fine. This endpoint re-resolves the template's current
    # header media (including from a data: URI) at fetch time.
    stored_media_url = active_media_url
    if template.header_type in ['IMAGE', 'VIDEO', 'DOCUMENT']:
        stored_media_url = f"/templates/{template.id}/header-media/?type={template.header_type.lower()}"

    msg = Message.objects.create(
        contact=contact,
        text=parsed_message,
        sender='automation',
        direction='OUTGOING',
        status='Sent',
        type='template',
        provider_message_id=provider_id,
        media_url=stored_media_url,
        buttons=template.buttons or [],
        timestamp=timezone.now()
    )

    contact.last_message = parsed_message
    contact.last_message_time = timezone.now()
    contact.save(update_fields=['last_message', 'last_message_time'])

    _broadcast_crm_event('message_sent', contact=contact, message=msg)
    return msg


def send_whatsapp_template_message(config, to_phone, template_name, language_code="en_US"):
    from whatsapp_app.services import send_whatsapp_message_direct_to_meta
    
    if hasattr(config, 'phone_id'):
        waba_config = {
            'phone_id': config.phone_id,
            'whatsapp_token': config.whatsapp_token,
            'waba_id': config.waba_id,
        }
    elif isinstance(config, dict):
        waba_config = config
    else:
        waba_config = {}
        
    res_data, status_code = send_whatsapp_message_direct_to_meta(
        recipient_id=to_phone,
        waba_config=waba_config,
        template_name=template_name,
        language_code=language_code
    )
    if status_code not in [200, 201]:
        raise Exception(f"Meta returned HTTP {status_code}: {res_data}")
    return res_data


