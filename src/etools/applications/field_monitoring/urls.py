from django.urls import include, re_path

urlpatterns = [
    re_path(r'^settings/', include('etools.applications.field_monitoring.fm_settings.urls')),
    re_path(r'^planning/', include('etools.applications.field_monitoring.planning.urls')),
    re_path(r'^data-collection/', include('etools.applications.field_monitoring.data_collection.urls')),
    re_path(r'^analyze/', include('etools.applications.field_monitoring.analyze.urls')),
]
