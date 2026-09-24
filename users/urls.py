from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    KLKTokenView, UserViewSet, beneficiary_register,
    GoogleAuthView, auth_methods,
)

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')

urlpatterns = [
    path('login/', KLKTokenView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', beneficiary_register, name='beneficiary_register'),

    # Which sign-in methods apply to this email (drives the login screen).
    path('methods/', auth_methods, name='auth_methods'),

    # Google sign-in. Two paths, one view — `google/callback/` matches the
    # shape the SRC app already speaks, so the mobile client needs no special
    # casing.
    path('google/', GoogleAuthView.as_view(), name='google_auth'),
    path('google/callback/', GoogleAuthView.as_view(), name='google_auth_callback'),

    path('', include(router.urls)),
]
