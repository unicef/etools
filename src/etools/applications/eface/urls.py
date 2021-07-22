from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.eface import views

root_api = routers.SimpleRouter()
root_api.register(r'forms', views.EFaceFormsViewSet, basename='forms')

app_name = 'eface_v1'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
