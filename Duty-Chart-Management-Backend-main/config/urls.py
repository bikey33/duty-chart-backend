"""
URL configuration for config project.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path

from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Local imports
from users.views import UserViewSet
from org.views import DirectorateViewSet, DepartmentViewSet, OfficeViewSet
from duties.views import (
    DutyChartViewSet,
    DutyViewSet,
    BulkDocumentUploadView,
    BulkUploadAssignmentsView,   # NEW
    ScheduleView                  # NEW
)

# ------------------------------------------------------------------------------
# Swagger / API documentation setup
# ------------------------------------------------------------------------------
schema_view = get_schema_view(
    openapi.Info(
        title="Duty Chart Management API",
        default_version="v1",
        description=(
            "Interactive API documentation for the Duty Chart Management System.\n"
            "Includes JWT authentication, duty scheduling with shift filters, "
            "bulk upload, bulk duty upsert, and rotation generation endpoints."
        ),
        terms_of_service="https://www.yourapp.com/terms/",
        contact=openapi.Contact(email="contact@yourapp.com"),
        license=openapi.License(name="Your License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# Apply Bearer JWT security globally in Swagger
schema_view.security_definitions = {
    "Bearer": {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header",
        "description": (
            "JWT Authorization header using the Bearer scheme. "
            "Example: 'Bearer <your JWT token>'"
        ),
    }
}
schema_view.security = [{"Bearer": []}]

# ------------------------------------------------------------------------------
# DRF Router registrations
# ------------------------------------------------------------------------------
router = DefaultRouter()

# Users
router.register(r"users", UserViewSet)

# Organization
router.register(r"directorates", DirectorateViewSet)
router.register(r"departments", DepartmentViewSet)
router.register(r"offices", OfficeViewSet)

# Duties
router.register(r"duty-charts", DutyChartViewSet)
router.register(r"duties", DutyViewSet)

# ------------------------------------------------------------------------------
# URL patterns
# ------------------------------------------------------------------------------
urlpatterns = [
    path("admin/", admin.site.urls),

    # API v1 routes
    path("api/v1/", include(router.urls)),
    path(
        "api/v1/bulk-upload/",
        BulkDocumentUploadView.as_view(),
        name="bulk_document_upload",
    ),

    # NEW strict Excel bulk upload for roster assignments
    path(
        "api/v1/roster-bulk-upload/",
        BulkUploadAssignmentsView.as_view(),
        name="roster_bulk_upload",
    ),

    # NEW schedule endpoint
    path(
        "api/v1/schedule/",
        ScheduleView.as_view({'get': 'list'}),
        name="schedule_api",
    ),

    # JWT Authentication
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # Browsable API login (optional, dev use)
    path("api-auth/", include("rest_framework.urls")),

    # Swagger / ReDoc
    re_path(
        r"^swagger(?P<format>\.json|\.yaml)$",
        schema_view.without_ui(cache_timeout=0),
        name="schema-json",
    ),
    path(
        "swagger/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path(
        "redoc/",
        schema_view.with_ui("redoc", cache_timeout=0),
        name="schema-redoc",
    ),
]

# ------------------------------------------------------------------------------
# Static & media in debug mode
# ------------------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    )
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
