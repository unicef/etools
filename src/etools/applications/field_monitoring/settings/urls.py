from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.settings.views import (
    CheckListCategoriesViewSet, CheckListViewSet, CPOutputConfigsViewSet, CPOutputsViewSet, LocationSitesViewSet,
    MethodsViewSet, MethodTypesViewSet, PlannedCheckListItemViewSet,)

root_api = routers.SimpleRouter()
root_api.register(r'methods/types', MethodTypesViewSet, base_name='method-types')
root_api.register(r'methods', MethodsViewSet, base_name='methods')
root_api.register(r'sites', LocationSitesViewSet, base_name='sites')
root_api.register(r'cp-outputs/configs', CPOutputConfigsViewSet, base_name='cp_output-configs')
root_api.register(r'cp-outputs', CPOutputsViewSet, base_name='cp_outputs')
root_api.register(r'checklist/categories', CheckListCategoriesViewSet, base_name='checklist-categories')
root_api.register(r'checklist', CheckListViewSet, base_name='checklist-items')

cp_outputs_configs_api = NestedComplexRouter(root_api, r'cp-outputs/configs', lookup='cp_output_config')
cp_outputs_configs_api.register(r'planned-checklist', PlannedCheckListItemViewSet, base_name='planned-checklist-items')

app_name = 'field_monitoring_settings'
urlpatterns = [
    url(r'^', include(cp_outputs_configs_api.urls)),
    url(r'^', include(root_api.urls)),
]
