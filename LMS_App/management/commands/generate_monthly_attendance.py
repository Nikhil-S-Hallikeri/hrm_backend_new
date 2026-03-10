from django.core.management.base import BaseCommand
from LMS_App.models import CompanyAttendanceDataModel, EmployeeDataModel
from datetime import date
from dateutil.relativedelta import relativedelta
import calendar


class Command(BaseCommand):
    help = 'Generate attendance records for current or next month (for scheduled monthly execution)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--next-month',
            action='store_true',
            help='Generate for next month instead of current month',
        )
        parser.add_argument(
            '--month',
            type=int,
            help='Specific month to process (1-12)',
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Specific year to process',
        )

    def handle(self, *args, **options):
        # Determine target month/year
        if options.get('month') and options.get('year'):
            month = options['month']
            year = options['year']
            self.stdout.write(f'Processing specified month: {month}/{year}')
        else:
            today = date.today()
            if options.get('next_month'):
                target_date = today + relativedelta(months=1)
            else:
                target_date = today
            
            month = target_date.month
            year = target_date.year
            self.stdout.write(f'Processing {"next" if options.get("next_month") else "current"} month: {month}/{year}')

        # Get active employees
        employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")
        emp_count = employees.count()
        
        if emp_count == 0:
            self.stdout.write(self.style.WARNING('No active employees found'))
            return

        self.stdout.write(f'Found {emp_count} active employees')

        # Get number of days in the month
        num_days = calendar.monthrange(year, month)[1]
        self.stdout.write(f'Month has {num_days} days')

        created_count = 0
        skipped_count = 0
        
        for emp in employees:
            for day in range(1, num_days + 1):
                attendance_date = date(year, month, day)
                
                # Use get_or_create to avoid duplicates
                attendance, created = CompanyAttendanceDataModel.objects.get_or_create(
                    Emp_Id=emp,
                    date=attendance_date,
                    defaults={
                        'Day': attendance_date.strftime("%A"),
                        'Shift': emp.employeeProfile.EmployeeShifts if hasattr(emp, 'employeeProfile') else None
                    }
                )
                
                if created:
                    created_count += 1
                    # Show progress every 500 records
                    if created_count % 500 == 0:
                        self.stdout.write(f'Created {created_count} records...')
                else:
                    skipped_count += 1

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\n✓ Completed!'))
        self.stdout.write(f'Created: {created_count} new records')
        self.stdout.write(f'Skipped: {skipped_count} existing records')
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(
                '\nAttendance records generated successfully!'
            ))
            self.stdout.write(
                'Week offs, holidays, and other statuses will be automatically calculated.'
            )
