from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.psea.views import AssessmentViewSet

root_api = routers.SimpleRouter()

root_api.register(r'assessment', AssessmentViewSet, basename='assessment')


app_name = 'psea'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
