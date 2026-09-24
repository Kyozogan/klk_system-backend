from rest_framework import serializers as drf_serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Avg, Count
from .models import (
    Institution, AcademicYear, CBCLevel, CBCPerformance,
    OldCurriculumLevel, OldCurriculumPerformance,
    UniversityEnrollment, UniversitySemesterResult,
    EmploymentRecord, AcademicCalendarEvent
)


class InstitutionSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = Institution
        fields = '__all__'


class AcademicYearSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'


class CBCPerformanceSerializer(drf_serializers.ModelSerializer):
    learning_area_display = drf_serializers.CharField(source='get_learning_area_display', read_only=True)
    rating_display = drf_serializers.CharField(source='get_rating_display', read_only=True)
    class Meta:
        model = CBCPerformance
        fields = '__all__'


class CBCLevelSerializer(drf_serializers.ModelSerializer):
    institution_name = drf_serializers.CharField(source='institution.name', read_only=True)
    academic_year_label = drf_serializers.CharField(source='academic_year.year', read_only=True)
    stage_display = drf_serializers.CharField(source='get_stage_display', read_only=True)
    performances = CBCPerformanceSerializer(many=True, read_only=True)
    class Meta:
        model = CBCLevel
        fields = '__all__'


class OldCurriculumPerformanceSerializer(drf_serializers.ModelSerializer):
    subject_display = drf_serializers.CharField(source='get_subject_display', read_only=True)
    class Meta:
        model = OldCurriculumPerformance
        fields = '__all__'


class OldCurriculumLevelSerializer(drf_serializers.ModelSerializer):
    institution_name = drf_serializers.CharField(source='institution.name', read_only=True)
    academic_year_label = drf_serializers.CharField(source='academic_year.year', read_only=True)
    grade_display = drf_serializers.CharField(source='get_grade_display', read_only=True)
    performances = OldCurriculumPerformanceSerializer(many=True, read_only=True)
    class Meta:
        model = OldCurriculumLevel
        fields = '__all__'


class UniversitySemesterResultSerializer(drf_serializers.ModelSerializer):
    class Meta:
        model = UniversitySemesterResult
        fields = '__all__'


class UniversityEnrollmentSerializer(drf_serializers.ModelSerializer):
    institution_name = drf_serializers.CharField(source='institution.name', read_only=True)
    beneficiary_name = drf_serializers.CharField(source='beneficiary.full_name', read_only=True)
    semester_results = UniversitySemesterResultSerializer(many=True, read_only=True)
    class Meta:
        model = UniversityEnrollment
        fields = '__all__'
        # DRF auto-adds a UniqueValidator for any model field with
        # unique=True, and that validator runs BEFORE validate_beneficiary()
        # below — so without this, DRF's generic "university enrollment with
        # this beneficiary already exists" message wins the race and the
        # friendlier one below never has a chance to fire. Turning off the
        # automatic validator here makes validate_beneficiary() the only
        # source of truth for this rule.
        extra_kwargs = {'beneficiary': {'validators': []}}

    def validate_beneficiary(self, value):
        # A scholar has exactly one university/tertiary record. The database
        # constraint (unique=True on the FK) is the actual guarantee; this
        # check exists purely so a duplicate attempt gets a readable message
        # instead of a raw IntegrityError. Only checked on CREATE — editing
        # the existing record naturally re-submits the same beneficiary id
        # and must not trip over its own row.
        if self.instance is None and UniversityEnrollment.objects.filter(beneficiary=value).exists():
            raise drf_serializers.ValidationError(
                'This scholar already has a university/tertiary record. '
                'Edit the existing record, or delete it first if you need to start over.'
            )
        return value


class EmploymentRecordSerializer(drf_serializers.ModelSerializer):
    beneficiary_name = drf_serializers.CharField(source='beneficiary.full_name', read_only=True)
    employment_type_display = drf_serializers.CharField(source='get_employment_type_display', read_only=True)
    class Meta:
        model = EmploymentRecord
        fields = '__all__'


