import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from whatsapp_app.models import WhatsAppTemplate


class Command(BaseCommand):
    help = "Sync approved WhatsApp templates from Flask middleware into local cache."

    def handle(self, *args, **options):
        flask_url = getattr(settings, 'FLASK_SERVER_URL', 'http://127.0.0.1:5000')
        flask_token = getattr(settings, 'FLASK_AUTH_TOKEN', 'super_secret_crm_token_123')
        endpoint = f"{flask_url.rstrip('/')}/templates"

        headers = {
            "Authorization": f"Bearer {flask_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(endpoint, headers=headers, timeout=20)
        except requests.RequestException as exc:
            self.stderr.write(self.style.ERROR(f"Failed to reach Flask middleware: {exc}"))
            return

        if response.status_code != 200:
            self.stderr.write(
                self.style.ERROR(
                    f"Flask middleware returned {response.status_code}: {response.text}"
                )
            )
            return

        try:
            payload = response.json()
        except ValueError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON from Flask middleware: {response.text}"))
            return

        templates = payload.get('templates', [])
        created_count = 0
        updated_count = 0
        skipped_count = 0

        for template_data in templates:
            if str(template_data.get('status', '')).upper() != 'APPROVED':
                skipped_count += 1
                continue

            template_name = (template_data.get('name') or '').strip()
            if not template_name:
                skipped_count += 1
                continue

            body_preview = ''
            for component in template_data.get('components', []):
                if str(component.get('type', '')).upper() == 'BODY':
                    body_preview = component.get('text') or ''
                    break

            defaults = {
                'language_code': template_data.get('language') or 'en_US',
                'category': str(template_data.get('category') or ''),
                'body_preview': body_preview,
            }

            _, created = WhatsAppTemplate.objects.update_or_create(
                template_name=template_name,
                defaults=defaults,
            )

            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Template sync complete: synced={created_count + updated_count}, "
                f"created={created_count}, updated={updated_count}, skipped={skipped_count}"
            )
        )

