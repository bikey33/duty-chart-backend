from rest_framework import serializers
from .models import DutyChart, Duty, Document, RosterAssignment, Office


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

    # ✅ CHANGE: Call full_clean() so model-level validations (Nepal phone number format, end_date > effective_date) run
    def create(self, validated_data):
        instance = DutyChart(**validated_data)
        instance.full_clean()  # runs model.clean() + field validators
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()  # re-validate on update
        instance.save()
        return instance

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

    # ✅ CHANGE: Call full_clean() so model-level validations (start_time < end_time, date within duty_chart period) run
    def create(self, validated_data):
        instance = Duty(**validated_data)
        instance.full_clean()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['user_name'] = instance.user.full_name
        data['office_name'] = instance.duty_chart.office.name
        return data


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['id', 'file', 'description', 'uploaded_at']

    # ✅ CHANGE: Call full_clean() so model-level validations (file size limit, checksum generation) run
    def create(self, validated_data):
        instance = Document(**validated_data)
        instance.full_clean()
        instance.save()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance


class BulkDocumentUploadSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True
    )
    meta = serializers.CharField(
        required=False,
        help_text="Optional JSON string with metadata for each file"
    )

    # ✅ CHANGE: Validate each Document instance with full_clean() before saving
    def create(self, validated_data):
        uploaded_files = validated_data['files']
        meta = validated_data.get('meta')
        docs = []
        for f in uploaded_files:
            doc = Document(file=f)
            doc.full_clean()  # enforce size/checksum rules
            doc.save()
            docs.append(doc)
        return docs


# ---------------- NEW STRICT BULK UPLOAD SERIALIZERS ----------------

# Must match exactly what your Excel parser expects:
# Must match exactly what your roster bulk upload Excel template expects:
ALLOWED_HEADERS = [
    "Start Date",
    "End Date",
    "Start Time",
    "End Time",
    "Shift",
    "Employee Name",
    "Office",
    "Phone Number"  # keep/remove depending on your template
]

# Map from Excel column names -> RosterAssignment model field names
HEADER_MAP = {
    "Start Date": "start_date",
    "End Date": "end_date",
    "Start Time": "start_time",
    "End Time": "end_time",
    "Shift": "shift",
    "Employee Name": "employee_name",
    "Office": "office",
    "Phone Number": "phone_number",
}

from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from django.core.exceptions import ValidationError

from .models import RosterAssignment, Office, Schedule


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
    office_name = serializers.CharField(source='office.name', read_only=True)

    class Meta:
        model = RosterAssignment
        fields = [
            'id',
            'start_date',
            'end_date',
            'start_time',
            'end_time',
            'shift',
            'employee_name',
            'office',
            'office_name',
            'phone_number',
            'created_at',
            'updated_at',
            '__all__'
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=RosterAssignment.objects.all(),
                fields=[
                    'employee_name', 'office',
                    'start_date', 'end_date',
                    'start_time', 'end_time', 'shift'
                ],
                message='An identical roster assignment already exists.'
            )
        ]

    def validate_office(self, value):
        """
        Allow office to be provided as either an ID or a case-insensitive name.
        """
        if isinstance(value, str):
            office_obj = Office.objects.filter(name__iexact=value).first()
            if not office_obj:
                raise serializers.ValidationError(
                    f"Office '{value}' not found."
                )
            return office_obj
        return value

    def create(self, validated_data):
        validated_data = self._normalize(validated_data)
        instance, created = RosterAssignment.objects.update_or_create(
            employee_name=validated_data['employee_name'],
            office=validated_data['office'],
            start_date=validated_data['start_date'],
            end_date=validated_data['end_date'],
            start_time=validated_data['start_time'],
            end_time=validated_data['end_time'],
            shift=validated_data['shift'],
            defaults={k: v for k, v in validated_data.items()
                      if k not in ['employee_name', 'office', 'start_date',
                                   'end_date', 'start_time', 'end_time', 'shift']}
        )
        instance.full_clean()
        return instance

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.full_clean()
        instance.save()
        return instance

    def _normalize(self, data):
        """
        Optional normalization to enforce consistent casing/spacing
        before uniqueness checks.
        """
        if 'employee_name' in data and isinstance(data['employee_name'], str):
            data['employee_name'] = data['employee_name'].strip()
        return data


# duties/serializers.py
from rest_framework import serializers
from .models import Schedule

from rest_framework import serializers
from .models import Schedule

from rest_framework import serializers
from .models import Schedule
from duties.models import RosterAssignment  # adjust import if needed


from rest_framework import serializers
from .models import Schedule
from duties.models import RosterAssignment  # adjust import if needed


from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from org.models import Office
from .models import Schedule

class ScheduleSerializer(serializers.ModelSerializer):
    office_name = serializers.CharField(source='office.name', read_only=True)

    class Meta:
        model = Schedule
        fields = [
            'start_date', 'end_date', 'start_time', 'end_time',
            'shift', 'employee_name', 'office', 'office_name',
            'phone_number', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
        validators = [
            UniqueTogetherValidator(
                queryset=Schedule.objects.all(),
                fields=[
                    'employee_name', 'office', 'start_date', 'end_date',
                    'start_time', 'end_time', 'shift'
                ],
                message='An identical schedule already exists.'
            )
        ]
