from django.conf.urls import url

from etools.applications.partners.views.interventions_v3 import PMPInterventionAPIView

app_name = 'partners'
urlpatterns = [
    url(
        r'^interventions/$',
        view=PMPInterventionAPIView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='intervention-list'),
]
