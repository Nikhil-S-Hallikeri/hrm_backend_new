from django.db import models

class FacebookConfig(models.Model):
    ACTIVE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    app_name = models.CharField(max_length=255, unique=True)
    app_id = models.CharField(max_length=255)
    app_secret = models.CharField(max_length=255)
    verify_token = models.CharField(max_length=255)
    active_status = models.CharField(
        max_length=20, 
        choices=ACTIVE_STATUS_CHOICES, 
        default='active'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.app_name


class FacebookPage(models.Model):
    ACTIVE_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]

    config = models.ForeignKey(
        FacebookConfig, 
        on_delete=models.CASCADE, 
        related_name='pages'
    )
    page_name = models.CharField(max_length=255)
    page_id = models.CharField(max_length=255, unique=True)
    page_access_token = models.TextField()
    expiry_date = models.DateTimeField(null=True, blank=True)
    generated_date = models.DateTimeField(null=True, blank=True)
    active_status = models.CharField(
        max_length=20, 
        choices=ACTIVE_STATUS_CHOICES, 
        default='active'
    )
    allowed_ad_ids = models.JSONField(default=list, blank=True)
    not_allowed_ad_ids = models.JSONField(default=list, blank=True)
    auto_assign_employee = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.page_name} ({self.page_id})"


class FacebookLead(models.Model):
    leadgen_id = models.CharField(max_length=100, unique=True, db_index=True)
    ad_id = models.CharField(max_length=100, null=True, blank=True)
    ad_name = models.CharField(max_length=255, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=50, null=True, blank=True)
    
    facebook_ad_detail = models.JSONField(null=True, blank=True)
    lead_gen_data = models.JSONField(null=True, blank=True)
    
    synced = models.BooleanField(default=False)
    synced_at = models.DateTimeField(null=True, blank=True)
    crm_sync = models.BooleanField(default=False)
    crm_sync_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Lead {self.leadgen_id} - {self.full_name or 'No Name'}"
