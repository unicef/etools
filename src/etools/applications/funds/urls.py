from django.urls import re_path

from etools.applications.funds.views import (
    DonorListAPIView,
    FRsView,
    FundsCommitmentHeaderListAPIView,
    FundsCommitmentItemListAPIView,
    FundsReservationHeaderListAPIView,
    FundsReservationItemListAPIView,
    GrantListAPIView,
)
from etools.applications.funds.views_ext import GPDExternalReservationAPIView, PDExternalReservationAPIView

app_name = 'funds'
urlpatterns = (
    re_path(r'^frs/$', view=FRsView.as_view(), name='frs'),
    re_path(r'^commitment-header/$',
            view=FundsCommitmentHeaderListAPIView.as_view(),
            name='funds-commitment-header'),
    re_path(r'^commitment-item/$',
            view=FundsCommitmentItemListAPIView.as_view(),
            name='funds-commitment-item'),
    re_path(r'^reservation-header/$',
            view=FundsReservationHeaderListAPIView.as_view(),
            name='funds-reservation-header'),
    re_path(r'^reservation-item/$',
            view=FundsReservationItemListAPIView.as_view(),
            name='funds-reservation-item'),
    re_path(r'^donor/$',
            view=DonorListAPIView.as_view(),
            name='funds-donor'),
    re_path(r'^grant/$',
            view=GrantListAPIView.as_view(),
            name='funds-grant'),
    re_path(r'^external-reservation/$',
            view=PDExternalReservationAPIView.as_view(),
            name='pd-external-funds-reservation'),
    re_path(r'^gpd-external-reservation-gpd/$',
            view=GPDExternalReservationAPIView.as_view(),
            name='gpd-external-funds-reservation'),
)
