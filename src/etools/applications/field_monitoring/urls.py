from django.conf.urls import url, include

urlpatterns = [
    url(r'^settings/', include('etools.applications.field_monitoring.fm_settings.urls')),
]
