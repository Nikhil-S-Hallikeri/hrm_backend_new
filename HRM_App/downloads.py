from .imports import *

from EMS_App.views import autoemployeeid
from rest_framework.parsers import MultiPartParser, FormParser

# .............................Bulkdata upload................................

class Download_doc_Sheet(APIView):
    def get(self,request,file):
        try:
            LT=LetterTemplatesModel.objects.filter(TemplateName=file).first()
            serializer=LetterTemplatesSerializer(LT,context={"request":request})
            return Response(serializer.data,status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e),status=status.HTTP_400_BAD_REQUEST)
        
def import_candidate_data_from_excel(excel_file):
    workbook = load_workbook(excel_file)
    worksheet = workbook.active
    headers = ["FirstName", "LastName", "Email","PrimaryContact", "SecondaryContact",   
               "Location","Gender","Fresher", "Experience", "HighestQualification", "University", 
                "Specialization", "Percentage", "YearOfPassout","CurrentDesignation","TotalExperience","TechnicalSkills_with_Exp", "GeneralSkills_with_Exp", "SoftSkills_with_Exp",
                "TechnicalSkills","GeneralSkills", "SoftSkills", "NoticePeriod","CurrentCTC","AppliedDesignation","ExpectedSalary",
                "ContactedBy","JobPortalSource","Filled_by","AppliedDate","Final_Results"]
                
    saved_data = []
    for row in worksheet.iter_rows(min_row=2, values_only=True):
        data = dict(zip(headers, row))
        # Convert 'Fresher' to Boolean
        if data["Fresher"] is not None:
            if str(data["Fresher"]).strip().lower() in ['fresher',"Fresher"]:
                data["Fresher"] = True
            else:
                data["Fresher"] = False
        else:
            data["Fresher"] = False

        # Convert 'Experience' to Boolean
        if data["Experience"] is not None:
            if str(data["Experience"]).strip().lower() in ["experience","Experience"]:
                data["Experience"] = True
            else:
                data["Experience"] = False
        else:
            data["Experience"] = False

        if data.get("AppliedDate"):
            try:
                data["AppliedDate"] = data["AppliedDate"]
            except ValueError:
                print("Incorrect date format for AppliedDate")
        
        if data["JobPortalSource"] is not None:
            if str(data["JobPortalSource"]).strip().lower() in ["linkedin","naukri","foundit"]:
                data["JobPortalSource"] = str(data["JobPortalSource"]).strip().lower()
            else:
                data["Other_jps"]=data["JobPortalSource"]
                data["JobPortalSource"] ="others"

        if data["Gender"] is not None:
            str(data["Gender"]).strip().lower
           

        instance = CandidateApplicationModel.objects.create(**data)
        # receiver=EmployeeDataModel.objects.filter(Designation="HR")
        # if receiver:
        #     for rec in receiver:
        #         user=RegistrationModel.objects.get(EmployeeId=rec.EmployeeId)
        #         obj=Notification.objects.create(sender=None, receiver=user, message=f"Canddates Applied With Id {instance.CandidateId}! ",condidate_id=instance)
        saved_data.append(instance)
    return saved_data

class ExcelUploadView(APIView):
    def post(self, request):
        serializer = CandidateExcelUploadSerializer(data=request.data)
        if serializer.is_valid(): 
            excel_file = serializer.validated_data['excel_file']
            saved_data = import_candidate_data_from_excel(excel_file)
            serializer = CandidateApplicationSerializer(saved_data,many=True)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
# def import_employee_data_from_excel(excel_file):
#     workbook = openpyxl.load_workbook(excel_file)
#     worksheet = workbook.active
#     headers = [cell.value for cell in worksheet[1]]  # Get headers from the first row

#     saved_data = []

#     for row in worksheet.iter_rows(min_row=2, values_only=True):
#         data = dict(zip(headers, row))
        
#         # Handle dates
#         if data.get("date_of_birth"):
#             data["date_of_birth"] = data["date_of_birth"].date()

#         if data.get("hired_date"):
#             data["hired_date"] = data["hired_date"].date()

#         if data.get("Internship_From"):
#             data["Internship_From"] = data["Internship_From"].date()

#         if data.get("Internship_To"):
#             data["Internship_To"] = data["Internship_To"].date()

#         if data.get("Internship_From"):
#             data["Internship_From"] = data["Internship_From"].date()

#         if data.get("Probation_To"):
#             data["Probation_To"] = data["Probation_To"].date()

        
#         # Handle department
#         if data.get("Dep_Name"):
#             department, created = Deparments.objects.get_or_create(Dep_Name=data["Dep_Name"])
#             data["Department"] = department
#             del data["Dep_Name"]

#         # Handle designation
#         if data.get("Designation_Name"):
#             designation, created = DesignationModel.objects.get_or_create(Name=data["Designation_Name"], Department=data["Department"])
#             data["Designation"] = designation
#             del data["Designation_Name"]

#         # Handle employee information
#         employee_data = {
#             "employee_Id": autoemployeeid(),
#             "full_name": data.get("full_name"),
#             "date_of_birth": data.get("date_of_birth"),
#             "gender": data.get("gender"),
#             "mobile": data.get("mobile"),
#             "email": data.get("email"),
#             "weight": data.get("weight"),
#             "height": data.get("height"),
#             "permanent_address": data.get("permanent_address"),
#             "present_address": data.get("present_address"),
#             "hired_date": data.get("hired_date"),
#             "ProfileVerification": "success",
#             "is_verified": True,
#             "employee_status": "active",
#             "Employeement_Type":data.get("Employeement_Type"),

