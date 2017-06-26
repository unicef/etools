from __future__ import absolute_import

from django.conf.urls import url, include

from rest_framework_nested import routers

from tpm.views import TPMPartnerViewSet, \
                      TPMVisitViewSet


tpm_partners_api = routers.SimpleRouter()
tpm_partners_api.register(r'partners', TPMPartnerViewSet, base_name='partners')

tpm_visits_api = routers.SimpleRouter()
tpm_visits_api.register(r'visits', TPMVisitViewSet, base_name='visits')


urlpatterns = [
    url(r'^', include(tpm_partners_api.urls)),
    url(r'^', include(tpm_visits_api.urls)),
]
