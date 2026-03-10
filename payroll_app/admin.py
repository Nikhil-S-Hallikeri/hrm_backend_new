from django.contrib import admin

# Register your models here.
from django.contrib import admin

# Register your models here.
from .models import*
from .models import EmployeeSalaryBreakUp, AllowanceType,EmployeePaySlips

# admin.site.register(Type)

admin.site.register(EmployeeSalaryBreakUp)

admin.site.register(SalaryTemplate)

admin.site.register(AllowanceType)

admin.site.register(EmployeePaySlips)