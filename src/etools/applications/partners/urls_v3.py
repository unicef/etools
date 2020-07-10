from django.conf.urls import url

from etools.applications.partners.views.interventions_v3 import PMPInterventionListAPIView

app_name = 'partners'
urlpatterns = [
    url(
        r'^interventions/$',
        view=PMPInterventionListAPIView.as_view(
            http_method_names=['get', 'post'],
        ),
        name='intervention-list'),
]
