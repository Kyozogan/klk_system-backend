from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count
from .models import Beneficiary, Guardian, County, Sponsor, BeneficiaryDocument
from .serializers import (
    BeneficiaryListSerializer, BeneficiaryDetailSerializer,
    GuardianSerializer, CountySerializer, SponsorSerializer,
    BeneficiaryDocumentSerializer,
)


class CountyViewSet(viewsets.ModelViewSet):
    queryset = County.objects.all()
    serializer_class = CountySerializer
    permission_classes = [IsAuthenticated]


class SponsorViewSet(viewsets.ModelViewSet):
    queryset = Sponsor.objects.all()
    serializer_class = SponsorSerializer
    permission_classes = [IsAuthenticated]


class GuardianViewSet(viewsets.ModelViewSet):
    queryset = Guardian.objects.all().order_by('last_name')
    serializer_class = GuardianSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter]
    search_fields = ['first_name', 'last_name', 'phone', 'national_id']

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


# Alias so both names work
GuardianUpdateViewSet = GuardianViewSet


class BeneficiaryViewSet(viewsets.ModelViewSet):
    queryset = Beneficiary.objects.select_related(
        'county', 'guardian', 'sponsor', 'user'
    ).prefetch_related(
        'cbc_levels', 'old_curriculum_levels', 'aid_packages', 'documents'
    ).order_by('last_name', 'first_name')
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'curriculum', 'gender', 'county', 'sponsor']
    search_fields = ['first_name', 'last_name', 'klk_id', 'guardian__first_name', 'guardian__phone']
    ordering_fields = ['last_name', 'enrollment_date', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return BeneficiaryListSerializer
        return BeneficiaryDetailSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.role == 'beneficiary':
            qs = qs.filter(user=self.request.user)
        return qs

    @action(detail=False, methods=['get'])
    def my_profile(self, request):
        try:
            b = Beneficiary.objects.get(user=request.user)
            return Response(BeneficiaryDetailSerializer(b, context={'request': request}).data)
        except Beneficiary.DoesNotExist:
            return Response({'detail': 'Profile not yet created.'}, status=404)

    @action(detail=False, methods=['patch'])
    def update_my_profile(self, request):
        try:
            b = Beneficiary.objects.get(user=request.user)
        except Beneficiary.DoesNotExist:
            return Response({'detail': 'Profile not found.'}, status=404)
        allowed = ['personal_statement', 'ambition', 'hobbies',
                   'emergency_contact_name', 'emergency_contact_phone']
        data = {k: v for k, v in request.data.items() if k in allowed}
        s = BeneficiaryDetailSerializer(b, data=data, partial=True, context={'request': request})
        if s.is_valid():
            s.save()
            return Response(s.data)
        return Response(s.errors, status=400)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = Beneficiary.objects.all()
        return Response({
            'total': qs.count(),
            'active': qs.filter(status='active').count(),
            'inactive': qs.filter(status='inactive').count(),
            'graduated': qs.filter(status='graduated').count(),
            'dropped': qs.filter(status='dropped').count(),
            'cbc': qs.filter(curriculum='cbc').count(),
            'old_curriculum': qs.filter(curriculum='844').count(),
            'special_needs': qs.filter(special_needs=True).count(),
            'orphans': qs.filter(orphan_status=True).count(),
            'profile_complete': qs.filter(profile_complete=True).count(),
            'by_gender': {'male': qs.filter(gender='M').count(), 'female': qs.filter(gender='F').count()},
            'by_county': list(qs.values('county__name').annotate(count=Count('id')).order_by('-count')[:10]),
        })

    @action(detail=True, methods=['get'])
    def journey(self, request, pk=None):
        b = self.get_object()
        # Each list below includes the RAW FOREIGN KEY IDS (institution,
        # academic_year) alongside the display names, plus every editable
        # field. Without the ids an edit dialog has no way to pre-select the
        # current institution in a dropdown, which is why these records could
        # only ever be created and never corrected.
        return Response({
            'beneficiary': BeneficiaryDetailSerializer(b, context={'request': request}).data,
            'cbc_levels': list(b.cbc_levels.select_related('institution', 'academic_year').values(
                'id', 'stage', 'institution', 'institution__name',
                'academic_year', 'academic_year__year',
                'start_date', 'end_date', 'promoted', 'is_current',
                'stream', 'admission_no', 'notes')),
            'old_curriculum_levels': list(b.old_curriculum_levels.select_related('institution', 'academic_year').values(
                'id', 'grade', 'institution', 'institution__name',
                'academic_year', 'academic_year__year',
                'start_date', 'end_date', 'promoted', 'is_current',
                'class_position', 'total_students', 'admission_no', 'stream', 'notes')),
            'university_enrollments': list(b.university_enrollments.select_related('institution').values(
                'id', 'course_name', 'institution', 'institution__name', 'degree_type',
                'start_year', 'expected_end_year', 'actual_end_year', 'status', 'gpa',
                'current_year_of_study', 'student_id', 'graduation_class', 'notes')),
            'employment_records': list(b.employment_records.values(
                'id', 'employer', 'job_title', 'employment_type',
                'start_date', 'end_date', 'is_current', 'industry',
                'monthly_salary', 'notes')),
            'aid_packages': list(b.aid_packages.values(
                'id', 'aid_type', 'status', 'annual_amount', 'start_date', 'end_date',
                'notes')),
        })

    @action(detail=False, methods=['get'])
    def export_list(self, request):
        import csv
        from django.http import HttpResponse
        qs = self.filter_queryset(self.get_queryset())
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="klk_beneficiaries.csv"'
        writer = csv.writer(response)
        writer.writerow(['KLK ID', 'Full Name', 'Gender', 'DOB', 'County', 'Curriculum',
                         'Status', 'Enrollment Date', 'Guardian', 'Guardian Phone'])
        for b in qs:
            writer.writerow([b.klk_id, b.full_name, b.get_gender_display(), b.date_of_birth,
                b.county.name if b.county else '', b.get_curriculum_display(),
                b.get_status_display(), b.enrollment_date,
                b.guardian.full_name if b.guardian else '',
                b.guardian.phone if b.guardian else ''])
        return response


class BeneficiaryDocumentViewSet(viewsets.ModelViewSet):
    queryset = BeneficiaryDocument.objects.all().order_by('-uploaded_at')
    serializer_class = BeneficiaryDocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['beneficiary', 'doc_type']

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    def get_queryset(self):
        qs = super().get_queryset()
        # Beneficiaries only see their own documents
        if self.request.user.role == 'beneficiary':
            try:
                b = Beneficiary.objects.get(user=self.request.user)
                qs = qs.filter(beneficiary=b)
            except Beneficiary.DoesNotExist:
                return qs.none()
        return qs

    def perform_create(self, serializer):
        is_ben = self.request.user.role == 'beneficiary'
        serializer.save(uploaded_by_beneficiary=is_ben)
