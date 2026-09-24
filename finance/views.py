from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.db.models import Sum, Count, Avg
from .models import FinancialAidPackage, Disbursement, SchoolFeeRecord, AnnualBudget, BudgetCategory


class BudgetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BudgetCategory
        fields = '__all__'


class DisbursementSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    processed_by_name = serializers.CharField(source='processed_by.get_full_name', read_only=True)

    class Meta:
        model = Disbursement
        fields = '__all__'


class FinancialAidPackageSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source='beneficiary.full_name', read_only=True)
    beneficiary_klk_id = serializers.CharField(source='beneficiary.klk_id', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    disbursements = DisbursementSerializer(many=True, read_only=True)
    total_disbursed = serializers.SerializerMethodField()

    class Meta:
        model = FinancialAidPackage
        fields = '__all__'

    def get_total_disbursed(self, obj):
        return obj.disbursements.filter(status='processed').aggregate(t=Sum('amount'))['t'] or 0


class SchoolFeeRecordSerializer(serializers.ModelSerializer):
    beneficiary_name = serializers.CharField(source='beneficiary.full_name', read_only=True)

    class Meta:
        model = SchoolFeeRecord
        fields = '__all__'


class AnnualBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnnualBudget
        fields = '__all__'


# ---- ViewSets ----
class BudgetCategoryViewSet(viewsets.ModelViewSet):
    queryset = BudgetCategory.objects.all()
    serializer_class = BudgetCategorySerializer
    permission_classes = [IsAuthenticated]


class FinancialAidPackageViewSet(viewsets.ModelViewSet):
    queryset = FinancialAidPackage.objects.select_related('beneficiary', 'approved_by').prefetch_related('disbursements')
    serializer_class = FinancialAidPackageSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'aid_type', 'beneficiary']
    search_fields = ['beneficiary__first_name', 'beneficiary__last_name', 'beneficiary__klk_id']

    @action(detail=False, methods=['get'])
    def financial_summary(self, request):
        qs = self.get_queryset()
        disbursements = Disbursement.objects.filter(status='processed')
        return Response({
            'total_packages': qs.count(),
            'active_packages': qs.filter(status='active').count(),
            'total_annual_committed': qs.filter(status__in=['active', 'approved']).aggregate(t=Sum('annual_amount'))['t'] or 0,
            'total_disbursed_all_time': disbursements.aggregate(t=Sum('amount'))['t'] or 0,
            'disbursed_this_year': disbursements.filter(
                disbursement_date__year=__import__('datetime').date.today().year
            ).aggregate(t=Sum('amount'))['t'] or 0,
            'by_aid_type': list(qs.values('aid_type').annotate(count=Count('id'), total=Sum('annual_amount'))),
            'by_status': list(qs.values('status').annotate(count=Count('id'))),
        })


class DisbursementViewSet(viewsets.ModelViewSet):
    queryset = Disbursement.objects.select_related('aid_package__beneficiary', 'category', 'processed_by')
    serializer_class = DisbursementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'payment_method', 'aid_package', 'category']
    search_fields = ['aid_package__beneficiary__first_name', 'aid_package__beneficiary__klk_id', 'reference_no']

    @action(detail=False, methods=['get'])
    def monthly_report(self, request):
        year = request.query_params.get('year', __import__('datetime').date.today().year)
        from django.db.models.functions import TruncMonth
        data = (
            self.get_queryset()
            .filter(status='processed', disbursement_date__year=year)
            .annotate(month=TruncMonth('disbursement_date'))
            .values('month')
            .annotate(total=Sum('amount'), count=Count('id'))
            .order_by('month')
        )
        return Response(list(data))


class SchoolFeeRecordViewSet(viewsets.ModelViewSet):
    queryset = SchoolFeeRecord.objects.select_related('beneficiary')
    serializer_class = SchoolFeeRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['status', 'academic_year', 'term', 'beneficiary']
    search_fields = ['beneficiary__first_name', 'beneficiary__klk_id', 'institution_name']

    @action(detail=False, methods=['get'])
    def outstanding(self, request):
        qs = self.get_queryset().exclude(status='paid').exclude(status='waived')
        total = qs.aggregate(total_balance=Sum('balance'))['total_balance'] or 0
        return Response({'count': qs.count(), 'total_outstanding': total, 'records': SchoolFeeRecordSerializer(qs[:50], many=True).data})


class AnnualBudgetViewSet(viewsets.ModelViewSet):
    queryset = AnnualBudget.objects.all()
    serializer_class = AnnualBudgetSerializer
    permission_classes = [IsAuthenticated]
