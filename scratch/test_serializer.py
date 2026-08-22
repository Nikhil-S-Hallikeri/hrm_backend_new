
import os, django, sys
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'HRM_Project.settings')
django.setup()

from whatsapp_app.serializers import AutoReplySerializer
from django.http import QueryDict

# Mock a QueryDict simulating the frontend FormData request
q = QueryDict('', mutable=True)
q['keywords'] = 'jd, developer jd'
q['reply_text'] = 'Here is the developer job description'
q['buttons'] = '["frontend jd", "backend jd"]'
q['is_active'] = 'true'

# Let's mock the to_internal_value method on a subclass to verify our fix
class CustomAutoReplySerializer(AutoReplySerializer):
    def to_internal_value(self, data):
        # Convert QueryDict to standard dict
        if hasattr(data, 'dict'):
            data_dict = data.dict()
        else:
            data_dict = dict(data)
            
        if 'buttons' in data_dict:
            buttons = data_dict.get('buttons')
            if isinstance(buttons, str):
                try:
                    import json
                    data_dict['buttons'] = json.loads(buttons)
                except Exception:
                    pass
        return super().to_internal_value(data_dict)

serializer = CustomAutoReplySerializer(data=q)
is_valid = serializer.is_valid()
print("Serializer is valid:", is_valid)
if not is_valid:
    print("Errors:", serializer.errors)
