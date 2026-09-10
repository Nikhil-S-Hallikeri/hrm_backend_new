
import json
from django.http import QueryDict

# Simulation of what to_internal_value will do
data = QueryDict('', mutable=True)
data['keywords'] = 'jd, developer'
data['reply_text'] = 'test'
data['buttons'] = '["btn1", "btn2"]'

# Extract to standard dict
if hasattr(data, 'dict'):
    data_dict = data.dict()
else:
    data_dict = dict(data)

if 'buttons' in data_dict:
    buttons = data_dict.get('buttons')
    if isinstance(buttons, str):
        try:
            data_dict['buttons'] = json.loads(buttons)
        except Exception:
            pass

print("Parsed data_dict['buttons'] type:", type(data_dict['buttons']))
print("Parsed data_dict['buttons'] value:", data_dict['buttons'])