#             "internship_Duration_From":data.get("Internship_From"),
#             "internship_Duration_To":data.get("Internship_To"),

#             "probation_status":data.get("Employeement_Status"),

#             "probation_Duration_From":data.get("Probation_From"),
#             "probation_Duration_To":data.get("Probation_To"),
#         }
#         employee_instance = EmployeeInformation.objects.create(**employee_data)

#         # Handle employee data model
#         reporting_to = None
#         if data.get("Reporting_To"):
#             try:
#                 reporting_to = EmployeeDataModel.objects.get(EmployeeId=data["Reporting_To"])
#             except EmployeeDataModel.DoesNotExist:
#                 pass
        
#         # Handle employee data model
#         employee_data_model = {
#             "EmployeeId": employee_instance.employee_Id,
#             "Name": employee_instance.full_name,
#             "employeeProfile": employee_instance,
#             "Designation": data.get("Dashboard"),
#             "Reporting_To": reporting_to,
#             "Position": data.get("Designation"),  # Assuming the position is the same as the designation
#         }
#         EmployeeDataModel.objects.create(**employee_data_model)

#         if data.get("Designation"):
#             registration_data = {
#                 "EmployeeId": employee_instance.employee_Id,
#                 "UserName": employee_instance.full_name,
#                 "Email": employee_instance.email,
#                 "PhoneNumber": employee_instance.mobile,
#                 "Password": make_password("MTM@123"),  # You should implement this function to generate a password
#                 "is_active": True
#             }
#             RegistrationModel.objects.create(**registration_data)

#             subject= f"HRMS Credentials of Your Merida Account on {timezone.localtime().date()}"
#             Message=f"Dear {employee_instance.full_name},\n\nWelcome to Merida Tech Minds! We are pleased to inform you that your account has been created in our HRMS.\n\nuse below credentials to login to HRMS.\n\nEmployeeId : {employee_instance.employee_Id}\n\nPassword   : MTM@123\nhttps://hrm.meridahr.com/\nRegards\nTeam Merida."
#             send_mail(
#                     subject,Message,
#                     'sender@example.com',  
#                     [employee_instance.email],
#                     fail_silently=False,)
            
#         saved_data.append(employee_instance)

#     return saved_data

# class EmployeeExcelUploadView(APIView):
#     def post(self, request):
#         serializer = EmployeeExcelUploadSerializer(data=request.data)
#         if serializer.is_valid():
#             excel_file = serializer.validated_data['excel_file']
#             saved_data = import_employee_data_from_excel(excel_file)
#             response_data = [EmployeeInformationSerializer(instance).data for instance in saved_data]
#             return Response(response_data, status=status.HTTP_201_CREATED)
#         else:
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
# def import_employee_data_from_excel(excel_file):
#     try:
#         workbook = openpyxl.load_workbook(excel_file)
#         worksheet = workbook.active
#     except Exception as e:
#         raise ValueError(f"Error loading Excel file: {str(e)}")

#     headers = [cell.value for cell in worksheet[1]]  # Get headers from the first row
#     saved_data = []

#     for row in worksheet.iter_rows(min_row=2, values_only=True):
#         data = dict(zip(headers, row))

#         try:
#             # Handle dates explicitly to extract only the date part
#             if isinstance(data.get("date_of_birth"), datetime):
#                 data["date_of_birth"] = data["date_of_birth"].date()

#             if isinstance(data.get("hired_date"), datetime):
#                 data["hired_date"] = data["hired_date"].date()

#             if isinstance(data.get("Internship_From"), datetime):
#                 data["Internship_From"] = data["Internship_From"].date()

#             if isinstance(data.get("Internship_To"), datetime):
#                 data["Internship_To"] = data["Internship_To"].date()

#             if isinstance(data.get("Probation_From"), datetime):
#                 data["Probation_From"] = data["Probation_From"].date()

#             if isinstance(data.get("Probation_To"), datetime):
#                 data["Probation_To"] = data["Probation_To"].date()

#             # Handle department
#             if data.get("Dep_Name"):
#                 department, created = Deparments.objects.get_or_create(Dep_Name=data["Dep_Name"])
#                 data["Department"] = department
#                 del data["Dep_Name"]

#             # Handle designation
#             if data.get("Designation_Name"):
#                 designation, created = DesignationModel.objects.get_or_create(Name=data["Designation_Name"], Department=data["Department"])
#                 data["Designation"] = designation
#                 del data["Designation_Name"]

#             # Handle employee information
#             employee_data = {
#                 "employee_Id": autoemployeeid(),
#                 "full_name": data.get("full_name"),
#                 "date_of_birth": data.get("date_of_birth"),
#                 "gender": data.get("gender"),
#                 "mobile": data.get("mobile"),
#                 "email": data.get("email"),
#                 "weight": data.get("weight"),
#                 "height": data.get("height"),
#                 "permanent_address": data.get("permanent_address"),
#                 "present_address": data.get("present_address"),
#                 "hired_date": data.get("hired_date"),
#                 "ProfileVerification": "success",
#                 "is_verified": True,
#                 "employee_status": "active",
#                 "Employeement_Type": data.get("Employeement_Type"),
#                 "internship_Duration_From": data.get("Internship_From"),
#                 "internship_Duration_To": data.get("Internship_To"),
#                 "probation_status": data.get("Employeement_Status"),
#                 "probation_Duration_From": data.get("Probation_From"),
#                 "probation_Duration_To": data.get("Probation_To"),
#             }
#             employee_instance = EmployeeInformation.objects.create(**employee_data)

