from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('users.urls')),
    path('api/beneficiaries/', include('beneficiaries.urls')),
    path('api/academics/', include('academics.urls')),
    path('api/finance/', include('finance.urls')),
    path('api/communications/', include('communications.urls')),
    path('api/reports/', include('reports.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
