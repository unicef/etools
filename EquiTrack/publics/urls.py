from __future__ import unicode_literals

from django.conf.urls import url

from publics.views import (
    AirlinesView, BusinessAreasView, CurrenciesView, DSARegionsView, ExpenseTypesView, StaticDataView, WBSGrantFundView)

urlpatterns = (
    url(r'^static_data/$', StaticDataView.as_view({'get': 'list'}), name='static'),
    url(r'^static_data/missing/$', StaticDataView.as_view({'get': 'missing'}), name='missing_static'),

    url(r'^wbs_grants_funds/$', WBSGrantFundView.as_view({'get': 'list'}), name='wbs_grants_funds'),
    url(r'^wbs_grants_funds/missing/$', WBSGrantFundView.as_view({'get': 'missing'}), name='missing_wbs_grants_funds'),

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
