from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from partners.views.prp_v1 import PRPInterventionDetailAPIView, PRPInterventionListAPIView


urlpatterns = (
    url(r'^interventions/$',
        view=PRPInterventionListAPIView.as_view(http_method_names=['get']),
        name='prp-intervention-list'),
    url(r'^interventions/(?P<pk>\d+)/$',
        view=PRPInterventionDetailAPIView.as_view(http_method_names=['get']),
        name='prp-intervention-detail'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
