from django.conf.urls import include, url
from rest_framework import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.permissions_simplified.tests.views import ParentViewSet, NotConfiguredParentViewSet, \
    ChildViewSet, ModelWithFSMFieldViewSet

root_api = routers.SimpleRouter()
root_api.register(r'wrong-parents', NotConfiguredParentViewSet, base_name='wrong-parents')
root_api.register(r'parents', ParentViewSet, base_name='parents')
root_api.register(r'fsm-model', ModelWithFSMFieldViewSet, base_name='fsm-model')

parent_api = NestedComplexRouter(root_api, r'parents', lookup='parent')
parent_api.register('children', ChildViewSet, base_name='children')


urlpatterns = [
    url(r'^', include(parent_api.urls)),
    url(r'^', include(root_api.urls)),
]