#             # Handle employee data model
#             reporting_to = None
#             if data.get("Reporting_To"):
#                 try:
#                     reporting_to = EmployeeDataModel.objects.get(EmployeeId=data["Reporting_To"])
#                 except EmployeeDataModel.DoesNotExist:
#                     pass

#             employee_data_model = {
#                 "EmployeeId": employee_instance.employee_Id,
#                 "Name": employee_instance.full_name,
#                 "employeeProfile": employee_instance,
#                 "Designation": data.get("Designation"),
#                 "Reporting_To": reporting_to,
#                 "Position": data.get("Designation"),  # Assuming the position is the same as the designation
#             }
#             EmployeeDataModel.objects.create(**employee_data_model)

#             # Handle registration model and email
#             if data.get("Designation"):
#                 registration_data = {
#                     "EmployeeId": employee_instance.employee_Id,
#                     "UserName": employee_instance.full_name,
#                     "Email": employee_instance.email,
#                     "PhoneNumber": employee_instance.mobile,
#                     "Password": make_password("MTM@123"),
#                     "is_active": True
#                 }
#                 RegistrationModel.objects.create(**registration_data)

#                 # subject = f"HRMS Credentials of Your Merida Account on {timezone.localtime().date()}"
#                 # message = f"Dear {employee_instance.full_name},\n\nWelcome to Merida Tech Minds! We are pleased to inform you that your account has been created in our HRMS.\n\nUse the below credentials to login to HRMS.\n\nEmployeeId : {employee_instance.employee_Id}\n\nPassword   : MTM@123\nhttps://hrm.meridahr.com/\nRegards\nTeam Merida."
#                 # send_mail(
#                 #     subject, message,
#                 #     'sender@example.com',
#                 #     [employee_instance.email],
#                 #     fail_silently=False,
#                 # )
            
#             saved_data.append(employee_instance)

#         except Exception as e:
#             print(f"Error processing row {row}: {str(e)}")

#     return saved_data

from django.db import transaction, IntegrityError

def import_employee_data_from_excel(excel_file):
    try:
        workbook = openpyxl.load_workbook(excel_file)
        worksheet = workbook.active
    except Exception as e:
        raise ValueError(f"Error loading Excel file: {str(e)}")

    headers = [cell.value for cell in worksheet[1]]
    saved_data = []

    for row in worksheet.iter_rows(min_row=2, values_only=True):
        data = dict(zip(headers, row))

        try:
            with transaction.atomic():  # Ensuring atomicity per row
                # Handle dates
                if isinstance(data.get("date_of_birth"), datetime):
                    data["date_of_birth"] = data["date_of_birth"].date()

                if isinstance(data.get("hired_date"), datetime):
                    data["hired_date"] = data["hired_date"].date()

                # Handle other date fields similarly...

                # Handle department
                if data.get("Dep_Name"):
                    department, created = Deparments.objects.get_or_create(Dep_Name=data["Dep_Name"])
                    data["Department"] = department
                    del data["Dep_Name"]

                # Handle designation
                if data.get("Designation_Name"):
                    designation, created = DesignationModel.objects.get_or_create(Name=data["Designation_Name"], Department=data["Department"])
                    data["Designation"] = designation
                    del data["Designation_Name"]

                # Create EmployeeInformation instance
                employee_data = {
                    "employee_Id": autoemployeeid(),
                    "full_name": data.get("full_name"),
                    "date_of_birth": data.get("date_of_birth"),
                    # Add the rest of the fields...
                }
                employee_instance = EmployeeInformation.objects.create(**employee_data)

                # Create EmployeeDataModel instance
                reporting_to = None
                if data.get("Reporting_To"):
                    reporting_to = EmployeeDataModel.objects.filter(EmployeeId=data["Reporting_To"]).first()

                employee_data_model = {
                    "EmployeeId": employee_instance.employee_Id,
                    "Name": employee_instance.full_name,
                    "employeeProfile": employee_instance,
                    "Designation": data.get("Designation"),
                    "Reporting_To": reporting_to,
                    "Position": data.get("Designation"),
                }
                EmployeeDataModel.objects.create(**employee_data_model)

                # Handle registration
                registration_data = {
                    "EmployeeId": employee_instance.employee_Id,
                    "UserName": employee_instance.full_name,
                    "Email": employee_instance.email,
                    "PhoneNumber": employee_instance.mobile,
                    "Password": make_password("MTM@123"),
                    "is_active": True
                }
                RegistrationModel.objects.create(**registration_data)

                # Optionally send an email here...

                saved_data.append(employee_instance)

        except IntegrityError as e:
            # Handle specific DB integrity issues
            print(f"Integrity error for row {row}: {str(e)}")
            continue  # Skip this row and continue processing

        except Exception as e:
            # Handle any other exceptions
            print(f"Error processing row {row}: {str(e)}")
            continue  # Skip this row and continue processing

    return saved_data


from django.db import transaction

class EmployeeExcelUploadView(APIView):
    def post(self, request):
        serializer = EmployeeExcelUploadSerializer(data=request.data)
        if serializer.is_valid():
            excel_file = serializer.validated_data['excel_file']
            try:
                with transaction.atomic():
                    saved_data = import_employee_data_from_excel(excel_file)
                    response_data = [EmployeeInformationSerializer(instance).data for instance in saved_data]
                    return Response(response_data, status=status.HTTP_201_CREATED)
            except ValueError as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            # except Exception as e:
            #     return Response({"detail": "An unexpected error occurred while processing the file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UploadCalledCandidatesExcel(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        file = request.FILES['file']
        df = pd.read_excel(file)
        
        # Convert DataFrame to list of dictionaries
        data = df.to_dict(orient='records')
        
        # Use the serializer to validate and save data
        serializer = CalledCandidatesSerializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DownloadCalledCandidatesExcel(APIView):
    def get(self, request):
        candidates = CalledCandidatesModel.objects.all()
        serializer = CalledCandidatesSerializer(candidates, many=True)
        
        # Convert to DataFrame
        df = pd.DataFrame(serializer.data)
        
        # Create an HttpResponse with the excel file
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=called_candidates.xlsx'
        
        # Use Pandas to output the data
        df.to_excel(response, index=False)
        
        return response

