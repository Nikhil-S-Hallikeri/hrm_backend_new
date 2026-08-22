import paramiko
import sys

sys.stdout.reconfigure(encoding='utf-8')

host = "157.173.222.4"
user = "root"
password = "Meridateam@123"
remote_dir = "/home/meridahr-hrmbackendapi/htdocs/hrmbackendapi.meridahr.com"
venv_python = f"{remote_dir}/.venv/bin/python"

# Python script to run on server that creates the table in MySQL using django's schema editor
create_table_code = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HRM_Project.settings')
django.setup()

from django.db import connection
from HRM_App.models import CandidateResumeFile

with connection.schema_editor() as schema_editor:
    try:
        print("Creating table CandidateResumeFile in MySQL...")
        schema_editor.create_model(CandidateResumeFile)
        print("Table created successfully!")
    except Exception as e:
        print("Error creating table:", e)
"""

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(host, username=user, password=password)

sftp = ssh.open_sftp()
with sftp.file(f"{remote_dir}/temp_create_table.py", "w") as f:
    f.write(create_table_code)
sftp.close()

stdin, stdout, stderr = ssh.exec_command(f"cd {remote_dir} && {venv_python} temp_create_table.py")
print("=== SQL EXECUTION RESULTS ===")
print(stdout.read().decode('utf-8'))
print(stderr.read().decode('utf-8'))

ssh.exec_command(f"rm -f {remote_dir}/temp_create_table.py")
ssh.close()
