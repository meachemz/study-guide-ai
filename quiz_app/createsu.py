from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Creates a superuser for development'

    def handle(self, *args, **options):
        if not User.objects.filter(username='newuser').exists():
            User.objects.create_superuser(
                username='newuser',
                password='securepassword123'
            )
            print('Superuser created successfully')
        else:
            print('Superuser already exists')