# ...............PANDAS DOWNLOAD.................

import pandas as pd
from io import BytesIO
from django.http import HttpResponse

class AppliedCandidatesDownload(APIView):
    def post(self, request):
        Candidate_ids=request.data["Candidate_ids"]
        if Candidate_ids:
            queryset = CandidateApplicationModel.objects.filter(CandidateId__in=Candidate_ids)
        else:
            queryset = CandidateApplicationModel.objects.all()

        # Convert queryset to DataFrame
        data = list(queryset.values())
        df = pd.DataFrame(data)

        # Modify DataFrame as needed
        del df['id']  # Delete 'id' column
        del df["Telephonic_Round_Status"]
        del df["Interview_Schedule"]
        del df["Final_Results"]
        del df["Test_levels"]
        del df["Documents_Upload_Status"]
        del df["BG_Status"]
        del df["Offer_Letter_Status"]
        del df["Interview_Accept_Status"]
        del df["Offer_Accept_Status"]
        del df["DataOfApplied"]
         
        df['Fresher'] = df['Fresher'].apply(lambda x: 'Fresher' if x else '')
        df['Experience'] = df['Experience'].apply(lambda x: 'Experience' if x else '')
        
        # Convert datetime columns to timezone unaware
        df['AppliedDate'] = df['AppliedDate'].dt.tz_localize(None)  # Assuming 'created_at' is your datetime column

        # Create Excel file in-memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Candidates')

        # Prepare response
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=mydata.xlsx'
        
        return response 
    

# class EmployeeDataDownload(APIView):
#     def post(self, request):
#         print(request.data)

#         EmployeeId=request.data["Employee_ids"]
#         # EmployeeId=json.loads(EmployeeId)

#         if EmployeeId:
#             queryset = EmployeeInformation.objects.filter(employee_Id__in=EmployeeId)
#         else:
#             queryset = EmployeeInformation.objects.all()

#          # Select related EmployeeDataModel fields
#         queryset = queryset.select_related('employeedatamodel__Position', 'employeedatamodel__Reporting_To')

#         # Convert queryset to DataFrame
#         data = list(queryset.values())
#         df = pd.DataFrame(data)

#         # Convert datetime fields to datetime objects if they are not already
#         # df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
#         df['hired_date'] = pd.to_datetime(df['hired_date'], errors='coerce')
#         df['date_of_birth'] = pd.to_datetime(df['date_of_birth'], errors='coerce')

#         # Remove timezone awareness
#         # df['created_at'] = df['created_at'].dt.tz_localize(None)
#         df['hired_date'] = df['hired_date'].dt.tz_localize(None) 
#         df['date_of_birth'] = df['date_of_birth'].dt.tz_localize(None) 

#         del df["form_submitted_status"]
#         del df["Candidate_id_id"]
#         del df["created_at"]
#         del df["date_of_submitted"]
#         del df["restricted_leave_count"]
#         del df["EmployeeShifts_id"]
#         del df["id"]

#         # Create Excel file in-memory
#         output = BytesIO() 
#         with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
#             df.to_excel(writer, index=False, sheet_name='Employees')

#         # Prepare response
#         output.seek(0)
#         response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = 'attachment; filename=employees.xlsx'
#         return response



from io import BytesIO
from django.http import HttpResponse
import pandas as pd
from rest_framework.views import APIView
from .models import EmployeeInformation  # Replace with your actual model import

