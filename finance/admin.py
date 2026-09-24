from django.contrib import admin
from .models import FinancialAidPackage, Disbursement, SchoolFeeRecord, AnnualBudget, BudgetCategory
for model in [FinancialAidPackage, Disbursement, SchoolFeeRecord, AnnualBudget, BudgetCategory]:
    admin.site.register(model)
