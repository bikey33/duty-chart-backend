from datetime import timedelta
import datetime
import pandas as pd  # ✅ Needed for Excel parsing in roster bulk upload

from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ValidationError

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

from org.models import Office  # ✅ Needed for office lookup in roster bulk upload

from .models import DutyChart, Duty, RosterAssignment, Schedule
from .serializers import (
    DutyChartSerializer,
    DutySerializer,
    BulkDocumentUploadSerializer,
    DocumentSerializer,
    ScheduleSerializer,
    ALLOWED_HEADERS,
    HEADER_MAP,
    RosterAssignmentSerializer,
)


class ScheduleView(viewsets.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer

    @action(detail=False, methods=['post'], url_path='sync-from-roster')
    def sync_from_roster(self, request):
        """
        Pulls all RosterAssignment entries and inserts/updates them into Schedule.
        """
        roster_entries = RosterAssignment.objects.all()
        created_count, updated_count = 0, 0

        for ra in roster_entries:
            obj, created = Schedule.objects.update_or_create(
                employee_name=ra.employee_name,
                office=ra.office,
                start_date=ra.start_date,
                end_date=ra.end_date,
                start_time=ra.start_time,
                end_time=ra.end_time,
                shift=ra.shift,
                defaults={'phone_number': ra.phone_number}
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        return Response({
            "message": "Schedule sync complete",
            "created": created_count,
            "updated": updated_count
        }, status=status.HTTP_200_OK)


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


# ✅ New Roster Bulk Upload View: 

class RosterBulkUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    querryset = RosterAssignment.objects.all()


    @swagger_auto_schema(
        operation_description=(
            "Bulk upload roster assignments from Excel.\n\n"
            f"**Required columns:** {', '.join(ALLOWED_HEADERS)}"
        ),
        manual_parameters=[
            openapi.Parameter(
                name='file',
                in_=openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                description=f'Excel file (.xls/.xlsx) with columns: {", ".join(ALLOWED_HEADERS)}',
                required=True
            )
        ],
        responses={201: 'Roster assignments created/updated successfully'}
    )
    
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({'detail': 'File is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            df = pd.read_excel(file_obj)
        except Exception as e:
            return Response({'detail': f'Invalid Excel file: {e}'}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({'detail': " | ".join(msg_parts)}, status=status.HTTP_400_BAD_REQUEST)

        created_count, updated_count, failed_count = 0, 0, 0
        errors = []

        for idx, row in df.iterrows():
            try:
                row_dict = {HEADER_MAP[col]: row[col] for col in ALLOWED_HEADERS}

                # Resolve office FK if needed
                if isinstance(row_dict.get('office'), str):
                    office_obj = Office.objects.filter(name__iexact=row_dict['office']).first()
                    if not office_obj:
                        failed_count += 1
                        errors.append(f"Row {idx+2}: Office '{row_dict['office']}' not found")
                        continue
                    row_dict['office'] = office_obj

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
                errors.append(f"Row {idx+2}: {e}")

        detail = (
            f"Created: {created_count}, "
            f"Updated: {updated_count}, "
            f"Failed: {failed_count}"
        )

        resp = {'detail': detail}
        if errors:
            resp['errors'] = errors[:10]  # Limit returned errors for safety

        return Response(resp, status=status.HTTP_201_CREATED)
