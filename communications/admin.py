from django.contrib import admin
from .models import Notification, CommunicationLog, BulkMessage
for model in [Notification, CommunicationLog, BulkMessage]:
    admin.site.register(model)
