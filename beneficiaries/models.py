from django.db import models
from simple_history.models import HistoricalRecords


class County(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Counties'

    def __str__(self):
        return self.name


class Sponsor(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    organization = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Guardian(models.Model):
    RELATIONSHIP_CHOICES = [
        ('parent', 'Parent'), ('guardian', 'Legal Guardian'),
        ('relative', 'Relative'), ('other', 'Other'),
    ]
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    phone_alt = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    occupation = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['last_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Beneficiary(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    STATUS_CHOICES = [
        ('active', 'Active'), ('inactive', 'Inactive'),
        ('graduated', 'Graduated'), ('transferred', 'Transferred'),
        ('dropped', 'Dropped Out'), ('deceased', 'Deceased'),
    ]
    CURRICULUM_CHOICES = [
        ('cbc', 'CBC (Competency Based Curriculum)'),
        ('844', '8-4-4 (Old System)'),
    ]

    # Link to user account (beneficiary portal user)
    user = models.OneToOneField(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='beneficiary_profile'
    )

    klk_id = models.CharField(max_length=20, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    birth_certificate_no = models.CharField(max_length=50, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='beneficiaries/', blank=True, null=True)

    county = models.ForeignKey(County, on_delete=models.SET_NULL, null=True, blank=True)
    sub_county = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    ward = models.CharField(max_length=100, blank=True)

    guardian = models.ForeignKey(Guardian, on_delete=models.SET_NULL, null=True, blank=True, related_name='beneficiaries')
    family_size = models.PositiveSmallIntegerField(default=1)
    orphan_status = models.BooleanField(default=False)
    orphan_type = models.CharField(max_length=20, choices=[('single','Single Orphan'),('double','Double Orphan'),('na','N/A')], default='na')
    special_needs = models.BooleanField(default=False)
    special_needs_description = models.TextField(blank=True)

    curriculum = models.CharField(max_length=10, choices=CURRICULUM_CHOICES, default='cbc')
    enrollment_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    sponsor = models.ForeignKey(Sponsor, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)

    # Beneficiary-filled fields (via portal)
    personal_statement = models.TextField(blank=True, help_text='Written by beneficiary')
    ambition = models.CharField(max_length=200, blank=True, help_text='Career aspiration')
    hobbies = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=200, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)

    profile_complete = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        verbose_name_plural = 'Beneficiaries'
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.full_name} ({self.klk_id})"

    @property
    def full_name(self):
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return ' '.join(parts)

    def save(self, *args, **kwargs):
        if not self.klk_id:
            last = Beneficiary.objects.order_by('id').last()
            num = (last.id + 1) if last else 1
            self.klk_id = f"KLK{num:05d}"
        super().save(*args, **kwargs)


class BeneficiaryDocument(models.Model):
    # Reworked around what a scholar actually uploads from their phone:
    # a payment receipt, a fee statement, a referral letter, a general photo,
    # or anything that doesn't fit those — one flat, unambiguous list.
    #
    # 'recommendation' is kept as a LEGACY value only — existing records keep
    # displaying correctly — but it is no longer offered anywhere new; new
    # referral letters use 'referral'. Likewise 'birth_cert', 'id_copy',
    # 'report_card' and 'medical' stay valid for staff-side filtering and
    # historic data, they're just not part of the scholar app's picker, which
    # only ever offers the five below.
    DOC_TYPE_CHOICES = [
        ('receipt', 'Payment Receipt'),
        ('statement', 'Fee Statement'),
        ('referral', 'Referral Letter'),
        ('photo', 'Image'),
        ('other', 'Other Document'),
        # Legacy — kept only so older records still render with a real
        # label instead of falling back to the raw stored value.
        ('birth_cert', 'Birth Certificate'), ('id_copy', 'ID/Passport Copy'),
        ('report_card', 'Report Card'), ('recommendation', 'Recommendation Letter'),
        ('medical', 'Medical Report'),
    ]
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='documents')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='documents/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by_beneficiary = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']
