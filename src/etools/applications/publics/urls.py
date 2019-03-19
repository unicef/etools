from django.conf.urls import url

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
    url(r'^static_data/$', StaticDataView.as_view({'get': 'list'}), name='static'),
    url(r'^static_data/missing/$', StaticDataView.as_view({'get': 'missing'}), name='missing_static'),

    url(r'^currencies/$', CurrenciesView.as_view({'get': 'list'}), name='currencies'),
    url(r'^currencies/missing/$', CurrenciesView.as_view({'get': 'missing'}), name='missing_currencies'),

    url(r'^dsa_regions/$', DSARegionsView.as_view({'get': 'list'}), name='dsa_regions'),
    url(r'^dsa_regions/missing/$', DSARegionsView.as_view({'get': 'missing'}), name='missing_dsa_regions'),

    url(r'^business_areas/$', BusinessAreasView.as_view({'get': 'list'}), name='business_areas'),
    url(r'^business_areas/missing/$', BusinessAreasView.as_view({'get': 'missing'}), name='missing_business_areas'),

    url(r'^expense_types/$', ExpenseTypesView.as_view({'get': 'list'}), name='expense_types'),
    url(r'^expense_types/missing/$', ExpenseTypesView.as_view({'get': 'missing'}), name='missing_expense_types'),

    url(r'^airlines/$', AirlinesView.as_view({'get': 'list'}), name='airlines'),
    url(r'^airlines/missing/$', AirlinesView.as_view({'get': 'missing'}), name='missing_airlines'),
)
