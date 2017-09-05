from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from partners.views.interventions_v3 import InterventionDetailAPIViewV3


urlpatterns = (
    url(r'^interventions/(?P<pk>\d+)/$',
        view=InterventionDetailAPIViewV3.as_view(http_method_names=['get', 'patch']),
        name='intervention-detail'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
