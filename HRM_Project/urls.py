"""
URL configuration for HRM_Project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from LMS_App.views import Job_Description_View

urlpatterns = [
    path('admin/', admin.site.urls),
    path("root/",include('HRM_App.urls')),
    path("root/ems/",include('EMS_App.urls')),
    path("root/lms/",include('LMS_App.urls')),
    path("root/pms/",include('payroll_app.urls')),
    path("root/cms/",include('Contract_Emp_App.urls')),
    path('api/job_description/', Job_Description_View.as_view(), name='job_description'),
    #6/01/2026
    # path('api/job_description/<int:pk>/', Job_Description_View.as_view(), name='job_description_detail'),
    path('api/job_description/<str:pk>/', Job_Description_View.as_view(), name='job_description_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

