from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (FinancialAidPackageViewSet, DisbursementViewSet,
                    SchoolFeeRecordViewSet, AnnualBudgetViewSet, BudgetCategoryViewSet)

router = DefaultRouter()
router.register('packages', FinancialAidPackageViewSet)
router.register('disbursements', DisbursementViewSet)
router.register('fees', SchoolFeeRecordViewSet)
router.register('budgets', AnnualBudgetViewSet)
router.register('categories', BudgetCategoryViewSet)

urlpatterns = [path('', include(router.urls))]
