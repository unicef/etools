from django.urls import re_path

from .views.v1 import PCAPDFView, PortalLoginFailedView

urlpatterns = (
    re_path(r'^accounts/loginfailed/(?P<email>.+)/$', PortalLoginFailedView.as_view(), name='sociallogin_notamember'),
    re_path(r'^agreement/(?P<agr>\d+)/pdf', PCAPDFView.as_view(), name='pca_pdf'),
)
