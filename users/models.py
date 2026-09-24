from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class KLKUserManager(DjangoUserManager):
    """
    Custom manager so that accounts created from the command line behave
    sensibly in the KLK access model.

    The bug this fixes: `manage.py createsuperuser` calls create_superuser(),
    which historically only set is_staff/is_superuser. Every other field fell
    back to the model defaults — role='beneficiary', portal='beneficiary',
    account_status='pending'. The result was that a brand-new superuser got
    bounced out of the management portal and shown the scholar-side "wait for
    a staff member to verify you" screen, even though they *are* the staff.

    A superuser is now always an approved admin-portal account.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('portal', 'admin')
        extra_fields.setdefault('account_status', 'approved')
        extra_fields.setdefault('is_active', True)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('manager', 'Program Manager'),
        ('coordinator', 'Field Coordinator'),
        ('finance_officer', 'Finance Officer'),
        ('office_staff', 'Office Staff'),
        ('beneficiary', 'Beneficiary'),
    ]
    PORTAL_CHOICES = [
        ('admin', 'Admin Portal'),
        ('beneficiary', 'Beneficiary Portal'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('suspended', 'Suspended'),
        ('rejected', 'Rejected'),
    ]
    AUTH_PROVIDER_CHOICES = [
        ('password', 'Email & Password'),
        ('google', 'Google'),
    ]

    # Every role in this tuple is management-side. Anything NOT in here is a
    # student/scholar, and students are the only accounts that need to be
    # verified before they can sign in. This single source of truth is used by
    # the login serializer, the Google flow and the permission helpers below,
    # so the rule can never drift between them.
    STAFF_ROLES = ('admin', 'manager', 'coordinator', 'finance_officer', 'office_staff')

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='beneficiary')
    portal = models.CharField(max_length=15, choices=PORTAL_CHOICES, default='beneficiary')
    phone = models.CharField(max_length=20, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    department = models.CharField(max_length=100, blank=True)
    account_status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    approved_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='approvals')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Who created this account. Staff accounts must be created by a superadmin
    # (or another admin/manager) — that provenance is what stands in for
    # verification on the management side, which is why staff never wait for
    # approval: somebody with authority already vouched for them by creating
    # the account in the first place.
    created_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users')

    # Google sign-in support (scholars may use either method).
    auth_provider = models.CharField(max_length=15, choices=AUTH_PROVIDER_CHOICES, default='password')
    google_id = models.CharField(max_length=100, blank=True, db_index=True)
    email_verified = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = KLKUserManager()

    class Meta:
        db_table = 'users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.role})"

    # ── Portal helpers ────────────────────────────────────────────────────
    @property
    def is_admin_portal(self):
        return self.portal == 'admin'

    @property
    def is_beneficiary_portal(self):
        return self.portal == 'beneficiary'

    @property
    def is_student(self):
        """A scholar/beneficiary. The ONLY kind of account that needs verifying."""
        return self.role == 'beneficiary' and not (self.is_staff or self.is_superuser)

    @property
    def is_management(self):
        """Staff, admin, or superuser — anyone who is not a student."""
        return not self.is_student

    @property
    def can_manage(self):
        return self.is_management

    @property
    def is_approved(self):
        return self.account_status == 'approved'

    @property
    def requires_verification(self):
        """
        Students must be approved by staff before they can sign in.
        Management accounts are vouched for at creation time by the superadmin,
        so they are never held at a verification gate.
        """
        return self.is_student

    def normalize_access(self, commit=True):
        """
        Repair an account whose access fields contradict each other, which is
        what produced the original "admin sent to the scholar waiting room"
        bug. Safe to call on every login.

        Returns True if anything actually changed.
        """
        changed = False

        # A superuser is an administrator by definition.
        if self.is_superuser and self.role not in self.STAFF_ROLES:
            self.role = 'admin'
            changed = True

        # Django staff flag without a management role means the role was never
        # set (e.g. created before this logic existed) — treat as office staff.
        if self.is_staff and not self.is_superuser and self.role not in self.STAFF_ROLES:
            self.role = 'office_staff'
            changed = True

        # Portal must follow the role, not the other way round.
        target_portal = 'beneficiary' if self.is_student else 'admin'
        if self.portal != target_portal:
            self.portal = target_portal
            changed = True

        # Management accounts are never left sitting at 'pending'.
        if self.is_management and self.account_status == 'pending':
            self.account_status = 'approved'
            changed = True

        if changed and commit and self.pk:
            self.save(update_fields=['role', 'portal', 'account_status', 'updated_at'])
        return changed
