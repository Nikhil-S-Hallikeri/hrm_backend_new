from django.urls import path,include
from .views import *
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter


urlpatterns = [

    path("AllowanceTemplateCreating",AllowanceTemplatesCreating.as_view()),
    path("AllowanceDelete/<int:id>/",AllowanceTemplatesCreating.as_view()),
    
    path("SalaryTemplates",EmployeesSalaryTemplatesCreating.as_view()),
    path("EmployeeSalaryTemplate/<int:pk>/",EmployeesSalaryTemplatesCreating.as_view()),

    path("EmployeeSalaryBreakUps",EmployeeSalaryBreakUpBulkCreateView.as_view()),

    path("EmployeesPaySlip/<int:month>/<int:year>/",EmployeesForPaySlip.as_view()),
    path("SingleEmployeesPaySlip/<int:month>/<int:year>/<str:emp_id>/",EmployeesForPaySlip.as_view()),
    
    path("DownloadEmployeePaySlipExcel/<int:month>/<int:year>/",DownloadEmployeePaySlipsExcel.as_view())


    ]