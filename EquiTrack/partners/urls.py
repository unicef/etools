from __future__ import absolute_import

from django.conf.urls import url

from partners.views.v1 import PCAPDFView, PortalLoginFailedView

urlpatterns = (
    url(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    url(r'^agreement/(?P<agr>\d+)/pdf', PCAPDFView.as_view(), name='pca_pdf'),
)
