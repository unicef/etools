from __future__ import unicode_literals

from django.conf.urls import url

from views import FRsView

urlpatterns = (
    url(r'^frs/$', view=FRsView.as_view(), name='frs'),
)
