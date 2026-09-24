from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MessageViewSet, NotificationViewSet, CommunicationLogViewSet, BulkMessageViewSet

router = DefaultRouter()
router.register('messages', MessageViewSet, basename='message')
router.register('notifications', NotificationViewSet, basename='notification')
router.register('logs', CommunicationLogViewSet, basename='log')
router.register('bulk-messages', BulkMessageViewSet, basename='bulk-message')

urlpatterns = [path('', include(router.urls))]
