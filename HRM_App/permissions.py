# HRM_App/permissions.py

from rest_framework.permissions import BasePermission
# from rest_framework_api_key.permissions import BaseHasAPIKey
# from rest_framework_api_key.models import APIKey

class IsHRManager(BasePermission):
    """
    Allows access only to authenticated users who are in the 'HRM' group.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return request.user.groups.filter(name='HRM').exists()

# class HasApiServiceKey(BaseHasAPIKey):
#     """
#     Allows access only to requests that include a valid, unrevoked API Key.
#     This is for service-to-service authentication (CRM -> HRM).
#     """
#     model = APIKey



    