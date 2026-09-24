from rest_framework import serializers as drf_s, viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from .models import Message, Notification, CommunicationLog, BulkMessage


class MessageSerializer(drf_s.ModelSerializer):
    sender_name = drf_s.CharField(source='sender.get_full_name', read_only=True)
    recipient_name = drf_s.CharField(source='recipient.get_full_name', read_only=True)
    sender_role = drf_s.CharField(source='sender.role', read_only=True)

    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'direction', 'is_read', 'read_at', 'created_at']


class NotificationSerializer(drf_s.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'


class CommunicationLogSerializer(drf_s.ModelSerializer):
    beneficiary_name = drf_s.CharField(source='beneficiary.full_name', read_only=True)
    logged_by_name = drf_s.CharField(source='logged_by.get_full_name', read_only=True)

    class Meta:
        model = CommunicationLog
        fields = '__all__'


class BulkMessageSerializer(drf_s.ModelSerializer):
    class Meta:
        model = BulkMessage
        fields = '__all__'


class MessageViewSet(viewsets.ModelViewSet):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['beneficiary', 'is_read', 'direction']

    def get_queryset(self):
        user = self.request.user
        # Users see only their own messages
        return Message.objects.filter(
            sender=user
        ) | Message.objects.filter(recipient=user)

    def perform_create(self, serializer):
        user = self.request.user
        recipient_id = self.request.data.get('recipient')
        direction = 'ben_to_admin' if user.role == 'beneficiary' else 'admin_to_ben'
        serializer.save(sender=user, direction=direction)

    @action(detail=False, methods=['get'])
    def inbox(self, request):
        msgs = Message.objects.filter(recipient=request.user).order_by('-created_at')
        return Response(MessageSerializer(msgs, many=True).data)

    @action(detail=False, methods=['get'])
    def sent(self, request):
        msgs = Message.objects.filter(sender=request.user).order_by('-created_at')
        return Response(MessageSerializer(msgs, many=True).data)

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        msg = self.get_object()
        if msg.recipient == request.user:
            msg.is_read = True
            msg.read_at = timezone.now()
            msg.save()
        return Response(MessageSerializer(msg).data)

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Message.objects.filter(recipient=request.user, is_read=False).count()
        return Response({'unread': count})

    @action(detail=False, methods=['get'])
    def thread(self, request):
        """Get conversation thread with a specific user"""
        other_id = request.query_params.get('user_id')
        if not other_id:
            return Response({'error': 'user_id required'}, status=400)
        msgs = Message.objects.filter(
            sender=request.user, recipient_id=other_id
        ) | Message.objects.filter(
            sender_id=other_id, recipient=request.user
        )
        msgs = msgs.order_by('created_at')
        # Mark received ones as read
        msgs.filter(recipient=request.user, is_read=False).update(is_read=True, read_at=timezone.now())
        return Response(MessageSerializer(msgs, many=True).data)


class NotificationViewSet(viewsets.ModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'channel', 'notification_type', 'recipient_beneficiary']

    @action(detail=False, methods=['get'])
    def my_notifications(self, request):
        qs = Notification.objects.filter(recipient_user=request.user)
        return Response(NotificationSerializer(qs[:20], many=True).data)


class CommunicationLogViewSet(viewsets.ModelViewSet):
    queryset = CommunicationLog.objects.select_related('beneficiary', 'logged_by')
    serializer_class = CommunicationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['beneficiary', 'contact_type', 'follow_up_required']

    def perform_create(self, serializer):
        serializer.save(logged_by=self.request.user)


class BulkMessageViewSet(viewsets.ModelViewSet):
    queryset = BulkMessage.objects.all()
    serializer_class = BulkMessageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
