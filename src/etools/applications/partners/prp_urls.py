from django.urls import re_path

from rest_framework.urlpatterns import format_suffix_patterns

from etools.applications.partners.views.prp_v1 import PRPInterventionListAPIView, PRPPartnerListAPIView, PRPPDFileView

app_name = 'partners'
urlpatterns = (
    re_path(r'^interventions/$',
            view=PRPInterventionListAPIView.as_view(http_method_names=['get']),
            name='prp-intervention-list'),
    re_path(r'^partners/$',
            view=PRPPartnerListAPIView.as_view(http_method_names=['get']),
            name='prp-partner-list'),
    re_path(r'^get_pd_document/(?P<intervention_pk>\d+)/$',
            view=PRPPDFileView.as_view(http_method_names=['get']),
            name='prp-pd-document-get'),
)
urlpatterns = format_suffix_patterns(urlpatterns, allowed=['json', 'csv'])
