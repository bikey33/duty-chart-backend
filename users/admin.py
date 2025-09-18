from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        'employee_id', 'full_name', 'email', 'phone_number',
        'directorate', 'department', 'office', 'is_active'
    )
    list_filter = (
        'is_active', 'is_staff', 'directorate', 'department', 'office'
    )
    search_fields = (
        'employee_id', 'full_name', 'email', 'phone_number',
        'directorate__name', 'department__name', 'office__name'
    )
    ordering = ('full_name',)

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'employee_id', 'full_name', 'email', 'phone_number', 'image',
                'directorate', 'department', 'office'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
            )
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'employee_id', 'full_name', 'email', 'phone_number',
                'directorate', 'department', 'office',
                'password1', 'password2'
            ),
        }),
    )
