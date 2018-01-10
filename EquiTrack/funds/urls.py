from __future__ import unicode_literals

from django.conf.urls import url

from .views import (
    DonorListAPIView,
    FRsView,
    FundsCommitmentHeaderListAPIView,
    FundsCommitmentItemListAPIView,
    FundsReservationHeaderListAPIView,
    FundsReservationItemListAPIView,
    GrantListAPIView,
)

urlpatterns = (
    url(r'^frs/$', view=FRsView.as_view(), name='frs'),
    url(r'^commitment-header/$',
        view=FundsCommitmentHeaderListAPIView.as_view(),
        name='funds-commitment-header'),
    url(r'^commitment-item/$',
        view=FundsCommitmentItemListAPIView.as_view(),
        name='funds-commitment-item'),
    url(r'^reservation-header/$',
        view=FundsReservationHeaderListAPIView.as_view(),
        name='funds-reservation-header'),
    url(r'^reservation-item/$',
        view=FundsReservationItemListAPIView.as_view(),
        name='funds-reservation-item'),
    url(r'^donor/$',
        view=DonorListAPIView.as_view(),
        name='funds-donor'),
    url(r'^grant/$',
        view=GrantListAPIView.as_view(),
        name='funds-grant'),
)
