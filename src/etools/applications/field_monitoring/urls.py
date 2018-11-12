from django.conf.urls import url, include

urlpatterns = [
    url(r'^settings/', include('etools.applications.field_monitoring.settings.urls')),
    url(r'^planning/', include('etools.applications.field_monitoring.planning.urls')),
    url(r'^visits/', include('etools.applications.field_monitoring.visits.urls')),
]
