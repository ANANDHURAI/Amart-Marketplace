

from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

import certifi # SSL: CERTIFICATE_VERIFY_FAILED
import os

os.environ['SSL_CERT_FILE'] = certifi.where() # This tells Python libraries: “Use this certificate file to verify HTTPS connections”



BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = 'django-insecure-f3#-izfmdm253-4l4d%@1f#&ej1^9e0xlhzzwba@&17^62w314'


DEBUG = True

ALLOWED_HOSTS = [

    'amart.fun',
    'localhost',
    'amart-e-commerce-website.onrender.com',
    '127.0.0.1'
]


CSRF_TRUSTED_ORIGINS = [
    "http://amart.fun",
    "https://amart.fun",
    "https://amart-e-commerce-website.onrender.com",
    
]


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'image_cropping',

    "home",
    "customer",
    "product",
    "accounts",
    "aadmin",
    "payment",
]




MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ecom.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecom.wsgi.application'




DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3', 
    }
}



AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]




LANGUAGE_CODE = 'en-us'

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

AUTH_USER_MODEL = "accounts.Account"


# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "smtp.gmail.com"
# EMAIL_USE_SSL = True
# EMAIL_USE_TSL = False
# EMAIL_PORT = 465
# EMAIL_HOST_USER = "anandhurai2004@gmail.com"
# EMAIL_HOST_PASSWORD = 'gtbi lfgc qhcj sedp'





DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# RazorPay credentials
RAZOR_KEY_ID = "rzp_test_iZ19mfmqcCWhFx"
RAZOR_KEY_SECRET = "AgyQbM4WqWQj1hvpHZ9GtT5C"


# To allow RazorPay Pop-up to restrict comment the below line.
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"





LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': 'debug.log',
        },
    },
    'loggers': {
        '': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

LOGIN_URL = 'customer_login' 
LOGOUT_REDIRECT_URL = 'customer_dashboard'


SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL")
