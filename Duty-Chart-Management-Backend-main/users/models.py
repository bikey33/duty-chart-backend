# users/models.py
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from org.models import Directorate, Department, Office  # import your org models

class User(AbstractUser):
    employee_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    image = models.ImageField(upload_to='user_images/', null=True, blank=True)

    office = models.ForeignKey(
        Office,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    directorate = models.ForeignKey(
        Directorate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'employee_id', 'full_name']

    def clean(self):
        super().clean()
        # Ensure department belongs to the selected directorate
        if self.department and self.directorate:
            if self.department.directorate != self.directorate:
                raise ValidationError({
                    "department": "Selected department does not belong to the chosen directorate."
                })
        # Ensure office belongs to the selected department
        if self.office and self.department:
            if self.office.department != self.department:
                raise ValidationError({
                    "office": "Selected office does not belong to the chosen department."
                })

    def __str__(self):
        return self.full_name
