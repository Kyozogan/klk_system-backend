from rest_framework import serializers
from .models import Beneficiary, Guardian, County, Sponsor, BeneficiaryDocument


class NestedWritableField(serializers.PrimaryKeyRelatedField):
    """
    Reads as a full nested object, writes as a plain primary key.

    This exists to fix a real bug. `guardian`, `county` and `sponsor` used to
    be declared as read-only nested serializers with separate `*_id` write
    fields. DRF silently DISCARDS unknown/read-only keys rather than erroring,
    so a client that POSTed `{"guardian": 7}` got a 200 back and no link was
    ever made — which is exactly why guardians "saved" but never appeared.

    Accepting the natural field name for both directions removes the trap:
    whatever the client reads back is what it can write.
    """

    def __init__(self, serializer_class, **kwargs):
        self.serializer_class = serializer_class
        super().__init__(**kwargs)

    def to_representation(self, value):
        # `value` is a PKOnlyRelatedObject when the parent used an optimised
        # queryset, so re-fetch through the relation to get a real instance.
        instance = getattr(value, 'pk', None) and self.get_queryset().filter(pk=value.pk).first()
        if instance is None:
            return None
        return self.serializer_class(instance, context=self.context).data


class CountySerializer(serializers.ModelSerializer):
    class Meta:
        model = County
        fields = '__all__'


class SponsorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sponsor
        fields = '__all__'


class GuardianSerializer(serializers.ModelSerializer):
    county_name = serializers.CharField(source='county.name', read_only=True)
    class Meta:
        model = Guardian
        fields = '__all__'


class BeneficiaryDocumentSerializer(serializers.ModelSerializer):
    # Absolute URL (http://host/media/...). The mobile app needs this because
    # it has no dev proxy and cannot resolve a site-relative path.
    file_url = serializers.SerializerMethodField()
    # Site-relative path (/media/...). The web portal uses THIS one so the
    # file is same-origin through the Vite proxy — a cross-origin file in an
    # <iframe> is what Firefox refuses to render in the preview modal.
    file_path = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_ext = serializers.SerializerMethodField()
    doc_type_display = serializers.CharField(source='get_doc_type_display', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)

    class Meta:
        model = BeneficiaryDocument
        fields = '__all__'
        read_only_fields = ['uploaded_at', 'uploaded_by', 'uploaded_by_beneficiary']

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def get_file_path(self, obj):
        return obj.file.url if obj.file else None

    def get_file_name(self, obj):
        if not obj.file:
            return None
        return obj.file.name.rsplit('/', 1)[-1]

    def get_file_ext(self, obj):
        """Lower-case extension without the dot, so the client can decide how
        to preview without parsing URLs that may carry query strings."""
        name = self.get_file_name(obj) or ''
        return name.rsplit('.', 1)[-1].lower() if '.' in name else ''


class BeneficiaryListSerializer(serializers.ModelSerializer):
    county_name = serializers.CharField(source='county.name', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    sponsor_name = serializers.CharField(source='sponsor.name', read_only=True)
    age = serializers.SerializerMethodField()
    current_level = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = Beneficiary
        fields = [
            'id', 'klk_id', 'first_name', 'last_name', 'full_name', 'gender',
            'date_of_birth', 'age', 'county_name', 'curriculum', 'status',
            'enrollment_date', 'guardian_name', 'sponsor_name', 'current_level',
            'photo', 'profile_complete', 'user', 'user_email',
        ]

    def get_age(self, obj):
        from datetime import date
        today = date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_current_level(self, obj):
        if obj.curriculum == 'cbc':
            level = obj.cbc_levels.filter(is_current=True).first()
            return level.get_stage_display() if level else None
        else:
            level = obj.old_curriculum_levels.filter(is_current=True).first()
            return level.get_grade_display() if level else None


class BeneficiaryDetailSerializer(serializers.ModelSerializer):
    county_name = serializers.CharField(source='county.name', read_only=True)

    # Read nested, write by id — see NestedWritableField above.
    guardian = NestedWritableField(
        GuardianSerializer, queryset=Guardian.objects.all(),
        required=False, allow_null=True)
    sponsor = NestedWritableField(
        SponsorSerializer, queryset=Sponsor.objects.all(),
        required=False, allow_null=True)
    county = NestedWritableField(
        CountySerializer, queryset=County.objects.all(),
        required=False, allow_null=True)

    # The `*_id` spellings are kept as aliases so any existing caller that
    # already used them keeps working.
    guardian_id = serializers.PrimaryKeyRelatedField(
        source='guardian', queryset=Guardian.objects.all(),
        write_only=True, required=False, allow_null=True)
    sponsor_id = serializers.PrimaryKeyRelatedField(
        source='sponsor', queryset=Sponsor.objects.all(),
        write_only=True, required=False, allow_null=True)
    county_id = serializers.PrimaryKeyRelatedField(
        source='county', queryset=County.objects.all(),
        write_only=True, required=False, allow_null=True)
    documents = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    total_aid_received = serializers.SerializerMethodField()
    current_level = serializers.SerializerMethodField()
    user_email = serializers.CharField(source='user.email', read_only=True)
    user_status = serializers.CharField(source='user.account_status', read_only=True)

    class Meta:
        model = Beneficiary
        fields = '__all__'
        read_only_fields = ['klk_id', 'created_at', 'updated_at']

    def get_documents(self, obj):
        docs = obj.documents.all().order_by('-uploaded_at')
        return BeneficiaryDocumentSerializer(docs, many=True, context=self.context).data

    def get_age(self, obj):
        from datetime import date
        today = date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_total_aid_received(self, obj):
        from django.db.models import Sum
        return obj.aid_packages.filter(
            disbursements__status='processed'
        ).aggregate(total=Sum('disbursements__amount'))['total'] or 0

    def get_current_level(self, obj):
        if obj.curriculum == 'cbc':
            level = obj.cbc_levels.filter(is_current=True).first()
            if level:
                return {'stage': level.get_stage_display(),
                        'institution': str(level.institution) if level.institution else None}
        else:
            level = obj.old_curriculum_levels.filter(is_current=True).first()
            if level:
                return {'grade': level.get_grade_display(),
                        'institution': str(level.institution) if level.institution else None}
        return None