class EmployeeDataDownload(APIView):
    def post(self, request):
        print(request.data)

        EmployeeId = request.data.get("Employee_ids", [])

        # If EmployeeId is provided, filter by these IDs
        if EmployeeId:
            queryset = EmployeeInformation.objects.filter(employee_Id__in=EmployeeId)
        else:
            queryset = EmployeeInformation.objects.all()

        # Select related EmployeeDataModel fields
        queryset = queryset.select_related('employeedatamodel__Position', 'employeedatamodel__Reporting_To')

        # Helper function for conditional string formatting
        def format_string(value, method="title"):
            if isinstance(value, str):
                return getattr(value, method)()
            return value

        # Convert queryset to list of dictionaries
        data = []
        for emp_info in queryset:
            emp_data = {
                'employee_Id': emp_info.employee_Id,
                'full_name': format_string(emp_info.full_name, "title"),
                'date_of_birth': emp_info.date_of_birth,
                'gender': format_string(emp_info.gender, "title"),
                'mobile': emp_info.mobile,
                'email': format_string(emp_info.email, "lower"),
                'weight': emp_info.weight,
                'height': emp_info.height,
                'permanent_address': format_string(emp_info.permanent_address, "title"),
                'permanent_City': format_string(emp_info.permanent_City, "title"),
                'permanent_state': format_string(emp_info.permanent_state, "title"),
                'permanent_pincode': emp_info.permanent_pincode,
                'present_address': format_string(emp_info.present_address, "title"),
                'present_City': format_string(emp_info.present_City, "title"),
                'present_state': format_string(emp_info.present_state, "title"),
                'present_pincode': emp_info.present_pincode,
                'ProfileVerification': format_string(emp_info.ProfileVerification, "title"),
                'employee_status': format_string(emp_info.employee_status, "title"),
                'hired_date': emp_info.hired_date,
                'Employeement_Type': format_string(emp_info.Employeement_Type, "title"),
                'internship_Duration_From': emp_info.internship_Duration_From,
                'internship_Duration_To': emp_info.internship_Duration_To,
                'probation_status': format_string(emp_info.probation_status, "title"),
                'probation_Duration_From': emp_info.probation_Duration_From,
                'probation_Duration_To': emp_info.probation_Duration_To,
            }

            # Adding EmployeeDataModel data
            if hasattr(emp_info, 'employeedatamodel'):
                emp_data['Role'] = format_string(emp_info.employeedatamodel.Designation, "title")
                emp_data['Designation'] = format_string(emp_info.employeedatamodel.Position.Name, "title") if emp_info.employeedatamodel.Position else None
                emp_data['Department'] = format_string(emp_info.employeedatamodel.Position.Department.Dep_Name, "title") if emp_info.employeedatamodel.Position else None
                emp_data['Reporting Manager'] = format_string(emp_info.employeedatamodel.Reporting_To.Name, "title") if emp_info.employeedatamodel.Reporting_To else None
                emp_data['Reporting Manager Emp_Id'] = emp_info.employeedatamodel.Reporting_To.EmployeeId if emp_info.employeedatamodel.Reporting_To else None

            data.append(emp_data)

        # Convert data to DataFrame
        df = pd.DataFrame(data)

        # Convert datetime fields to dd/mm/yy format
        for date_field in ['hired_date', 'date_of_birth', 'internship_Duration_From', 'internship_Duration_To', 'probation_Duration_From', 'probation_Duration_To']:
            if date_field in df.columns:
                df[date_field] = pd.to_datetime(df[date_field], errors='coerce').dt.strftime('%d/%m/%y')

        # Rename headers for title case and replace underscores
        df.rename(columns=lambda col: ' '.join(col.split('_')).title(), inplace=True)

        # Additional specific header renames
        df.rename(columns={
            'Mobile': 'Primary Contact Number',
            'Email': 'Personal Email ID',
            'Present Address': 'Current Address',
            'Present City': 'Current Address City',
            'Present State': 'Current Address State',
            'Present Pincode': 'Current Address Pincode',
            'Profileverification': 'Profile Verification Status',
            'Hired Date': 'Date Of Joining / Hire Date',
            'Internship Duration From': 'Internship Start Date',
            'Internship Duration To': 'Internship End Date',
            'Probation Duration From': 'Probation Start Date',
            'Probation Duration To': 'Probation End Date',
        }, inplace=True)

        # Create Excel file in-memory
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Employees')

        # Prepare response
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=employees.xlsx'
        return response



# candidate particular applied details download
class PerticularAppliedCandidateDownload(APIView):
    def get(self, request,can_id):
        if can_id:
            try:
                candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
                # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                if candidate.current_position in ['Fresher' , 'Student']:
                    serializer = FresherApplicationSerializer(candidate)
                else:
                    serializer = ExperienceApplicationSerializer(candidate)
                response_data = serializer.data  # Get the JSON response data


                del response_data['id']

                # response_data['Experience'] =response_data['Experience'].apply(lambda x: 'Fresher' if x else '')
                # response_data['Experience'] = response_data['Experience'].apply(lambda x: 'Experience' if x else '')
                if candidate.Experience:
                    response_data['Experience'] = 'Experience'
                else:
                    response_data['Experience'] = 'Fresher'


                # Convert JSON response data to a DataFrame
                df = pd.DataFrame([response_data])
                # Create an in-memory Excel file
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Candidate Data')
                # Prepare response
                excel_buffer.seek(0)
                response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=candidate_data.xlsx'
                return response
            except CandidateApplicationModel.DoesNotExist:
                return Response("Candidate Not Found", status=status.HTTP_404_NOT_FOUND)


# shotrlist candidates download list
class ScreeningDownloadExcel(APIView):
    def get(self, request):
            headers = ["CandidateId", "FirstName","screeningassigningmodel__AssignedBy","screeningassigningmodel__Date_of_assigned","screeningassigningmodel__Recruiter__EmployeeId","review__ReviewedBy","review__ReviewedOn","review__Screening_Status"]
            required_models = [CandidateApplicationModel]
            wb = Workbook()
            ws = wb.active
            ws.append(headers)
            for model in required_models:
                # queryset = model.objects.values(*headers)
                queryset = model.objects.filter(screeningassigningmodel__isnull=False).values(*headers)
                for item in queryset:
                    row = [item.get(field) for field in headers]
                    for i, value in enumerate(row):
                        if isinstance(value, timezone.datetime):
                            row[i] = value.replace(tzinfo=None)
                    ws.append(row)
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=mydata.xlsx'
            return response
    

# class InterviewDownloadExcel(APIView):
#     def get(self, request):
#             headers = ["CandidateId", "FirstName","interviewschedulmodel__InterviewDate","interviewschedulmodel__InterviewRoundName","interviewschedulmodel__InterviewType","interviewschedulmodel__interviewer__EmployeeId","review__ReviewedOn","review__interview_Status","interviewschedulmodel__ScheduledBy","interviewschedulmodel__ScheduledOn"]
#             required_models = [CandidateApplicationModel]
#             wb = Workbook()
#             ws = wb.active
#             ws.append(headers)
#             for model in required_models:
#                 # queryset = model.objects.values(*headers)
#                 queryset = model.objects.filter(interviewschedulmodel__isnull=False).values(*headers)
#                 for item in queryset:
#                     row = [item.get(field) for field in headers]
#                     for i, value in enumerate(row):
#                         if isinstance(value, timezone.datetime):
#                             row[i] = value.replace(tzinfo=None)
#                     ws.append(row)
#             output = BytesIO()
#             wb.save(output)
#             output.seek(0)
#             response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#             response['Content-Disposition'] = 'attachment; filename=mydata.xlsx'
#             return response



