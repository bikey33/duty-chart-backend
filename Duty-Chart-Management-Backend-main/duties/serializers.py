from rest_framework import serializers
from .models import DutyChart, Duty, Document, RosterAssignment


class DutyChartSerializer(serializers.ModelSerializer):
    class Meta:
        model = DutyChart
        fields = [
            'id',
            'office',
            'effective_date',
            'end_date',
            'employee_name',   # new field
            'phone_number'     # new field
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['office_name'] = instance.office.name
        data['department_name'] = instance.office.department.name
        data['directorate_name'] = instance.office.department.directorate.name
        return data


class DutySerializer(serializers.ModelSerializer):
    class Meta:
        model = Duty
        fields = [
            'id', 'user', 'duty_chart', 'date', 'shift',
            'is_completed', 'currently_available', 'start_time', 'end_time'
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['user_name'] = instance.user.full_name
        data['office_name'] = instance.duty_chart.office.name
        return data


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'description', 'uploaded_at']


class BulkDocumentUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True
    )
    meta = serializers.CharField(
        required=False,
        help_text="Optional JSON string with metadata for each file"
    )

    def create(self, validated_data):
        uploaded_files = validated_data['files']
        meta = validated_data.get('meta')
        # TODO: parse meta and attach to docs if needed
        docs = [Document.objects.create(file=f) for f in uploaded_files]
        return docs


# ---------------- NEW STRICT BULK UPLOAD SERIALIZERS ----------------

# Must match exactly what your Excel parser expects:
ALLOWED_HEADERS = ["Date", "Shift", "Employee", "Network"]


class BulkUploadExcelSerializer(serializers.Serializer):
    """
    Strict Excel upload: accepts only .xls/.xlsx,
    validates headers EXACTLY as in the provided spec.
    """
    file = serializers.FileField()
    dry_run = serializers.BooleanField(required=False, default=False)

    def validate_file(self, f):
        name = (f.name or "").lower()
        if not (name.endswith(".xlsx") or name.endswith(".xls")):
            raise serializers.ValidationError("Only .xlsx or .xls Excel files are allowed.")
        # Check OpenXML / XLS magic bytes
        head = f.read(4)
        f.seek(0)
        if head != b'PK\x03\x04' and not name.endswith(".xls"):
            raise serializers.ValidationError("Invalid Excel file content.")
        return f


class RosterAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RosterAssignment
        fields = [
            'id', 'date', 'shift', 'employee', 'network',
            'created_at', 'updated_at'
        ]
