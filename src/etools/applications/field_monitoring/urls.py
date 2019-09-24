from django.conf.urls import include, url

urlpatterns = [
    url(r'^settings/', include('etools.applications.field_monitoring.fm_settings.urls')),
    url(r'^planning/', include('etools.applications.field_monitoring.planning.urls')),
    url(r'^data-collection/', include('etools.applications.field_monitoring.data_collection.urls')),
    url(r'^analyze/', include('etools.applications.field_monitoring.analyze.urls')),
]
