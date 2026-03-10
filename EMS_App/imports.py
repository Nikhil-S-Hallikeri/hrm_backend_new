from django.shortcuts import render,get_object_or_404,get_list_or_404,HttpResponse
from rest_framework.response import Response
from rest_framework import status
from EMS_App.serializers import *
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
