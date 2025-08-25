from django.shortcuts import render
from datetime import timedelta
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import DutyChart, Duty
from .serializers import DutyChartSerializer, DutySerializer, BulkDocumentUploadSerializer, DocumentSerializer

# NEW imports for bulk roster upload & schedule
import pandas as pd
import datetime
from django.db import transaction
from .models import RosterAssignment, RosterShift
from .serializers import BulkUploadExcelSerializer, ALLOWED_HEADERS, RosterAssignmentSerializer


class BulkDocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Upload multiple documents in one request.",
        manual_parameters=[
            openapi.Parameter(
                name='files',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description='Multiple files to upload',
                required=True
            ),
            openapi.Parameter(
                name='meta',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description='Optional JSON mapping filenames to metadata (e.g. description)',
                required=False
            ),
        ],
        responses={201: DocumentSerializer(many=True)}
    )
    def post(self, request, *args, **kwargs):
        serializer = BulkDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        documents = serializer.save()
        return Response(
            DocumentSerializer(documents, many=True).data,
            status=status.HTTP_201_CREATED
        )


class DutyChartViewSet(viewsets.ModelViewSet):
    queryset = DutyChart.objects.all()
    serializer_class = DutyChartSerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List duty charts, optionally filtered by office ID.",
        manual_parameters=[
            openapi.Parameter(
                'office', openapi.IN_QUERY,
                description="Filter by office ID",
                type=openapi.TYPE_INTEGER
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = DutyChart.objects.all()
        office_id = self.request.query_params.get('office', None)
        if office_id:
            queryset = queryset.filter(office_id=office_id)
        return queryset


class DutyViewSet(viewsets.ModelViewSet):
    queryset = Duty.objects.all()
    serializer_class = DutySerializer
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="List duties, optionally filtered by chart, user, date, and/or shift.",
        manual_parameters=[
            openapi.Parameter('duty_chart', openapi.IN_QUERY, description="Filter by Duty Chart ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('user', openapi.IN_QUERY, description="Filter by User ID", type=openapi.TYPE_INTEGER),
            openapi.Parameter('date', openapi.IN_QUERY, description="Filter by date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('shift', openapi.IN_QUERY, description="Filter by shift: morning, day, night", type=openapi.TYPE_STRING),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Duty.objects.all()
        chart_id = self.request.query_params.get('duty_chart', None)
        user_id = self.request.query_params.get('user', None)
        date = self.request.query_params.get('date', None)
        shift = self.request.query_params.get('shift', None)

        if chart_id:
            queryset = queryset.filter(duty_chart_id=chart_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if date:
            queryset = queryset.filter(date=date)
        if shift:
            queryset = queryset.filter(shift=shift)

        return queryset

    @swagger_auto_schema(
        method='post',
        operation_description="Bulk create or update duties with shift values.",
        request_body=openapi.Schema(
            type=openapi.TYPE_ARRAY,
            items=openapi.Items(type=openapi.TYPE_OBJECT, properties={
                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                'duty_chart': openapi.Schema(type=openapi.TYPE_INTEGER),
                'date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'shift': openapi.Schema(type=openapi.TYPE_STRING, description="morning/day/night"),
                'is_completed': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'currently_available': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                'start_time': openapi.Schema(type=openapi.TYPE_STRING, format="time"),
                'end_time': openapi.Schema(type=openapi.TYPE_STRING, format="time"),
            })
        )
    )
    @action(detail=False, methods=['post'], url_path='bulk-upsert')
    def bulk_upsert(self, request):
        """Create/update multiple Duty entries at once."""
        data = request.data
        created, updated = 0, 0
        for item in data:
            obj, was_created = Duty.objects.update_or_create(
                user_id=item['user'],
                duty_chart_id=item['duty_chart'],
                date=item['date'],
                defaults={
                    'shift': item['shift'],
                    'is_completed': item.get('is_completed', False),
                    'currently_available': item.get('currently_available', True),
                    'start_time': item['start_time'],
                    'end_time': item['end_time'],
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1
        return Response({'created': created, 'updated': updated}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        method='post',
        operation_description="Generate a rotation of duties for a user in a date range, cycling shifts.",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                'duty_chart': openapi.Schema(type=openapi.TYPE_INTEGER),
                'start_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'end_date': openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
                'pattern': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description="List of shifts in order to rotate"),
                'overwrite': openapi.Schema(type=openapi.TYPE_BOOLEAN, default=False),
            },
            required=['user', 'duty_chart', 'start_date', 'end_date', 'pattern']
        )
    )
    @action(detail=False, methods=['post'], url_path='generate-rotation')
    def generate_rotation(self, request):
        """Auto-create Duty entries for a user/date range with repeating shifts."""
        user_id = request.data['user']
        chart_id = request.data['duty_chart']
        start_date = request.data['start_date']
        end_date = request.data['end_date']
        pattern = request.data['pattern']
        overwrite = request.data.get('overwrite', False)

        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)
        if end < start:
            return Response({'detail': 'end_date must be after or equal to start_date'}, status=status.HTTP_400_BAD_REQUEST)

        days = (end - start).days + 1
        created, updated, skipped = 0, 0, 0

        for i in range(days):
            duty_date = start + timedelta(days=i)
            shift_val = pattern[i % len(pattern)]
            if overwrite:
                obj, was_created = Duty.objects.update_or_create(
                    user_id=user_id,
                    duty_chart_id=chart_id,
                    date=duty_date,
                    defaults={'shift': shift_val}
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            else:
                obj, was_created = Duty.objects.get_or_create(
                    user_id=user_id,
                    duty_chart_id=chart_id,
                    date=duty_date,
                    defaults={'shift': shift_val}
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        return Response({'created': created, 'updated': updated, 'skipped': skipped}, status=status.HTTP_200_OK)


# ------------------- NEW BULK UPLOAD ASSIGNMENTS & SCHEDULE ENDPOINTS -------------------
# ------------------- NEW BULK UPLOAD ASSIGNMENTS & SCHEDULE ENDPOINTS -------------------

class BulkUploadAssignmentsView(APIView):
    """
    Strict Excel bulk upload for roster assignments.
    Expected columns exactly: ALLOWED_HEADERS (e.g., ['Date', 'Shift', 'Employee', 'Network'])
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="Strict Excel bulk upload for roster assignments.",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, description="Excel .xlsx/.xls file", type=openapi.TYPE_FILE, required=True),
            openapi.Parameter('dry_run', openapi.IN_QUERY, description="Validate without saving", type=openapi.TYPE_BOOLEAN),
        ],
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'created': openapi.Schema(type=openapi.TYPE_INTEGER),
                'updated': openapi.Schema(type=openapi.TYPE_INTEGER),
                'errors': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_OBJECT)),
                'dry_run': openapi.Schema(type=openapi.TYPE_BOOLEAN),
            }
        )}
    )
    def post(self, request):
        # Validate incoming form using your serializer contract
        serializer = BulkUploadExcelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_obj = serializer.validated_data['file']
        dry_run = bool(serializer.validated_data.get('dry_run', False))

        # Parse Excel
        try:
            df = pd.read_excel(file_obj, dtype=str)
        except Exception as e:
            return Response({'error': f'Failed to read Excel file: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        # Normalize and validate headers strictly
        normalized_cols = [str(c).strip() for c in list(df.columns)]
        df.columns = normalized_cols

        missing = [c for c in ALLOWED_HEADERS if c not in normalized_cols]
        unexpected = [c for c in normalized_cols if c not in ALLOWED_HEADERS]
        if missing or unexpected:
            return Response({
                'error': 'Header mismatch',
                'missing': missing,
                'unexpected': unexpected,
                'expected_exact': ALLOWED_HEADERS
            }, status=status.HTTP_400_BAD_REQUEST)

        created_count, updated_count = 0, 0
        errors = []

        # Use a transaction; in dry_run we skip writes but still validate rows
        with transaction.atomic():
            for idx, row in df.iterrows():
                row_num = int(idx) + 2  # account for header row
                try:
                    date_val = pd.to_datetime(row['Date']).date()
                    shift_val = (row['Shift'] or '').strip()
                    emp_val = (row['Employee'] or '').strip()
                    net_val = (row['Network'] or '').strip()

                    if not date_val or not shift_val or not emp_val or not net_val:
                        raise ValueError('One or more required fields are empty')

                    if dry_run:
                        # Determine would-create / would-update without writing
                        exists = RosterAssignment.objects.filter(
                            date=date_val, shift=shift_val, employee=emp_val
                        ).exists()
                        if exists:
                            updated_count += 1
                        else:
                            created_count += 1
                        continue

                    obj, created = RosterAssignment.objects.update_or_create(
                        date=date_val,
                        shift=shift_val,
                        employee=emp_val,
                        defaults={'network': net_val}
                    )
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except Exception as e:
                    errors.append({'row': row_num, 'error': str(e)})

        return Response({
            'created': created_count,
            'updated': updated_count,
            'errors': errors,
            'dry_run': dry_run
        }, status=status.HTTP_200_OK)


class ScheduleView(viewsets.ReadOnlyModelViewSet):
    """
    Read-only schedule API for RosterAssignment.
    Filters: start_date, end_date, shift, employee
    """
    queryset = RosterAssignment.objects.all().order_by('date', 'shift', 'employee')
    serializer_class = RosterAssignmentSerializer  # ensure this is imported at top
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        operation_description="Fetch schedule filtered by date range, shift, or employee.",
        manual_parameters=[
            openapi.Parameter('start_date', openapi.IN_QUERY, description="Filter from date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="Filter to date (YYYY-MM-DD)", type=openapi.TYPE_STRING, format=openapi.FORMAT_DATE),
            openapi.Parameter('shift', openapi.IN_QUERY, description="Exact shift value", type=openapi.TYPE_STRING),
            openapi.Parameter('employee', openapi.IN_QUERY, description="Partial match on employee name", type=openapi.TYPE_STRING),
            openapi.Parameter('network', openapi.IN_QUERY, description="Exact network match", type=openapi.TYPE_STRING),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        start = self.request.query_params.get('start_date')
        end = self.request.query_params.get('end_date')
        shift = self.request.query_params.get('shift')
        employee = self.request.query_params.get('employee')
        network = self.request.query_params.get('network')

        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        if shift:
            qs = qs.filter(shift__iexact=shift)
        if employee:
            qs = qs.filter(employee__icontains=employee)
        if network:
            qs = qs.filter(network__iexact=network)
        return qs
