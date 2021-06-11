from django.urls import include, path, re_path

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.psea import views
from etools.applications.psea.views import PSEAStaticDropdownsListAPIView

root_api = routers.SimpleRouter()

root_api.register(
    r'assessment',
    views.AssessmentViewSet,
    basename='assessment',
)
root_api.register(r'indicator', views.IndicatorViewSet, basename='indicator')

assessor_api = NestedComplexRouter(root_api, r'assessment')
assessor_api.register(r'assessor', views.AssessorViewSet, basename='assessor')
assessor_api.register(r'attachments', views.NFRAttachmentViewSet, basename='nfr-attachments')

action_points_api = NestedComplexRouter(
    root_api,
    r'assessment',
    lookup='psea_assessment',
)
action_points_api.register(
    r'action-points',
    views.AssessmentActionPointViewSet,
    basename='action-points',
)

answer_list_api = NestedComplexRouter(root_api, r'assessment')
answer_list_api.register(
    r'answer',
    views.AnswerListViewSet,
    basename='answer-list',
)
answer_api = NestedComplexRouter(root_api, r'assessment')
answer_api.register(r'indicator', views.AnswerViewSet, basename='answer')

attachments_api = NestedComplexRouter(answer_api, r'indicator')
attachments_api.register(
    r'attachments',
    views.AnswerAttachmentsViewSet,
    basename='answer-attachments',
)

app_name = 'psea'
urlpatterns = [
    re_path(r'^static/$',
            PSEAStaticDropdownsListAPIView.as_view(http_method_names=['get']),
            name='psea-static-list'),
    path('', include(root_api.urls)),
    path('', include(action_points_api.urls)),
    path('', include(assessor_api.urls)),
    path('', include(answer_list_api.urls)),
    path('', include(answer_api.urls)),
    path('', include(attachments_api.urls)),
]
