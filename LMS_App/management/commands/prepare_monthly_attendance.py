"""
Management command to prepare attendance data for the current month.
This should be run via cron job on the server.

Usage:
    python manage.py prepare_monthly_attendance
    python manage.py prepare_monthly_attendance --month=8 --year=2025
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Prepares attendance data for payslip generation (creates missing records and fixes data)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Month to prepare (1-12). Defaults to current month.',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to prepare. Defaults to current year.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-preparation even if already prepared',
        )

    def handle(self, *args, **options):
        # Get month and year
        month = options.get('month') or datetime.now().month
        year = options.get('year') or datetime.now().year
        force = options.get('force', False)

        self.stdout.write(self.style.WARNING(f'\n{"="*60}'))
        self.stdout.write(self.style.WARNING(f'Preparing Attendance Data for {month}/{year}'))
        self.stdout.write(self.style.WARNING(f'{"="*60}\n'))

        try:
            # Check if already prepared (unless force=True)
            if not force:
                from LMS_App.models import AttendanceDataPreparationLog
                existing_log = AttendanceDataPreparationLog.objects.filter(
                    month=month,
                    year=year
                ).first()
                
                if existing_log:
                    self.stdout.write(self.style.SUCCESS(
                        f'✓ Already prepared on {existing_log.prepared_at.strftime("%Y-%m-%d %H:%M")}'
                    ))
                    self.stdout.write(self.style.SUCCESS(
                        f'  Records: {existing_log.record_count}'
                    ))
                    self.stdout.write(self.style.WARNING(
                        f'\n  Use --force to re-prepare\n'
                    ))
                    return

            # Step 1: Create missing attendance records
            self.stdout.write(self.style.WARNING('Step 1: Creating missing attendance records...'))
            call_command('create_missing_attendance', month=month, year=year)
            self.stdout.write(self.style.SUCCESS('✓ Missing records created\n'))

            # Step 2: Fix/calculate attendance data
            self.stdout.write(self.style.WARNING('Step 2: Calculating attendance data...'))
            call_command('fix_attendance_data', month=month, year=year, force=True)
            self.stdout.write(self.style.SUCCESS('✓ Attendance data calculated\n'))

            # Step 3: Log the preparation
            from LMS_App.models import AttendanceDataPreparationLog, CompanyAttendanceDataModel
            
            record_count = CompanyAttendanceDataModel.objects.filter(
                date__month=month,
                date__year=year
            ).count()

            log, created = AttendanceDataPreparationLog.objects.update_or_create(
                month=month,
                year=year,
                defaults={
                    'record_count': record_count,
                    'prepared_by': 'cron_job'
                }
            )

            self.stdout.write(self.style.SUCCESS(f'\n{"="*60}'))
            self.stdout.write(self.style.SUCCESS(f'✓ SUCCESS: Prepared {record_count} attendance records'))
            self.stdout.write(self.style.SUCCESS(f'{"="*60}\n'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n{"="*60}'))
            self.stdout.write(self.style.ERROR(f'✗ ERROR: {str(e)}'))
            self.stdout.write(self.style.ERROR(f'{"="*60}\n'))
            logger.error(f'Error preparing attendance for {month}/{year}: {e}', exc_info=True)
            raise
