from .imports import *

class CandidateAppliedNotifications(APIView):
    def get(self, request, login_user=None, id=None):
        if id is None:
            try:
                
                notifications = Notification.objects.filter(receiver__EmployeeId=login_user).order_by('timestamp')
                serializer = NotificationSerializer(notifications, many=True)
               
               
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                print(e)
                return Response("Logged-in user notifications could not be retrieved", status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                notification = Notification.objects.get(pk=id)
                notification.delete()
                return Response("Notification deleted successfully", status=status.HTTP_200_OK)
            except Notification.DoesNotExist:
                return Response("Notification not found", status=status.HTTP_404_NOT_FOUND)



# from rest_framework.views import APIView
# from rest_framework.response import Response
# import pypandoc
# from django.http import StreamingHttpResponse

# class LetterTemplateView(APIView):
#     def get(self, request):

#         docx_url = "http://192.168.0.105:9000/media/Letter_Templates/Appointment_Letter_-_Template.docx"
        
#         # Convert DOCX to HTML using Pandoc
#         pypandoc.download_pandoc()
#         html_content = pypandoc.convert_file(docx_url, 'html')
        
#         # Set the response content type to HTML
#         response = StreamingHttpResponse([html_content], content_type='text/html')
        
#         # Allow cross-origin resource sharing (CORS)
#         response["Access-Control-Allow-Origin"] = "*"
        
#         # Return the response
#         return response

# import os

# class LetterTemplateView(APIView):
#     def get(self, request):
#         # Get the URL of the DOCX file
#         docx_url = "http://192.168.0.105:9000/media/Letter_Templates/Appointment_Letter_-_Template.docx"
        
#         # Convert DOCX to HTML using Pandoc
#         pypandoc.download_pandoc()
#         html_content = pypandoc.convert_file(docx_url, 'html')

#         # Specify the directory where you want to save the HTML file
#         html_directory = "/path/to/your/directory/"

#         # Create the directory if it does not exist
#         os.makedirs(html_directory, exist_ok=True)

#         # Specify the name of the HTML file
#         html_file_name = "generated_template.html"

#         # Save HTML content to a file
#         html_file_path = os.path.join(html_directory, html_file_name)
#         with open(html_file_path, "w", encoding="utf-8") as f:
#             f.write(html_content)

#         # Check if the file exists
#         if os.path.exists(html_file_path):
#             # Construct the link to the HTML file
#             html_file_link = request.build_absolute_uri("/media/Letter_Templates/") + html_file_name

#             # Return the link to the HTML file in the JSON response
#             return Response({"html_file_link": html_file_link})
#         else:
#             return Response({"error": "Failed to generate HTML file."}, status=500)