import os
import django

# This must match your project folder name shown in VS Code
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecom.settings') 
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# This pulls from your Render Environment variables
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

try:
    user = User.objects.get(email=email)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    if password:
        user.set_password(password)
    user.save()
    print(f"Successfully updated permissions for {email}")
except User.DoesNotExist:
    print(f"User {email} not found. Ensure the user exists before running this.")