from datetime import datetime
from django.utils import timezone
from django.db.models import F, Value
from django.db.models.functions import Concat

class InterviewDownloadExcel(APIView):
    def get(self, request):
        headers = [
            "CandidateId",
            "FirstName",
            "Interview Date",
            "Interview Round Name",
            "Interview Type",
            "Interviewer EmployeeID",
            "Reviewed On",
            "Interview Status",
            "Scheduled By",
            "Scheduled On"
            "Assigned Status"
        ]
        required_models = [InterviewScheduleStatusModel]
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for model in required_models:
            queryset = model.objects.filter(interviewe__isnull=False).annotate(
                CandidateId=F('InterviewScheduledCandidate__CandidateId'),
                FirstName=F('InterviewScheduledCandidate__FirstName'),
                InterviewDate=F('interviewe__InterviewDate'),
                InterviewRoundName=F('interviewe__InterviewRoundName'),
                InterviewType=F('interviewe__InterviewType'),
                InterviewerEmployeeId=F('interviewe__interviewer__EmployeeId'),
                ReviewedOn=F('review__ReviewedOn'),
                InterviewStatus=F('review__interview_Status'),
                ScheduledBy=F('interviewe__ScheduledBy'),
                ScheduledOn=F('interviewe__ScheduledOn'),
                Interview_Schedule_Status=F("Interview_Schedule_Status")
            ).values(*[f.replace(" ", "") for f in headers])
            for item in queryset:
                row = [item.get(field.replace(" ", "")) for field in headers]
                for i, value in enumerate(row):
                    if isinstance(value, datetime):
                        row[i] = value.replace(tzinfo=None)
                ws.append(row)
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=mydata.xlsx'
        return response


class FinalDownloadExcel(APIView):
    def get(self, request):
        headers = ["CandidateId", "FirstName","Email","PrimaryContact","AppliedDesignation","Final_Results"]
        required_models = [CandidateApplicationModel]
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for model in required_models:
                    # queryset = model.objects.values(*headers)
            queryset = model.objects.filter(review__isnull=False).values(*headers)
            for item in queryset:
                row = [item.get(field) for field in headers]
                for i, value in enumerate(row):
                    if isinstance(value, timezone.datetime):
                        row[i] = value.replace(tzinfo=None)
                ws.append(row)
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=mydata.xlsx'
        return response
    
