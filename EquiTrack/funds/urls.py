from __future__ import unicode_literals

from django.conf.urls import url

from views import (
    FRsView,
    FundsReservationHeaderListAPIView,
    FundsReservationItemListAPIView
)

urlpatterns = (
    url(r'^frs/$', view=FRsView.as_view(), name='frs'),
    url(r'^reservation-header/$',
        view=FundsReservationHeaderListAPIView.as_view(),
        name='funds-reservation-header'),
    url(r'^reservation-item/$',
        view=FundsReservationItemListAPIView.as_view(),
        name='funds-reservation-item'),
)
