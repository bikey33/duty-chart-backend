from django.contrib import admin
from .models import Directorate, Department, Office

@admin.register(Directorate)
class DirectorateAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'directorate')
    list_filter = ('directorate',)
    search_fields = ('name', 'directorate__name')
    autocomplete_fields = ['directorate']

@admin.register(Office)
class OfficeAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'get_directorate')
    list_filter = ('department__directorate', 'department')
    search_fields = ('name', 'department__name', 'department__directorate__name')
    autocomplete_fields = ['department']

    def get_directorate(self, obj):
        return obj.department.directorate.name
    get_directorate.short_description = 'Directorate'
    get_directorate.admin_order_field = 'department__directorate__name'

    
