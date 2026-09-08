import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-me')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    # Apps du projet
    'apps.users',
    'apps.produits',
    'apps.commandes',
    'apps.facturation',
    'apps.messagerie',
    'apps.avis',
    'apps.notifications',
    'apps.sad',
    'apps.evenements',
    # Packages
    'crispy_forms',
    'crispy_bootstrap5',
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

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.users.context_processors.boutique',
                'apps.users.context_processors.notifications_commercant',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Django Channels — messagerie en temps réel (WebSockets)
# InMemoryChannelLayer : suffisant en développement (1 seul process).
# En production avec plusieurs workers, remplacer par channels_redis :
#   CHANNEL_LAYERS = {
#       'default': {
#           'BACKEND': 'channels_redis.core.RedisChannelLayer',
#           'CONFIG': {'hosts': [(os.getenv('REDIS_HOST', 'localhost'), 6379)]},
#       }
#   }
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

AUTH_USER_MODEL = 'users.Utilisateur'

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/users/login/'

# --- Configuration Email ---

# Récupération des identifiants
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# 1. Choix du backend : SMTP si identifiants présents, sinon CONSOLE
if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    print("ATTENTION : EMAIL_HOST_USER ou PASSWORD manquant. Les emails s'afficheront dans la console.")

EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# 2. TRÈS IMPORTANT pour Gmail : l'expéditeur DOIT être votre adresse Gmail
# On force l'utilisation de EMAIL_HOST_USER comme expéditeur par défaut
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
# Si EMAIL_HOST_USER est vide, on met une adresse bidon pour le mode console
if not DEFAULT_FROM_EMAIL:
    DEFAULT_FROM_EMAIL = 'admin@sama-gerant.local'

# --- Fin Configuration Email ---

# Logging — rend visibles en console les erreurs d'envoi d'email
# (facture, alertes stock, nouvelle commande...) qui seraient sinon
# avalées silencieusement, et sert à diagnostiquer un souci SMTP
# (identifiants invalides, mot de passe d'application Gmail requis, etc.)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}