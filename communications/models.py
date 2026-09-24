from django.db import models
from beneficiaries.models import Beneficiary


class Message(models.Model):
    """Direct messages between admin/staff and beneficiaries"""
    DIRECTION_CHOICES = [
        ('admin_to_ben', 'Admin to Beneficiary'),
        ('ben_to_admin', 'Beneficiary to Admin'),
    ]
    sender = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='sent_messages')
    recipient = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='received_messages')
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.SET_NULL, null=True, blank=True, related_name='messages')
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='admin_to_ben')
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.sender} → {self.recipient}: {self.subject or 'No subject'}"


class Notification(models.Model):
    CHANNEL_CHOICES = [('sms','SMS'),('email','Email'),('internal','Internal'),('whatsapp','WhatsApp')]
    TYPE_CHOICES = [('payment','Payment'),('reminder','Reminder'),('performance','Performance'),('enrollment','Enrollment'),('general','General'),('emergency','Emergency'),('approval','Account Approval')]
    STATUS_CHOICES = [('pending','Pending'),('sent','Sent'),('failed','Failed'),('read','Read')]

    recipient_beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    recipient_user = models.ForeignKey('users.User', on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class CommunicationLog(models.Model):
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='communication_logs')
    logged_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    contact_type = models.CharField(max_length=30, choices=[
        ('home_visit','Home Visit'),('phone_call','Phone Call'),
        ('email','Email'),('meeting','Meeting'),
        ('guardian_visit','Guardian Visit'),('school_visit','School Visit'),
    ])
    date = models.DateField()
    summary = models.TextField()
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    follow_up_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']


class BulkMessage(models.Model):
    STATUS_CHOICES = [('draft','Draft'),('sent','Sent'),('scheduled','Scheduled')]
    title = models.CharField(max_length=200)
    message = models.TextField()
    channel = models.CharField(max_length=20)
    target_group = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
