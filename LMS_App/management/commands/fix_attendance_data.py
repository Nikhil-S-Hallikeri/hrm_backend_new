#09/02/2026
from django.core.management.base import BaseCommand
from LMS_App.models import CompanyAttendanceDataModel
from django.db.models import Q


class Command(BaseCommand):
    help = 'Populate attendance calculation fields for existing data with NULL Status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            help='Month to process (1-12)',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to process',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all records with NULL Status (ignores month/year)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recalculation even for records that already have Status populated',
        )

    def handle(self, *args, **options):
        month = options.get('month')
        year = options.get('year')
        process_all = options.get('all')
        dry_run = options.get('dry_run')
        force = options.get('force')

        # Build query
        if force:
            # Force mode: process all records regardless of Status
            query = Q()
        else:
            # Normal mode: only process records with NULL Status
            query = Q(Status__isnull=True)
        
        if process_all:
            if force:
                self.stdout.write(self.style.WARNING('Processing ALL records (FORCE mode)...'))
            else:
                self.stdout.write(self.style.WARNING('Processing ALL records with NULL Status...'))
        elif month and year:
            query &= Q(date__month=month, date__year=year)
            if force:
                self.stdout.write(self.style.WARNING(f'Processing ALL records for {month}/{year} (FORCE mode)...'))
            else:
                self.stdout.write(self.style.WARNING(f'Processing records for {month}/{year}...'))
        else:
            self.stdout.write(self.style.ERROR('Please specify --month and --year, or use --all'))
            return

        # Get records to process
        records = CompanyAttendanceDataModel.objects.filter(query).select_related(
            'Emp_Id', 'Shift'
        ).prefetch_related('companyattendance_set')

        total_count = records.count()
        
        if total_count == 0:
            if force:
                self.stdout.write(self.style.SUCCESS('No records found'))
            else:
                self.stdout.write(self.style.SUCCESS('No records found with NULL Status'))
            return

        self.stdout.write(f'Found {total_count} records to process')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
            # Show sample records
            for record in records[:5]:
                punch_count = record.companyattendance_set.count()
                self.stdout.write(
                    f'  - {record.Emp_Id.EmployeeId} | {record.date} | {punch_count} punches'
                )
            if total_count > 5:
                self.stdout.write(f'  ... and {total_count - 5} more records')
            return

        # Process records
        processed = 0
        errors = 0
        
        for record in records:
            try:
                # Force recalculation
                record.save(force_recalculate=True)
                processed += 1
                
                # Show progress every 50 records
                if processed % 50 == 0:
                    self.stdout.write(f'Processed {processed}/{total_count} records...')
                    
            except Exception as e:
                errors += 1
                self.stdout.write(
                    self.style.ERROR(
                        f'Error processing {record.Emp_Id.EmployeeId} - {record.date}: {str(e)}'
                    )
                )

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nCompleted!'))
        self.stdout.write(f'Successfully processed: {processed} records')
        if errors > 0:
            self.stdout.write(self.style.WARNING(f'Errors: {errors} records'))
