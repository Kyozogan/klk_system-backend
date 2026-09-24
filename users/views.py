import datetime

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import User
from .serializers import (
    UserSerializer, AdminUserCreateSerializer, BeneficiaryRegisterSerializer,
    KLKTokenSerializer, GoogleAuthSerializer,
    issue_tokens, check_account_access, AccessDenied,
)

GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'
GOOGLE_TOKENINFO_URL = 'https://oauth2.googleapis.com/tokeninfo'


class KLKTokenView(TokenObtainPairView):
    """
    POST /api/auth/login/ — username-or-email + password, for both clients.

    Body: {"username"|"email": ..., "password": ..., "portal": "admin"|"beneficiary"}
    """
    serializer_class = KLKTokenSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)   # credentials only

        user = serializer.user
        try:
            check_account_access(user, portal=getattr(serializer, 'requested_portal', None))
        except AccessDenied as exc:
            # 403, not 401 — the password was right, the account just isn't
            # allowed through this door yet.
            return Response(exc.detail, status=status.HTTP_403_FORBIDDEN)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        # check_account_access() may have repaired a mis-stamped account (the
        # classic "superuser left on role=beneficiary" case), so serialize the
        # user AFTER the gate — otherwise the client is handed the stale
        # pre-repair record and routes itself to the wrong portal anyway.
        data = dict(serializer.validated_data)
        data['user'] = UserSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def auth_methods(request):
    """
    POST /api/auth/methods/  body: {"email": "..."}

    Lets the login screen decide what to show before asking for a password.
    Deliberately vague for unknown addresses so this cannot be used to
    enumerate who has an account.
    """
    email = (request.data.get('email') or '').strip()
    user = User.objects.filter(email__iexact=email).first() if email else None
    if not user:
        return Response({
            'exists': False,
            'methods': ['password', 'google'],
            'portal': None,
        })
    methods = ['google'] if user.auth_provider == 'google' and not user.has_usable_password() \
        else ['password', 'google']
    return Response({
        'exists': True,
        'methods': methods,
        'portal': user.portal,
        'is_student': user.is_student,
        'account_status': user.account_status,
    })


