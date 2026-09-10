from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from whatsapp_app.models import User, WhatsAppConfig, Contact, Message, MessageTemplate, Notification, Campaign
from whatsapp_app.middleware import _thread_locals

class MultiNumberCRMTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create a test User
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpassword123",
            role="ADMIN",
            is_staff=True,
            is_superuser=True
        )
        # Authenticate the user by default
        self.client.force_authenticate(user=self.user)

        # Create two distinct WhatsApp configurations
        self.config_sales = WhatsAppConfig.objects.create(
            name="Sales WhatsApp",
            phone_number_id="phone_sales_123",
            whatsapp_business_account_id="waba_sales_123",
            webhook_verify_token="verify_token_sales",
            whatsapp_api_token="dummy_token_sales",
            is_ai_enabled=False
        )

        self.config_support = WhatsAppConfig.objects.create(
            name="Support WhatsApp",
            phone_number_id="phone_support_456",
            whatsapp_business_account_id="waba_support_456",
            webhook_verify_token="verify_token_support",
            whatsapp_api_token="dummy_token_support",
            is_ai_enabled=True
        )

        # Create contacts linked to respective configs
        self.contact_sales = Contact.objects.create(
            name="Sales Client",
            phone_number="911234567890", # Match webhook wa_id format
            whatsapp_config=self.config_sales,
            user=self.user
        )

        self.contact_support = Contact.objects.create(
            name="Support Client",
            phone_number="911234567890", # Match webhook wa_id format
            whatsapp_config=self.config_support,
            user=self.user
        )

    def tearDown(self):
        # Clean up thread local context if any
        if hasattr(_thread_locals, 'active_config_id'):
            del _thread_locals.active_config_id

    def test_multi_config_creation(self):
        """Verify that multiple configuration records exist without forced id=1 constraint."""
        configs = list(WhatsAppConfig.objects.all())
        self.assertEqual(len(configs), 2)
        self.assertEqual(configs[0].name, "Sales WhatsApp")
        self.assertEqual(configs[1].name, "Support WhatsApp")

    def test_middleware_and_header_isolation(self):
        """Verify that requests containing specific X-WhatsApp-Config-ID headers filter viewsets accordingly."""
        # 1. Fetch contacts with X-WhatsApp-Config-ID for Sales
        self.client.credentials(HTTP_X_WHATSAPP_CONFIG_ID=str(self.config_sales.id))
        response = self.client.get(reverse('contacts-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify the returned contact is contact_sales
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Sales Client")

        # 2. Fetch contacts with X-WhatsApp-Config-ID for Support
        self.client.credentials(HTTP_X_WHATSAPP_CONFIG_ID=str(self.config_support.id))
        response = self.client.get(reverse('contacts-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Support Client")

    def test_webhook_verification_across_configs(self):
        """Verify that hub.verify_token matches any verify token from active configs."""
        # Unauthenticate client to test webhook endpoints which are public (AllowAny)
        self.client.force_authenticate(user=None)
        url = reverse('whatsapp-webhook-events')

        # Test valid sales token
        response = self.client.get(url, {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'verify_token_sales',
            'hub.challenge': 'sales_challenge'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode(), 'sales_challenge')

        # Test valid support token
        response = self.client.get(url, {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'verify_token_support',
            'hub.challenge': 'support_challenge'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content.decode(), 'support_challenge')

        # Test invalid token
        response = self.client.get(url, {
            'hub.mode': 'subscribe',
            'hub.verify_token': 'wrong_token',
            'hub.challenge': 'challenge_123'
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_webhook_event_routing(self):
        """Verify that incoming webhook events are correctly mapped to the matching phone_number_id config."""
        self.client.force_authenticate(user=None)
        url = reverse('whatsapp-webhook-events')

        # Construct raw payload mock representing a message from "1234567890" incoming to support channel
        payload = {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": "waba_support_456",
                    "changes": [
                        {
                            "value": {
                                "messaging_product": "whatsapp",
                                "metadata": {
                                    "display_phone_number": "16505551111",
                                    "phone_number_id": "phone_support_456" # Routes to Support Config
                                },
                                "contacts": [
                                    {
                                        "profile": {"name": "Customer User"},
                                        "wa_id": "911234567890"
                                    }
                                ],
                                "messages": [
                                    {
                                        "from": "911234567890",
                                        "id": "message_id_support_999",
                                        "timestamp": str(int(timezone.now().timestamp())),
                                        "type": "text",
                                        "text": {"body": "Hello Support, I need help"}
                                    }
                                ]
                            },
                            "field": "messages"
                        }
                    ]
                }
            ]
        }

        # Post the webhook payload
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if a Message object was created under Support Config
        messages = Message.objects.filter(provider_message_id="message_id_support_999")
        self.assertEqual(messages.count(), 1)
        self.assertEqual(messages.first().contact.whatsapp_config, self.config_support)
        self.assertEqual(messages.first().contact, self.contact_support)

    def test_inbox_viewset_config_isolation(self):
        """Verify that InboxViewSet conversations and messages are isolated by X-WhatsApp-Config-ID."""
        # 1. Test conversations isolation
        # For Sales configuration
        self.client.credentials(HTTP_X_WHATSAPP_CONFIG_ID=str(self.config_sales.id))
        response = self.client.get(reverse('inbox-conversations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Sales Client")

        # For Support configuration
        self.client.credentials(HTTP_X_WHATSAPP_CONFIG_ID=str(self.config_support.id))
        response = self.client.get(reverse('inbox-conversations'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], "Support Client")

        # 2. Test messages isolation (Sales contact under Support config should be 404)
        # Check sales contact messages under support config -> Should return 404 not found
        response = self.client.get(reverse('inbox-messages'), {'contact_id': self.contact_sales.id})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Check support contact messages under support config -> Should return 200 OK
        response = self.client.get(reverse('inbox-messages'), {'contact_id': self.contact_support.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_serializer_uniqueness_by_config(self):
        """Verify serializer allows duplicate contact phone numbers under different configs but blocks duplicate in same config."""
        from whatsapp_app.serializers import ContactSerializer
        
        # 1. Clean database contacts to test serialization validator clean slate
        Contact.objects.filter(phone_number="919988776655").delete()

        # 2. Serialize creation request for Sales Config
        # Using a dummy request object to supply request context
        from django.test.client import RequestFactory
        factory = RequestFactory()
        request = factory.post('/api/contacts/', data={'phone_number': '919988776655', 'whatsapp_config': self.config_sales.id})
        request.user = self.user
        
        # Validate data with serializer context
        serializer_sales = ContactSerializer(
            data={'phone_number': '919988776655', 'whatsapp_config': self.config_sales.id},
            context={'request': request}
        )
        self.assertTrue(serializer_sales.is_valid(), serializer_sales.errors)
        serializer_sales.save(user=self.user, whatsapp_config=self.config_sales)

        # 3. Serialize creation request for Support Config with the same phone number
        request_support = factory.post('/api/contacts/', data={'phone_number': '919988776655', 'whatsapp_config': self.config_support.id})
        request_support.user = self.user
        
        serializer_support = ContactSerializer(
            data={'phone_number': '919988776655', 'whatsapp_config': self.config_support.id},
            context={'request': request_support}
        )
        # Should be valid because config is different!
        self.assertTrue(serializer_support.is_valid(), serializer_support.errors)
        serializer_support.save(user=self.user, whatsapp_config=self.config_support)

        # 4. Serialize creation request for same Sales Config again -> Should fail validation
        request_dup = factory.post('/api/contacts/', data={'phone_number': '919988776655', 'whatsapp_config': self.config_sales.id})
        request_dup.user = self.user

        serializer_sales_dup = ContactSerializer(
            data={'phone_number': '919988776655', 'whatsapp_config': self.config_sales.id},
            context={'request': request_dup}
        )
        self.assertFalse(serializer_sales_dup.is_valid())
        self.assertIn('phone_number', serializer_sales_dup.errors)

    def test_reminder_campaign_update_preserves_executions(self):
        """Verify updating a ReminderCampaign updates schedules in-place and preserves ReminderExecution history for existing contacts."""
        from whatsapp_app.models import ReminderCampaign, ReminderSchedule, ReminderExecution
        from whatsapp_app.serializers import ReminderCampaignSerializer

        # 1. Create a campaign with 1 schedule and User 1
        campaign = ReminderCampaign.objects.create(
            name="Webinar Reminder",
            whatsapp_config=self.config_sales,
            event_type="WEBINAR",
            event_title="SaaS Demo",
            event_date_time=timezone.now() + timezone.timedelta(days=1),
            created_by=self.user
        )
        campaign.contacts.add(self.contact_sales)

        schedule = ReminderSchedule.objects.create(
            reminder_campaign=campaign,
            timing_type="1_HOUR_BEFORE",
            stage_name="Initial Invite",
            button_actions={"btn1": {"action": "SEND_TEMPLATE"}}
        )

        # 2. Simulate User 1 receiving the message (SENT status)
        exec_user1 = ReminderExecution.objects.create(
            reminder_campaign=campaign,
            contact=self.contact_sales,
            schedule=schedule,
            status="SENT",
            execution_time=timezone.now()
        )

        # 3. Create User 2 (new recipient)
        user2 = Contact.objects.create(
            name="New User 2",
            phone_number="918904329482",
            whatsapp_config=self.config_sales,
            user=self.user
        )

        # 4. Perform campaign update via serializer (adding extra buttons and adding User 2)
        update_data = {
            "name": "Webinar Reminder (Updated)",
            "contacts": [self.contact_sales.id, user2.id],
            "schedules": [
                {
                    "id": schedule.id,
                    "timing_type": "1_HOUR_BEFORE",
                    "button_actions": {
                        "btn1": {"action": "SEND_TEMPLATE"},
                        "btn2": {"action": "STOP"}  # Extra button added!
                    }
                }
            ]
        }

        serializer = ReminderCampaignSerializer(campaign, data=update_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        updated_campaign = serializer.save()

        # 5. Assertions:
        # A. Schedule ID should be preserved (in-place update)
        schedules = list(updated_campaign.schedules.all())
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0].id, schedule.id)
        self.assertIn("btn2", schedules[0].button_actions)

        # B. User 1's SENT execution record must be intact
        exec_user1_refreshed = ReminderExecution.objects.filter(id=exec_user1.id).first()
        self.assertIsNotNone(exec_user1_refreshed)
        self.assertEqual(exec_user1_refreshed.status, "SENT")

        # C. Contacts list now has 2 users
        self.assertEqual(updated_campaign.contacts.count(), 2)


class PublicCampaignTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="client@porchgeek.in", password="password123", name="Jane Client")
        self.config = WhatsAppConfig.objects.create(name="Test WABA", user=self.user)
        self.template = MessageTemplate.objects.create(
            name="welcome_template",
            category="MARKETING",
            body="Hello {{1}}, welcome to our campaign!",
            created_by=self.user
        )
        self.campaign = Campaign.objects.create(
            name="Special Offer",
            template=self.template,
            created_by=self.user,
            whatsapp_config=self.config
        )

    def test_public_campaign_detail_view(self):
        response = self.client.get('/public/campaign/jane-client/special-offer/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['campaign_name'], "Special Offer")
        self.assertEqual(response.json()['user_name'], "Jane Client")
        self.assertEqual(response.json()['template']['name'], "welcome_template")

    def test_public_campaign_submit_lead_view(self):
        payload = {
            "campaign_id": self.campaign.id,
            "name": "New Lead",
            "phone_number": "+919876543210"
        }
        response = self.client.post('/public/campaign/submit-lead/', data=payload, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()['success'])

        # Verify contact created and added to campaign
        contact = Contact.objects.get(phone_number="919876543210")
        self.assertEqual(contact.name, "New Lead")
        self.assertIn(contact, self.campaign.contacts.all())



