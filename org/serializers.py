from rest_framework import serializers
from .models import Directorate, Department, Office

class DirectorateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Directorate
        fields = ['id', 'name']

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'directorate']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['directorate_name'] = instance.directorate.name
        return data

class OfficeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Office
        fields = ['id', 'name', 'department']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['department_name'] = instance.department.name
        data['directorate_name'] = instance.department.directorate.name
        return data 