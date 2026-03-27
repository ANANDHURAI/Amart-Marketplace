"""
WSGI config for ecom project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings')

application = get_wsgi_application()


# Auto-create superuser on startup using Render Environment Variables
import os
from django.core.management import call_command
from django.contrib.auth import get_user_model

try:
    User = get_user_model()
    
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
    if email and not User.objects.filter(email=email).exists():
        call_command('createsuperuser', '--no-input')
        
except Exception as e:
    print(f"Superuser creation skipped: {e}")