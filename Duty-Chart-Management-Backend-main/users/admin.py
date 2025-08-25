from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('employee_id', 'full_name', 'email', 'phone_number', 'office', 'is_active')
    list_filter = ('is_active', 'office', 'is_staff')
    search_fields = ('employee_id', 'full_name', 'email', 'phone_number')
    ordering = ('full_name',)
    
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('employee_id', 'full_name', 'email', 'phone_number', 'image', 'office')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'employee_id', 'full_name', 'email', 'phone_number', 'password1', 'password2'),
        }),
    )
