from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class AccessDenied(serializers.ValidationError):
    """
    A login refusal that carries a stable, machine-readable `code` alongside
    the human-readable message.

    DRF normally wraps every value in a ValidationError detail dict inside a
    list, which would turn `"code": "pending_verification"` into
    `["pending_verification"]` and force every client to unwrap it. Building
    the detail dict after __init__ keeps the code a plain string, so the
    Scholar app and the management portal can both branch on it directly.
    """

    def __init__(self, message, code=None, **extra):
        super().__init__({'detail': message})
        self.detail = {'detail': message}
        if code:
            self.detail['code'] = code
        self.detail.update(extra)


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    is_student = serializers.BooleanField(read_only=True)
    is_management = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'portal', 'phone', 'department', 'is_active', 'account_status',
            'approved_by_name', 'approved_at', 'avatar', 'created_at',
            'auth_provider', 'email_verified', 'is_student', 'is_management',
        ]
        read_only_fields = ['created_at', 'approved_at', 'auth_provider', 'email_verified']

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class AdminUserCreateSerializer(serializers.ModelSerializer):
    """
    A superadmin/admin creating a management account (staff, coordinator,
    finance officer, manager, or another admin).

    Accounts created here are approved on the spot. The act of a superadmin
    creating the account IS the verification — asking a second staff member to
    then approve it would be circular.
    """
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password',
                  'role', 'phone', 'department']
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'department': {'required': False},
            'phone': {'required': False},
        }

    def validate_role(self, value):
        if value == 'beneficiary':
            raise serializers.ValidationError(
                'Scholars register themselves through the Scholar app; '
                'they are not created here.'
            )
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        if user.role not in User.STAFF_ROLES:
            user.role = 'office_staff'
        user.portal = 'admin'
        user.account_status = 'approved'   # vouched for by whoever created it
        user.approved_at = timezone.now()
        user.is_active = True
        user.auth_provider = 'password'

        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user.created_by = request.user
            user.approved_by = request.user
        user.save()
        return user


class BeneficiaryRegisterSerializer(serializers.ModelSerializer):
    """Scholars self-register from the Scholar app. These DO need approval."""
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password',
                  'confirm_password', 'phone']

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('confirm_password'):
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.role = 'beneficiary'
        user.portal = 'beneficiary'
        user.account_status = 'pending'   # needs staff verification
        user.auth_provider = 'password'
        user.save()
        return user


def issue_tokens(user):
    """Build the JWT pair both clients expect."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def check_account_access(user, portal=None):
    """
    The single gate both the password login and the Google login run through.

    Rules:
      * Suspended / rejected accounts are always refused.
      * Students (scholars) must be approved by staff first.
      * Everyone else — admin, manager, coordinator, finance officer, office
        staff, superusers — signs straight in. Their account only exists
        because a superadmin created it, so there is nothing left to verify.
      * If `portal` is given, the account must belong to that side.

    Raises serializers.ValidationError, or returns None when access is allowed.
    """
    # Heal any account whose role/portal/status fields contradict each other
    # before judging it, so a mis-stamped admin is never sent to the waiting
    # room.
    user.normalize_access()

    if user.account_status in ('rejected', 'suspended'):
        raise AccessDenied(
            f'Your account has been {user.account_status}.',
            code=f'account_{user.account_status}',
        )

    if user.requires_verification and not user.is_approved:
        raise AccessDenied(
            'Your account is awaiting verification by the KLK team. '
            'You will be able to sign in once a staff member approves it.',
            code='pending_verification',
            account_status=user.account_status,
        )

    if portal == 'admin' and not user.is_management:
        raise AccessDenied(
            'This is the management portal. Scholars should sign in using '
            'the KLK Scholar app.',
            code='wrong_portal',
        )
    if portal == 'beneficiary' and not user.is_student:
        raise AccessDenied(
            'Staff accounts sign in through the management portal, not the '
            'Scholar app.',
            code='wrong_portal',
        )
    return None


class KLKTokenSerializer(TokenObtainPairSerializer):
    """
    Password login for BOTH clients.

    Accepts `username` or `email` (the Scholar app asks for an email; the
    management portal asks for a username), and takes an optional `portal`
    hint so each client can reject accounts belonging to the other side with a
    clear message instead of a confusing redirect loop.
    """
    portal = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False
        self.fields['email'] = serializers.EmailField(required=False, write_only=True)

    def validate(self, attrs):
        portal = (attrs.pop('portal', '') or '').strip() or None
        email = attrs.pop('email', None)

        # Let people type an email into the username box and vice versa.
        if not attrs.get(self.username_field) and email:
            match = User.objects.filter(email__iexact=email).first()
            attrs[self.username_field] = match.username if match else email
        elif attrs.get(self.username_field) and '@' in attrs[self.username_field]:
            match = User.objects.filter(email__iexact=attrs[self.username_field]).first()
            if match:
                attrs[self.username_field] = match.username

        if not attrs.get(self.username_field):
            raise serializers.ValidationError({'detail': 'Enter your username or email.'})

        data = super().validate(attrs)

        # The account-access gate deliberately runs in the VIEW, not here.
        # Anything raised inside a serializer's validate() gets re-wrapped by
        # DRF, which would turn our stable `code` string into a one-element
        # list and force both clients to unwrap it. Stashing the portal hint
        # lets the view apply the same rules and return the error untouched.
        self.requested_portal = portal

        data['user'] = UserSerializer(self.user).data
        return data


class GoogleAuthSerializer(serializers.Serializer):
    """
    Body for the Google sign-in endpoint.

    The mobile app sends the `access_token` it got from Google Identity
    Services; a browser-based flow may send an `id_token` instead. Either is
    accepted.
    """
    access_token = serializers.CharField(required=False, allow_blank=True)
    id_token = serializers.CharField(required=False, allow_blank=True)
    portal = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('access_token') and not attrs.get('id_token'):
            raise serializers.ValidationError(
                {'detail': 'Provide either access_token or id_token from Google.'}
            )
        return attrs
