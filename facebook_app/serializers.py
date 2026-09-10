from rest_framework import serializers
from .models import FacebookConfig, FacebookPage, FacebookLead

class FacebookPageSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False)
    
    class Meta:
        model = FacebookPage
        fields = [
            'id', 'page_name', 'page_id', 'page_access_token', 
            'expiry_date', 'generated_date', 'active_status', 
            'allowed_ad_ids', 'not_allowed_ad_ids', 'auto_assign_employee'
        ]
        extra_kwargs = {
            'page_id': {
                'validators': []  # Disable default UniqueValidator for nested updates
            }
        }

class FacebookConfigSerializer(serializers.ModelSerializer):
    pages = FacebookPageSerializer(many=True, required=False)

    class Meta:
        model = FacebookConfig
        fields = ['id', 'app_name', 'app_id', 'app_secret', 'verify_token', 'active_status', 'pages', 'created_at', 'updated_at']

    def create(self, validated_data):
        pages_data = validated_data.pop('pages', [])
        config = FacebookConfig.objects.create(**validated_data)
        for page_data in pages_data:
            FacebookPage.objects.create(config=config, **page_data)
        return config

    def update(self, instance, validated_data):
        pages_data = validated_data.pop('pages', None)
        
        # Update top-level config fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if pages_data is not None:
            # We can delete all and re-create pages, or update existing.
            # To mirror MongoDB single-document replacement, deleting and re-creating is easiest and most robust.
            instance.pages.all().delete()
            for page_data in pages_data:
                # Remove optional nested ID if passed from FE
                page_data.pop('id', None)
                FacebookPage.objects.create(config=instance, **page_data)
                
        return instance


class FacebookLeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacebookLead
        fields = '__all__'
