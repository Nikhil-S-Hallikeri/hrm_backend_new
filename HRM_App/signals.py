from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import EmployeeInformation
from LMS_App.models import *
from EMS_App.models import EmployeePersonalInformation
from LMS_App.serializers import EmployeeLeaveTypesEligiblitySerializer
from django.db.models import *
from .models import EmployeeInformation, Notification, RegistrationModel, CandidateApplicationModel
from LMS_App.models import LeaveRequestForm

@receiver(post_save, sender=EmployeeInformation)
def update_probation_status(sender, instance, created, **kwargs):
    if created:
        # When a new instance is created, calculate and set probation status
        current_date = timezone.localdate()
        print("mskdfmdffffkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkkk")

        if instance.probation_Duration_From and instance.probation_Duration_To:
            print("mskdfmdffffkkkkkkkkkkkkkkkkkkk")
            if instance.probation_Duration_From <= current_date <= instance.probation_Duration_To:
                print("mskdfmdffffkkkkkkkk")
                instance.probation_status = "probationer"
            elif current_date > instance.probation_Duration_To:
                print("mskdfmdffffkkk")
                instance.probation_status = "confirmed"
            else:
                instance.probation_status = None  # or some other default value

            # instance.save()
            EmployeeInformation.objects.filter(pk=instance.pk).update(probation_status=instance.probation_status)


        # Create leave eligibility for the new employee
        # try:
        #     emp_type = instance.probation_status
        #     leaves_applicable = LeavesTypeDetailModel.objects.filter(Q(applicable_to=emp_type) | Q(applicable_to="both"))
        #     for leave_type in leaves_applicable:
        #         if not EmployeeLeaveTypesEligiblity.objects.filter(employee=instance, LeaveType=leave_type).exists():
        #             leave_eligibility = {"employee": instance.pk, "LeaveType": leave_type.pk}
        #             serializer = EmployeeLeaveTypesEligiblitySerializer(data=leave_eligibility)
        #             if serializer.is_valid():
        #                 serializer.save()
        # except Exception as e:
        #     print(f"Leave creation failed: {e}")

        # # Create available restricted leaves for the new employee
        # try:
        #     EPIO = EmployeePersonalInformation.objects.filter(religion=instance.Religion)
        #     for emp in EPIO:
        #         emp_obj = EmployeeDataModel.objects.get(employeeProfile__pk=emp.EMP_Information.pk)
        #         if not AvailableRestrictedLeaves.objects.filter(holiday=instance, employee=emp_obj).exists():
        #             AvailableRestrictedLeaves.objects.create(
        #                 holiday=instance,
        #                 employee=emp_obj,
        #             )
        # except Exception as e:
        #     print(f"Restricted leave creation failed: {e}")

#changes
@receiver(post_save, sender=NewActivityModel)
def create_activity_assignment_notification(sender, instance, created, **kwargs):
    """
    Creates a notification when a new activity (Interview Calls, Job Posts, etc.)
    is assigned to an employee.
    """
    if created:
        try:
            assigner_employee = instance.activity_assigned_by
            assignee_employee = instance.Employee

            if assigner_employee and assignee_employee and assigner_employee != assignee_employee:
                
                sender_reg = RegistrationModel.objects.filter(EmployeeId=assigner_employee.EmployeeId).first()
                receiver_reg = RegistrationModel.objects.filter(EmployeeId=assignee_employee.EmployeeId).first()

                if sender_reg and receiver_reg:
                    activity_name = instance.Activity.activity_name.replace('_', ' ').title()
                    
                    message = f"{assigner_employee.Name} has assigned you a new activity: {activity_name}."

                    Notification.objects.create(
                        sender=sender_reg,
                        receiver=receiver_reg,
                        message=message,
                        not_type='task_assign',
                        reference_id=instance.pk 
                    )
        except Exception as e:
            print(f"Failed to create activity assignment notification: {e}")