from django.db import models
from django.utils import timezone
from EMS_App.models import *

from HRM_App.models import EmployeeDataModel,EmployeeInformation

class AllowanceType(models.Model):
    ALLOWANCETYPES = [
        ('Earning','Earning'),
        ('Pre_Tax_Deduction','Pre_Tax_Deduction'),
        ('Post_Tax_Deduction','Post_Tax_Deduction'),
    ]
    paytype=[("Fixed_Pay","Fixed_Pay"),("Variable_Pay","Variable_Pay")]
    c_type=[("Flat_Amount","Flat_Amount"),("Percentage_oF_CTC","Percentage_oF_CTC")]
    DF=[("OneTime","OneTime"),("recurring","recurring")]

    type = models.CharField(max_length=100,choices=ALLOWANCETYPES,blank=True,null=True)
    earning_name = models.CharField(max_length=100,blank=True,null=True)
    name_in_payslip=models.CharField(max_length=100,blank=True,null=True)
    pay_type=models.CharField(max_length=100,choices=paytype,blank=True,null=True)
    caluculate_type=models.CharField(max_length=100,choices=c_type,blank=True,null=True)
    fixed_amount = models.CharField(max_length=100,blank=True,null=True)
    percentage_of_ctc=models.CharField(max_length=100,blank=True,null=True)
    earning_status=models.BooleanField(default=False)

    # Post Tax deducation
    deduction_frequency=models.CharField(max_length=100,choices=DF,blank=True,null=True)
    post_tax_d_status=models.BooleanField(default=False)

    #Pre Tax Deducation
    deducting_plan = models.CharField(max_length=100,blank=True,null=True)
    deduction_associate_with=models.CharField(max_length=100,blank=True,null=True)
    emp_contribution_ctc=models.BooleanField(default=False)
    caluculate_on_prorata_basic=models.BooleanField(default=False)
    pre_tax_d_status=models.BooleanField(default=False)

    consider_for_epf = models.BooleanField(default=False)
    epf_choices=[("always","always"),("pfwage","pfwage")]
    epf_type=models.CharField(max_length=100,choices=epf_choices,blank=True,null=True)
    consider_for_esi = models.BooleanField(default=False)
    status = models.BooleanField(default=True)
    



class SalaryTemplate(models.Model):
    template_name = models.CharField(max_length=100)
    description =models.TextField()
    types = models.ManyToManyField(AllowanceType,related_name='typesoftemplates')
    created_at = models.DateTimeField(default=timezone.localtime)

    # basic_percentage = models.DecimalField(max_digits=4,decimal_places=2,default=40)
    # annual_ctc = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    # annual_basic = models.DecimalField(max_digits=100,decimal_places=2,blank=True,null=True)
    # annual_fixed_allowance = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    # monthly_gross = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    # monthly_basic = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    # monthly_fixed_allowances = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    # monthly_cost_to_company = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    # yearly_cost_to_company = models.DecimalField(max_digits=10,decimal_places=2,blank=True,null=True)
    
    # def save(self, *args, **kwargs):

    #     # Calculate annual_basic as a percentage of annual_ctc
    #     self.annual_basic = (self.annual_ctc * self.basic_percentage) / 100
    #     # Calculate annual_fixed_allowance as the remaining amount
    #     self.annual_fixed_allowance = self.annual_ctc - self.annual_basic
    #     # Calculate monthly values
    #     self.monthly_gross = self.annual_ctc / 12
    #     self.monthly_basic = self.annual_basic / 12
    #     self.monthly_fixed_allowances = self.annual_fixed_allowance / 12
    #     self.monthly_cost_to_company = self.monthly_gross
    #     self.yearly_cost_to_company = self.annual_ctc
    #     super(SalaryTemplate, self).save(*args, **kwargs)

class EmployeeSalaryBreakUp(models.Model):
    CTC_per_annum=models.DecimalField(max_digits=12,decimal_places=2,blank=True,null=True)
    employee_id = models.OneToOneField(EmployeeDataModel,on_delete=models.CASCADE)
    salary_template = models.ForeignKey(SalaryTemplate,on_delete=models.CASCADE,blank=True,null=True)
    def __str__(self):
        return f'Salary Breakup for {self.employee_id}' 
    
    def save(self, *args, **kwargs):
        if self.employee_id:
            ESH=CompanyEmployeesPositionHistory.objects.filter(employee=self.employee_id,is_applicable=True).first()
            if ESH:
                self.CTC_per_annum=ESH.assigned_salary
            else:
                self.CTC_per_annum=0
        super().save(*args, **kwargs)


class EmployeePaySlips(models.Model):
    employee = models.ForeignKey(EmployeeDataModel, on_delete=models.CASCADE,blank=True,null=True)
    salary_breakups=models.ForeignKey(EmployeeSalaryBreakUp,on_delete=models.CASCADE,blank=True,null=True)
    month = models.CharField(max_length=50,blank=True,null=True)
    year = models.IntegerField(blank=True,null=True)
    company_name = models.CharField(max_length=100,blank=True,null=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2,blank=True,null=True)
    employee_name = models.CharField(max_length=100,blank=True,null=True)
    uan_number = models.CharField(max_length=50,blank=True,null=True)
    pf_number = models.CharField(max_length=50,blank=True,null=True)
    total_working_days = models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    worked_days=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    week_off_days=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    public_holidays=models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    paid_days = models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    leaves_taken = models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    lop_days = models.DecimalField(max_digits=5, decimal_places=2,blank=True,null=True)
    account_number = models.CharField(max_length=50,blank=True,null=True)
    bank_branch = models.CharField(max_length=100,blank=True,null=True)
    doj = models.DateField(blank=True,null=True)
    designation = models.CharField(max_length=50,blank=True,null=True)
    total_earnings = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    total_deductions = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    monthly_gross_pay= models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.localtime)

    def __str__(self):
        return f"Pay Slip for {self.employee} - {self.month} {self.year}"
    
    