from django.urls import path

from etools.applications.ecn.views import ECNSyncView

app_name = 'ecn_v1'

urlpatterns = [
    path(
        'interventions/import/ecn/',
        view=ECNSyncView.as_view(
            http_method_names=['post'],
        ),
        name='intervention-import-ecn',
    ),
]
