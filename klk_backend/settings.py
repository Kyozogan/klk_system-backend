from pathlib import Path
from decouple import config
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = config('SECRET_KEY', default='klk-kenya-kids-league-super-secret-key-2024-change-in-prod')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    'simple_history',
    'users',
    'beneficiaries',
    'academics',
    'finance',
    'communications',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "whitenoise.middleware.WhiteNoiseMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'klk_backend.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.debug','django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'klk_backend.wsgi.application'

import dj_database_url

DATABASES = {
    'default': dj_database_url.parse(
        'postgresql://klk_system_db_am0t_user:asgFBjr9opqlw1YHQbUrjwf6c7tHpKc2@dpg-dan8frbm8hqs73ae7ru0-a/klk_system_db_am0t',
        conn_max_age=600,
        ssl_require=True
    )
}



# DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}
AUTH_USER_MODEL = 'users.User'
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Nairobi'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django defaults X_FRAME_OPTIONS to 'DENY', which makes every response —
# including uploaded files under /media/ — refuse to load inside an <iframe>.
# That is what broke the document Preview modal: Firefox reports the framing
# refusal as an error page instead of rendering the PDF. SAMEORIGIN still
# blocks other sites from framing this app, while letting the portal preview
# its own files. The portal requests /media/ through its dev proxy so the
# file really is same-origin.
X_FRAME_OPTIONS = 'SAMEORIGIN'

# Scholars upload receipts/report cards from their phone — keep a sane ceiling.
DATA_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 15 * 1024 * 1024

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated'],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend','rest_framework.filters.SearchFilter','rest_framework.filters.OrderingFilter'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'SIGNING_KEY': config('SECRET_KEY', default='klk-kenya-kids-league-super-secret-key-2024-change-in-prod'),
}

# ── CORS ──────────────────────────────────────────────────────────────
# The management portal is a browser app, so it needs an origin allow-list.
# The Scholar app is a native Expo build: requests from it carry no Origin
# header at all, so CORS never applies to it — nothing extra is needed here
# for the phone. During `expo start --web` previews the dev origin below
# covers it.
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "https://kidsleaguekenyaportal.vercel.app"
]
CORS_ALLOW_CREDENTIALS = True

# ── Google sign-in ────────────────────────────────────────────────────
# Scholars may sign in with Google. The backend verifies the token Google
# handed the app, so no client secret is needed for the access-token flow.
#
# GOOGLE_OAUTH_CLIENT_IDS only matters for the id_token flow: it is the list
# of OAuth client IDs this backend will accept an id_token audience from.
# List every platform client you created (web, android, ios), comma-separated.
GOOGLE_OAUTH_CLIENT_IDS = [
    c.strip() for c in config('GOOGLE_OAUTH_CLIENT_IDS', default='').split(',') if c.strip()
]

