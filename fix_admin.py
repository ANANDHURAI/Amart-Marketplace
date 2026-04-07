import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecom.settings")
django.setup()

from accounts.models import Account  
from accounts.models import Account

email = os.getenv("DJANGO_SUPERUSER_EMAIL")
password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
first_name = os.getenv("DJANGO_SUPERUSER_FIRST_NAME")
last_name = os.getenv("DJANGO_SUPERUSER_LAST_NAME")

if not Account.objects.filter(email=email).exists():
    print("Creating superuser...")
    Account.objects.create_superuser(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
else:
    print("Superuser already exists")