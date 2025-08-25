from __future__ import annotations

import datetime
import hashlib
import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def document_upload_to(instance: 'Document', filename: str) -> str:
    return f"documents/{instance.uploaded_at:%Y/%m}/{filename}"


def file_checksum(django_file, chunk_size: int = 1024 * 1024) -> str:
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
    size = models.PositiveIntegerField(help_text="File size in bytes")
    checksum = models.CharField(max_length=64, unique=True, help_text="SHA-256 checksum for deduplication")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="uploaded_documents")
    uploaded_at = models.DateTimeField(default=timezone.now)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self) -> str:
        return f"{Path(self.filename).name} ({self.size} bytes)"

    @classmethod
    def build_from_inmemory(cls, f, user, meta: dict | None = None) -> 'Document':
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

    # New fields
    employee_name = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

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

    def __str__(self):
        return f"{self.user.full_name} - {self.date} ({self.shift})"


class Schedule(models.Model):
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField(db_index=True)
    shift = models.CharField(max_length=10, choices=Duty.SHIFT_CHOICES, db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['user', 'date'], name='unique_schedule_user_date')]
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['shift', 'date']),
        ]
        ordering = ['user_id', 'date']

    def clean(self):
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("end_time must be after start_time.")

    def __str__(self):
        return f"{getattr(self.user, 'full_name', self.user)} - {self.date} ({self.shift})"


# ---------------- NEW MODELS FOR BULK UPLOAD ----------------

class RosterShift(models.Model):
    """Optional: defines allowed shifts for roster assignments (if needed)."""
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class RosterAssignment(models.Model):
    date = models.DateField(db_index=True)
    shift = models.CharField(max_length=50, db_index=True)
    employee = models.CharField(max_length=255, db_index=True)
    network = models.CharField(max_length=255, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['date', 'shift', 'employee']
        indexes = [
            models.Index(fields=['date', 'shift']),
            models.Index(fields=['employee']),
        ]
        ordering = ['date', 'shift', 'employee']

    def __str__(self):
        return f"{self.date} - {self.shift} - {self.employee}"
