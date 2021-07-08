from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.eface import views

root_api = routers.SimpleRouter()
root_api.register(r'forms', views.EFaceFormsViewSet, basename='forms')

forms_api = NestedComplexRouter(root_api, r'forms', lookup='form')
forms_api.register(r'activities', views.EFaceFormActivitiesViewSet, basename='form_activities')

app_name = 'eface_v1'
urlpatterns = [
    url(r'^', include(forms_api.urls)),
    url(r'^', include(root_api.urls)),
]
