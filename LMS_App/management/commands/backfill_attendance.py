"""
Backfill Attendance Data for Historical Months
Automatically prepares attendance for all past months that need it.

Usage:
    # Backfill all months in 2025
    python manage.py backfill_attendance --year=2025
    
    # Backfill specific range
    python manage.py backfill_attendance --start-month=1 --start-year=2025 --end-month=12 --end-year=2025
    
    # Backfill everything from Jan 2024 to current month
    python manage.py backfill_attendance --start-month=1 --start-year=2024
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from datetime import datetime
import calendar
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Backfill attendance data for historical months'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            help='Backfill all months in this year (1-12)',
        )
        parser.add_argument(
            '--start-month',
            type=int,
            help='Starting month (1-12)',
        )
        parser.add_argument(
            '--start-year',
            type=int,
            help='Starting year',
        )
        parser.add_argument(
            '--end-month',
            type=int,
            help='Ending month (1-12). Defaults to current month.',
        )
        parser.add_argument(
            '--end-year',
            type=int,
            help='Ending year. Defaults to current year.',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-preparation even if already prepared',
        )

    def handle(self, *args, **options):
        now = datetime.now()
        
        # Determine date range
        if options.get('year'):
            # Simple mode: backfill entire year
            start_month = 1
            start_year = options['year']
            end_month = 12
            end_year = options['year']
        else:
            # Range mode
            start_month = options.get('start_month') or 1
            start_year = options.get('start_year') or now.year
            end_month = options.get('end_month') or now.month
            end_year = options.get('end_year') or now.year
        
        force = options.get('force', False)
        
        self.stdout.write(self.style.WARNING(f'\n{"="*70}'))
        self.stdout.write(self.style.WARNING(f'BACKFILLING ATTENDANCE DATA'))
        self.stdout.write(self.style.WARNING(f'{"="*70}\n'))
        self.stdout.write(f'Range: {start_month}/{start_year} to {end_month}/{end_year}')
        self.stdout.write(f'Force: {force}\n')
        
        # Generate list of (month, year) tuples
        months_to_process = []
        current_year = start_year
        current_month = start_month
        
        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            months_to_process.append((current_month, current_year))
            
            # Increment month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        
        total_months = len(months_to_process)
        self.stdout.write(f'Total months to process: {total_months}\n')
        
        # Process each month
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for idx, (month, year) in enumerate(months_to_process, 1):
            self.stdout.write(f'\n[{idx}/{total_months}] Processing {month}/{year}...')
            
            try:
                # Check if already prepared
                from LMS_App.models import AttendanceDataPreparationLog
                
                if not force:
                    existing = AttendanceDataPreparationLog.objects.filter(
                        month=month,
                        year=year
                    ).first()
                    
                    if existing:
                        self.stdout.write(self.style.SUCCESS(
                            f'  ✓ Already prepared on {existing.prepared_at.strftime("%Y-%m-%d")} '
                            f'({existing.record_count} records) - SKIPPED'
                        ))
                        skip_count += 1
                        continue
                
                # Run preparation
                call_command('prepare_monthly_attendance', month=month, year=year, force=force)
                
                self.stdout.write(self.style.SUCCESS(f'  ✓ SUCCESS'))
                success_count += 1
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ ERROR: {e}'))
                logger.error(f'Error backfilling {month}/{year}: {e}', exc_info=True)
                error_count += 1
        
        # Summary
        self.stdout.write(f'\n{"="*70}')
        self.stdout.write(self.style.WARNING('BACKFILL SUMMARY'))
        self.stdout.write(f'{"="*70}')
        self.stdout.write(f'Total months: {total_months}')
        self.stdout.write(self.style.SUCCESS(f'✓ Successfully prepared: {success_count}'))
        self.stdout.write(self.style.WARNING(f'⊘ Skipped (already done): {skip_count}'))
        
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Errors: {error_count}'))
        
        self.stdout.write(f'{"="*70}\n')
        
        if error_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ Backfill completed successfully!'))
        else:
            self.stdout.write(self.style.ERROR('⚠ Backfill completed with errors'))
