from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User
@admin.register(User)
class KLKUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'get_full_name', 'role', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = UserAdmin.fieldsets + (('KLK Info', {'fields': ('role', 'phone', 'department', 'avatar')}),)
