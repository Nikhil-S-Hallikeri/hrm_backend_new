from django.shortcuts import render,get_object_or_404,get_list_or_404,HttpResponse
from rest_framework.response import Response
from rest_framework import status
from .serializers import *
from rest_framework import viewsets
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from django.core.mail import send_mail
import random
from django.contrib.auth.hashers import make_password
from django.contrib.auth.hashers import check_password
from datetime import datetime
import json
from django.contrib.sessions.models import Session
import openpyxl
from openpyxl import Workbook, load_workbook
from django.core.management.base import BaseCommand
from io import BytesIO


# interviewers = InterviewSchedulModel.objects.values_list('interviewer__EmployeeId', flat=True).distinct()
        # interview_data_by_interviewer = {}
        # for interviewer in interviewers:
        #     interview_schedule = InterviewSchedulModel.objects.filter(interviewer__EmployeeId=interviewer)
        #     serializer = FilterInterviewSchedulSerializer(interview_schedule, many=True)
        #     interview_data_by_interviewer[interviewer] = serializer.data
        # return Response(interview_data_by_interviewer)