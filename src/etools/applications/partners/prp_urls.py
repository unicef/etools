from django.conf.urls import url

from rest_framework.urlpatterns import format_suffix_patterns

from etools.applications.partners.views.prp_v1 import PRPInterventionListAPIView

app_name = 'partners'
urlpatterns = (
    url(r'^interventions/$',
        view=PRPInterventionListAPIView.as_view(http_method_names=['get']),
        name='prp-intervention-list'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
