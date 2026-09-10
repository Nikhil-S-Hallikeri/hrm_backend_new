from django.core.management.base import BaseCommand
from LMS_App.models import CompanyAttendanceDataModel, EmployeeDataModel
from datetime import date
import calendar


class Command(BaseCommand):
    help = 'Create missing attendance records for all days in a month (including week offs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month',
            type=int,
            required=True,
            help='Month to process (1-12)',
        )
        parser.add_argument(
            '--year',
            type=int,
            required=True,
            help='Year to process',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without actually creating',
        )
        parser.add_argument(
            '--employee-id',
            type=str,
            help='Process only specific employee (optional)',
        )

    def handle(self, *args, **options):
        month = options['month']
        year = options['year']
        dry_run = options.get('dry_run')
        employee_id = options.get('employee_id')

        self.stdout.write(self.style.WARNING(f'Creating missing attendance records for {month}/{year}...'))

        # Get employees to process
        if employee_id:
            employees = EmployeeDataModel.objects.filter(EmployeeId=employee_id)
            if not employees.exists():
                self.stdout.write(self.style.ERROR(f'Employee {employee_id} not found'))
                return
        else:
            employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")

        emp_count = employees.count()
        self.stdout.write(f'Processing {emp_count} employees...')

        # Get number of days in the month
        num_days = calendar.monthrange(year, month)[1]
        self.stdout.write(f'Month has {num_days} days')

        created_count = 0
        skipped_count = 0
        
        for emp in employees:
            for day in range(1, num_days + 1):
                attendance_date = date(year, month, day)
                
                # Check if record already exists
                exists = CompanyAttendanceDataModel.objects.filter(
                    Emp_Id=emp,
                    date=attendance_date
                ).exists()
                
                if exists:
                    skipped_count += 1
                    continue
                
                if dry_run:
                    day_name = attendance_date.strftime("%A")
                    self.stdout.write(
                        f'  Would create: {emp.EmployeeId} - {attendance_date} ({day_name})'
                    )
                    created_count += 1
                else:
                    # Create record - calculation will happen automatically in save()
                    CompanyAttendanceDataModel.objects.create(
                        Emp_Id=emp,
                        date=attendance_date,
                        Day=attendance_date.strftime("%A")
                    )
                    created_count += 1
                    
                    # Show progress every 100 records
                    if created_count % 100 == 0:
                        self.stdout.write(f'Created {created_count} records...')

        # Summary
        self.stdout.write(self.style.SUCCESS(f'\nCompleted!'))
        if dry_run:
            self.stdout.write(f'Would create: {created_count} records')
        else:
            self.stdout.write(f'Created: {created_count} records')
        self.stdout.write(f'Skipped (already exist): {skipped_count} records')
        
        if not dry_run and created_count > 0:
            self.stdout.write(self.style.SUCCESS(
                '\n✓ Attendance records created successfully!'
            ))
            self.stdout.write(
                'Week offs and holidays will be automatically marked with correct Status.'
            )
