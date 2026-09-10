import time
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from .views import AoutLeaveCreatingFunction

# def loopfun():
#     while True:
#         messages = AoutLeaveCreatingFunction()
#         for message in messages:
#             print(message)
#         time.sleep(60 * 60 * 24)

from threading import Thread
# def thread_function():
#     Thread(target=loopfun)
#     Thread.daemon=True
#     # thread_function()
    