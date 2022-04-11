from django.urls import re_path

from etools.applications.publics.views import (
    AirlinesView,
    BusinessAreasView,
    CurrenciesView,
    DSARegionsView,
    ExpenseTypesView,
    StaticDataView,
)

app_name = 'publics'
urlpatterns = (
    re_path(r'^static_data/$', StaticDataView.as_view({'get': 'list'}), name='static'),
    re_path(r'^static_data/missing/$', StaticDataView.as_view({'get': 'missing'}), name='missing_static'),

    re_path(r'^currencies/$', CurrenciesView.as_view({'get': 'list'}), name='currencies'),
    re_path(r'^currencies/missing/$', CurrenciesView.as_view({'get': 'missing'}), name='missing_currencies'),

    re_path(r'^dsa_regions/$', DSARegionsView.as_view({'get': 'list'}), name='dsa_regions'),
    re_path(r'^dsa_regions/missing/$', DSARegionsView.as_view({'get': 'missing'}), name='missing_dsa_regions'),

    re_path(r'^business_areas/$', BusinessAreasView.as_view({'get': 'list'}), name='business_areas'),
    re_path(r'^business_areas/missing/$', BusinessAreasView.as_view({'get': 'missing'}), name='missing_business_areas'),

    re_path(r'^expense_types/$', ExpenseTypesView.as_view({'get': 'list'}), name='expense_types'),
    re_path(r'^expense_types/missing/$', ExpenseTypesView.as_view({'get': 'missing'}), name='missing_expense_types'),

    re_path(r'^airlines/$', AirlinesView.as_view({'get': 'list'}), name='airlines'),
    re_path(r'^airlines/missing/$', AirlinesView.as_view({'get': 'missing'}), name='missing_airlines'),
)
