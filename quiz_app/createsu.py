import os
import sys
import django

# --- ADD THESE LINES ---
# This gets the folder where this script lives (quiz_app)
current_dir = os.path.dirname(os.path.abspath(__file__))
# This gets the parent folder (the project root)
parent_dir = os.path.dirname(current_dir)
# This adds the parent folder to Python's "search list" so it can find 'config'
sys.path.append(parent_dir)
# -----------------------

# Now this will work because Python knows where to look
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import User

# Your User Creation Logic
if not User.objects.filter(username='newuser').exists():
    print("Creating superuser...")
    User.objects.create_superuser('newuser', 'admin@example.com', 'securepassword123')
    print("Superuser created.")
else:
    print("Superuser already exists.")