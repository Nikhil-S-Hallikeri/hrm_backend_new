from django.shortcuts import render
from django.db.models import Q

# Create your views here.
from EMS_App.imports import *
from HRM_App.models import *
from HRM_App.serializers import *
from LMS_App.models import *
from LMS_App.serializers import *
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

# emp_joined_year=str(timezone.localdate().year)[2:]
# def autoemployeeid():
#     return f"MTM{emp_joined_year}E"+str(uuid.uuid4().hex)[:2].upper()


def autoemployeeid(emp_status):
    emp_joined_year = str(timezone.localdate().year)[2:]
    next_number = EmployeeIDTracker.get_next_employee_number()
    return f"MTM{emp_joined_year}{emp_status}{next_number}"


# 10/1/2026
class CandidateEmployeeInformation(APIView):
    def get(self, request, can_obj):
        try:
            employee = EmployeeInformation.objects.filter(Candidate_id=can_obj).first()
            if employee:
                serializer = EmployeeInformationSerializer(employee).data
                offer_data = OfferLetterModel.objects.filter(
                    CandidateId=employee.Candidate_id
                ).first()
                # Combine the serialized data with the offer letter data
                # serializer["offered_position"] = offer_data.position.Name if offer_data else None
                serializer["offered_position"] = (
                    offer_data.position.Name
                    if offer_data and offer_data.position
                    else None
                )
                serializer["contact_info"] = (
                    offer_data.contact_info if offer_data else None
                )

                return Response(serializer, status=status.HTTP_200_OK)
            else:
                return Response(
                    {"detail": "Employee not found"}, status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EmployeeInformationView(APIView):
    def get(self, request, emp_info_id=None):
        try:
            if emp_info_id:
                employee = EmployeeInformation.objects.filter(pk=emp_info_id).first()
                if employee:
                    serializer = EmployeeInformationSerializer(employee)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    return Response({}, serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, can_id):
        try:
            emp_info = request.data.copy()
            can_obj = get_object_or_404(CandidateApplicationModel, pk=can_id)
            emp_info["Candidate_id"] = can_obj.pk
            serializer = EmployeeInformationSerializer(data=emp_info)
            if serializer.is_valid():
                if not EmployeeInformation.objects.filter(
                    Candidate_id=can_obj.pk
                ).exists():
                    instance = serializer.save()
                    emp_info_instance = EmployeeInformation.objects.filter(
                        pk=instance.pk
                    ).first()

                    if (
                        emp_info_instance.Employeement_Type
                        and emp_info_instance.Employeement_Type == "intern"
                    ):
                        emp_info_instance.employee_Id = autoemployeeid(emp_status="I")
                    else:
                        emp_info_instance.employee_Id = autoemployeeid(emp_status="E")

                    emp_info_instance.save()
                    serializer_data = serializer.data
                    serializer_data["employee_Id"] = emp_info_instance.employee_Id
                    return Response(serializer_data, status=status.HTTP_201_CREATED)
                else:
                    return Response(
                        "candidate_id exist", status=status.HTTP_201_CREATED
                    )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except CandidateApplicationModel.DoesNotExist:
            return Response(
                {"error": "Candidate not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, emp_info_id):
        emp_info = EmployeeInformation.objects.get(pk=emp_info_id)
        serializer = EmployeeInformationSerializer(
            emp_info, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            if emp_info.form_submitted_status == False:
                if not emp_info.ProfileVerification:
                    emp_info.ProfileVerification = None
                emp_info.save()
            return Response("done!", status=status.HTTP_201_CREATED)
        else:
            print(serializer.errors)
            return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)


class EmployeeEducationView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = EmployeeEducation.objects.filter(
                EMP_Information__pk=emp_info_id
            )
            serializer = EmployeeEducationSerializer(employees, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        educations = request.data
        education_data_list = []
        for education in educations:
            education["EMP_Information"] = emp_info_id
            serializer = EmployeeEducationSerializer(data=education)
            if serializer.is_valid():
                instance = serializer.save()
                education_data_list.append(serializer.data)
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(education_data_list, status=status.HTTP_201_CREATED)

    def patch(self, request, id):
        try:
            emp_info = EmployeeEducation.objects.get(pk=id)
            serializer = EmployeeEducationSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = EmployeeEducation.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmployeeEducation.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class FamilyDetailsView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = FamilyDetails.objects.filter(EMP_Information__pk=emp_info_id)
            serializer = FamilyDetailsSerializer(employees, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            family_data = request.data.copy()
            if not family_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            family_data_list = []
            for data in family_data:
                data["EMP_Information"] = emp_info_id
                serializer = FamilyDetailsSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    family_data_list.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(family_data_list, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = FamilyDetails.objects.get(pk=id)
            serializer = FamilyDetailsSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = FamilyDetails.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except FamilyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class EmergencyDetailsView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = EmergencyDetails.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = EmergencyDetailsSerializer(employees)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            emergency_details_data = request.data
            if not emergency_details_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(emergency_details_data, list):
                emergency_details_data = [emergency_details_data]
            saved_data = []
            for data in emergency_details_data:
                data["EMP_Information"] = emp_info_id
                serializer = EmergencyDetailsSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = EmergencyDetails.objects.get(pk=id)
            serializer = EmergencyDetailsSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = FamilyDetails.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmergencyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class EmergencyContactView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = EmergencyContact.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = EmergencyContactSerializer(employees)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Emergency_Contact_data = request.data
            if not Emergency_Contact_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Emergency_Contact_data, list):
                Emergency_Contact_data = [Emergency_Contact_data]
            saved_data = []
            for data in Emergency_Contact_data:
                data["EMP_Information"] = emp_info_id
                serializer = EmergencyContactSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = EmergencyContact.objects.get(pk=id)
            serializer = EmergencyContactSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = EmergencyDetails.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmergencyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class CandidateReferenceView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = CandidateReference.objects.filter(
                EMP_Information__pk=emp_info_id
            )
            serializer = CandidateReferenceSerializer(employees, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Candidate_Reference_data = request.data
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = CandidateReferenceSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = CandidateReference.objects.get(pk=id)
            serializer = CandidateReferenceSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = CandidateReference.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmergencyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class ExceperienceModelView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = ExceperienceModel.objects.filter(
                EMP_Information__pk=emp_info_id
            )
            serializer = ExceperienceModelSerializer(employees, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Exceperience_Model_data = request.data
            if not Exceperience_Model_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Exceperience_Model_data, list):
                Exceperience_Model_data = [Exceperience_Model_data]
            saved_data = []
            for data in Exceperience_Model_data:
                data["EMP_Information"] = emp_info_id
                serializer = ExceperienceModelSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = ExceperienceModel.objects.get(pk=id)
            serializer = ExceperienceModelSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = ExceperienceModel.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmergencyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class LastPositionHeldView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = Last_Position_Held.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = Last_Position_HeldSerializer(employees)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Last_Position_data = request.data
            if not Last_Position_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Last_Position_data, list):
                Last_Position_data = [Last_Position_data]
            saved_data = []
            for data in Last_Position_data:
                data["EMP_Information"] = emp_info_id
                serializer = Last_Position_HeldSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = Last_Position_Held.objects.get(pk=id)
            serializer = Last_Position_HeldSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = Last_Position_Held.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmergencyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class EmployeePersonalInformationView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = EmployeePersonalInformation.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = EmployeePersonalInformationSerializer(employees)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Candidate_Reference_data = request.data
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = EmployeePersonalInformationSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = EmployeePersonalInformation.objects.get(pk=id)

            serializer = EmployeePersonalInformationSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)


class EmployeeIdentityView(APIView):
    def get(self, request, emp_info_id):
        try:
            employee = EmployeeIdentity.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = EmployeeIdentitySerializer(
                employee, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            data = request.data
            print(data)
            if not data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(data, list):
                data = [data]
            saved_data = []
            for item in data:
                item["EMP_Information"] = emp_info_id
                serializer = EmployeeIdentitySerializer(data=item)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = EmployeeIdentity.objects.get(pk=id)
            data = request.data.copy()  # Make a mutable copy of request data

            # Check for pan_proof file
            if "pan_proof" in request.FILES:
                pan_file = request.FILES["pan_proof"]
                if isinstance(pan_file, (InMemoryUploadedFile, TemporaryUploadedFile)):
                    data["pan_proof"] = pan_file
                else:
                    return Response(
                        {"error": "Invalid file type for pan_proof"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif "pan_proof" in data:
                if isinstance(data["pan_proof"], str) and data["pan_proof"].startswith(
                    "http"
                ):
                    # URL provided instead of a file, ignore this field or handle as needed
                    del data["pan_proof"]
                elif not data["pan_proof"]:
                    del data["pan_proof"]  # Remove if empty or invalid
            else:
                data["pan_proof"] = emp_info.pan_proof

            # Check for aadher_proof file
            if "aadher_proof" in request.FILES:
                aadher_file = request.FILES["aadher_proof"]
                if isinstance(
                    aadher_file, (InMemoryUploadedFile, TemporaryUploadedFile)
                ):
                    data["aadher_proof"] = aadher_file
                else:
                    return Response(
                        {"error": "Invalid file type for aadher_proof"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif "aadher_proof" in data:
                if isinstance(data["aadher_proof"], str) and data[
                    "aadher_proof"
                ].startswith("http"):
                    # URL provided instead of a file, ignore this field or handle as needed
                    del data["aadher_proof"]
                elif not data["aadher_proof"]:
                    del data["aadher_proof"]  # Remove if empty or invalid
            else:
                data["aadher_proof"] = emp_info.aadher_proof

            serializer = EmployeeIdentitySerializer(
                emp_info, data=data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                # Optionally delete old files if new files are provided
                if "pan_proof" in request.FILES and emp_info.pan_proof:
                    emp_info.pan_proof.delete(save=False)
                if "aadher_proof" in request.FILES and emp_info.aadher_proof:
                    emp_info.aadher_proof.delete(save=False)

                serializer.save()
                return Response("Update successful!", status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except EmployeeIdentity.DoesNotExist:
            return Response("Not found.", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class BankAccountDetailsView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = BankAccountDetails.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = BankAccountDetailsSerializer(
                employees, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Candidate_Reference_data = request.data
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = BankAccountDetailsSerializer(
                    data=data, context={"request": request}
                )
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            print(id)
            print(request.data)
            emp_info = BankAccountDetails.objects.get(pk=id)
            data = request.data.copy()  # Make a mutable copy of request data

            # Check for account_proof file
            if "account_proof" in request.FILES:
                account_file = request.FILES["account_proof"]
                if isinstance(
                    account_file, (InMemoryUploadedFile, TemporaryUploadedFile)
                ):
                    data["account_proof"] = account_file
                else:
                    return Response(
                        {"error": "Invalid file type for account_proof"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            elif "account_proof" in data:
                if isinstance(data["account_proof"], str) and data[
                    "account_proof"
                ].startswith("http"):
                    # URL provided instead of a file, ignore this field or handle as needed
                    del data["account_proof"]
                elif not data["account_proof"]:
                    del data["account_proof"]  # Remove if empty or invalid
            else:
                data["account_proof"] = emp_info.account_proof

            serializer = BankAccountDetailsSerializer(
                emp_info, data=data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                # Optionally delete old file if a new file is provided
                if "account_proof" in request.FILES and emp_info.account_proof:
                    emp_info.account_proof.delete(save=False)

                serializer.save()
                return Response("Update successful!", status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except BankAccountDetails.DoesNotExist:
            return Response("Not found.", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PFDetailsView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = PFDetails.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = PFDetailsSerializer(employees, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            Candidate_Reference_data = request.data
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = PFDetailsSerializer(
                    data=data, context={"request": request}
                )
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = PFDetails.objects.get(pk=id)
            data = request.data.copy()  # Make a mutable copy of request data

            # Validate and update data
            serializer = PFDetailsSerializer(
                emp_info, data=data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response("Update successful!", status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except PFDetails.DoesNotExist:
            return Response("Not found.", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AditionalInformationView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = AditionalInformationModel.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = AditionalInformationSerializer(
                employees, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            print(request.data)
            Candidate_Reference_data = request.data
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = AditionalInformationSerializer(
                    data=data, context={"request": request}
                )
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = AditionalInformationModel.objects.get(pk=id)
            serializer = AditionalInformationSerializer(
                emp_info, data=request.data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class AttachmentModelView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = AttachmentsModel.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = AttachmentsModelSerializer(
                employees, context={"request": request}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            print(request.data)
            data = request.data
            if not data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(data, list):
                data = [data]
            saved_data = []
            for item in data:
                item["EMP_Information"] = emp_info_id
                serializer = AttachmentsModelSerializer(data=item)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            emp_info = AttachmentsModel.objects.get(pk=id)
            data = request.data.copy()  # Make a mutable copy of request data

            # Define file fields to handle
            file_fields = [
                "Degree_mark_sheets",
                "Offer_letter_copy",
                "upload_photo",
                "present_address_proof",
                "permanent_address_proof",
            ]

            for field in file_fields:
                if field in request.FILES:
                    file = request.FILES[field]
                    if isinstance(file, (InMemoryUploadedFile, TemporaryUploadedFile)):
                        data[field] = file
                    else:
                        return Response(
                            {"error": f"Invalid file type for {field}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                elif field in data:
                    if isinstance(data[field], str) and data[field].startswith("http"):
                        # URL provided, ignore this field or handle as needed
                        del data[field]
                    elif not data[field]:
                        # Remove if empty or invalid
                        del data[field]
                else:
                    # Use the existing file if not provided in the request
                    data[field] = getattr(emp_info, field)

            serializer = AttachmentsModelSerializer(
                emp_info, data=data, partial=True, context={"request": request}
            )
            if serializer.is_valid():
                # Optionally delete old files if new files are provided
                for field in file_fields:
                    if field in request.FILES and getattr(emp_info, field):
                        getattr(emp_info, field).delete(save=False)

                serializer.save()
                return Response("Update successful!", status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AttachmentsModel.DoesNotExist:
            return Response("Not found.", status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            print(e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class Documents_SubmitedView(APIView):
    def get(self, request, emp_info_id):
        try:
            employees = Documents_Submited.objects.filter(
                EMP_Information__pk=emp_info_id
            )
            serializer = Documents_SubmitedSerializer(employees, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            print(request.data)
            Candidate_Reference_data = request.data
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = Documents_SubmitedSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            id = request.data.get("id")
            emp_info = Documents_Submited.objects.get(pk=id)
            serializer = Documents_SubmitedSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response("error", status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            emp_info = Documents_Submited.objects.get(pk=id)
            emp_info.delete()
            return Response("Deleted successfully!", status=status.HTTP_204_NO_CONTENT)
        except EmergencyDetails.DoesNotExist:
            return Response(
                "Employee education record not found!", status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                f"An error occurred: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


class DeclarationView(APIView):
    def get(self, request, emp_info_id):
        try:
            employee_info = EmployeeInformation.objects.filter(pk=emp_info_id).first()
            employees = Declaration.objects.filter(
                EMP_Information__pk=emp_info_id
            ).first()
            serializer = DeclarationSerializer(
                employees, context={"request": request}
            ).data

            serializer["name"] = employee_info.full_name
            return Response(serializer, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        try:
            print(request.data)
            Candidate_Reference_data = request.data.copy()
            if not Candidate_Reference_data:
                return Response(
                    {"error": "No data provided"}, status=status.HTTP_400_BAD_REQUEST
                )
            if not isinstance(Candidate_Reference_data, list):
                Candidate_Reference_data = [Candidate_Reference_data]
            saved_data = []
            for data in Candidate_Reference_data:
                data["EMP_Information"] = emp_info_id
                serializer = DeclarationSerializer(data=data)
                if serializer.is_valid():
                    instance = serializer.save()
                    saved_data.append(serializer.data)
                else:
                    print(serializer.errors)
                    return Response(
                        serializer.errors, status=status.HTTP_400_BAD_REQUEST
                    )
            return Response(saved_data, status=status.HTTP_201_CREATED)
        except KeyError as e:
            print(e)
            return Response(
                {"error": f"Missing key: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            print(e)
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def patch(self, request, id):
        try:
            print(request.data)
            emp_info = Declaration.objects.get(pk=id)
            serializer = DeclarationSerializer(
                emp_info, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response("done!", status=status.HTTP_201_CREATED)
            else:
                print(serializer.errors)
                return Response("Fail!", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class EmployeeAssetsListCreateView(APIView):
    def get(self, request):

        emp_id = request.query_params.get("emp_id")
        if emp_id:
            assets = EmployeeAssetsModel.objects.filter(
                EMP_Information__employee_Id=emp_id
            )
        else:
            assets = EmployeeAssetsModel.objects.all()

        serializer = EmployeeAssetsSerializer(assets, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = EmployeeAssetsSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, asset_id):
        if not asset_id:
            return Response(
                "asset id is required to update", status=status.HTTP_400_BAD_REQUEST
            )
        asset = EmployeeAssetsModel.objects.filter(pk=asset_id).first()
        if not asset:
            return Response("asset not found", status=status.HTTP_400_BAD_REQUEST)

        serializer = EmployeeAssetsSerializer(asset, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, asset_id):
        if not asset_id:
            return Response(
                "asset id is required to update", status=status.HTTP_400_BAD_REQUEST
            )
        asset = EmployeeAssetsModel.objects.filter(pk=asset_id).first()
        if not asset:
            return Response("asset not found", status=status.HTTP_400_BAD_REQUEST)
        try:
            asset.delete()
            return Response("deleted successfully", status=status.HTTP_200_OK)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# add employee and  eddit employee
from django.db import IntegrityError
from django.core.exceptions import ObjectDoesNotExist


class NewEmployeesAdding(APIView):
    def get(self, request, id=None, emp_id=None):
        try:
            if id:
                emp_info = EmployeeInformation.objects.get(pk=id)
            else:
                emp_info = EmployeeInformation.objects.get(employee_Id=emp_id)

            emp_obj = EmployeeDataModel.objects.filter(
                employeeProfile=emp_info.pk
            ).first()
            emp_info_serializer = EmployeeInformationSerializer(emp_info).data
            emp_personal_info = EmployeePersonalInformation.objects.filter(
                EMP_Information__pk=emp_info.pk
            ).first()

            if emp_personal_info:
                emp_info_serializer["emp_personal_info"] = emp_personal_info.pk
                if emp_personal_info.religion:
                    emp_info_serializer["religion"] = emp_personal_info.religion.pk
                else:
                    emp_info_serializer["religion"] = None
            else:
                emp_info_serializer["emp_personal_info"] = None

            try:
                emp_info_serializer["Position"] = emp_obj.Position.Name
                emp_info_serializer["Position_id"] = emp_obj.Position.id
                emp_info_serializer["Department"] = emp_obj.Position.Department.Dep_Name
                emp_info_serializer["Department_id"] = emp_obj.Position.Department.id
                emp_info_serializer["Reporting_To"] = emp_obj.Reporting_To.EmployeeId
            except:
                emp_info_serializer["Position"] = None
                emp_info_serializer["Department"] = None
                emp_info_serializer["Reporting_To"] = None

            # permissions={"applied_list_access":emp_obj.applied_list_access,"screening_shedule_access":emp_obj.screening_shedule_access,
            #  "interview_shedule_access":emp_obj.interview_shedule_access,"final_status_access":emp_obj.final_status_access}

            emp_info_serializer["Dashboard"] = emp_obj.Designation
            emp_info_serializer["applied_list_access"] = emp_obj.applied_list_access
            emp_info_serializer["screening_shedule_access"] = (
                emp_obj.screening_shedule_access
            )
            emp_info_serializer["interview_shedule_access"] = (
                emp_obj.interview_shedule_access
            )
            emp_info_serializer["final_status_access"] = emp_obj.final_status_access
            emp_info_serializer["all_applicants_access"] = emp_obj.all_applicants_access
            # 6/6/26
            emp_info_serializer["leads_access"] = emp_obj.leads_access
            emp_info_serializer["universal_leads_access"] = (
                emp_obj.universal_leads_access
            )
            emp_info_serializer["self_activity_add"] = emp_obj.self_activity_add
            emp_info_serializer["all_employees_view"] = emp_obj.all_employees_view
            emp_info_serializer["all_employees_edit"] = emp_obj.all_employees_edit
            emp_info_serializer["employee_personal_details_view"] = (
                emp_obj.employee_personal_details_view
            )
            emp_info_serializer["massmail_communication"] = (
                emp_obj.massmail_communication
            )
            emp_info_serializer["holiday_calender_creation"] = (
                emp_obj.holiday_calender_creation
            )
            emp_info_serializer["assign_offerletter_prepare"] = (
                emp_obj.assign_offerletter_prepare
            )
            emp_info_serializer["job_post"] = emp_obj.job_post
            emp_info_serializer["attendance_upload"] = emp_obj.attendance_upload
            emp_info_serializer["leave_create"] = emp_obj.leave_create

            emp_info_serializer["leave_edit"] = emp_obj.leave_edit
            emp_info_serializer["salary_component_creation"] = (
                emp_obj.salary_component_creation
            )
            emp_info_serializer["salary_template_creation"] = (
                emp_obj.salary_template_creation
            )
            emp_info_serializer["assign_leave_apply"] = emp_obj.assign_leave_apply
            emp_info_serializer["assign_resignation_apply"] = (
                emp_obj.assign_resignation_apply
            )

            # emp_info_serializer.update({"permissions":permissions})

            return Response(emp_info_serializer, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        # Deserialize request data
        serializer = EmployeeInformationSerializer(data=request.data)
        if not serializer.is_valid():
            first_key = next(iter(serializer.errors))
            return Response(
                {"error": serializer.errors[first_key]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate fields and check for duplicates
        is_valid, error_message = self._validate_employee_data(serializer)
        if not is_valid:
            return Response(
                {"error": error_message}, status=status.HTTP_400_BAD_REQUEST
            )

        required_fields = ["Dasboard_Dig", "Designation", "Reporting_To"]
        missing_fields = [
            field for field in required_fields if not request.data.get(field)
        ]
        if missing_fields:
            return Response(
                {"error": ", ".join(missing_fields)}, status=status.HTTP_400_BAD_REQUEST
            )

        # Generate Employee ID
        emp_email = serializer.validated_data["email"]
        emp_type = serializer.validated_data["Employeement_Type"]
        autoemployee_id = autoemployeeid("I" if emp_type == "intern" else "E")

        # Set additional fields for employee
        serializer.validated_data.update(
            {
                "employee_Id": autoemployee_id,
                "ProfileVerification": "success",
                "is_verified": True,
                "employee_status": "active",
            }
        )

        # Save employee info
        emp_info = serializer.save()
        dashboard = request.data.get("Dasboard_Dig")
        emp_data_model = self._create_employee_data_model(emp_info, dashboard, request)

        # Handle leave eligibility and restricted leaves
        self._setup_employee_leave_eligibility(emp_data_model)
        self._setup_restricted_leaves(emp_data_model, request.data.get("religion"))

        # Set employee permissions and create registration
        try:
            self._set_employee_permissions(emp_data_model, request)
            self._create_employee_registration(emp_info)
            # self._employee_work_history(emp_data_model)

        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _validate_employee_data(self, serializer):
        """Check required employee fields and unique constraints."""
        required_fields = {
            "full_name": "Full name is required",
            "date_of_birth": "Date of birth is required",
            "gender": "Gender is required",
            "email": "Email is required",
            "employee_attendance_id": "Employee attendance ID is required",
            "mobile": "Mobile number is required",
            "hired_date": "Hired date is required",
            "Employeement_Type": "Employment type is required",
        }

        for field, error_message in required_fields.items():
            if not serializer.validated_data.get(field):
                return False, error_message

        emp_email = serializer.validated_data["email"]
        attendance_id = serializer.validated_data["employee_attendance_id"]

        if EmployeeInformation.objects.filter(email=emp_email.strip()).exists():
            print(EmployeeInformation.objects.filter(email=emp_email.strip()))
            return False, "Email already in use!"
        if EmployeeInformation.objects.filter(
            employee_attendance_id=attendance_id.strip()
        ).exists():
            return False, "Employee attendance ID already in use!"

        return True, None

    def _create_employee_data_model(self, emp_info, dashboard, request):
        """Create an entry in EmployeeDataModel with the given dashboard."""
        print("Designation", request.data.get("Designation"))
        designation_obj = DesignationModel.objects.filter(
            pk=request.data.get("Designation")
        ).first()
        rep_to = EmployeeDataModel.objects.filter(
            EmployeeId=request.data.get("Reporting_To")
        ).first()

        emp_data = EmployeeDataModel.objects.create(
            EmployeeId=emp_info.employee_Id,
            Name=emp_info.full_name,
            employeeProfile=emp_info,
            Designation=dashboard,
            Position=designation_obj if designation_obj else None,
            Reporting_To=rep_to if rep_to else None,
        )

        return emp_data

    def _setup_employee_leave_eligibility(self, emp_info):
        """Create leave eligibility for the employee."""
        emp_type = emp_info.employeeProfile.probation_status
        leaves_applicable = LeavesTypeDetailModel.objects.filter(
            Q(applicable_to=emp_type) | Q(applicable_to="both")
        )

        for leave_type in leaves_applicable:
            leave_eligibility = {"employee": emp_info.pk, "LeaveType": leave_type.pk}
            serializer = EmployeeLeaveTypesEligiblitySerializer(data=leave_eligibility)
            if serializer.is_valid():
                serializer.save()

    def _setup_restricted_leaves(self, emp_info, religion_id):
        """Create restricted leaves based on the employee's religion."""
        if religion_id:
            religion_obj = ReligionModels.objects.filter(pk=religion_id).first()
            EPIO = EmployeePersonalInformation.objects.create(
                EMP_Information=emp_info.employeeProfile, religion=religion_obj
            )

            holidays = CompanyHolidaysDataModel.objects.filter(
                Religion__pk=EPIO.religion.pk
            )
            for holiday in holidays:
                if not AvailableRestrictedLeaves.objects.filter(
                    holiday=holiday, employee=emp_info.pk
                ).exists():
                    AvailableRestrictedLeaves.objects.create(
                        holiday=holiday, employee=emp_info
                    )

    def _set_employee_permissions(self, emp, request):
        """Set employee permissions based on request data."""

        def str_to_bool(value):
            return value.lower() == "true"

        emp.applied_list_access = str_to_bool(
            request.data.get("applied_list_access", "false")
        )
        emp.screening_shedule_access = str_to_bool(
            request.data.get("screening_shedule_access", "false")
        )
        emp.interview_shedule_access = str_to_bool(
            request.data.get("interview_shedule_access", "false")
        )
        emp.final_status_access = str_to_bool(
            request.data.get("final_status_access", "false")
        )
        emp.all_applicants_access = str_to_bool(
            request.data.get("all_applicants_access", "false")
        )
        # 6/6/26
        emp.leads_access = str_to_bool(request.data.get("leads_access", "false"))
        emp.universal_leads_access = str_to_bool(
            request.data.get("universal_leads_access", "false")
        )
        emp.self_activity_add = str_to_bool(
            request.data.get("self_activity_add", "false")
        )
        emp.all_employees_view = str_to_bool(
            request.data.get("all_employees_view", "false")
        )
        emp.all_employees_edit = str_to_bool(
            request.data.get("all_employees_edit", "false")
        )
        emp.employee_personal_details_view = str_to_bool(
            request.data.get("employee_personal_details_view", "false")
        )
        emp.massmail_communication = str_to_bool(
            request.data.get("massmail_communication", "false")
        )
        emp.holiday_calender_creation = str_to_bool(
            request.data.get("holiday_calender_creation", "false")
        )
        emp.assign_offerletter_prepare = str_to_bool(
            request.data.get("assign_offerletter_prepare", "false")
        )
        emp.job_post = str_to_bool(request.data.get("job_post", "false"))
        emp.attendance_upload = str_to_bool(
            request.data.get("attendance_upload", "false")
        )
        emp.leave_create = str_to_bool(request.data.get("leave_create", "false"))
        emp.leave_edit = str_to_bool(request.data.get("leave_edit", "false"))
        emp.salary_component_creation = str_to_bool(
            request.data.get("salary_component_creation", "false")
        )
        emp.salary_template_creation = str_to_bool(
            request.data.get("salary_template_creation", "false")
        )
        emp.assign_resignation_apply = str_to_bool(
            request.data.get("assign_resignation_apply", "false")
        )
        emp.assign_leave_apply = str_to_bool(
            request.data.get("assign_leave_apply", "false")
        )
        emp.save()

    # def _employee_work_history(self,emp_data_model):
    #     emp_obj=EmployeeDataModel.objects.filter(employeeProfile="k")
    #     EPH=CompanyEmployeesPositionHistory.objects.create(
    #         employee=emp_data_model,
    #         last_designation=emp_data_model.Position.Name,
    #         das_position=emp_data_model.Designation,
    #     )
    #     pass

    def _create_employee_registration(self, emp_info):
        """Create registration and send HRMS credentials via email."""
        hashed_password = make_password("MTM@123")
        register_obj = RegistrationModel.objects.create(
            EmployeeId=emp_info.employee_Id,
            UserName=emp_info.full_name,
            Email=emp_info.email,
            PhoneNumber=emp_info.mobile,
            Password=hashed_password,
            is_active=True,
        )

        subject = (
            f"HRMS Credentials of Your Merida Account on {timezone.localtime().date()}"
        )
        message = f"""Dear {emp_info.full_name},
        
        Welcome to Merida Tech Minds! We are pleased to inform you that your account has been created in our HRMS.
            
        Use the below credentials to login to HRMS:
        Employee ID: {emp_info.employee_Id}
        Password: MTM@123
        https://hrm.meridahr.com/
            
        Regards,
        Team Merida."""

        send_mail(
            subject,
            message,
            "sender@example.com",
            [emp_info.email],
            fail_silently=False,
        )

    def patch(self, request, id):
        try:
            request_data = request.data.get("Update_Data")
            name = request_data.get("full_name")
            designation = request_data.get("Dashboard")
            position = request_data.get("Position")
            reporting_to = request_data.get("Reporting_To")
            emp_status = request_data.get("employee_status")

            emp_email = request_data["email"]

            if not emp_email:
                return Response("Email required!", status=status.HTTP_400_BAD_REQUEST)

            emp_info = EmployeeInformation.objects.get(pk=id)

            if emp_info.employee_status == "active" and emp_status == "in_active":
                request_data["email"] = emp_info.email + str(timezone.localtime())

            if emp_info.email != request_data["email"].strip():
                if EmployeeInformation.objects.filter(
                    email=request_data["email"].strip()
                ).exists():
                    print(EmployeeInformation.objects.filter(email=emp_email.strip()))
                    return Response(
                        "Email already in use!", status=status.HTTP_400_BAD_REQUEST
                    )

            employeement_type = request_data.get("Employeement_Type")
            probation_status = request_data.get("probation_status")
            if employeement_type == "intern":
                # del request_data["probation_Duration_From"]
                # del request_data["probation_Duration_To"]
                request_data.pop("probation_Duration_From", None)
                request_data.pop("probation_Duration_To", None)
            else:
                if probation_status == "probationer":
                    # del request_data["internship_Duration_From"]
                    # del request_data["internship_Duration_To"]
                    request_data.pop("internship_Duration_From", None)
                    request_data.pop("internship_Duration_To", None)
                else:
                    # del request_data["probation_Duration_From"]
                    # del request_data["probation_Duration_To"]
                    # del request_data["internship_Duration_From"]
                    # del request_data["internship_Duration_To"]
                    request_data.pop("probation_Duration_From", None)
                    request_data.pop("probation_Duration_To", None)
                    request_data.pop("internship_Duration_From", None)
                    request_data.pop("internship_Duration_To", None)

            serializer = EmployeeInformationSerializer(
                emp_info, data=request_data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                try:
                    register_obj = RegistrationModel.objects.filter(
                        EmployeeId=emp_info.employee_Id
                    ).first()
                    register_obj.UserName = emp_info.full_name
                    register_obj.Email = emp_info.email
                    register_obj.PhoneNumber = emp_info.mobile
                    register_obj.save()
                except:
                    pass
                emp_obj = EmployeeDataModel.objects.get(employeeProfile=emp_info.pk)
                if request_data.get("Reporting_To") or emp_obj.Reporting_To:
                    try:
                        emp_type = emp_info.probation_status
                        leaves_applicable = LeavesTypeDetailModel.objects.filter(
                            Q(applicable_to=emp_type) | Q(applicable_to="both")
                        )
                        for leave_type in leaves_applicable:
                            if not EmployeeLeaveTypesEligiblity.objects.filter(
                                LeaveType=leave_type.pk, employee__pk=emp_obj.pk
                            ).exists():
                                leave_eligibility = {
                                    "employee": emp_obj.pk,
                                    "LeaveType": leave_type.pk,
                                }
                                serializer = EmployeeLeaveTypesEligiblitySerializer(
                                    data=leave_eligibility
                                )
                                if serializer.is_valid():
                                    serializer.save()
                                else:
                                    print(serializer.errors)
                            else:
                                pass
                    except Exception as e:
                        print("Leave Creation fail", e)

                    try:
                        emp_religion = request_data.get("religion")
                        if emp_religion:
                            try:
                                religion_obj = ReligionModels.objects.get(
                                    pk=emp_religion
                                )
                            except ReligionModels.DoesNotExist:
                                raise ValueError(
                                    "Religion with the provided ID does not exist."
                                )

                            emp_personal_obj, created = (
                                EmployeePersonalInformation.objects.get_or_create(
                                    EMP_Information=emp_info
                                )
                            )

                            emp_personal_obj.religion = religion_obj
                            emp_personal_obj.save()
                            employee_religion = emp_personal_obj.religion
                        else:
                            emp_personal_obj = (
                                EmployeePersonalInformation.objects.filter(
                                    EMP_Information=emp_info
                                ).first()
                            )
                            if emp_personal_obj:
                                employee_religion = emp_personal_obj.religion
                            else:
                                employee_religion = None
                                pass
                                # raise ValueError("Employee personal information not found.")

                        if employee_religion:
                            holidays = CompanyHolidaysDataModel.objects.filter(
                                Religion__pk=employee_religion.pk
                            )
                            for holiday in holidays:
                                try:
                                    if not AvailableRestrictedLeaves.objects.filter(
                                        holiday__pk=holiday.pk, employee__pk=emp_obj.pk
                                    ).exists():
                                        AvailableRestrictedLeaves.objects.create(
                                            holiday=holiday, employee=emp_obj
                                        )
                                except IntegrityError as ie:
                                    print(f"IntegrityError: {ie}")
                                except Exception as e:
                                    print(f"An unexpected error occurred: {e}")

                    except ValueError as ve:
                        print(f"ValueError: {ve}")
                    except ObjectDoesNotExist as odne:
                        print(f"ObjectDoesNotExist: {odne}")
                    except IntegrityError as ie:
                        print(f"IntegrityError: {ie}")
                    except Exception as e:
                        print(f"An unexpected error occurred: {e}")

                if name:
                    emp_obj.Name = name
                    emp_obj.save()
                if designation and emp_obj.Designation != designation:
                    emp_obj.Designation = designation
                    emp_obj.save()

                    subject = f"HRMS Credentials of Your Merida Account "  # on {timezone.localtime().date()}
                    Message = f"Dear {emp_obj.Name},\n\nWelcome to Merida Tech Minds! We are pleased to inform you that your account has been created in our HRMS.\n\nuse below credentials to login to HRMS.\n\nEmployeeId : {emp_obj.EmployeeId}\n\nPassword   : MTM@123\nhttps://hrm.meridahr.com/\nRegards\nTeam Merida."
                    send_mail(
                        subject,
                        Message,
                        "sender@example.com",
                        [emp_info.email],
                        fail_silently=False,
                    )

                designation_obj = DesignationModel.objects.filter(pk=position).first()
                if designation_obj:
                    emp_obj.Position = designation_obj
                    emp_obj.save()
                rep_to = EmployeeDataModel.objects.filter(
                    EmployeeId=reporting_to
                ).first()
                if reporting_to:
                    emp_obj.Reporting_To = rep_to
                    emp_obj.save()

                # emp_obj.applied_list_access=request_data.get("applied_list_access")
                # emp_obj.screening_shedule_access=request_data.get("screening_shedule_access")
                # emp_obj.interview_shedule_access=request_data.get("interview_shedule_access")
                # emp_obj.final_status_access=request_data.get("final_status_access")

                permissions = [
                    "applied_list_access",
                    "screening_shedule_access",
                    "self_activity_add",
                    "all_employees_view",
                    "all_employees_edit",
                    "interview_shedule_access",
                    "final_status_access",
                    "employee_personal_details_view",
                    "massmail_communication",
                    "holiday_calender_creation",
                    "assign_offerletter_prepare",
                    "job_post",
                    "attendance_upload",
                    "leave_create",
                    "leave_edit",
                    "salary_component_creation",
                    "salary_template_creation",
                    "assign_leave_apply",
                    "assign_resignation_apply",
                    "all_applicants_access",
                    "leads_access",
                    "universal_leads_access",  # 6/6/26
                ]

                # Loop through each permission and set it if the value in request_data is not None
                for permission in permissions:
                    new_value = request_data.get(permission)
                    if new_value is not None:
                        setattr(emp_obj, permission, new_value)
                emp_obj.save()

                return Response("Done!", status=status.HTTP_200_OK)
            else:
                print(serializer.errors)
                return Response("Failed", status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id):
        try:
            # Retrieve the instance you want to delete
            emp_info = EmployeeInformation.objects.filter(pk=id).first()
            if not emp_info:
                return Response("Employee not found", status=status.HTTP_404_NOT_FOUND)
            # Delete the instance
            reg_obj = RegistrationModel.objects.filter(
                EmployeeId=emp_info.employee_Id
            ).first()
            emp_info.delete()
            if reg_obj:
                reg_obj.delete()
            return Response(
                "Employee deleted successfully", status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


from rest_framework import viewsets


class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Deparments.objects.all()
    serializer_class = DepartmentSerializer


class DesignationViewSet(viewsets.ModelViewSet):
    serializer_class = DesignationSerializer

    def get_queryset(self):
        queryset = DesignationModel.objects.all()
        designation_id = self.kwargs.get("pk")
        department_id = self.kwargs.get("Dep_id")

        if designation_id:
            # If a designation ID is provided, filter by that ID
            queryset = queryset.filter(id=designation_id)
        elif department_id:
            # If a department ID is provided, filter by department
            queryset = queryset.filter(Department_id=department_id)

        return queryset

    def retrieve(self, request, *args, **kwargs):
        # Override the retrieve method to handle specific designation fetching
        designation_id = self.kwargs.get("pk")
        if designation_id:
            # Get the specific designation
            designation = self.get_queryset().first()
            if designation:
                serializer = self.get_serializer(designation)
                return Response(serializer.data)
            else:
                return Response({"detail": "Not found."}, status=404)
        return super().retrieve(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        print(request.data)
        designation_id = self.kwargs.get("pk")
        if designation_id:
            # Check if the designation exists
            designation = self.get_queryset().first()
            if not designation:
                return Response({"detail": "Not found."}, status=404)

            # Proceed with the update
            serializer = self.get_serializer(
                designation, data=request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        designation_id = self.kwargs.get("pk")
        if designation_id:
            designation = self.get_queryset().first()
            if not designation:
                return Response({"detail": "Not found."}, status=404)

            self.perform_destroy(designation)
            return Response(status=status.HTTP_204_NO_CONTENT)

        return super().destroy(request, *args, **kwargs)


class ReligionViewSet(viewsets.ModelViewSet):
    queryset = ReligionModels.objects.all()
    serializer_class = ReligionSerializer


# ..........................Joining formalityes verification...................................

class EmployeeCreation(APIView):
    def post(self, request, emp_info_id):
        try:
            data = request.data.copy()
            prof_verification = data.get("ProfileVerification")
            verifier = data.get("Verifier")
            subject = data.get("subject")
            mail_content = data.get("mail_content")
            mail_send_status = data.get("mail_send_status")

            emp_info_obj = get_object_or_404(EmployeeInformation, pk=emp_info_id)
            emp_info_obj.ProfileVerification = prof_verification
            emp_info_obj.save()

            if emp_info_obj.ProfileVerification == "success":
                emp_info_obj.employee_status = "active"
                emp_info_obj.is_verified = True
                offer_obj = OfferLetterModel.objects.filter(
                    CandidateId=emp_info_obj.Candidate_id
                ).first()
                if offer_obj:
                    emp_info_obj.hired_date = offer_obj.Date_of_Joining
                    emp_info_obj.Employeement_Type = offer_obj.Employeement_Type
                    if offer_obj.Employeement_Type == "intern":
                        emp_info_obj.internship_Duration_From = (
                            offer_obj.internship_Duration_From
                        )
                        emp_info_obj.internship_Duration_To = (
                            offer_obj.internship_Duration_To
                        )
                    elif offer_obj.Employeement_Type == "permanent":
                        emp_info_obj.probation_status = offer_obj.probation_status
                        if offer_obj.probation_status == "probationer":
                            emp_info_obj.probation_Duration_From = (
                                offer_obj.probation_Duration_From
                            )
                            emp_info_obj.probation_Duration_To = (
                                offer_obj.probation_Duration_To
                            )
                    emp_info_obj.save()

                # Check and create EmployeeDataModel if not exists
                if not EmployeeDataModel.objects.filter(
                    EmployeeId=emp_info_obj.employee_Id
                ).exists():
                    emp_obj = EmployeeDataModel.objects.filter(
                        EmployeeId=verifier
                    ).first()
                    emp_create = EmployeeDataModel.objects.create(
                        EmployeeId=emp_info_obj.employee_Id,
                        Name=emp_info_obj.full_name,
                        employeeProfile=emp_info_obj,
                        verified_by=emp_obj,
                        Designation="Employee",
                    )
                    if offer_obj and offer_obj.position:
                        emp_create.Position = offer_obj.position
                        emp_create.save()

                    # Create CompanyEmployeesPositionHistory record
                    try:
                        EPH = CompanyEmployeesPositionHistory.objects.create(
                            employee=emp_create
                        )
                        EPH.designation = emp_create.Position
                        EPH.assigned_salary = offer_obj.CTC if offer_obj.CTC else None
                        EPH.start_date = (
                            offer_obj.Date_of_Joining
                            if offer_obj.Date_of_Joining
                            else None
                        )
                        EPH.rm_manager = (
                            emp_create.Reporting_To if emp_create.Reporting_To else None
                        )
                        EPH.Employeement_Type = offer_obj.Employeement_Type
                        EPH.internship_Duration_From = (
                            offer_obj.internship_Duration_From
                        )
                        EPH.internship_Duration_To = offer_obj.internship_Duration_To
                        EPH.probation_status = offer_obj.probation_status
                        EPH.probation_Duration_From = offer_obj.probation_Duration_From
                        EPH.probation_Duration_To = offer_obj.probation_Duration_To
                        EPH.applicable_date = timezone.localdate()
                        EPH.save()
                    except Exception as e:
                        return Response(
                            f"Error creating position history: {str(e)}",
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Create RegistrationModel record
                    try:
                        if not RegistrationModel.objects.filter(
                            EmployeeId=emp_info_obj.employee_Id
                        ).exists():
                            password = data.get("Password")
                            hashed_password = make_password(password)
                            RegistrationModel.objects.create(
                                EmployeeId=emp_info_obj.employee_Id,
                                UserName=emp_info_obj.full_name,
                                Email=emp_info_obj.email,
                                PhoneNumber=emp_info_obj.mobile,
                                Password=hashed_password,
                                is_active=True,
                            )
                    except Exception as e:
                        return Response(
                            f"Error creating registration: {str(e)}",
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Send email if required
                try:
                    if mail_content and mail_send_status:
                        send_mail(
                            subject=subject,
                            message=mail_content,
                            from_email="sender@example.com",
                            recipient_list=[emp_info_obj.email],
                            fail_silently=False,
                            html_message=mail_content,
                        )

                except Exception as e:
                    return Response(
                        f"Error sending email: {str(e)}",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                return Response(
                    "Employment Created Successfully", status=status.HTTP_201_CREATED
                )

            elif emp_info_obj.ProfileVerification == "failed":
                emp_info_obj.employee_status = "inactive"
                emp_info_obj.form_submitted_status = False
                emp_info_obj.is_verified = False
                emp_info_obj.save()

                # Send email for failed verification
                try:
                    if mail_content and mail_send_status:
                        send_mail(
                            subject=subject,
                            message=mail_content,
                            from_email="sender@example.com",
                            recipient_list=[emp_info_obj.email],
                            fail_silently=False,
                        )
                except Exception as e:
                    return Response(
                        f"Error sending email: {str(e)}",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                return Response(
                    "Employment Verification Failed!", status=status.HTTP_200_OK
                )

        except EmployeeInformation.DoesNotExist:
            return Response(
                "Employee information not found.", status=status.HTTP_404_NOT_FOUND
            )
        except KeyError as e:
            return Response(
                f"Missing field: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )
        # except Exception as e:
        #     return
        except Exception as e:
            import traceback

            traceback.print_exc()
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JoiningFormalityesSubmitedList(APIView):
    def get(self, request, emp_info_id=None):
        if emp_info_id:
            try:
                employee_information = get_object_or_404(
                    EmployeeInformation, pk=emp_info_id
                )

                # Using prefetch_related to retrieve related objects
                employee_information = EmployeeInformation.objects.prefetch_related(
                    "employeeeducation_set",
                    "familydetails_set",
                    "emergencydetails_set",
                    "emergencycontact_set",
                    "candidatereference_set",
                    "exceperiencemodel_set",
                    "last_position_held_set",
                    "employeepersonalinformation_set",
                    "employeeidentity_set",
                    "bankaccountdetails_set",
                    "pfdetails_set",
                    "aditionalinformationmodel_set",
                    "attachmentsmodel_set",
                    "declaration_set",
                ).get(pk=emp_info_id)

                employee_profile = EmployeeInformationSerializer(employee_information)
                education_serializer = EmployeeEducationSerializer(
                    employee_information.employeeeducation_set.all(), many=True
                )
                family_serializer = FamilyDetailsSerializer(
                    employee_information.familydetails_set.all(), many=True
                )
                emergency_details_serializer = EmergencyDetailsSerializer(
                    employee_information.emergencydetails_set.all(), many=True
                )
                emergency_contact_serializer = EmergencyContactSerializer(
                    employee_information.emergencycontact_set.all(), many=True
                )
                candidate_reference_serializer = CandidateReferenceSerializer(
                    employee_information.candidatereference_set.all(), many=True
                )
                experience_serializer = ExceperienceModelSerializer(
                    employee_information.exceperiencemodel_set.all(), many=True
                )
                last_position_held_serializer = Last_Position_HeldSerializer(
                    employee_information.last_position_held_set.all(), many=True
                )
                personal_info_serializer = EmployeePersonalInformationSerializer(
                    employee_information.employeepersonalinformation_set.all(),
                    many=True,
                )
                employee_identity_serializer = EmployeeIdentitySerializer(
                    employee_information.employeeidentity_set.all(), many=True
                )
                bank_account_serializer = BankAccountDetailsSerializer(
                    employee_information.bankaccountdetails_set.all(), many=True
                )
                pf_details_serializer = PFDetailsSerializer(
                    employee_information.pfdetails_set.all(), many=True
                )
                additional_info_serializer = AditionalInformationSerializer(
                    employee_information.aditionalinformationmodel_set.all(), many=True
                )
                attachments_serializer = AttachmentsModelSerializer(
                    employee_information.attachmentsmodel_set.all(), many=True
                )
                declaration_serializer = DeclarationSerializer(
                    employee_information.declaration_set.all(), many=True
                )

                employee_profile_data = {
                    "EmployeeInformation": employee_profile.data,
                    "EducationDetails": education_serializer.data,
                    "FamilyDetails": family_serializer.data,
                    "EmergencyDetails": emergency_details_serializer.data,
                    "EmergencyContactDetails": emergency_contact_serializer.data,
                    "CandidateReferenceDetails": candidate_reference_serializer.data,
                    "ExperienceDetails": experience_serializer.data,
                    "LastPositionHeldDetails": last_position_held_serializer.data,
                    "PersonalInformation": personal_info_serializer.data,
                    "EmployeeIdentity": employee_identity_serializer.data,
                    "BankAccountDetails": bank_account_serializer.data,
                    "PFDetails": pf_details_serializer.data,
                    "AdditionalInformation": additional_info_serializer.data,
                    "Attachments": attachments_serializer.data,
                    "Declaration": declaration_serializer.data,
                }

                return Response(employee_profile_data, status=status.HTTP_200_OK)

            except Exception as e:
                print(e)
                return Response(
                    f"Bad Request: {str(e)}", status=status.HTTP_400_BAD_REQUEST
                )
        else:
            emp_info_obj = EmployeeInformation.objects.filter(
                ProfileVerification=None, form_submitted_status=True
            )
            serializer = EmployeeInformationSerializer(emp_info_obj, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


from payroll_app.models import EmployeeSalaryBreakUp


class EmployeeHistoryCreating(APIView):
    def get(self, request, emp_info_id):
        try:
            if emp_info_id:
                emp_obj = EmployeeDataModel.objects.filter(
                    employeeProfile=emp_info_id
                ).first()

                EPH = CompanyEmployeesPositionHistory.objects.filter(
                    employee=emp_obj.pk, is_applicable=True
                ).first()
                emp_history = {}
                serializer = CompanyEmployeesPositionHistorySerializer(EPH).data
                emp_history["emp_history"] = serializer

                ESB = EmployeeSalaryBreakUp.objects.filter(
                    employee_id__pk=emp_obj.pk
                ).first()
                esb_serializer = EmployeeSalaryBreakUpSerializer(ESB).data
                emp_history["template"] = esb_serializer
                return Response(emp_history, status=status.HTTP_200_OK)

            else:
                EPH = CompanyEmployeesPositionHistory.objects.all()
                serializer = CompanyEmployeesPositionHistorySerializer(
                    EPH, many=True
                ).data
                return Response(serializer, status=status.HTTP_200_OK)
        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, emp_info_id):
        gross_salary = request.data.get("assigned_salary")
        if not gross_salary:
            return Response(
                {"error": "Gross_salary is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        emp_obj = EmployeeDataModel.objects.filter(employeeProfile=emp_info_id).first()
        if not emp_obj:
            return Response(
                {"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND
            )
        else:
            EPH = CompanyEmployeesPositionHistory.objects.create(
                employee=emp_obj, assigned_salary=gross_salary
            )
            if EPH:
                EPH.designation = emp_obj.Position if emp_obj.Position else None
                EPH.rm_manager = emp_obj.Reporting_To if emp_obj.Reporting_To else None
                EPH.das_position = emp_obj.Designation if emp_obj.Designation else None
                EPH.applicable_date = timezone.localdate()
                EPH.Employeement_Type = emp_obj.employeeProfile.Employeement_Type
                EPH.is_applicable = True
                EPH.save()
                serializer = CompanyEmployeesPositionHistorySerializer(EPH).data
                return Response(serializer, status=status.HTTP_200_OK)

    def patch(self, request, id):
        try:
            EPH = CompanyEmployeesPositionHistory.objects.filter(pk=id).first()
            if EPH:
                serializer = CompanyEmployeesPositionHistorySerializer(
                    EPH, data=request.data, partial=True
                )
                if serializer.is_valid():
                    serializer.save()
                    return Response(serializer.data, status=status.HTTP_200_OK)
                else:
                    print(serializer.errors)
                    return Response(serializer.errors, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


# class ProfileVerification(APIView):
#     def post(self, request, emp_info_id):
#         employee_information = get_object_or_404(EmployeeInformation, pk=emp_info_id)
#         # Dictionary to map keys to serializers and related managers
#         if request.data.get("model_name") and emp_info_id:
#             related_serializers = {
#                 'employee_profile': (EmployeeInformationSerializer, employee_information),
#                 'education': employee_information.employeeeducation_set,
#                 'family': employee_information.familydetails_set,
#                 'emergency_details': employee_information.emergencydetails_set,
#                 'emergency_contact': employee_information.emergencycontact_set,
#                 'candidate_reference': employee_information.candidatereference_set,
#                 'experience': employee_information.exceperiencemodel_set,
#                 'last_position_held': employee_information.last_position_held_set,
#                 'employee_identity': employee_information.employeeidentity_set,
#             }
#             for i,j in related_serializers.items():
#                 if i==request.data.get("model_name"):
#                     obj=j.get(pk=request.data.get("id"))
#                     obj.is_verified=request.data.get("is_verified")
#                     obj.reason=request.data.get("reason")
#                     obj.save()
#                     if obj.is_verified==True:

#                         return Response(f"{request.data.get("model_name")} Correct Details Uploaded! Verified Successful!")
#                     else:
#                         return Response(f"{request.data.get("model_name")} Wrong Details Uploaded! Verified Successful!")
#         else:
#             employee_information.ProfileVerification=request.data.get("ProfileVerification")
#             if employee_information.ProfileVerification=="success":
#                 employee_information.employee_status="active"
#                 employee_information.save()
#                 return Response(f"profile verification was done sucessfully!\n The status is{employee_information.employee_status}")
#             else:
#                 return Response(f"profile verification was done sucessfully!\n The status is{employee_information.employee_status}")


from django.core.mail import EmailMessage
import mimetypes
from django.core.mail import EmailMessage
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import EmailMultiAlternatives
from django.core.files.uploadedfile import InMemoryUploadedFile
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from slugify import slugify
import urllib.parse


class MassMailsView(APIView):
    # def get(self,request):
    #     emp_position=request.GET.get("position")
    #     emp=request.GET.get("employee")
    #     if emp_position:
    #         emp_list=EmployeeDataModel.objects.filter(Position=emp_position)
    #         employee_mails=[data.employeeProfile.email for data in emp_list]
    #         serializer_data={"EmployeeMails":employee_mails}

    #     elif emp_position and emp:
    #         emp_list=EmployeeDataModel.objects.filter(emp,Position=emp_position)
    #         employee_mails=[data.employeeProfile.email for data in emp_list]
    #         serializer_data={"EmployeeMails":employee_mails}

    def get(self, request, dep_value=None, deg_value=None, search_value=None):
        # mail sending filter based on the single employees ,employee designation ,employee Department, Active employees,General or intern employees
        try:
            if dep_value:
                # slugified_value = slugify(dep_value)
                # encoded_value = urllib.parse.quote(slugified_value)
                print("encoded_value", dep_value)
                dep = Deparments.objects.filter(Dep_Name=dep_value).first()
                serializer_data = {}
                if dep:
                    emp_list = EmployeeDataModel.objects.filter(
                        Position__Department=dep.pk
                    ).exclude(employeeProfile__employee_status="in_active")
                    deg_list = {data.Position.Name for data in emp_list}
                    # employee_mails=[data.employeeProfile.email for data in emp_list]

                    employee_details = []
                    for emp in emp_list:
                        if emp.employeeProfile:
                            serialize_details = EmployeeInformationSerializer(
                                emp.employeeProfile
                            ).data
                            serialize_details["Designation"] = emp.Position.Name
                            serialize_details["Reporting_To"] = emp.Reporting_To.Name
                            serialize_details["Department"] = (
                                emp.Position.Department.Dep_Name
                            )
                            employee_details.append(serialize_details)

                    serializer_data = {
                        "Designations": deg_list,
                        "EmployeeMails": employee_details,
                    }

                return Response(serializer_data)
            elif deg_value:
                deg = DesignationModel.objects.filter(Name=deg_value).first()
                serializer_data = {}
                if deg:
                    emp_list = EmployeeDataModel.objects.filter(
                        Position=deg.pk
                    ).exclude(employeeProfile__employee_status="in_active")
                    # employee_mails=[data.employeeProfile.email for data in emp_list]
                    employee_details = []
                    for emp in emp_list:
                        if emp.employeeProfile:
                            serialize_details = EmployeeInformationSerializer(
                                emp.employeeProfile
                            ).data
                            serialize_details["Designation"] = emp.Position.Name
                            serialize_details["Reporting_To"] = emp.Reporting_To.Name
                            serialize_details["Department"] = (
                                emp.Position.Department.Dep_Name
                            )
                            employee_details.append(serialize_details)

                    serializer_data = {"EmployeeMails": employee_details}

                return Response(serializer_data)

            elif search_value:
                emp = (
                    EmployeeDataModel.objects.filter(EmployeeId=search_value)
                    .exclude(employeeProfile__employee_status="in_active")
                    .first()
                )
                serializer_data = {}
                if emp:
                    # employee_mails=[ emp.employeeProfile.email]

                    serialize_details = EmployeeInformationSerializer(
                        emp.employeeProfile
                    ).data
                    serialize_details["Designation"] = emp.Position.Name
                    serialize_details["Reporting_To"] = emp.Reporting_To.Name
                    serialize_details["Department"] = emp.Position.Department.Dep_Name

                    serializer_data = {"EmployeeMails": serialize_details}

                    return Response(serializer_data)
                else:
                    return Response("EmployeeId not found")
            else:
                emp_list = EmployeeDataModel.objects.all().exclude(
                    employeeProfile__employee_status="in_active"
                )
                serializer_data = {}
                if emp_list:
                    dep_list = {
                        data.Position.Department.Dep_Name
                        for data in emp_list
                        if data.Position
                    }
                    # employee_mails=[data.employeeProfile.email for data in emp_list if data.employeeProfile]

                    employee_details = []
                    for emp in emp_list:
                        if emp.employeeProfile:
                            serialize_details = EmployeeInformationSerializer(
                                emp.employeeProfile
                            ).data
                            serialize_details["Designation"] = emp.Position.Name
                            serialize_details["Reporting_To"] = emp.Reporting_To.Name
                            serialize_details["Department"] = (
                                emp.Position.Department.Dep_Name
                            )
                            employee_details.append(serialize_details)

                    serializer_data = {
                        "Departments": list(dep_list),
                        "EmployeeMails": employee_details,
                    }

                    return Response(serializer_data)

        except Exception as e:
            print(e)
            return Response(str(e))

    def post(self, request):
        try:
            emp_mail_list = request.data.getlist("employee_mails_list")
            mail_sentby = request.data.get("mail_sentby")
            mail_subject = request.data.get("subject")
            email_message = request.data.get("message")  # HTML message content
            mail_attachment = request.FILES.getlist(
                "attachment"
            )  # Use request.FILES to get attachments

            print(email_message)
            # Validate required fields
            local_time = timezone.localtime()
            mail_subject = f"{mail_subject}{str(local_time)[0:18]}"
            if not mail_sentby:
                return Response(
                    "Who sent the email is required", status=status.HTTP_400_BAD_REQUEST
                )

            if not emp_mail_list:
                return Response(
                    "Employee email list is required",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Get the employee object who sent the mail
            emp_obj = EmployeeDataModel.objects.filter(EmployeeId=mail_sentby).first()
            if not emp_obj:
                return Response(
                    "Sender employee not found", status=status.HTTP_400_BAD_REQUEST
                )

            request_data = request.data.copy()
            request_data["mail_sended_by"] = emp_obj.pk

            # Serialize and save email data
            emp_mail_serializer = CompanyMassMailsSendedSerializer(data=request_data)
            if emp_mail_serializer.is_valid():
                saved_mail_obj = emp_mail_serializer.save()
                employee_objs = EmployeeDataModel.objects.filter(
                    employeeProfile__email__in=emp_mail_list
                )
                saved_mail_obj.employees_list.set(employee_objs)

                # Create the email
                email = EmailMultiAlternatives(
                    subject=mail_subject,
                    body="This is a fallback text message",  # Fallback text message
                    from_email="sender@example.com",
                    to=emp_mail_list,
                )
                email.attach_alternative(
                    email_message, "text/html"
                )  # Attach the HTML content

                # Attach any uploaded files
                for attachment in mail_attachment:
                    filename = (
                        attachment.name
                    )  # Use the original filename from the uploaded file
                    mime_type, _ = mimetypes.guess_type(filename)
                    email.attach(
                        filename,
                        attachment.read(),
                        mime_type or "application/octet-stream",
                    )

                # Send the email
                email.send()
                return Response("Mail sent successfully", status=status.HTTP_200_OK)

            else:
                return Response(
                    emp_mail_serializer.errors, status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)

    # def post(self, request):
    #     subject = request.data.get("subject")
    #     message = request.data.get("message")
    #     logo = request.data.get("logo")  # This can still be a URL
    #     special_logo = request.FILES.get("s_logo")  # Get the special logo as a file
    #     attached_file = request.FILES.get("file")  # Get the uploaded file

    #     # Create the email object using EmailMultiAlternatives
    #     email = EmailMultiAlternatives(
    #         subject,  # Subject
    #         message,  # Message body (plain text)
    #         'sender@example.com',  # From email address
    #         ['harikrishnad76@gmail.com'],  # Recipient email
    #     )

    #     # Replace '\n' with '<br>' for HTML content
    #     html_message = message.replace("\n", "<br>")

    #     # HTML content for the email
    #     html_content = f"""
    #     <html>
    #         <head></head>
    #         <body style="background-color: #f9f9f9; padding: 50px; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: sans-serif;">
    #             <div style="background-color: #fff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); max-width: 600px; width: 100%; position: relative; box-sizing: border-box;">
    #                 <img src="https://hrmbackendapi.meridahr.com/media/Profile_Images/image8_mYtBvyH.jpg" alt="Image" style="display: block; max-width: 100px; margin-bottom: 20px;">

    #                 <h1 style="color: #333; text-align: left; margin-bottom: 20px; font-family: serif; font-size: 24px;">
    #                     {subject}
    #                 </h1>

    #                 <p style="color: #555; text-align: left; font-size: 16px; font-family: sans-serif; word-wrap: break-word;">
    #                     {html_message}
    #                 </p>

    #                 <!-- The special logo will be displayed in the email body -->
    #                 <img src="cid:special_logo" style="max-width: 300px; display: block; margin: 20px auto 0; border-radius: 10px;">
    #             </div>
    #         </body>
    #     </html>
    #     """

    #     # Attach the HTML content
    #     email.attach_alternative(html_content, "text/html")

    #     # Attach the special logo if provided
    #     if special_logo and isinstance(special_logo, InMemoryUploadedFile):
    #         image = MIMEImage(special_logo.read())
    #         image.add_header('Content-ID', '<special_logo>')
    #         image.add_header('Content-Disposition', 'inline', filename=special_logo.name)
    #         email.attach(image)

    #     # If there's an attached file, add it to the email using MIMEBase
    #     if attached_file and isinstance(attached_file, InMemoryUploadedFile):
    #         part = MIMEBase('application', 'octet-stream')
    #         part.set_payload(attached_file.read())
    #         encoders.encode_base64(part)
    #         part.add_header('Content-Disposition', f'attachment; filename={attached_file.name}')
    #         email.attach(part)

    #     try:
    #         # Send the email
    #         email.send(fail_silently=False)
    #         return Response({"status": "Email sent successfully!"}, status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response({"status": "Failed to send email.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SendEmailAPIView(APIView):
    pass

    # def post(self, request):
    #     subject = request.data.get("subject")
    #     message = request.data.get("message")
    #     logo = request.data.get("logo")  # This can still be a URL
    #     special_logo = request.FILES.get("s_logo")  # Get the special logo as a file
    #     attached_file = request.FILES.get("file")  # Get the uploaded file

    #     # Create the email object using EmailMultiAlternatives
    #     email = EmailMultiAlternatives(
    #         subject,  # Subject
    #         message,  # Message body (plain text)
    #         'sender@example.com',  # From email address
    #         ['harikrishnad76@gmail.com'],  # Recipient email
    #     )

    #     # Replace '\n' with '<br>' for HTML content
    #     html_message = message.replace("\n", "<br>")

    #     # HTML content for the email
    #     html_content = f"""
    #     <html>
    #         <head></head>
    #         <body style="background-color: #f9f9f9; padding: 50px; display: flex; justify-content: center; align-items: center; min-height: 100vh; font-family: sans-serif;">
    #             <div style="background-color: #fff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1); max-width: 600px; width: 100%; position: relative; box-sizing: border-box;">
    #                 <img src="{logo}" alt="Image" style="display: block; max-width: 100px; margin-bottom: 20px;">

    #                 <h1 style="color: #333; text-align: left; margin-bottom: 20px; font-family: serif; font-size: 24px;">
    #                     {subject}
    #                 </h1>

    #                 <p style="color: #555; text-align: left; font-size: 16px; font-family: sans-serif; word-wrap: break-word;">
    #                     {html_message}
    #                 </p>

    #                 <!-- The special logo will be displayed in the email body -->
    #                 <img src="cid:special_logo" style="max-width: 300px; display: block; margin: 20px auto 0; border-radius: 10px;">
    #             </div>
    #         </body>
    #     </html>
    #     """

    #     # Attach the HTML content
    #     email.attach_alternative(html_content, "text/html")

    #     # Attach the special logo if provided
    #     if special_logo and isinstance(special_logo, InMemoryUploadedFile):
    #         image = MIMEImage(special_logo.read())
    #         image.add_header('Content-ID', '<special_logo>')
    #         image.add_header('Content-Disposition', 'inline', filename=special_logo.name)
    #         email.attach(image)

    #     # If there's an attached file, add it to the email using MIMEBase
    #     if attached_file and isinstance(attached_file, InMemoryUploadedFile):
    #         part = MIMEBase('application', 'octet-stream')
    #         part.set_payload(attached_file.read())
    #         encoders.encode_base64(part)
    #         part.add_header('Content-Disposition', f'attachment; filename={attached_file.name}')
    #         email.attach(part)

    #     try:
    #         # Send the email
    #         email.send(fail_silently=False)
    #         return Response({"status": "Email sent successfully!"}, status=status.HTTP_200_OK)
    #     except Exception as e:
    #         return Response({"status": "Failed to send email.", "error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


{
    "subject": "Announcement of Dussehra Holiday",
    "message": "Dear Team,\n\nWe are pleased to announce that the office will be closed in observance of Dussehra.\n\nHoliday Date: 12/10/2024\n\nDussehra is a time for celebration and reflection, marking the victory of good over evil. We encourage everyone to spend this time with family and friends.\n\nPlease ensure that all pending tasks are completed before the holiday.\n\nWishing you and your loved ones a joyful Dussehra!\n\nBest Regards,\nHari\nHR\nMTM",
    "logo": "https://hrmbackendapi.meridahr.com/media/Profile_Images/image8_mYtBvyH.jpg",
    "s_logo": "https://hrmbackendapi.meridahr.com/media/Profile_Images/image8_mYtBvyH.jpg",
}


class CompanyPolicies(APIView):
    def get(self, request, applicable=None):
        if applicable == "Departments":
            dep_emp = Deparments.objects.all()
            serializer = DepartmentSerializer(dep_emp, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif applicable == "Designations":
            des_emp = DesignationModel.objects.all()
            serializer = DesignationSerializer(des_emp, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            pass

    def post(self, request):
        dep_emps = Deparments.objects.all()
        des_emps = DesignationModel.objects.all()
        applicable_Value = request.data.get("Value")
        applicable_Value_id = request.data.get("Value_id")

        if applicable_Value in [dep_emp.Dep_Name for dep_emp in dep_emps]:
            company_policy = CompanyPolicySerializer(data=request.data)

            if company_policy.is_valid():
                instance = company_policy.save()

                com_policy = CompanyPolicy.objects.get(pk=instance.pk)
                employees = EmployeeDataModel.objects.filter(
                    Position__Department__pk=applicable_Value_id
                )

                for emp_id in employees:
                    com_policy.applicable_employees.add(emp_id)
                    # com_policy.applicable_employees=emp_id
                    # com_policy.save()
                return Response(company_policy.data, status=status.HTTP_200_OK)

            else:
                print(company_policy.errors)
                return Response(
                    company_policy.errors, status=status.HTTP_400_BAD_REQUEST
                )

        elif applicable_Value in [des_emp.Name for des_emp in des_emps]:
            company_policy = CompanyPolicySerializer(data=request.data)

            if company_policy.is_valid():
                instance = company_policy.save()

                com_policy = CompanyPolicy.objects.get(pk=instance.pk)
                employees = EmployeeDataModel.objects.filter(
                    Position__pk=applicable_Value_id
                )

                for emp_id in employees:
                    com_policy.applicable_employees.add(emp_id)
                    # com_policy.applicable_employees=emp_id
                    # com_policy.save()
                return Response(company_policy.data, status=status.HTTP_200_OK)
            else:
                print(company_policy.errors)
                return Response(
                    company_policy.errors, status=status.HTTP_400_BAD_REQUEST
                )


# ..............................Employee seporation..................................

from HRM_App.models import EmployeeDataModel, RegistrationModel

from payroll_app.models import EmployeeSalaryBreakUp
from payroll_app.serializer import EmployeeSalaryBreakUpSerializer


# class HRDashboardEmployees(APIView):
#     def get(self, request, login_user, Department_id=None, EmployeeId=None, Designation_id=None):

#         login_user = get_object_or_404(EmployeeDataModel, EmployeeId=login_user)
#         emp_status = request.GET.get("emp_status")

#         # Check if the login_user is HR or Admin
#         if login_user.Designation in ["HR", "Admin"]:
#             all_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status=emp_status).order_by("Name") #.exclude(EmployeeId=login_user,)
#         else:
#             all_employees = EmployeeDataModel.objects.filter(employeeProfile__employee_status=emp_status,Reporting_To=login_user.pk)


#         if all_employees:
#             try:
#                 response_data = []
#                 for info in all_employees:

#                     if info.employeeProfile:

#                         #print(info.employeeProfile)
#                         emp_info = get_object_or_404(EmployeeInformation, pk=info.employeeProfile.pk)
#                         employee_info_serializer = EmployeeInformationSerializer(emp_info, context={'request': request}).data
#                         employee_info = employee_info_serializer
#                         employee_info["employee_Id"] = info.EmployeeId
#                         employee_info["full_name"] = info.Name
#                         if info.employeeProfile.last_name:
#                             employee_info["full_name"] = f"{info.employeeProfile.full_name} {info.employeeProfile.last_name}"
#                         try:
#                             employee_info["Designation"]=info.Position.Name if info.Position else None
#                             employee_info["Dashboard"]=info.Designation if info.Designation else None
#                             employee_info["Department"]=info.Position.Department.Dep_Name if info.Position else None
#                             employee_info["Reporting_To"]=info.Reporting_To.EmployeeId if info.Reporting_To else None
#                             employee_info["Reporting_To_Name"]=info.Reporting_To.Name if info.Reporting_To else None

#                             from .filters import currentexperience
#                             current_experience=currentexperience(exp_data=info,exp_type="cur_exp")
#                             employee_info["Currrent_Experience"]=current_experience["current_exp"]

#                         except AttributeError:
#                             pass

#                         offer_details = OfferLetterModel.objects.filter(CandidateId=emp_info.Candidate_id).first()
#                         if offer_details:
#                             EOD_serializer = DOJ_OfferLetterserializer(offer_details, context={'request': request}).data
#                             employee_info.update(EOD_serializer)
#                         try:
#                             ESH=CompanyEmployeesPositionHistory.objects.filter(employee=info,is_applicable=True).first()
#                             if ESH:
#                                 employee_info["salary"]=ESH.assigned_salary
#                             else:
#                                 employee_info["salary"]=None
#                         except:
#                             pass
#                         try:
#                             ESB=EmployeeSalaryBreakUp.objects.filter(employee_id=info).first()
#                             serializer_data=EmployeeSalaryBreakUpSerializer(ESB).data
#                             employee_info["salary_Template"]=serializer_data
#                         except:
#                             pass
#                         # resignation_request = ResignationModel.objects.filter(employee_id=info.pk, resignation_verification=None)
#                         # resignation_serializer = ResignationSerializer(resignation_request, many=True, context={'request': request}).data if resignation_request else []
#                         # employee_info["Requests"] = {"ResignationRequest": resignation_serializer, "LeaveRequests": []}

#                         employee_information = EmployeeInformation.objects.prefetch_related(
#                                 'employeeeducation_set', 'familydetails_set', 'emergencydetails_set', 'emergencycontact_set',
#                                 'candidatereference_set', 'exceperiencemodel_set', 'last_position_held_set',
#                                 'employeepersonalinformation_set', 'employeeidentity_set', 'bankaccountdetails_set',
#                                 'pfdetails_set', 'aditionalinformationmodel_set', 'attachmentsmodel_set', 'declaration_set'
#                             ).filter( employee_Id=info.EmployeeId,ProfileVerification="success").first()


#                         # employee_profile = EmployeeInformationSerializer(employee_information).data
#                         education_serializer = EmployeeEducationSerializer(employee_information.employeeeducation_set.all(), many=True,context={"request":request})
#                         family_serializer = FamilyDetailsSerializer(employee_information.familydetails_set.all(), many=True,context={"request":request})
#                         emergency_details_serializer = EmergencyDetailsSerializer(employee_information.emergencydetails_set.all(), many=True,context={"request":request})
#                         emergency_contact_serializer = EmergencyContactSerializer(employee_information.emergencycontact_set.all(), many=True,context={"request":request})
#                         candidate_reference_serializer = CandidateReferenceSerializer(employee_information.candidatereference_set.all(), many=True,context={"request":request})
#                         experience_serializer = ExceperienceModelSerializer(employee_information.exceperiencemodel_set.all(), many=True,context={"request":request})
#                         last_position_held_serializer = Last_Position_HeldSerializer(employee_information.last_position_held_set.all(), many=True,context={"request":request})
#                         personal_info_serializer = EmployeePersonalInformationSerializer(employee_information.employeepersonalinformation_set.all(), many=True,context={"request":request})
#                         employee_identity_serializer = EmployeeIdentitySerializer(employee_information.employeeidentity_set.all(), many=True,context={"request":request})
#                         bank_account_serializer = BankAccountDetailsSerializer(employee_information.bankaccountdetails_set.all(), many=True,context={"request":request})
#                         pf_details_serializer = PFDetailsSerializer(employee_information.pfdetails_set.all(), many=True,context={"request":request})
#                         additional_info_serializer = AditionalInformationSerializer(employee_information.aditionalinformationmodel_set.all(), many=True,context={"request":request})
#                         attachments_serializer = AttachmentsModelSerializer(employee_information.attachmentsmodel_set.all(), many=True,context={"request":request})
#                         declaration_serializer = DeclarationSerializer(employee_information.declaration_set.all(), many=True,context={"request":request})

#                         employee_info.update({"EducationDetails": education_serializer.data})
#                         employee_info.update({"FamilyDetails": family_serializer.data})
#                         employee_info.update({"EmergencyDetails": emergency_details_serializer.data})
#                         employee_info.update({"EmergencyContactDetails": emergency_contact_serializer.data})
#                         employee_info.update({"CandidateReferenceDetails": candidate_reference_serializer.data})
#                         employee_info.update({"LastPositionHeldDetails": last_position_held_serializer.data})
#                         employee_info.update({"ExperienceDetails": experience_serializer.data})
#                         employee_info.update({"PersonalInformation": personal_info_serializer.data})
#                         employee_info.update({"EmployeeIdentity": employee_identity_serializer.data})
#                         employee_info.update({"BankAccountDetails": bank_account_serializer.data})
#                         employee_info.update({"AdditionalInformation": additional_info_serializer.data})
#                         employee_info.update({"PFDetails": pf_details_serializer.data})
#                         employee_info.update({"Attachments": attachments_serializer.data})
#                         employee_info.update({"Declaration": declaration_serializer.data})

#                         employee_info["Total_Experience"]=currentexperience(exp_data=experience_serializer.data,exp_type="total_exp",cur_years_exp=current_experience["years"],cur_months_exp=current_experience["months"])

#                         response_data.append(employee_info)
#                         # response_data.append(employee_profile_data)
#                 return Response(response_data, status=status.HTTP_200_OK)
#             except Exception as e:
#                 return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
#         try:
#             if Department_id:
#                 employees_dep = Deparments.objects.filter(pk=Department_id).first()
#                 emp_list = EmployeeDataModel.objects.filter(Position__Department=employees_dep.pk,employeeProfile__employee_status="active")
#                 response_data = []
#                 for info in emp_list:
#                     if info.employeeProfile:
#                         emp_info = get_object_or_404(EmployeeInformation, pk=info.employeeProfile.pk)
#                         employee_info_serializer = EmployeeInformationSerializer(emp_info, context={'request': request}).data
#                         employee_info = employee_info_serializer
#                         offer_details = OfferLetterModel.objects.filter(CandidateId=emp_info.Candidate_id).first()
#                         if offer_details:
#                             EOD_serializer = DOJ_OfferLetterserializer(offer_details, context={'request': request}).data
#                             employee_info.update(EOD_serializer)
#                         response_data.append(employee_info)
#                 return Response(response_data, status=status.HTTP_200_OK)

#             elif Designation_id:
#                 employees_deg = DesignationModel.objects.filter(pk=Designation_id).first()
#                 emp_list = EmployeeDataModel.objects.filter(Position=employees_deg.pk)
#                 response_data = []
#                 for info in emp_list:
#                     if info.employeeProfile:
#                         emp_info = get_object_or_404(EmployeeInformation, pk=info.employeeProfile.pk,employeeProfile__employee_status="active")
#                         employee_info_serializer = EmployeeInformationSerializer(emp_info, context={'request': request}).data
#                         employee_info = employee_info_serializer
#                         offer_details = OfferLetterModel.objects.filter(CandidateId=emp_info.Candidate_id).first()
#                         if offer_details:
#                             EOD_serializer = DOJ_OfferLetterserializer(offer_details, context={'request': request}).data
#                             employee_info.update(EOD_serializer)
#                         response_data.append(employee_info)
#                 return Response(response_data, status=status.HTTP_200_OK)

#             elif EmployeeId:
#                 employee = get_object_or_404(EmployeeDataModel, EmployeeId=EmployeeId)
#                 serializer = EmployeeDataSerializer(employee, context={'request': request})
#                 return Response(serializer.data, status=status.HTTP_200_OK)

#             else:
#                 position_list = EmployeeDataModel.objects.filter(employeeProfile__employee_status="active")#.exclude(EmployeeId=login_user.EmployeeId)
#                 response_data = []
#                 for info in position_list:
#                     if info.employeeProfile:
#                         emp_info = get_object_or_404(EmployeeInformation, pk=info.employeeProfile.pk)
#                         employee_info_serializer = EmployeeInformationSerializer(emp_info, context={'request': request}).data
#                         employee_info = employee_info_serializer
#                         employee_info["employee_Id"] = info.EmployeeId
#                         employee_info["full_name"] = info.Name
#                         if info.employeeProfile.last_name:
#                             employee_info["full_name"] = f"{info.employeeProfile.full_name} {info.employeeProfile.last_name}"

#                         try:
#                             employee_info["Designation"]=info.Position.Name if info.Position else None
#                             employee_info["Dashboard"]=info.Designation if info.Designation else None
#                             employee_info["Department"]=info.Position.Department.Dep_Name if info.Position else None
#                             employee_info["Reporting_To"]=info.Reporting_To.EmployeeId if info.Reporting_To else None
#                             employee_info["Reporting_To_Name"]=info.Reporting_To.Name if info.Reporting_To else None

#                             from .filters import currentexperience
#                             current_experience=currentexperience(exp_data=info,exp_type="cur_exp")
#                             employee_info["Currrent_Experience"]=current_experience["current_exp"]

#                         except AttributeError:
#                             pass

#                         offer_details = OfferLetterModel.objects.filter(CandidateId=emp_info.Candidate_id).first()
#                         if offer_details:
#                             EOD_serializer = DOJ_OfferLetterserializer(offer_details, context={'request': request}).data
#                             employee_info.update(EOD_serializer)
#                         try:
#                             ESH=CompanyEmployeesPositionHistory.objects.filter(employee=info,is_applicable=True).first()
#                             if ESH:
#                                 employee_info["salary"]=ESH.assigned_salary
#                             else:
#                                 employee_info["salary"]=None
#                         except:
#                             pass
#                         try:
#                             ESB=EmployeeSalaryBreakUp.objects.filter(employee_id=info).first()
#                             serializer_data=EmployeeSalaryBreakUpSerializer(ESB).data
#                             employee_info["salary_Template"]=serializer_data
#                         except:
#                             pass
#                         # resignation_request = ResignationModel.objects.filter(employee_id=info.pk, resignation_verification=None)
#                         # resignation_serializer = ResignationSerializer(resignation_request, many=True, context={'request': request}).data if resignation_request else []
#                         # employee_info["Requests"] = {"ResignationRequest": resignation_serializer, "LeaveRequests": []}

#                         employee_information = EmployeeInformation.objects.prefetch_related(
#                                 'employeeeducation_set', 'familydetails_set', 'emergencydetails_set', 'emergencycontact_set',
#                                 'candidatereference_set', 'exceperiencemodel_set', 'last_position_held_set',
#                                 'employeepersonalinformation_set', 'employeeidentity_set', 'bankaccountdetails_set',
#                                 'pfdetails_set', 'aditionalinformationmodel_set', 'attachmentsmodel_set', 'declaration_set'
#                             ).filter( employee_Id=info.EmployeeId,ProfileVerification="success").first()

#                         # employee_profile = EmployeeInformationSerializer(employee_information).data
#                         education_serializer = EmployeeEducationSerializer(employee_information.employeeeducation_set.all(), many=True,context={"request":request})
#                         family_serializer = FamilyDetailsSerializer(employee_information.familydetails_set.all(), many=True,context={"request":request})
#                         emergency_details_serializer = EmergencyDetailsSerializer(employee_information.emergencydetails_set.all(), many=True,context={"request":request})
#                         emergency_contact_serializer = EmergencyContactSerializer(employee_information.emergencycontact_set.all(), many=True,context={"request":request})
#                         candidate_reference_serializer = CandidateReferenceSerializer(employee_information.candidatereference_set.all(), many=True,context={"request":request})
#                         experience_serializer = ExceperienceModelSerializer(employee_information.exceperiencemodel_set.all(), many=True,context={"request":request})
#                         last_position_held_serializer = Last_Position_HeldSerializer(employee_information.last_position_held_set.all(), many=True,context={"request":request})
#                         personal_info_serializer = EmployeePersonalInformationSerializer(employee_information.employeepersonalinformation_set.all(), many=True,context={"request":request})
#                         employee_identity_serializer = EmployeeIdentitySerializer(employee_information.employeeidentity_set.all(), many=True,context={"request":request})
#                         bank_account_serializer = BankAccountDetailsSerializer(employee_information.bankaccountdetails_set.all(), many=True,context={"request":request})
#                         pf_details_serializer = PFDetailsSerializer(employee_information.pfdetails_set.all(), many=True,context={"request":request})
#                         additional_info_serializer = AditionalInformationSerializer(employee_information.aditionalinformationmodel_set.all(), many=True,context={"request":request})
#                         attachments_serializer = AttachmentsModelSerializer(employee_information.attachmentsmodel_set.all(), many=True,context={"request":request})
#                         declaration_serializer = DeclarationSerializer(employee_information.declaration_set.all(), many=True,context={"request":request})

#                         employee_info.update({"EducationDetails": education_serializer.data})
#                         employee_info.update({"FamilyDetails": family_serializer.data})
#                         employee_info.update({"EmergencyDetails": emergency_details_serializer.data})
#                         employee_info.update({"EmergencyContactDetails": emergency_contact_serializer.data})
#                         employee_info.update({"CandidateReferenceDetails": candidate_reference_serializer.data})
#                         employee_info.update({"LastPositionHeldDetails": last_position_held_serializer.data})
#                         employee_info.update({"ExperienceDetails": experience_serializer.data})
#                         employee_info.update({"PersonalInformation": personal_info_serializer.data})
#                         employee_info.update({"EmployeeIdentity": employee_identity_serializer.data})
#                         employee_info.update({"BankAccountDetails": bank_account_serializer.data})
#                         employee_info.update({"AdditionalInformation": additional_info_serializer.data})
#                         employee_info.update({"PFDetails": pf_details_serializer.data})
#                         employee_info.update({"Attachments": attachments_serializer.data})
#                         employee_info.update({"Declaration": declaration_serializer.data})

#                         employee_info["Total_Experience"]=currentexperience(exp_data=experience_serializer.data,exp_type="total_exp",cur_years_exp=current_experience["years"],cur_months_exp=current_experience["months"])

#                         response_data.append(employee_info)
#                 return Response(response_data, status=status.HTTP_200_OK)
#         except Exception as e:
#             print(e)
#             return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


# 19/02/2026
class HRDashboardEmployees(APIView):
    def get(
        self,
        request,
        login_user,
        Department_id=None,
        EmployeeId=None,
        Designation_id=None,
    ):

        login_user = get_object_or_404(EmployeeDataModel, EmployeeId=login_user)
        emp_status = request.GET.get("emp_status", "active")

        # MAIN OPTIMIZED QUERY
        all_employees = EmployeeDataModel.objects.select_related(
            "Position",
            "Position__Department",
            "Reporting_To",
            "employeeProfile",
        ).prefetch_related(
            "employeeProfile__employeeeducation_set",
            "employeeProfile__familydetails_set",
            "employeeProfile__emergencydetails_set",
            "employeeProfile__emergencycontact_set",
            "employeeProfile__candidatereference_set",
            "employeeProfile__exceperiencemodel_set",
            "employeeProfile__last_position_held_set",
            "employeeProfile__employeepersonalinformation_set",
            "employeeProfile__employeeidentity_set",
            "employeeProfile__bankaccountdetails_set",
            "employeeProfile__pfdetails_set",
            "employeeProfile__aditionalinformationmodel_set",
            "employeeProfile__attachmentsmodel_set",
            "employeeProfile__declaration_set",
        )

        if login_user.Designation in ["HR", "Admin"]:
            all_employees = all_employees.filter(
                employeeProfile__employee_status=emp_status
            )
        else:
            all_employees = all_employees.filter(
                employeeProfile__employee_status=emp_status, Reporting_To=login_user.pk
            )

        # 🔥 BULK FETCH SALARY & OFFER DATA (NO LOOP QUERIES)
        employee_ids = list(all_employees.values_list("EmployeeId", flat=True))
        profile_ids = list(all_employees.values_list("employeeProfile__pk", flat=True))

        offer_map = {
            o.CandidateId: o
            for o in OfferLetterModel.objects.filter(CandidateId__in=profile_ids)
        }

        salary_history_map = {
            s.employee_id: s
            for s in CompanyEmployeesPositionHistory.objects.filter(
                employee_id__in=all_employees, is_applicable=True
            )
        }

        salary_template_map = {
            s.employee_id: s
            for s in EmployeeSalaryBreakUp.objects.filter(employee_id__in=all_employees)
        }

        from .filters import currentexperience

        response_data = []

        for info in all_employees:
            profile = info.employeeProfile
            if not profile:
                continue

            employee_info = EmployeeInformationSerializer(
                profile, context={"request": request}
            ).data

            # BASIC INFO
            employee_info["employee_Id"] = info.EmployeeId
            employee_info["full_name"] = (
                f"{profile.full_name} {profile.last_name}"
                if profile.last_name
                else info.Name
            )
            employee_info["Designation"] = info.Position.Name if info.Position else None
            employee_info["Dashboard"] = info.Designation
            employee_info["Department"] = (
                info.Position.Department.Dep_Name
                if info.Position and info.Position.Department
                else None
            )
            employee_info["Reporting_To"] = (
                info.Reporting_To.EmployeeId if info.Reporting_To else None
            )
            employee_info["Reporting_To_Name"] = (
                info.Reporting_To.Name if info.Reporting_To else None
            )

            # EXPERIENCE
            current_exp = currentexperience(exp_data=info, exp_type="cur_exp")
            employee_info["Currrent_Experience"] = current_exp.get("current_exp")

            # OFFER
            offer = offer_map.get(profile.Candidate_id)
            if offer:
                employee_info.update(
                    DOJ_OfferLetterserializer(offer, context={"request": request}).data
                )

            # SALARY
            history = salary_history_map.get(info.pk)
            employee_info["salary"] = history.assigned_salary if history else None

            template = salary_template_map.get(info.pk)
            if template:
                employee_info["salary_Template"] = EmployeeSalaryBreakUpSerializer(
                    template
                ).data

            # RELATED DATA (NO EXTRA QUERIES NOW — PREFETCHED)
            employee_info["EducationDetails"] = EmployeeEducationSerializer(
                profile.employeeeducation_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["FamilyDetails"] = FamilyDetailsSerializer(
                profile.familydetails_set.all(), many=True, context={"request": request}
            ).data

            employee_info["EmergencyDetails"] = EmergencyDetailsSerializer(
                profile.emergencydetails_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["EmergencyContactDetails"] = EmergencyContactSerializer(
                profile.emergencycontact_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["CandidateReferenceDetails"] = CandidateReferenceSerializer(
                profile.candidatereference_set.all(),
                many=True,
                context={"request": request},
            ).data

            experience_serializer = ExceperienceModelSerializer(
                profile.exceperiencemodel_set.all(),
                many=True,
                context={"request": request},
            )

            employee_info["ExperienceDetails"] = experience_serializer.data

            employee_info["Total_Experience"] = currentexperience(
                exp_data=experience_serializer.data,
                exp_type="total_exp",
                cur_years_exp=current_exp.get("years"),
                cur_months_exp=current_exp.get("months"),
            )

            employee_info["LastPositionHeldDetails"] = Last_Position_HeldSerializer(
                profile.last_position_held_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["PersonalInformation"] = (
                EmployeePersonalInformationSerializer(
                    profile.employeepersonalinformation_set.all(),
                    many=True,
                    context={"request": request},
                ).data
            )

            employee_info["EmployeeIdentity"] = EmployeeIdentitySerializer(
                profile.employeeidentity_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["BankAccountDetails"] = BankAccountDetailsSerializer(
                profile.bankaccountdetails_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["PFDetails"] = PFDetailsSerializer(
                profile.pfdetails_set.all(), many=True, context={"request": request}
            ).data

            employee_info["AdditionalInformation"] = AditionalInformationSerializer(
                profile.aditionalinformationmodel_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["Attachments"] = AttachmentsModelSerializer(
                profile.attachmentsmodel_set.all(),
                many=True,
                context={"request": request},
            ).data

            employee_info["Declaration"] = DeclarationSerializer(
                profile.declaration_set.all(), many=True, context={"request": request}
            ).data

            response_data.append(employee_info)

        return Response(response_data, status=status.HTTP_200_OK)


from django.db.models import Q


class Employee_search(APIView):
    def get(
        self,
        request,
        search_value=None,
        filter_value=None,
        From_Date=None,
        To_Date=None,
    ):
        if search_value:
            employees_deg = EmployeeDataModel.objects.filter(
                Q(Position__Department__Dep_Name__icontains=search_value)
                | Q(Position__Name__icontains=search_value)
                | Q(EmployeeId__icontains=search_value)
                | Q(Designation__icontains=search_value)
                | Q(Name__icontains=search_value)
                | Q(employeeProfile__email=search_value)
                | Q(employeeProfile__mobile=search_value)
                | Q(employeeProfile__hired_date__icontains=search_value)
            )
            all_employees = []
            for info in employees_deg:
                if info.employeeProfile:
                    employee_info_serializer = EmployeeDataSerializer(info).data
                    employee_info = employee_info_serializer
                    try:
                        employee_info["Designation"] = (
                            info.Position.Name if info.Position else None
                        )
                        employee_info["Dashboard"] = (
                            info.Designation if info.Designation else None
                        )
                    except:
                        pass
                    emp_info = get_object_or_404(
                        EmployeeInformation, pk=info.employeeProfile.pk
                    )
                    emp_info_serializer = EmployeeInformationSerializer(emp_info).data

                    offer_details = OfferLetterModel.objects.filter(
                        CandidateId=emp_info.Candidate_id
                    ).first()
                    if offer_details:
                        EOD_serializer = DOJ_OfferLetterserializer(offer_details).data
                        employee_info.update(EOD_serializer)
                    employee_info.update(emp_info_serializer)
                    all_employees.append(employee_info)
            return Response(all_employees, status=status.HTTP_200_OK)

        elif From_Date and To_Date:
            try:
                date_filter = Q(
                    employeeProfile__Offered_Instance__Date_of_Joining__gte=From_Date
                ) & Q(employeeProfile__Offered_Instance__Date_of_Joining__lte=To_Date)
                employees = EmployeeDataModel.objects.filter(date_filter)
                all_employees = []
                for info in employees:
                    if info.employeeProfile:
                        emp_info = get_object_or_404(
                            EmployeeInformation, pk=info.employeeProfile.pk
                        )
                        employee_info_serializer = EmployeeInformationSerializer(
                            emp_info
                        ).data
                        employee_info = employee_info_serializer
                        try:
                            employee_info["Designation"] = (
                                info.Position.Name if info.Position else None
                            )
                            employee_info["Department"] = (
                                info.Designation if info.Designation else None
                            )
                        except:
                            pass

                        offer_details = OfferLetterModel.objects.filter(
                            CandidateId=emp_info.Candidate_id
                        ).first()
                        if offer_details:
                            EOD_serializer = DOJ_OfferLetterserializer(
                                offer_details
                            ).data
                            employee_info.update(EOD_serializer)
                        all_employees.append(employee_info)
                return Response(all_employees, status=status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class DepartmentsList(APIView):
    def get(self, request, login_user=None, dep_id=None, des_id=None):
        try:
            if login_user:
                employee_dep = get_object_or_404(
                    EmployeeDataModel, EmployeeId=login_user
                )
                department_list = []
                if employee_dep.Designation in ["HR", "Admin"]:
                    dep_list = Deparments.objects.all()

                    for dep in dep_list:
                        emp_count = EmployeeDataModel.objects.filter(
                            Position__Department=dep,
                            employeeProfile__employee_status="active",
                        ).count()
                        dep_name = {
                            "id": dep.pk,
                            "Department": dep.Dep_Name,
                            "No_Of_Employees": emp_count,
                        }
                        department_list.append(dep_name)

                    return Response(department_list, status=status.HTTP_200_OK)
                else:
                    return Response(department_list, status=status.HTTP_200_OK)
            elif dep_id:
                des_obj = DesignationModel.objects.filter(Department=dep_id)
                designation_list = []
                for des in des_obj:
                    emp_count = EmployeeDataModel.objects.filter(
                        Position__pk=des.pk, employeeProfile__employee_status="active"
                    ).count()
                    dep_name = {
                        "id": des.pk,
                        "Designation": des.Name,
                        "No_Of_Employees": emp_count,
                    }
                    designation_list.append(dep_name)
                return Response(designation_list, status=status.HTTP_200_OK)

            elif des_id:
                emp_obj = EmployeeDataModel.objects.filter(Position=des_id)
                employee_list = []
                for emp in emp_obj:
                    employee = {
                        "id": emp.pk,
                        "EmployeeId": emp.EmployeeId,
                        "Emp_profile_id": emp.employeeProfile.pk,
                        "EmployeeName": emp.Name,
                        "Designation": emp.Position.Name,
                    }
                    employee_list.append(employee)
                return Response(employee_list, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


class DesignationListView(APIView):
    def get(self, request, login_user):
        try:
            employee_dep = get_object_or_404(EmployeeDataModel, EmployeeId=login_user)
            designation_list = []
            if employee_dep.Designation in ["HR", "Admin"]:
                deg_list = DesignationModel.objects.all()
                for deg in deg_list:
                    dep_name = deg.Department.Dep_Name if deg.Department else None
                    deg_count = EmployeeDataModel.objects.filter(Position=deg).count()
                    deg_name = {
                        "id": deg.pk,
                        "Department": dep_name,
                        "position": deg.Name,
                        "No_Of_Employees": deg_count,
                    }
                    designation_list.append(deg_name)

                return Response(designation_list, status=status.HTTP_200_OK)
            else:
                return Response(designation_list, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(str(e), status=status.HTTP_400_BAD_REQUEST)


# Perticular employee profile in the Hr dashboard


class EmployeeProfileView(APIView):
    def get(self, request, emp_info_id):
        try:
            # employee_information =EmployeeInformation.objects.filter( pk=emp_info_id,ProfileVerification="success").first
            # Using prefetch_related to retrieve related objects
            # Support both string EmployeeId and numeric PK
            lookup_query = Q(employee_Id=emp_info_id)
            if str(emp_info_id).isdigit():
                lookup_query |= Q(pk=emp_info_id)

            # Using prefetch_related and select_related for efficiency
            employee_information = (
                EmployeeInformation.objects.prefetch_related(
                    "employeeeducation_set",
                    "familydetails_set",
                    "emergencydetails_set",
                    "emergencycontact_set",
                    "candidatereference_set",
                    "exceperiencemodel_set",
                    "last_position_held_set",
                    "employeepersonalinformation_set",
                    "employeeidentity_set",
                    "bankaccountdetails_set",
                    "pfdetails_set",
                    "aditionalinformationmodel_set",
                    "attachmentsmodel_set",
                    "declaration_set",
                    # ).filter( employee_Id=emp_info_id,ProfileVerification="success").first()
                )
                .select_related(
                    "employeedatamodel__Position__Department",
                    "employeedatamodel__Reporting_To",
                )
                .filter(lookup_query)
                .first()
            )

            if not employee_information:
                return Response(
                    "employee id not exist", status=status.HTTP_400_BAD_REQUEST
                )

            # Relaxed ProfileVerification check for active employees
            if employee_information.ProfileVerification != "success":
                # Check if they are already an active employee even if verification is pending
                if not hasattr(employee_information, "employeedatamodel"):
                    return Response(
                        "profile verification has to be done.",
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            employee_profile = EmployeeInformationSerializer(employee_information).data
            education_serializer = EmployeeEducationSerializer(
                employee_information.employeeeducation_set.all(),
                many=True,
                context={"request": request},
            )
            family_serializer = FamilyDetailsSerializer(
                employee_information.familydetails_set.all(),
                many=True,
                context={"request": request},
            )
            emergency_details_serializer = EmergencyDetailsSerializer(
                employee_information.emergencydetails_set.all(),
                many=True,
                context={"request": request},
            )
            emergency_contact_serializer = EmergencyContactSerializer(
                employee_information.emergencycontact_set.all(),
                many=True,
                context={"request": request},
            )
            candidate_reference_serializer = CandidateReferenceSerializer(
                employee_information.candidatereference_set.all(),
                many=True,
                context={"request": request},
            )
            experience_serializer = ExceperienceModelSerializer(
                employee_information.exceperiencemodel_set.all(),
                many=True,
                context={"request": request},
            )
            last_position_held_serializer = Last_Position_HeldSerializer(
                employee_information.last_position_held_set.all(),
                many=True,
                context={"request": request},
            )
            personal_info_serializer = EmployeePersonalInformationSerializer(
                employee_information.employeepersonalinformation_set.all(),
                many=True,
                context={"request": request},
            )
            employee_identity_serializer = EmployeeIdentitySerializer(
                employee_information.employeeidentity_set.all(),
                many=True,
                context={"request": request},
            )
            bank_account_serializer = BankAccountDetailsSerializer(
                employee_information.bankaccountdetails_set.all(),
                many=True,
                context={"request": request},
            )
            pf_details_serializer = PFDetailsSerializer(
                employee_information.pfdetails_set.all(),
                many=True,
                context={"request": request},
            )
            additional_info_serializer = AditionalInformationSerializer(
                employee_information.aditionalinformationmodel_set.all(),
                many=True,
                context={"request": request},
            )
            attachments_serializer = AttachmentsModelSerializer(
                employee_information.attachmentsmodel_set.all(),
                many=True,
                context={"request": request},
            )
            declaration_serializer = DeclarationSerializer(
                employee_information.declaration_set.all(),
                many=True,
                context={"request": request},
            )

            # emp_data=EmployeeDataModel.objects.get(EmployeeId=employee_information.employee_Id)
            # register_obj=RegistrationModel.objects.filter(EmployeeId=emp_data.EmployeeId).first()
            # Efficiently get employee data
            try:
                emp_data = employee_information.employeedatamodel
            except EmployeeDataModel.DoesNotExist:
                # Fallback if the OneToOne relation isn't prefilled
                emp_data = (
                    EmployeeDataModel.objects.select_related(
                        "Position__Department", "Reporting_To"
                    )
                    .filter(EmployeeId=employee_information.employee_Id)
                    .first()
                )

            register_obj = RegistrationModel.objects.filter(
                EmployeeId=employee_information.employee_Id
            ).first()

            try:
                # rep_to=EmployeeDataModel.objects.filter(Reporting_To=emp_data.pk)

                # sub_rep_to = False
                # for rep in rep_to:
                #     emp_obj = EmployeeDataModel.objects.filter(Reporting_To=rep.pk)
                #     if emp_obj.exists():
                #         sub_rep_to = True
                #         break

                # Optimized reporting logic
                direct_reports = EmployeeDataModel.objects.filter(
                    Reporting_To=emp_data.pk
                )
                has_direct_reports = direct_reports.exists()
                sub_rep_to = EmployeeDataModel.objects.filter(
                    Reporting_To__Reporting_To=emp_data.pk
                ).exists()

                if emp_data.Designation == "Admin":
                    Status = "admin"
                elif emp_data.Designation == "HR" or sub_rep_to:
                    Status = "manager"
                # elif rep_to.exists() and (emp_data.Designation == "Employee" or emp_data.Designation == "Recruiter"):
                elif has_direct_reports and (
                    emp_data.Designation == "Employee"
                    or emp_data.Designation == "Recruiter"
                ):
                    Status = "team_leader"
                elif (
                    emp_data.Designation == "Recruiter"
                    or emp_data.Designation == "Employee"
                ):
                    Status = "employee"
                else:
                    Status = None

                employee_profile["Designation"] = (
                    emp_data.Designation if emp_data.Designation else None
                )
                employee_profile["Dash_Status"] = Status
                # employee_profile["Department"]=emp_data.Position.Department.Dep_Name if emp_data.Position else None
                employee_profile["Department"] = (
                    emp_data.Position.Department.Dep_Name
                    if emp_data.Position and emp_data.Position.Department
                    else None
                )
                employee_profile["Position"] = (
                    emp_data.Position.Name if emp_data.Position else None
                )
                employee_profile["Reporting_To"] = (
                    emp_data.Reporting_To.Name if emp_data.Reporting_To else None
                )

                # if register_obj.profile_img:
                if register_obj and register_obj.profile_img:
                    employee_profile["EmployeeProfile"] = request.build_absolute_uri(
                        register_obj.profile_img.url
                    )
                else:
                    employee_profile["EmployeeProfile"] = None

            except Exception as inner_e:
                print(f"Inner error in EmployeeProfileView: {inner_e}")
                pass

            employee_profile_data = {
                "EmployeeInformation": employee_profile,
                "EducationDetails": education_serializer.data,
                "FamilyDetails": family_serializer.data,
                "EmergencyDetails": emergency_details_serializer.data,
                "EmergencyContactDetails": emergency_contact_serializer.data,
                "CandidateReferenceDetails": candidate_reference_serializer.data,
                "ExperienceDetails": experience_serializer.data,
                "LastPositionHeldDetails": last_position_held_serializer.data,
                "PersonalInformation": personal_info_serializer.data,
                "EmployeeIdentity": employee_identity_serializer.data,
                "BankAccountDetails": bank_account_serializer.data,
                "PFDetails": pf_details_serializer.data,
                "AdditionalInformation": additional_info_serializer.data,
                "Attachments": attachments_serializer.data,
                "Declaration": declaration_serializer.data,
            }

            return Response(employee_profile_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(
                f"Bad Request: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


# login employee profile
class LoginEmployeeProfileView(APIView):
    def get(self, request, loginuser):
        try:
            # Employee = get_object_or_404(EmployeeDataModel, EmployeeId=loginuser)
            Employee = (
                EmployeeDataModel.objects.select_related(
                    "employeeProfile", "Position__Department", "Reporting_To"
                )
                .filter(EmployeeId=loginuser)
                .first()
            )

            if not Employee:
                return Response("Employee not found", status=status.HTTP_404_NOT_FOUND)

            # Using prefetch_related to retrieve related objects
            employee_information = EmployeeInformation.objects.prefetch_related(
                "employeeeducation_set",
                "familydetails_set",
                "emergencydetails_set",
                "emergencycontact_set",
                "candidatereference_set",
                "exceperiencemodel_set",
                "last_position_held_set",
                "employeeidentity_set",
            ).get(pk=Employee.employeeProfile.pk)

            # employee_profile=EmployeeInformationSerializer(employee_information)
            # employee_profile=employee_profile.data
            # employee_profile["employee_Id"]=Employee.EmployeeId
            # employee_profile["full_name"]=Employee.Name
            # try:
            #     employee_profile["Position"]=Employee.Position.Name if Employee.Position else None
            #     employee_profile["Department"]=Employee.Position.Department.Dep_Name if Employee.Position else None
            # except:
            #     pass

            employee_profile = EmployeeInformationSerializer(employee_information).data
            employee_profile["employee_Id"] = Employee.EmployeeId
            employee_profile["full_name"] = Employee.Name

            employee_profile["Position"] = (
                Employee.Position.Name if Employee.Position else None
            )
            employee_profile["Department"] = (
                Employee.Position.Department.Dep_Name
                if Employee.Position and Employee.Position.Department
                else None
            )

            employee_profile["RepotringTo_Id"] = (
                Employee.Reporting_To.EmployeeId if Employee.Reporting_To else None
            )
            employee_profile["RepotringTo_Name"] = (
                Employee.Reporting_To.Name if Employee.Reporting_To else None
            )

            education_serializer = EmployeeEducationSerializer(
                employee_information.employeeeducation_set.all(), many=True
            )
            family_serializer = FamilyDetailsSerializer(
                employee_information.familydetails_set.all(), many=True
            )
            emergency_details_serializer = EmergencyDetailsSerializer(
                employee_information.emergencydetails_set.all(), many=True
            )
            emergency_contact_serializer = EmergencyContactSerializer(
                employee_information.emergencycontact_set.all(), many=True
            )
            candidate_reference_serializer = CandidateReferenceSerializer(
                employee_information.candidatereference_set.all(), many=True
            )
            experience_serializer = ExceperienceModelSerializer(
                employee_information.exceperiencemodel_set.all(), many=True
            )
            last_position_held_serializer = Last_Position_HeldSerializer(
                employee_information.last_position_held_set.all(), many=True
            )
            employee_identity_serializer = EmployeeIdentitySerializer(
                employee_information.employeeidentity_set.all(), many=True
            )

            employee_profile_data = {
                "EmployeeInformation": employee_profile,
                "EducationDetails": education_serializer.data,
                "FamilyDetails": family_serializer.data,
                "EmergencyDetails": emergency_details_serializer.data,
                "EmergencyContactDetails": emergency_contact_serializer.data,
                "CandidateReferenceDetails": candidate_reference_serializer.data,
                "ExperienceDetails": experience_serializer.data,
                "LastPositionHeldDetails": last_position_held_serializer.data,
                "EmployeeIdentity": employee_identity_serializer.data,
            }
            return Response(employee_profile_data, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response(
                f"Bad Request: {str(e)}", status=status.HTTP_400_BAD_REQUEST
            )


# Friday......................17/05/24................................


class HRList(APIView):
    def get(self, request):
        hr_list = EmployeeDataModel.objects.filter(Designation="HR")
        serializer = EmployeeDataSerializer(hr_list, many=True)
        return Response(serializer.data)


# class ReportingTeamView(APIView):
#     def get(self, request, loginuser):
#         try:
#             reporting_head = EmployeeDataModel.objects.filter(EmployeeId=loginuser).first()

#             # Initialize the Reporting_Team based on designation
#             # if reporting_head.Designation == "Admin":
#             #     Reporting_Team = EmployeeDataModel.objects.exclude(EmployeeId=reporting_head.EmployeeId,employeeProfile__employee_status="in_active")
#             # else:
#             Reporting_Team = EmployeeDataModel.objects.filter(Reporting_To=reporting_head.pk,employeeProfile__employee_status="active")

#             def get_all_reports(reporting_head, visited=None):
#                     # Track visited employees to prevent infinite loops in case of cycles
#                 if visited is None:
#                     visited = set()

#                     # Avoid revisiting the same employee
#                 if reporting_head.pk in visited:
#                     return EmployeeDataModel.objects.none()

#                 visited.add(reporting_head.pk)

#                     # Get direct reports and initialize the reports queryset
#                 direct_reports = EmployeeDataModel.objects.filter(Reporting_To=reporting_head.pk,employeeProfile__employee_status="active")
#                 reports = direct_reports

#                     # Recursively fetch sub-reports
#                 for report in direct_reports:
#                     reports |= get_all_reports(report, visited)
#                 return reports
#                 # Append all recursive reports to Reporting_Team
#             Reporting_Team |= get_all_reports(reporting_head)

#             # Collect all employee details
#             all_employees = []

#             for info in Reporting_Team:
#                 if info.employeeProfile:
#                     # Fetch Employee Information Profile
#                     emp_info = get_object_or_404(EmployeeInformation, pk=info.employeeProfile.pk)
#                     employee_info = EmployeeInformationSerializer(emp_info, context={'request': request}).data

#                     # Populate department, designation, and reporting information
#                     employee_info["Department"] = info.Position.Department.Dep_Name if info.Position else None
#                     employee_info["Designation"] = info.Position.Name if info.Position else None
#                     employee_info["Reporting_To"] = info.Reporting_To.Name if info.Reporting_To else None

#                     # Add resignation and leave requests
#                     resignation_request = ResignationModel.objects.filter(employee_id=info.pk, resignation_verification=None)
#                     resignation_serializer = ResignationSerializer(resignation_request, many=True, context={'request': request}).data
#                     employee_info["Requests"] = {
#                         "ResignationRequest": resignation_serializer,
#                         "LeaveRequests": []  # Placeholder for leave requests
#                     }

#                     all_employees.append(employee_info)

#             return Response(all_employees, status=status.HTTP_200_OK)

#         except Exception as e:
#             print("Error:", e)
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 31/01/24
from collections import defaultdict, deque
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class ReportingTeamView(APIView):
    def get(self, request, loginuser):
        try:
            # 1. Fetch reporting head
            reporting_head = (
                EmployeeDataModel.objects.select_related("employeeProfile")
                .filter(EmployeeId=loginuser)
                .first()
            )

            if not reporting_head:
                return Response(
                    {"error": "Invalid employee"}, status=status.HTTP_404_NOT_FOUND
                )

            # 2. Fetch ALL active employees in ONE query
            employees = EmployeeDataModel.objects.filter(
                employeeProfile__employee_status="active"
            ).select_related(
                "employeeProfile", "Position", "Position__Department", "Reporting_To"
            )

            # 3. Build reporting tree in memory
            report_map = defaultdict(list)
            for emp in employees:
                if emp.Reporting_To_id:
                    report_map[emp.Reporting_To_id].append(emp)

            # 4. Iterative BFS to collect all reports
            reporting_team = []
            visited = set()
            queue = deque([reporting_head.pk])

            while queue:
                manager_id = queue.popleft()

                if manager_id in visited:
                    continue
                visited.add(manager_id)

                for report in report_map.get(manager_id, []):
                    reporting_team.append(report)
                    queue.append(report.pk)

            if not reporting_team:
                return Response([], status=status.HTTP_200_OK)

            # 5. Bulk fetch EmployeeInformation
            emp_profile_ids = [
                emp.employeeProfile_id
                for emp in reporting_team
                if emp.employeeProfile_id
            ]

            emp_info_map = EmployeeInformation.objects.in_bulk(emp_profile_ids)

            # 6. Bulk fetch resignation requests
            # resignations = ResignationModel.objects.filter(
            resignations = ResignationModel.objects.select_related(
                "employee_id", "reporting_manager_name", "HR_manager_name"
            ).filter(
                employee_id__in=[emp.pk for emp in reporting_team],
                resignation_verification=None,
            )

            resignation_map = defaultdict(list)
            for r in resignations:
                resignation_map[r.employee_id].append(r)

            # 7. Serialize response (NO DB HITS HERE)
            response_data = []

            for emp in reporting_team:
                emp_info = emp_info_map.get(emp.employeeProfile_id)
                if not emp_info:
                    continue

                employee_data = EmployeeInformationSerializer(
                    emp_info, context={"request": request}
                ).data

                employee_data["Department"] = (
                    emp.Position.Department.Dep_Name
                    if emp.Position and emp.Position.Department
                    else None
                )

                employee_data["Designation"] = (
                    emp.Position.Name if emp.Position else None
                )

                employee_data["Reporting_To"] = (
                    emp.Reporting_To.Name if emp.Reporting_To else None
                )

                employee_data["Requests"] = {
                    "ResignationRequest": ResignationSerializer(
                        resignation_map.get(emp.pk, []),
                        many=True,
                        context={"request": request},
                    ).data,
                    "LeaveRequests": [],
                }

                response_data.append(employee_data)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# automatic leaves creation

# from LMS_App.models import *
# import logging
# from apscheduler.schedulers.background import BackgroundScheduler
# from django_apscheduler.jobstores import DjangoJobStore
# from apscheduler.triggers.cron import CronTrigger
# from django.utils import timezone
# from django.core.mail import EmailMessage
# from django.core.management import call_command
# from django.core.management.base import OutputWrapper
# from io import StringIO

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# def start():
#     scheduler = BackgroundScheduler()
#     scheduler.add_jobstore(DjangoJobStore(), "default")
#     scheduler.add_job(
#             CompanyLeavesCreation,
#             trigger=CronTrigger(hour=0,minute=0),
#             id="hello",  # Ensure the job ID is unique
#             max_instances=100,
#             replace_existing=True,
#     )
#     scheduler.start()  # Start the scheduler after adding all jobs

# def CompanyLeavesCreation():
#     leave_type_functions = [SickLeavesCreation]
#     for func in leave_type_functions:
#         func()

# def SickLeavesCreation():
#     emp_objs = CompanyLeaveApplicationModel.objects.filter(EmployeeId__employeeProfile__employee_status="active")
#     for emp_item in emp_objs:
#         if emp_item.is_sick_leave:
#             joined_date = emp_item.EmployeeId.employeeProfile.hired_date
#             current_date = timezone.localdate()
#             if current_date.day == 1 and (current_date.month != joined_date.month or current_date.year != joined_date.year):
#                 try:
#                     sick_leave_obj = SickLeavesModel.objects.get(CompanyLeaveApplication=emp_item.pk)
#                     sick_leave_obj.Sick_Leaves += 1
#                     sick_leave_obj.in_mbl+=1
#                     sick_leave_obj.save()
#                     if current_date.day ==31 and current_date.month==12:
#                         sick_leave_obj.Sick_Leaves =0
#                         sick_leave_obj.carried_forward_leaves=0
#                         sick_leave_obj.utilised_leaves=0
#                         sick_leave_obj.unpaid_leaves=0
#                         sick_leave_obj.Year=timezone.localdate()
#                         sick_leave_obj.save()

#                 except SickLeavesModel.DoesNotExist:
#                     # Handle the case where SickLeavesModel does not exist
#                     sick_leave_obj = SickLeavesModel.objects.create(
#                         CompanyLeaveApplication=emp_item,
#                         Sick_Leaves=1,
#                         Year=current_date
#                     )
#                     emp_item.is_sick_leave = True
#                     emp_item.save()

#         elif emp_item.is_annual_leave:
#             joined_date = emp_item.EmployeeId.employeeProfile.hired_date
#             current_date = timezone.localdate()
#             if current_date.day == 1 and (current_date.month != joined_date.month or current_date.year != joined_date.year):
#                 try:
#                     annual_leave_obj = AnnualLeavesModel.objects.get(CompanyLeaveApplication=emp_item.pk)
#                     annual_leave_obj.Annual_Leaves += 1
#                     annual_leave_obj.in_mbl+=1
#                     annual_leave_obj.save()
#                     if current_date.day ==31 and current_date.month==12:
#                         annual_leave_obj.Annual_Leaves =0
#                         annual_leave_obj.carried_forward_leaves=0
#                         annual_leave_obj.utilised_leaves=0
#                         annual_leave_obj.Year=timezone.localdate()
#                         annual_leave_obj.save()

#                 except AnnualLeavesModel.DoesNotExist:
#                     # Handle the case where SickLeavesModel does not exist
#                     annual_leave_obj = AnnualLeavesModel.objects.create(
#                         CompanyLeaveApplication=emp_item,
#                         Annual_Leaves=1,
#                         Year=current_date
#                     )
#                     emp_item.is_sick_leave = True
#                     emp_item.save()

#         elif emp_item.is_casual_leave:
#             joined_date = emp_item.EmployeeId.employeeProfile.hired_date
#             current_date = timezone.localdate()
#             if current_date.day == 1 and (current_date.month != joined_date.month or current_date.year != joined_date.year):
#                 try:
#                     casual_leave_obj = CasualLeavesModel.objects.get(CompanyLeaveApplication=emp_item.pk)
#                     casual_leave_obj.Casual_Leaves += 1
#                     casual_leave_obj.in_mbl+=1
#                     casual_leave_obj.save()
#                     if current_date.day ==31 and current_date.month==12:
#                         casual_leave_obj.Casual_Leaves =0
#                         casual_leave_obj.carried_forward_leaves=0
#                         casual_leave_obj.utilised_leaves=0
#                         casual_leave_obj.Year=timezone.localdate()
#                         casual_leave_obj.save()

#                 except CasualLeavesModel.DoesNotExist:
#                     # Handle the case where SickLeavesModel does not exist
#                     casual_leave_obj = CasualLeavesModel.objects.create(
#                         CompanyLeaveApplication=emp_item,
#                         Casual_Leaves=1,
#                         Year=current_date
#                     )
#                     emp_item.is_casual_leave = True
#                     emp_item.save()


# else:

#     a=SickLeavesModel.objects.create(
#         CompanyLeaveApplication=emp_item,
#         Sick_Leaves=1,
#         Year=timezone.localdate()
#     )
#     emp_item.is_sick_leave = True
#     emp_item.save()


# start()
