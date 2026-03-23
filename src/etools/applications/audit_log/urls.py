from django.urls import include, path

from rest_framework.routers import DefaultRouter

from etools.applications.audit_log.views import AuditLogEntryViewSet

app_name = 'audit_log'

router = DefaultRouter()
router.register(r'entries', AuditLogEntryViewSet, basename='audit-log-entries')

urlpatterns = [
    path('', include(router.urls)),
]