# selected canadidates download
class download(APIView):
    def get(self,request,selected_list):
        selected_list=json.loads(selected_list)
        print(selected_list)
        try:
            # selected_list=request.data.get("Candidates")
            headers = ["CandidateId", "FirstName","Email","PrimaryContact","AppliedDesignation","Final_Results"]
            required_models = [CandidateApplicationModel]
            wb = Workbook()
            ws = wb.active
            ws.append(headers)
            for model in required_models:
                        # queryset = model.objects.values(*headers)
                queryset = model.objects.filter(review__isnull=False,CandidateId__in=selected_list).values(*headers)
                for item in queryset:
                    row = [item.get(field) for field in headers]
                    for i, value in enumerate(row):
                        if isinstance(value, timezone.datetime):
                            row[i] = value.replace(tzinfo=None)
                    ws.append(row)
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            response = HttpResponse(output.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = 'attachment; filename=mydata.xlsx'
            return response
        except:
            return response("bad")




# Screening Assigned Candidates details download
class ScreeningAssignedCandidateDownload(APIView):
    def get(self, request,loginuser):
        candidate_ids = request.GET.getlist('can_id')  # Get the list of candidate IDs from the URL parameters
        assigned_candidates = InterviewScheduleStatusModel.objects.filter(screening__AssignedBy__EmployeeId=loginuser)
        assigned_candidates_data = []

        if candidate_ids:
            # If candidate IDs are provided, filter candidates by the provided IDs
            assigned_candidates = assigned_candidates.filter(screening__Candidate__in=candidate_ids)

        for assigned_candidate in assigned_candidates:
            if assigned_candidate.screening:
                ScreeningScheduleStatus = ScreeningAssigningModel.objects.get(id=assigned_candidate.screening.pk)
                assigned_candidate_data = ScreeningAssigningSerializer(ScreeningScheduleStatus).data

                rpk = assigned_candidate_data.get("Recruiter")
                cpk = assigned_candidate_data.get("Candidate")
                emp = EmployeeDataModel.objects.get(pk=rpk)
                can = CandidateApplicationModel.objects.get(pk=cpk)

                assigned_candidate_data["Recruiter"] = emp.EmployeeId
                assigned_candidate_data["AssignedBy"] = loginuser
                assigned_candidate_data["Candidate"] = can.CandidateId
                assigned_candidate_data["Name"] = can.FirstName
                assigned_candidate_data["Assigned_Status"] = assigned_candidate.Interview_Schedule_Status

                if assigned_candidate.review:
                    review_candidates = Review.objects.get(id=assigned_candidate.review.pk)
                    rev_data = SRS(review_candidates).data
                    assigned_candidate_data.update({"Review": rev_data})
                else:
                    assigned_candidate_data.update({"Review": {}})

                assigned_candidates_data.append(assigned_candidate_data)

        # Convert the data to a DataFrame
        df = pd.DataFrame(assigned_candidates_data)

# Interview Assigned Candidates details download
class InterviewAssignedCandidateDownload(APIView):
    def get(self, request,loginuser):
        candidate_ids = request.GET.getlist('can_id')  # Get the list of candidate IDs from the URL parameters
        assigned_candidates = InterviewScheduleStatusModel.objects.filter(interviewe__ScheduledBy__EmployeeId=loginuser)
        assigned_candidates_data = []

        if candidate_ids:
            # If candidate IDs are provided, filter candidates by the provided IDs
            assigned_candidates = assigned_candidates.filter(interviewe__Candidate__in=candidate_ids)

        for assigned_candidate in assigned_candidates:
            if assigned_candidate.interviewe:
                InterviewScheduleStatus = InterviewSchedulModel.objects.get(id=assigned_candidate.interviewe.pk)
                assigned_candidate_data = InterviewSchedulSerializer(InterviewScheduleStatus).data

                ipk = assigned_candidate_data.get("interviewer")
                emp = EmployeeDataModel.objects.get(pk=ipk)
                cpk = assigned_candidate_data.get("Candidate")
                can = CandidateApplicationModel.objects.get(pk=cpk)

                assigned_candidate_data["ScheduledBy"] = loginuser
                assigned_candidate_data["interviewer"] = emp.EmployeeId
                assigned_candidate_data["Candidate"] = can.CandidateId
                assigned_candidate_data["Name"] = can.FirstName
                assigned_candidate_data["Assigned_Status"] = assigned_candidate.Interview_Schedule_Status

                if assigned_candidate.review:
                    review_candidates = Review.objects.get(id=assigned_candidate.review.pk)
                    rev_data = IRS(review_candidates).data
                    assigned_candidate_data.update({"Review": rev_data})
                else:
                    assigned_candidate_data.update({"Review": {}})

                assigned_candidates_data.append(assigned_candidate_data)

        # Convert the data to a DataFrame
        df = pd.DataFrame(assigned_candidates_data)

        # Create an in-memory Excel file
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Assigned Candidates')

        # Prepare response
        excel_buffer.seek(0)
        response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=assigned_candidates.xlsx'
        return response

# Perticular Interview Assigned Candidates details download
class SingleInterviewAssignedCandidateDownload(APIView):
    def get(self, request, Interview=None,can_id=None):
        try:
            candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
            interview_employee = InterviewSchedulModel.objects.filter(id=Interview).first()
            interview_status = InterviewScheduleStatusModel.objects.filter(
                InterviewScheduledCandidate__CandidateId=candidate,
                interviewe__interviewer=interview_employee.interviewer,
                review__interview_id=Interview
            )
            
            if interview_status:
                list_data = {}
                interview_list = {}
                
                for i in interview_status:
                    if i.interviewe: 
                        Interview_Scheduled_data = InterviewSchedulModel.objects.get(id=i.interviewe.pk)
                        if i.review:
                            candidate_review = Review.objects.get(id=i.review.pk)
                            serialised_review = InterviewReviewSerializer(candidate_review).data
                        else:
                            serialised_review = {}

                        serialised_interview = InterviewSchedulSerializer(Interview_Scheduled_data).data
                        serialised_interview.update(serialised_review)
                        interview_list.update(serialised_interview)
                
                # if candidate.Fresher: #candidate.current_position in ['Fresher' , 'Student']
                if candidate.current_position in ['Fresher' , 'Student']:
                    candidate_data = FresherApplicationSerializer(candidate).data
                    list_data.update({"candidate_data": candidate_data})
                    list_data.update({"interview_data": interview_list})
                else:
                    candidate_data = ExperienceApplicationSerializer(candidate).data
                    list_data.update({"candidate_data": candidate_data})
                    list_data.update({"interview_data": interview_list})
                
                # Serialize the response data into a pandas DataFrame
                df = pd.DataFrame(list_data)
                
                # Create an in-memory Excel file
                excel_buffer = BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Candidate Data')

                # Prepare response
                excel_buffer.seek(0)
                response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename=candidate_data.xlsx'
                return response
            else:
                return Response({"message": "No interview data found for the candidate"}, status=status.HTTP_404_NOT_FOUND)
        except CandidateApplicationModel.DoesNotExist:
            return Response({"message": "Candidate not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response({"error": "An error occurred while processing the request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Perticular Interview Assigned Candidates details download
class SingleScreeningAssignedCandidateDownload(APIView):
    def get(self, request, can_id=None,screener=None):
        try:
            if can_id:
                candidate = CandidateApplicationModel.objects.get(CandidateId=can_id)
                interview_employee = ScreeningAssigningModel.objects.filter(id=screener).first()
                interview_status = InterviewScheduleStatusModel.objects.filter(
                    InterviewScheduledCandidate__CandidateId=candidate,
                    screening__Recruiter=interview_employee.Recruiter,
                    review__screeingreview=screener
                )
                
                if interview_status:
                    list_data = {}
                    interview_list = {}
                    
                    for i in interview_status:
                        if i.screening: 
                            Screening_Scheduled_data = ScreeningAssigningModel.objects.get(id=i.screening.pk)
                            if i.review:
                                candidate_review = Review.objects.get(id=i.review.pk)
                                serialised_review = ScreeningReviewSerializer(candidate_review).data
                            else:
                                serialised_review = {}

                            serialised_interview = ScreeningAssigningSerializer(Screening_Scheduled_data).data
                            serialised_interview.update(serialised_review)
                            interview_list.update(serialised_interview)
                    
                    # if candidate.Fresher:#candidate.current_position in ['Fresher' , 'Student']
                    if candidate.current_position in ['Fresher' , 'Student']:
                        candidate_data = FresherApplicationSerializer(candidate).data
                        list_data.update({"candidate_data": candidate_data})
                        list_data.update({"screening_data": interview_list})
                    else:
                        candidate_data = ExperienceApplicationSerializer(candidate).data
                        list_data.update({"candidate_data": candidate_data})
                        list_data.update({"screening_data": interview_list})
                    
                    # Serialize the response data into a pandas DataFrame
                    df = pd.DataFrame(list_data)
                    
                    # Create an in-memory Excel file
                    excel_buffer = BytesIO()
                    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='Candidate Data')

                    # Prepare response
                    excel_buffer.seek(0)
                    response = HttpResponse(excel_buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=candidate_data.xlsx'
                    return response
                else:
                    return Response({"message": "No interview data found for the candidate"}, status=status.HTTP_404_NOT_FOUND)
            
            else:
                return Response({"message": "No candidate ID provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        except CandidateApplicationModel.DoesNotExist:
            return Response({"message": "Candidate not found"}, status=status.HTTP_404_NOT_FOUND)
        
        except Exception as e:
            print(e)
            return Response({"error": "An error occurred while processing the request"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        


        # //////////////////////////////////////////////////////complete download /////////////////////////////////////////////////////////////////////


import pandas as pd
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import CandidateApplicationModel, InterviewScheduleStatusModel, Documents_Upload_Model, BG_VerificationModel
from .serializers import (
    InterviewSchedulSerializer, InterviewReviewSerializer, ScreeningAssigningSerializer,
    ScreeningReviewSerializer, DocumentsUploadModelSerializer, BGVerificationSerializer,
    FresherApplicationSerializer, ExperienceApplicationSerializer
)
from django.http import HttpResponse
import os
class CompleteFinalStatusDownloadView(APIView):
    def get(self, request, can_id): 
        try:
            Can_obj = CandidateApplicationModel.objects.get(CandidateId=can_id)
            single_can_review = InterviewScheduleStatusModel.objects.filter(Interview_Schedule_Status="Completed", InterviewScheduledCandidate=Can_obj)
            if not single_can_review:
                return Response({"message": "No interview data found for the candidate"}, status=status.HTTP_404_NOT_FOUND)

            interview_list = []
            screening_list = []
            for i in single_can_review:
                if i.interviewe: 
                    Interview_Scheduled_data = InterviewSchedulModel.objects.get(id=i.interviewe.pk)
                    candidate_review = Review.objects.get(id=i.review.pk)

                    serialised_interview = InterviewSchedulSerializer(Interview_Scheduled_data).data
                    serialised_review = InterviewReviewSerializer(candidate_review).data

                    serialised_interview.update(serialised_review)

                    interview_list.append(serialised_interview)
                elif i.screening:
                    Screenied_Assigned_data = ScreeningAssigningModel.objects.get(id=i.screening.pk)
                    candidate_review = Review.objects.get(id=i.review.pk)
    
                    serialised_screening = ScreeningAssigningSerializer(Screenied_Assigned_data).data
                    serialised_review = ScreeningReviewSerializer(candidate_review).data

                    serialised_screening.update(serialised_review)

                    screening_list.append(serialised_screening)

            Documents_Upload = Documents_Upload_Model.objects.filter(CandidateID__CandidateId=can_id, CandidateID__Documents_Upload_Status="Uploaded").first()
            if Documents_Upload:
                doc_serializer = DocumentsUploadModelSerializer(Documents_Upload, context={'request': request})
            else:
                doc_serializer = {}
            
            BG_review = BG_VerificationModel.objects.filter(candidate__CandidateId=can_id, candidate__BG_Status="Verified").first()
            if BG_review:
                BGV = BGVerificationSerializer(BG_review).data
            else:
                BGV = {}
            
            # if Can_obj.Fresher:#candidate.current_position in ['Fresher' , 'Student']
            if Can_obj.current_position in ['Fresher' , 'Student']:
                candidate_data = FresherApplicationSerializer(Can_obj).data
            else:
                candidate_data = ExperienceApplicationSerializer(Can_obj).data

            # Create DataFrames for interview, screening, uploaded documents, and background verification data
            interview_df = pd.DataFrame(interview_list)
            screening_df = pd.DataFrame(screening_list)
            if doc_serializer:
                documents_df = pd.DataFrame([doc_serializer.data])
            else:
                documents_df = pd.DataFrame()
            if BG_review:
                bg_verification_df = pd.DataFrame([BGV])
            else:
                bg_verification_df = pd.DataFrame()

            # Combine all data into a single DataFrame
            all_data = pd.concat([pd.DataFrame([candidate_data]), interview_df, screening_df, documents_df, bg_verification_df], axis=1)

            # Delete 'id' column
            if 'id' in all_data.columns:
                del all_data['id']

            # Convert 'Fresher' and 'Experience' columns based on conditions
            if 'Fresher' in all_data:
                all_data['Fresher'] = all_data['Fresher'].apply(lambda x: 'Fresher' if x else '')
            if 'Experience' in all_data:
                all_data['Experience'] = all_data['Experience'].apply(lambda x: 'Experience' if x else '')

            # Create a file path to save the Excel file
            file_path = os.path.join(os.getcwd(), 'candidate_data.xlsx')

            # Save the combined data to the Excel file
            all_data.to_excel(file_path, index=False)

            # Open and read the Excel file as binary data
            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename="candidate_data.xlsx"'
                return response

        except Exception as e:
            print(f"Error occurred: {e}")
            import traceback
            traceback.print_exc()
            return Response({"message": "Error occurred while processing the request"}, status=status.HTTP_400_BAD_REQUEST)
        