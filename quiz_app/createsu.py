import os
import django
from django.conf import settings

# 1. Tell the script where your settings.py is located
# Based on your logs, your project folder is named 'config'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 2. Boot up Django
django.setup()

# 3. NOW you can import models (do not move these lines up!)
from django.contrib.auth.models import User

# 4. The logic to create the user
if not User.objects.filter(username='newuser').exists():
    print("Creating superuser...")
    User.objects.create_superuser('newuser', 'securepassword123')
    print("Superuser created.")
else:
    print("Superuser already exists.")