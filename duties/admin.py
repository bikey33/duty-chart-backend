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
# admin.py
from django.contrib import admin, messages
from django import forms
import pandas as pd
from .models import RosterAssignment
from django.core.exceptions import ValidationError

REQUIRED_COLUMNS = [
    "Start Date", "End Date", "Employee Name", "Start Time",
    "End Time", "Shift", "Phone no.", "Office"
]

class RosterBulkUploadForm(forms.Form):
    file = forms.FileField(help_text=(
        "Upload Excel file with columns: "
        "`Start Date`, `End Date`, `Employee Name`, "
        "`Start Time`, `End Time`, `Shift`, `Phone no.`, `Office`"
    ))

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.core.exceptions import ValidationError
import pandas as pd
from .models import RosterAssignment, Office


# Shared header spec (exact match, in order)
REQUIRED_COLUMNS = [
    "Start Date", "End Date", "Employee Name", "Start Time",
    "End Time", "Shift", "Phone no.", "Office"
]

# duties/admin.py
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils.safestring import mark_safe

import pandas as pd

from .models import RosterAssignment  # adjust if your model import path differs
from .forms import RosterBulkUploadForm

REQUIRED_COLUMNS = [
    "Start Date",
    "End Date",
    "Employee Name",
    "Start Time",
    "End Time",
    "Shift",
    "Phone no.",
    "Office",
]

from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.safestring import mark_safe
import pandas as pd

from .models import RosterAssignment
from .forms import RosterBulkUploadForm
from .serializers import (
    ALLOWED_HEADERS,
    HEADER_MAP,
    RosterAssignmentSerializer,
)

from django.contrib import admin
from .models import RosterAssignment

@admin.register(RosterAssignment)
class RosterAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "start_date",
        "end_date",
        "start_time",
        "end_time",
        "shift",
        "employee_name",
        "office",
        "phone_number",
        "status",  # Optional 
    )
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "bulk-upload/",
                self.admin_site.admin_view(self.bulk_upload_view),
                name="roster_bulk_upload",
            ),
        ]
        return custom + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["bulk_upload_url"] = reverse("admin:roster_bulk_upload")
        extra_context["required_columns"] = ALLOWED_HEADERS
        return super().changelist_view(request, extra_context=extra_context)

    def bulk_upload_view(self, request):
        if request.method == "POST":
            form = RosterBulkUploadForm(request.POST, request.FILES)
            if form.is_valid():
                f = form.cleaned_data["file"]
                try:
                    # Try openpyxl first; fallback for .xls
                    try:
                        df = pd.read_excel(f, engine="openpyxl")
                    except Exception:
                        f.seek(0)
                        df = pd.read_excel(f)
                except Exception as e:
                    messages.error(request, f"Could not read Excel file: {e}")
                    return redirect("admin:duties_rosterassignment_changelist")

                # Normalize headers
                df.columns = [str(c).strip() for c in df.columns]

                # Strict header check
                if list(df.columns) != ALLOWED_HEADERS:
                    missing = [c for c in ALLOWED_HEADERS if c not in df.columns]
                    extra = [c for c in df.columns if c not in ALLOWED_HEADERS]
                    msg_parts = []
                    if missing:
                        msg_parts.append(f"Missing columns: {', '.join(missing)}")
                    if extra:
                        msg_parts.append(f"Unexpected columns: {', '.join(extra)}")
                    messages.error(request, " | ".join(msg_parts))
                    return redirect("admin:duties_rosterassignment_changelist")

                created_count, updated_count, failed_count = 0, 0, 0
                row_errors = []

                # Use only required columns in expected order
                df = df[ALLOWED_HEADERS]

                for idx, row in df.iterrows():
                    try:
                        # Map human-friendly headers to model fields
                        row_dict = {HEADER_MAP[col]: row[col] for col in ALLOWED_HEADERS}

                        # Pass to serializer for validation + saving
                        serializer = RosterAssignmentSerializer(data=row_dict)
                        serializer.is_valid(raise_exception=True)
                        instance = serializer.save()

                        # Track created vs updated
                        if getattr(instance, "_state", None) and not instance._state.adding:
                            updated_count += 1
                        else:
                            created_count += 1

                    except Exception as e:
                        failed_count += 1
                        row_errors.append(f"Row {idx + 2}: {e}")  # Excel rows are 1‑based

                # Messaging
                if created_count:
                    messages.success(request, f"Created {created_count} roster assignment(s).")
                if updated_count:
                    messages.info(request, f"Updated {updated_count} existing roster assignment(s).")
                if failed_count:
                    details = "<br>".join(row_errors[:10])
                    more = f"<br>…and {failed_count - 10} more" if failed_count > 10 else ""
                    messages.error(
                        request,
                        mark_safe(f"Failed {failed_count} row(s).<br>{details}{more}")
                    )

                return redirect("admin:duties_rosterassignment_changelist")
        else:
            form = RosterBulkUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "form": form,
            "title": "Bulk upload roster assignments",
            "required_columns": ALLOWED_HEADERS,
        }
        return render(request, "admin/duties/rosterassignment/bulk_upload.html", context)


#admin.site.register(RosterAssignment, RosterAssignmentAdmin)
