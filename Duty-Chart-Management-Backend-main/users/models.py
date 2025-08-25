from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    employee_id = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    image = models.ImageField(upload_to='user_images/', null=True, blank=True)
    office = models.ForeignKey('org.Office', on_delete=models.SET_NULL, null=True, related_name='users')
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'employee_id', 'full_name']

    def __str__(self):
        return self.full_name
