from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.utils import timezone


def document_upload_to(instance: 'Document', filename: str) -> str:
    """Dynamic upload path for documents based on upload date."""
    return f"documents/{instance.uploaded_at:%Y/%m}/{filename}"


def file_checksum(django_file, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 checksum for a file in chunks to avoid memory overload."""
    pos = django_file.tell()
    django_file.seek(0)
    h = hashlib.sha256()
    for chunk in iter(lambda: django_file.read(chunk_size), b''):
        h.update(chunk)
    django_file.seek(pos)
    return h.hexdigest()

class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(
        help_text="File size in bytes",
        # ✅ Validation: Ensure file size > 0 and <= MAX_UPLOAD_SIZE (default 50MB if not set)
        validators=[MinValueValidator(1), MaxValueValidator(getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024))]
    )
    checksum = models.CharField(max_length=64, unique=True, help_text="SHA-256 checksum for deduplication")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_documents")
    uploaded_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self) -> str:
        return f"{Path(self.filename).name} ({self.size} bytes)"

    def clean(self):
        super().clean()
        # ✅ Validation: Auto-generate checksum if missing (ensures deduplication works even outside serializers)
        if self.file and not self.checksum:
            self.checksum = file_checksum(self.file)

    @classmethod
    def build_from_inmemory(cls, f, user, meta: dict | None = None) -> 'Document':
        """Factory method for creating Document from an in-memory file."""
        checksum = file_checksum(f)
        f.seek(0)
        description = str(meta.get('description', '')).strip() if meta else ''
        return cls(
            file=f,
            filename=getattr(f, 'name', 'uploaded.bin'),
            size=getattr(f, 'size', f.size if hasattr(f, 'size') else 0),
            content_type=getattr(f, 'content_type', ''),
            checksum=checksum,
            description=description,
            uploaded_by=user,
        )


class DutyChart(models.Model):
    office = models.ForeignKey('org.Office', on_delete=models.CASCADE, related_name='duty_charts')
    effective_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    employee_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(
        max_length=14,
        blank=True,
        null=True,
        # ✅ Validation: Must start with +977 and have exactly 10 digits after it (Nepal format)
        validators=[RegexValidator(
            r'^\+977\d{10}$',
            'Enter a valid Nepal phone number starting with +977 followed by exactly 10 digits.'
        )]
    )

    def clean(self):
        super().clean()
        # ✅ Validation: End date must be after effective date
        if self.end_date and self.end_date < self.effective_date:
            raise ValidationError({'end_date': "End date must be after effective date."})

    def __str__(self):
        return f"{self.office.name} - {self.effective_date} ({self.employee_name or 'No Name'})"


class Duty(models.Model):
    SHIFT_CHOICES = [
        ('morning', 'Morning'),
        ('day', 'Day'),
        ('night', 'Night'),
    ]

    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='duties')
    duty_chart = models.ForeignKey(DutyChart, on_delete=models.CASCADE, related_name='duties')
    date = models.DateField()
    shift = models.CharField(max_length=10, choices=SHIFT_CHOICES)
    is_completed = models.BooleanField(default=False)
    currently_available = models.BooleanField(default=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ['duty_chart', 'date', 'shift']

    def clean(self):
        super().clean()
        # ✅ Validation: Start time must be before end time
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({'end_time': "End time must be after start time."})
        # ✅ Validation: Duty date must be within the duty chart's effective period
        if self.date < self.duty_chart.effective_date or (
            self.duty_chart.end_date and self.date > self.duty_chart.end_date
        ):
            raise ValidationError({'date': "Duty date must be within the duty chart's effective period."})

    def __str__(self):
        return f"{self.user.full_name} - {self.date} ({self.shift})"


# duties/models.py
from django.db import models

from django.db import models

# duties/models.py
from django.db import models

from django.conf import settings

from django.conf import settings
from django.db import models


from django.conf import settings
from django.db import models

from django.utils import timezone

date = models.DateField(default=timezone.now)



class Schedule(models.Model):
    # Keep the link to the actual user account
   # user = models.ForeignKey(
       # settings.AUTH_USER_MODEL,
        #on_delete=models.CASCADE,
        #related_name="schedules"
    #)

    # Match RosterAssignment's required/optional fields
    status = models.CharField(max_length=20, default="pending")

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)  # ✅ can be empty

    start_time = models.TimeField(default=datetime.time(9, 0))
    end_time = models.TimeField(default=datetime.time(17, 0))

    shift = models.CharField(max_length=20)

    employee_name = models.CharField(max_length=255, default="__Missing__")
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    # Keep office as CharField to match RosterAssignment exactly
    office = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'employee_name']
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'employee_name', 'office',
                    'start_date', 'end_date',
                    'start_time', 'end_time', 'shift'
                ],
                name='uniq_schedule_emp_office_span_times_shift',
            ),
        ]

    def __str__(self):
        date_str = self.start_date.strftime("%Y-%m-%d") if self.start_date else "No date"
        office_str = self.office or "No office"
        shift_str = (self.shift.strip().title() if self.shift else "No shift")
        return f"{self.employee_name} – {date_str} {shift_str} @ {office_str}"

    def clean(self):
        """
        Centralized validation – mirrors RosterAssignment's rules.
        """
        errors = {}

        # Date logic
        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors['end_date'] = "End date cannot be before start date."

        # Time logic (same-day)
        if (
            self.start_date
            and self.end_date
            and self.start_date == self.end_date
            and self.end_time
            and self.start_time
            and self.end_time <= self.start_time
        ):
            errors['end_time'] = "End time must be after start time on the same day."

        # Phone number validation
        if self.phone_number:
            nepal_pattern = r'^\+977\d{10}$'
            if not re.match(nepal_pattern, self.phone_number):
                self.phone_number = None

        if errors:
            raise ValidationError(errors)

    @classmethod
    def from_roster_assignment(cls, roster):
        """
        Create a Schedule instance from a RosterAssignment object.
        """
        return cls(
            user=getattr(roster, 'user', None),  # if roster has a user FK
            status=roster.status,
            start_date=roster.start_date,
            end_date=roster.end_date,
            start_time=roster.start_time,
            end_time=roster.end_time,
            shift=roster.shift,
            employee_name=roster.employee_name,
            phone_number=roster.phone_number,
            office=roster.office
        )


class RosterShift(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


from org.models import Office

import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.exceptions import ValidationError

REQUIRED_COLUMNS = [
    "Start Date", "End Date", "Employee Name", "Start Time",
    "End Time", "Shift", "Phone no.", "Office"
]

from django.db import models
from django.core.exceptions import ValidationError

import re
import datetime


class RosterAssignment(models.Model):
    status = models.CharField(max_length=20, default="pending")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)  # ✅ can be empty

    start_time = models.TimeField(default=datetime.time(9, 0))
    end_time = models.TimeField(default=datetime.time(17, 0))
    shift = models.CharField(max_length=20)
    employee_name = models.CharField(max_length=255, default="__Missing__")
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    office = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_date', 'employee_name']
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'employee_name', 'office',
                    'start_date', 'end_date',
                    'start_time', 'end_time', 'shift'
                ],
                name='uniq_rosterassignment_emp_office_span_times_shift',
            ),
        ]

        """
       
        Descriptive label for admin drop‑downs, relations, and logs.
        Example: "John Doe – 2025-08-27 Morning @ Kathmandu Office"
        """
    def __str__(self):
        date_str = self.start_date.strftime("%Y-%m-%d") if self.start_date else "No date"
        office_str = self.office or "No office"
        shift_str = (self.shift.strip().title() if self.shift else "No shift")
        return f"{self.employee_name} – {date_str} {shift_str} @ {office_str}"

       


    def clean(self):
        """
        Centralized validation – keeps admin, API, and bulk uploads consistent.
        """
        errors = {}

        # Date logic
        if self.end_date and self.start_date and self.end_date < self.start_date:
            errors['end_date'] = "End date cannot be before start date."

        # Time logic (same-day)
        if (
            self.start_date
            and self.end_date
            and self.start_date == self.end_date
            and self.end_time
            and self.start_time
            and self.end_time <= self.start_time
        ):
            errors['end_time'] = "End time must be after start time on the same day."

        # Phone number validation
        if self.phone_number:
            nepal_pattern = r'^\+977\d{10}$'
            if not re.match(nepal_pattern, self.phone_number):
                # Using None instead of "__Missing__" to avoid polluting UI/exports
                self.phone_number = None

        if errors:
            raise ValidationError(errors)
