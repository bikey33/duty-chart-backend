from django.contrib import admin
from .models import DutyChart, Duty, RosterAssignment  # added RosterAssignment import

@admin.register(DutyChart)
class DutyChartAdmin(admin.ModelAdmin):
    list_display = ('office', 'get_department', 'get_directorate', 'effective_date', 'end_date')
    list_filter = ('office__department__directorate', 'office__department', 'office')
    search_fields = ('office__name', 'office__department__name', 'office__department__directorate__name')
    autocomplete_fields = ['office']
    date_hierarchy = 'effective_date'

    def get_department(self, obj):
        return obj.office.department.name
    get_department.short_description = 'Department'
    get_department.admin_order_field = 'office__department__name'

    def get_directorate(self, obj):
        return obj.office.department.directorate.name
    get_directorate.short_description = 'Directorate'
    get_directorate.admin_order_field = 'office__department__directorate__name'


@admin.register(Duty)
class DutyAdmin(admin.ModelAdmin):
    list_display = ('user', 'duty_chart', 'date', 'shift', 'start_time', 'end_time',
                   'is_completed', 'currently_available')
    list_filter = ('shift', 'is_completed', 'currently_available',
                  'duty_chart__office__department__directorate',
                  'duty_chart__office__department',
                  'duty_chart__office')
    search_fields = ('user__full_name', 'user__employee_id',
                    'duty_chart__office__name',
                    'duty_chart__office__department__name',
                    'duty_chart__office__department__directorate__name')
    autocomplete_fields = ['user', 'duty_chart']
    date_hierarchy = 'date'


# NEW: Admin for strict roster assignments
@admin.register(RosterAssignment)
class RosterAssignmentAdmin(admin.ModelAdmin):
    list_display = ('date', 'shift', 'employee', 'network')
    list_filter = ('shift', 'network')
    search_fields = ('employee', 'network')
    date_hierarchy = 'date'
