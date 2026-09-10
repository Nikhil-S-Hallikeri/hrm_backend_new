"""
WhatsApp App Authentication.

Uses HRM's existing session/token from sessionStorage ('user' key) to identify
the logged-in employee. For API calls from the WA frontend module, the HRM
employee ID is passed via the X-HRM-Employee-ID header or falls back to
DRF default authentication (session/basic).

We keep SimpleJWT imported so the WA module's own JWT endpoints (login/signup)
still work for standalone WA-only login if needed in future, but all HRM-
integrated requests authenticate via the HRM session.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from HRM_App.models import RegistrationModel


class HRMEmployeeAuthentication(BaseAuthentication):
    """
    Lightweight authentication that reads the X-HRM-Employee-ID header
    and returns the matching RegistrationModel instance as request.user.
    
    The HRM React frontend stores the logged-in employee's EmployeeId in
    sessionStorage under the 'user' key. The WA axios instance reads it
    and attaches it as the X-HRM-Employee-ID header on every request.
    """

    def authenticate(self, request):
        emp_id = (
            request.headers.get('X-HRM-Employee-ID')
            or request.META.get('HTTP_X_HRM_EMPLOYEE_ID')
        )
        if not emp_id:
            return None  # Let other authenticators try

        try:
            employee = RegistrationModel.objects.get(EmployeeId=emp_id, is_active=True)
        except RegistrationModel.DoesNotExist:
            raise AuthenticationFailed('HRM employee not found or inactive.')

        return (employee, None)

    def authenticate_header(self, request):
        return 'X-HRM-Employee-ID'


# Keep a thin wrapper so existing whatsapp_app code that references
# CustomJWTAuthentication doesn't break — it just falls back to our
# HRM employee auth above.
CustomJWTAuthentication = HRMEmployeeAuthentication