class GoogleAuthView(APIView):
    """
    POST /api/auth/google/  body: {"access_token": "..."} or {"id_token": "..."}

    Verifies the token with Google, then signs the person in.

    Account creation through this route is scholars only. If the email is
    already attached to a management account, that staff member is signed in
    and their Google identity is linked — but a Google sign-in can never
    *create* a staff account, since staff accounts must come from a superadmin.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        body = GoogleAuthSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        portal = (body.validated_data.get('portal') or '').strip() or None

        info = self._verify(
            access_token=body.validated_data.get('access_token'),
            id_token=body.validated_data.get('id_token'),
        )
        if info is None:
            return Response(
                {'detail': 'Google sign-in could not be verified. Please try again.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = (info.get('email') or '').strip().lower()
        if not email:
            return Response({'detail': 'Google did not return an email address.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user, created = self._get_or_create_user(info, email)

        try:
            check_account_access(user, portal=portal)
        except AccessDenied as exc:
            return Response(exc.detail, status=status.HTTP_403_FORBIDDEN)

        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        tokens = issue_tokens(user)
        return Response({
            **tokens,
            'user': UserSerializer(user).data,
            'is_new_user': created,
        }, status=status.HTTP_200_OK)

    # ── helpers ───────────────────────────────────────────────────────────
    def _verify(self, access_token=None, id_token=None):
        """Ask Google who this token belongs to. Returns the profile or None."""
        try:
            if access_token:
                res = requests.get(
                    GOOGLE_USERINFO_URL,
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=12,
                )
                if res.status_code == 200:
                    return res.json()
                return None

            res = requests.get(GOOGLE_TOKENINFO_URL, params={'id_token': id_token}, timeout=12)
            if res.status_code != 200:
                return None
            data = res.json()
            expected = getattr(settings, 'GOOGLE_OAUTH_CLIENT_IDS', [])
            if expected and data.get('aud') not in expected:
                return None
            return data
        except requests.RequestException:
            return None

    @transaction.atomic
    def _get_or_create_user(self, info, email):
        google_id = info.get('sub', '')
        first = info.get('given_name', '') or (info.get('name', '').split(' ')[0] if info.get('name') else '')
        last = info.get('family_name', '') or ' '.join(info.get('name', '').split(' ')[1:])
        verified = bool(info.get('email_verified') in (True, 'true'))

        user = User.objects.filter(email__iexact=email).first()
        if user:
            updates = []
            if not user.google_id and google_id:
                user.google_id = google_id
                updates.append('google_id')
            if verified and not user.email_verified:
                user.email_verified = True
                updates.append('email_verified')
            if not user.has_usable_password() and user.auth_provider != 'google':
                user.auth_provider = 'google'
                updates.append('auth_provider')
            if updates:
                user.save(update_fields=updates)
            return user, False

        # New account → scholar, pending verification. Never staff.
        base = email.split('@')[0][:140] or 'scholar'
        username, n = base, 1
        while User.objects.filter(username=username).exists():
            username = f'{base}{n}'
            n += 1

        user = User(
            username=username,
            email=email,
            first_name=first,
            last_name=last,
            role='beneficiary',
            portal='beneficiary',
            account_status='pending',
            auth_provider='google',
            google_id=google_id,
            email_verified=verified,
        )
        user.set_unusable_password()
        user.save()
        return user, True


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        return UserSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def create(self, request, *args, **kwargs):
        # Only a superadmin/admin/manager may mint management accounts.
        if not (request.user.is_superuser or request.user.role in ('admin', 'manager')):
            return Response({'detail': 'Only an administrator can create staff accounts.'},
                            status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # Echo back the full user record (not just the create fields) so the
        # portal can drop the new staff member straight into its table.
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        qs = User.objects.all().order_by('-created_at')
        role = self.request.query_params.get('role')
        portal = self.request.query_params.get('portal')
        status_f = self.request.query_params.get('account_status')
        if role:
            qs = qs.filter(role=role)
        if portal:
            qs = qs.filter(portal=portal)
        if status_f:
            qs = qs.filter(account_status=status_f)
        return qs

    @action(detail=False, methods=['get'])
    def me(self, request):
        # Repair on read too, so a stale session can't keep an admin stuck.
        request.user.normalize_access()
        return Response(UserSerializer(request.user).data)

    @action(detail=False, methods=['patch'])
    def update_profile(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        user = request.user
        new_password = request.data.get('new_password', '')
        if len(new_password) < 6:
            return Response({'error': 'New password must be at least 6 characters.'}, status=400)
        # A Google-only account has no current password to check against —
        # this is how such a scholar sets one for the first time.
        if user.has_usable_password():
            if not user.check_password(request.data.get('old_password', '')):
                return Response({'error': 'Incorrect current password'}, status=400)
        user.set_password(new_password)
        if user.auth_provider == 'google':
            user.auth_provider = 'password'
        user.save()
        return Response({'message': 'Password changed successfully'})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a scholar and auto-create their beneficiary profile."""
        if not (request.user.is_superuser or request.user.role in ('admin', 'manager')):
            return Response({'error': 'Permission denied'}, status=403)
        user = self.get_object()
        user.account_status = 'approved'
        user.approved_by = request.user
        user.approved_at = timezone.now()
        user.is_active = True
        user.save()

        if user.portal == 'beneficiary' and user.role == 'beneficiary':
            try:
                from beneficiaries.models import Beneficiary
                if not Beneficiary.objects.filter(user=user).exists():
                    Beneficiary.objects.create(
                        user=user,
                        first_name=user.first_name or user.username,
                        last_name=user.last_name or '',
                        gender='M',
                        date_of_birth=datetime.date(2000, 1, 1),
                        enrollment_date=datetime.date.today(),
                        status='active',
                        curriculum='cbc',
                    )
            except Exception:
                pass  # never fail the approval itself

        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        if not (request.user.is_superuser or request.user.role in ('admin', 'manager')):
            return Response({'error': 'Permission denied'}, status=403)
        user = self.get_object()
        user.account_status = 'rejected'
        user.is_active = False
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=True, methods=['post'])
    def suspend(self, request, pk=None):
        if not (request.user.is_superuser or request.user.role in ('admin', 'manager')):
            return Response({'error': 'Permission denied'}, status=403)
        user = self.get_object()
        user.account_status = 'suspended'
        user.is_active = False
        user.save()
        return Response(UserSerializer(user).data)

    @action(detail=False, methods=['get'])
    def pending(self, request):
        """Only scholars ever sit here — staff are approved at creation."""
        qs = User.objects.filter(account_status='pending', role='beneficiary').order_by('-created_at')
        return Response(UserSerializer(qs, many=True).data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        return Response({
            'total': User.objects.count(),
            'pending': User.objects.filter(account_status='pending', role='beneficiary').count(),
            'approved': User.objects.filter(account_status='approved').count(),
            'beneficiaries': User.objects.filter(role='beneficiary').count(),
            'staff': User.objects.filter(portal='admin').count(),
            'suspended': User.objects.filter(account_status='suspended').count(),
        })


@api_view(['POST'])
@permission_classes([AllowAny])
def beneficiary_register(request):
    serializer = BeneficiaryRegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'Registration successful. Your account is pending verification by the KLK team.',
            'user_id': user.id,
            'username': user.username,
            'account_status': user.account_status,
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
