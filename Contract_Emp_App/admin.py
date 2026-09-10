from django.contrib import admin

# Register your models here.
from .models import *
from django.apps import apps

Req_Assign_Model = apps.get_app_config('HRM_App').get_model('RequirementAssign')

admin.site.register(OurClients)
admin.site.register(Requirement)
admin.site.register(Req_Assign_Model)


