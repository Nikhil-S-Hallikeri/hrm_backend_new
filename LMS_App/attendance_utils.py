#12/02/2026 - Automatic Attendance Preparation Utility
"""
This module provides utilities for ensuring attendance data completeness
before payslip generation. It automatically runs data preparation commands
if needed, with smart caching to prevent redundant operations.
"""

from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)


def ensure_attendance_data_complete(month, year, force=False):
    """
    Ensures attendance data is complete for the given month/year.
    
    This function is called before payslip generation to guarantee that:
    1. All days in the month have attendance records (including week offs)
    2. All fields (Status, Hours_Worked, LunchIn/LunchOut, etc.) are calculated
    
    The function uses a caching mechanism to avoid redundant preparation.
    """
    from LMS_App.models import AttendanceDataPreparationLog, CompanyAttendanceDataModel
    
    # Check if already prepared (unless force=True)
    if not force:
        existing_log = AttendanceDataPreparationLog.objects.filter(
            month=month,
            year=year
        ).first()
        
        if existing_log:
            logger.info(f"Attendance data for {month}/{year} already prepared on {existing_log.prepared_at}")
            return {
                'prepared': False,
                'message': f'Data already prepared on {existing_log.prepared_at.strftime("%Y-%m-%d %H:%M")}',
                'record_count': existing_log.record_count
            }
    
    # Run preparation commands
    try:
        logger.info(f"Starting attendance data preparation for {month}/{year}")
        
        # Step 1: Create missing attendance records (including week offs, holidays)
        call_command('create_missing_attendance', month=month, year=year)
        
        # Step 2: Calculate all fields (Status, Hours, Breaks, LunchIn/Out, etc.)
        call_command('fix_attendance_data', month=month, year=year, force=True)
        
        # Count records created/updated
        record_count = CompanyAttendanceDataModel.objects.filter(
            date__month=month,
            date__year=year
        ).count()
        
        # Log the preparation (update if exists, create if new)
        log, created = AttendanceDataPreparationLog.objects.update_or_create(
            month=month,
            year=year,
            defaults={
                'record_count': record_count,
                'prepared_by': 'auto_payslip_generation'
            }
        )
        
        action = "Created" if created else "Updated"
        logger.info(f"{action} preparation log for {month}/{year}. Records: {record_count}")
        
        return {
            'prepared': True,
            'message': f'Successfully prepared {record_count} attendance records',
            'record_count': record_count
        }
        
    except Exception as e:
        logger.error(f"Error preparing attendance data for {month}/{year}: {e}", exc_info=True)
        return {
            'prepared': False,
            'message': f'Error during preparation: {str(e)}',
            'record_count': 0
        }