class CalendarEventSerializer(drf_serializers.ModelSerializer):
    event_type_display = drf_serializers.CharField(source='get_event_type_display', read_only=True)
    class Meta:
        model = AcademicCalendarEvent
        fields = '__all__'


class InstitutionViewSet(viewsets.ModelViewSet):
    queryset = Institution.objects.all()
    serializer_class = InstitutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['level', 'is_active']
    search_fields = ['name', 'county', 'sub_county']


class AcademicYearViewSet(viewsets.ModelViewSet):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [IsAuthenticated]


class CBCLevelViewSet(viewsets.ModelViewSet):
    queryset = CBCLevel.objects.select_related('beneficiary', 'institution', 'academic_year').prefetch_related('performances')
    serializer_class = CBCLevelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['beneficiary', 'stage', 'is_current', 'academic_year']


class CBCPerformanceViewSet(viewsets.ModelViewSet):
    queryset = CBCPerformance.objects.all()
    serializer_class = CBCPerformanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['cbc_level', 'term', 'learning_area', 'rating']

    @action(detail=False, methods=['get'])
    def summary(self, request):
        beneficiary_id = request.query_params.get('beneficiary_id')
        if not beneficiary_id:
            return Response({'error': 'beneficiary_id required'}, status=400)
        qs = self.get_queryset().filter(cbc_level__beneficiary_id=beneficiary_id)
        return Response({
            'by_learning_area': list(qs.values('learning_area').annotate(count=Count('id'))),
            'by_rating': list(qs.values('rating').annotate(count=Count('id'))),
        })


class OldCurriculumLevelViewSet(viewsets.ModelViewSet):
    queryset = OldCurriculumLevel.objects.select_related('beneficiary', 'institution', 'academic_year').prefetch_related('performances')
    serializer_class = OldCurriculumLevelSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['beneficiary', 'grade', 'is_current', 'academic_year']


class OldCurriculumPerformanceViewSet(viewsets.ModelViewSet):
    queryset = OldCurriculumPerformance.objects.all()
    serializer_class = OldCurriculumPerformanceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['old_curriculum_level', 'term', 'subject']

    @action(detail=False, methods=['get'])
    def analytics(self, request):
        qs = self.get_queryset()
        level = request.query_params.get('level')
        year = request.query_params.get('academic_year')
        if level:
            qs = qs.filter(old_curriculum_level__grade=level)
        if year:
            qs = qs.filter(academic_year__year=year)
        return Response({'by_subject': list(qs.values('subject').annotate(avg_score=Avg('score')).order_by('-avg_score'))})


class UniversityEnrollmentViewSet(viewsets.ModelViewSet):
    queryset = UniversityEnrollment.objects.select_related('beneficiary', 'institution')
    serializer_class = UniversityEnrollmentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['beneficiary', 'status', 'degree_type']
    search_fields = ['course_name', 'student_id', 'beneficiary__first_name', 'beneficiary__last_name']


class UniversitySemesterResultViewSet(viewsets.ModelViewSet):
    queryset = UniversitySemesterResult.objects.all()
    serializer_class = UniversitySemesterResultSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['enrollment', 'year_of_study', 'semester']


class EmploymentRecordViewSet(viewsets.ModelViewSet):
    queryset = EmploymentRecord.objects.select_related('beneficiary')
    serializer_class = EmploymentRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['beneficiary', 'employment_type', 'is_current']
    search_fields = ['employer', 'job_title', 'industry', 'beneficiary__first_name', 'beneficiary__last_name']

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self.get_queryset()
        return Response({
            'total_employed': qs.filter(is_current=True).count(),
            'by_type': list(qs.filter(is_current=True).values('employment_type').annotate(count=Count('id'))),
            'total_alumni_tracked': qs.values('beneficiary').distinct().count(),
        })


class CalendarEventViewSet(viewsets.ModelViewSet):
    queryset = AcademicCalendarEvent.objects.all()
    serializer_class = CalendarEventSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['event_type', 'applies_to_curriculum']
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
