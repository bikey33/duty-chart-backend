from django.shortcuts import render
from rest_framework import viewsets, permissions
from .models import Directorate, Department, Office
from .serializers import DirectorateSerializer, DepartmentSerializer, OfficeSerializer

# Create your views here.

class DirectorateViewSet(viewsets.ModelViewSet):
    queryset = Directorate.objects.all()
    serializer_class = DirectorateSerializer
    permission_classes = [permissions.IsAuthenticated]

class DepartmentViewSet(viewsets.ModelViewSet):
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Department.objects.all()
        directorate_id = self.request.query_params.get('directorate', None)
        if directorate_id:
            queryset = queryset.filter(directorate_id=directorate_id)
        return queryset

class OfficeViewSet(viewsets.ModelViewSet):
    queryset = Office.objects.all()
    serializer_class = OfficeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Office.objects.all()
        department_id = self.request.query_params.get('department', None)
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset
