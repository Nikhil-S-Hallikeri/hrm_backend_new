import logging
from rest_framework import permissions

logger = logging.getLogger(__name__)

class HasActiveSubscription(permissions.BasePermission):
    message = "You don't have an active subscription plan. Please contact your system administrator."

    def has_permission(self, request, view):
        user = request.user
        if not user or not getattr(user, 'is_authenticated', False):
            return False

        # RegistrationModel uses is_active; standard Django users have is_superuser/is_staff
        if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
            return True

        return getattr(user, 'is_active', False)


