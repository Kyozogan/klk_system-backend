from django.contrib import admin
from .models import Beneficiary, Guardian, County, Sponsor, BeneficiaryDocument
@admin.register(Beneficiary)
class BeneficiaryAdmin(admin.ModelAdmin):
    list_display = ['klk_id', 'full_name', 'gender', 'curriculum', 'status', 'enrollment_date']
    list_filter = ['status', 'curriculum', 'gender', 'county']
    search_fields = ['first_name', 'last_name', 'klk_id']
    readonly_fields = ['klk_id', 'created_at', 'updated_at']
admin.site.register(Guardian)
admin.site.register(County)
admin.site.register(Sponsor)
admin.site.register(BeneficiaryDocument)
