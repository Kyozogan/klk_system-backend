from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth
from django.urls import path
from beneficiaries.models import Beneficiary
from finance.models import Disbursement, FinancialAidPackage
from academics.models import OldCurriculumPerformance, CBCPerformance, EmploymentRecord, UniversityEnrollment
import datetime


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = datetime.date.today()
        current_year = today.year

        # Beneficiaries
        bens = Beneficiary.objects.all()
        total = bens.count()
        active = bens.filter(status='active').count()
        graduated = bens.filter(status='graduated').count()

        # Enrollment trend (last 6 months)
        enrollment_trend = []
        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - datetime.timedelta(days=30 * i)
            count = bens.filter(
                enrollment_date__year=month_date.year,
                enrollment_date__month=month_date.month
            ).count()
            enrollment_trend.append({
                'month': month_date.strftime('%b %Y'),
                'count': count
            })

        # Finance
        disbursements = Disbursement.objects.filter(status='processed')
        total_disbursed = disbursements.aggregate(t=Sum('amount'))['t'] or 0
        this_year_disbursed = disbursements.filter(disbursement_date__year=current_year).aggregate(t=Sum('amount'))['t'] or 0

        # Monthly disbursement (last 6 months)
        monthly_finance = []
        for i in range(5, -1, -1):
            month_date = today.replace(day=1) - datetime.timedelta(days=30 * i)
            amt = disbursements.filter(
                disbursement_date__year=month_date.year,
                disbursement_date__month=month_date.month
            ).aggregate(t=Sum('amount'))['t'] or 0
            monthly_finance.append({'month': month_date.strftime('%b'), 'amount': float(amt)})

        # Level distribution
        level_dist = list(bens.values('curriculum').annotate(count=Count('id')))

        # Performance average (8-4-4)
        avg_perf = OldCurriculumPerformance.objects.aggregate(avg=Avg('score'))['avg'] or 0

        # Employment
        employed = EmploymentRecord.objects.filter(is_current=True).count()

        # Recent enrollments
        recent = bens.order_by('-enrollment_date')[:5]
        recent_data = [{'name': b.full_name, 'klk_id': b.klk_id, 'date': b.enrollment_date, 'curriculum': b.curriculum} for b in recent]

        return Response({
            'beneficiaries': {
                'total': total, 'active': active, 'graduated': graduated,
                'cbc': bens.filter(curriculum='cbc').count(),
                'old_curriculum': bens.filter(curriculum='844').count(),
                'special_needs': bens.filter(special_needs=True).count(),
            },
            'finance': {
                'total_disbursed': float(total_disbursed),
                'this_year': float(this_year_disbursed),
                'active_packages': FinancialAidPackage.objects.filter(status='active').count(),
            },
            'enrollment_trend': enrollment_trend,
            'monthly_finance': monthly_finance,
            'avg_performance': round(avg_perf, 1),
            'employed_alumni': employed,
            'university_enrolled': UniversityEnrollment.objects.filter(status='enrolled').count(),
            'recent_enrollments': recent_data,
        })


class PerformanceAnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        curriculum = request.query_params.get('curriculum', 'all')
        year = request.query_params.get('year')

        result = {}

        if curriculum in ('all', '844'):
            qs = OldCurriculumPerformance.objects.all()
            if year:
                qs = qs.filter(academic_year__year=year)
            result['old_curriculum'] = {
                'by_subject': list(qs.values('subject').annotate(avg=Avg('score')).order_by('-avg')),
                'by_term': list(qs.values('term').annotate(avg=Avg('score')).order_by('term')),
                'overall_avg': qs.aggregate(avg=Avg('score'))['avg'] or 0,
            }

        if curriculum in ('all', 'cbc'):
            cqs = CBCPerformance.objects.all()
            if year:
                cqs = cqs.filter(academic_year__year=year)
            result['cbc'] = {
                'by_learning_area': list(cqs.values('learning_area').annotate(count=Count('id'))),
                'by_rating': list(cqs.values('rating').annotate(count=Count('id'))),
            }

        return Response(result)


urlpatterns = [
    path('dashboard/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('performance-analytics/', PerformanceAnalyticsView.as_view(), name='performance-analytics'),
]
