from __future__ import unicode_literals

from django.conf.urls import patterns, include, url

from publics.views import StaticDataView, WBSGrantFundView, CurrenciesView, DSARegionsView, BusinessAreasView,\
    ExpenseTypesView

urlpatterns = patterns(
    '',
    url(r'^static_data/$', StaticDataView.as_view(), name='static'),
    url(r'^wbs_grants_funds/$', WBSGrantFundView.as_view(), name='wbs_grants_funds'),
    url(r'^currencies/$', CurrenciesView.as_view(), name='currencies'),
    url(r'^dsa_regions/$', DSARegionsView.as_view(), name='dsa_regions'),
    url(r'^business_areas/$', BusinessAreasView.as_view(), name='business_areas'),
    url(r'^expense_types/$', ExpenseTypesView.as_view(), name='expense_types'),
)
