import threading
from django.utils import timezone

_thread_locals = threading.local()


class JWTSessionMiddleware:
    """
    Minimal session middleware — in HRM integration we use X-HRM-Employee-ID header
    for auth. This middleware is kept as a no-op so existing imports don't break.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response


class WhatsAppConfigMiddleware:
    """
    Middleware to extract X-WhatsApp-Config-ID header and store it in thread-local storage.
    Used by views to determine which WhatsAppConfig to use for multi-config scenarios.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        config_id = (
            request.headers.get('X-WhatsApp-Config-ID')
            or request.META.get('HTTP_X_WHATSAPP_CONFIG_ID')
        )
        if config_id:
            try:
                _thread_locals.active_config_id = int(config_id)
            except ValueError:
                _thread_locals.active_config_id = None
        else:
            _thread_locals.active_config_id = None

        response = self.get_response(request)

        # Cleanup thread-local to prevent leaks
        if hasattr(_thread_locals, 'active_config_id'):
            del _thread_locals.active_config_id

        return response


def get_current_request_config_id():
    """
    Retrieve the active WhatsAppConfig ID stored in the current thread lifecycle.
    """
    return getattr(_thread_locals, 'active_config_id', None)
