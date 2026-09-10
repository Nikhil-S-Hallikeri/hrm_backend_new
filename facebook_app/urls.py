from django.urls import path
from . import views

urlpatterns = [
    path('lead', views.facebook_lead_list_create, name='facebook_lead_list_create'),
    path('lead/unique-ads', views.get_unique_ads, name='get_unique_ads'),
    path('sync', views.synced_data, name='synced_data'),
    path('sync-data', views.sync_facebook_lead_data, name='sync_facebook_lead_data'),
    path('pass-crm', views.passing_one_lead_to_crm, name='passing_one_lead_to_crm'),
    
    # Backwards compatibility and standard route matching
    path('unique-ads', views.get_unique_ads, name='get_unique_ads_legacy'),

    # Config automation CRUD endpoints
    path('', views.facebook_config_list_create_update, name='facebook_config_list_create_update'),
    path('<int:id>', views.facebook_config_detail_delete, name='facebook_config_detail_delete'),
]
