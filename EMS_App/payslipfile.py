from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from HRM_App.models import EmployeeInformation, EmployeeDataModel
from .models import Deductions, BankAccountDetails, PFDetails,PaySlip
from django.http import JsonResponse
from decimal import Decimal
from django.shortcuts import render
import calendar
from django.utils import timezone
# from .models import *
from payroll_app.models import *
from LMS_App.models import *
from django.utils import timezone
from .serializers import *
# from decimal import Decimal
# from django.shortcuts import get_object_or_404
from .models import * #EmployeeInformation, SalaryTemplate, PaySlip, AllowanceDeduction, EmployeeSalaryBreakUp, BankAccountDetails, EmployeeDataModel, PFDetails


from django.db.models import Q

def generatePaySlip(employee, month, year, total_working_days, paid_days, leaves_taken, lop_days):

    # print("the total working days is ",total_working_days)
    # Fetch the EmployeeSalaryBreakUp for the given employee
    EDO = get_object_or_404(EmployeeDataModel, employeeProfile__employee_Id=employee)
    ESB = EmployeeSalaryBreakUp.objects.filter(employee_id=EDO).first()
    salary_template = ESB.salary_template
    gross_salary = Decimal(salary_template.monthly_gross)
    allowance_objects = salary_template.types.filter(tyype='allowance')
    deduction_objects = salary_template.types.filter(tyype='deduction')

    # print("The allowance",allowance_objects)

    # print("Deductions data",deduction_objects)


    # print(allowance_objects,deduction_objects)

    try:
        # print(employee)
        EBO = BankAccountDetails.objects.get(EMP_Information=employee)
        # print(EBO)
        EDM = EmployeeDataModel.objects.get(employeeProfile=employee)
        PDO = PFDetails.objects.get(EMP_Information=employee)
        designation = EDM.Designation
        uan_number = PDO.uan
        pf_number = PDO.pf
        company_name = 'Merida Tech Minds Pvt.Ltd'
    except (BankAccountDetails.DoesNotExist, EmployeeDataModel.DoesNotExist, PFDetails.DoesNotExist):
        # Handle exceptions or provide default values
        designation = ""
        uan_number = ""
        pf_number = ""
        company_name = ""

    # print(gross_salary,total_working_days,paid_days)
    # Calculate actual salary based on working days
    if total_working_days == 0:
        total_working_days = 31
    actual_salary = (gross_salary / total_working_days) * paid_days

    # print("the actual salary is ",actual_salary)
    # Create the PaySlip object if it doesn't already exist for the given month and year
    if not PaySlip.objects.filter(employee=employee, month=month, year=year).exists():
        payslip = PaySlip.objects.create(
            employee=employee,
            month=month,
            year=year,
            company_name=company_name,
            salary=gross_salary,
            employee_name=employee.full_name,
            uan_number=uan_number,
            pf_number=pf_number,
            total_working_days=total_working_days,
            paid_days=paid_days,
            leaves_taken=leaves_taken,
            lop_days=lop_days,
            account_number=EBO.account_no if EBO else '',
            bank_branch=EBO.branch if EBO else '',
            doj=employee.hired_date if employee.hired_date else timezone.now(),
            designation=designation,
        )

        total_allowances = Decimal(0)
        total_deductions = Decimal(0)

        # Add allowances to the PaySlip
        for allowance in allowance_objects:
            if allowance.percentage and float(allowance.percentage) > 0:
                amount = actual_salary * Decimal(allowance.percentage) / 100
            else:
                amount = Decimal(allowance.fixed_amount)

            total_allowances += amount

            AllowanceDeduction.objects.create(
                payslip=payslip,
                type='allowance',
                name=allowance.type_name,
                amount=amount
            )

        # Add deductions to the PaySlip
        for deduction in deduction_objects:
            if deduction.percentage and float(deduction.percentage) > 0:
                amount = actual_salary * Decimal(deduction.percentage) / 100
            else:
                amount = Decimal(deduction.fixed_amount)

            total_deductions += amount
            # print(deduction.type_name)
            AllowanceDeduction.objects.create(
                payslip=payslip,
                type='deduction',
                name=deduction.type_name,
                amount=amount
            )

        # Calculate the "Other Allowances" to balance the total earnings
        other_allowances = round(actual_salary) - (round(total_allowances) + round(total_deductions))
        # print(actual_salary,total_allowances,total_deductions)
        # print(other_allowances)

        AllowanceDeduction.objects.create(
            payslip=payslip,
            type='allowance',
            name='Other Allowances',
            amount=other_allowances
        )

        # Calculate totals
        payslip.calculate_totals()

        return payslip

    else:
        return "PaySlip already generated for this month and year"


def getEmployeesAttendanceCalculation(emp_id,month,year):
    try:
        cad_obj=CompanyAttendanceDataModel.objects.filter(Emp_Id__EmployeeId=emp_id,date__month=month,date__year=year)
        cld_obj=EmployeesLeavesmodel.objects.filter(leave_request__employee__EmployeeId=emp_id,leave_date__month=month,leave_date__year=year)

        paid_leaves=cld_obj.filter(fall_under="Paid_Leave").count()
    
        work_days=cad_obj.filter(Q(Status="present") | Q(Status="week_off") | Q(Status="public_leave")).count()

        unpaid_leaves=cld_obj.filter(fall_under="Unpaid_Leave").count()
        un_info_obj=cad_obj.filter(leave_information="uninformed").count()

        total_working_days=cad_obj.exclude(Status="public_leave").count()
        total_paid_leaves= paid_leaves
        total_unpaid_leaves= unpaid_leaves + un_info_obj

        att_dict={
            "total_working_days":total_working_days,
            "work_days":work_days,
            "total_paid_leaves":total_paid_leaves,
            "total_unpaid_leaves":total_unpaid_leaves
            }
      
        return att_dict
    except Exception as e:
        print(e)


class EmployeesForPaySlip(APIView):
    def get(self, request):
        employees = EmployeeInformation.objects.all().exclude(employee_status='in_active')
        payslips = []

        # Get current month and year
        now = timezone.now()
        month_name = calendar.month_name[now.month]
        year = now.year

        for employee in employees:
            data = getEmployeesAttendanceCalculation(employee,now.month,year)
            
            # print(data) 

# def generatePaySlip(employee, month, year, total_working_days, paid_days, leaves_taken, lop_days):
            payslip_data = generatePaySlip(employee, month_name, year,data['total_working_days'],data['work_days']+ data['total_paid_leaves'],data['total_paid_leaves'],data['total_unpaid_leaves'])
        
        PO = PaySlip.objects.all()  
        for p in PO:

            serializer = PlaySlipSerializer(p,context={'request':request}).data

            payslips.append(serializer)

        # print(payslips)

        print(len(payslips))

        return Response(payslips)
        return render(request, 'payslip.html', {'payslips': payslips})
