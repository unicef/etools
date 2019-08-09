from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.psea import views

root_api = routers.SimpleRouter()

root_api.register(
    r'assessment',
    views.AssessmentViewSet,
    basename='assessment',
)
root_api.register(r'assessor', views.AssessorViewSet, basename='assessor')


app_name = 'psea'
urlpatterns = [
    url(r'^', include(root_api.urls)),
]
