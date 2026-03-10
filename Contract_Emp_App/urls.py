from django.urls import path,include
from django.conf import settings
from django.conf.urls.static import static
from .views import *

urlpatterns = [
    
    path("clients",OurClientsView.as_view()),
    path('documents/', ClientsDocumentsAPIView.as_view()),  # For POST
    path('documents/<int:pk>/', ClientsDocumentsAPIView.as_view()),
    path("add-clients-requirements",RequirementsView.as_view()),
    path("assign-requirements",ClientRequirementAssignView.as_view()),
    path("client-interviews-assigned",ClientInverviewsAssignedCandidatesList.as_view()),
    path("recruiters-requirement-access",RecruitersRequirementAccess.as_view()),
    path("ClientInterviews",ClientInterviewList.as_view()),
    
    # date 05/12/2024
    path("assigned-requirements-interviews/<str:login_emp>",AssignedRequirementsInterviews.as_view()),
    path("client-finalstatus-count",ClientFinalStatusListCountView.as_view()),

    path('client-joining/', ClientCandidateJoiningHistoryView.as_view(), name='client-joining-create'),
    path('client-joining/<int:pk>/', ClientCandidateJoiningHistoryView.as_view(), name='client-joining-update'),
    path("client-requirement-invoice-generate",ClientRequirementInvoiceGenerationView.as_view())

]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)