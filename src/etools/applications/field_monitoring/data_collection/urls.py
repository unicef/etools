from django.conf.urls import include, url

from rest_framework_nested import routers

from etools.applications.field_monitoring.data_collection import views
from etools.applications.field_monitoring.data_collection.routers import NestedBulkRouter

root_api = routers.SimpleRouter()
root_api.register(r'activities', views.ActivityDataCollectionViewSet, basename='methods')

activities_api = NestedBulkRouter(root_api, r'activities', lookup='monitoring_activity')
activities_api.register(r'attachments', views.ActivityReportAttachmentsViewSet, basename='activity-report-attachments')
activities_api.register(r'checklists/attachments', views.ActivityChecklistAttachmentsViewSet,
                        basename='activity-checklists-attachments')
activities_api.register(r'questions', views.ActivityQuestionsViewSet, basename='activity-questions')
activities_api.register(r'methods', views.ActivityMethodsViewSet, basename='activity-methods')
activities_api.register(r'checklists', views.ChecklistsViewSet, basename='checklists')
activities_api.register(r'overall-findings', views.ActivityOverallFindingsViewSet,
                        basename='activity-overall-findings')
activities_api.register(r'findings', views.ActivityFindingsViewSet, basename='activity-findings')

checklists_api = NestedBulkRouter(activities_api, r'checklists', lookup='started_checklist')
checklists_api.register(r'overall', views.ChecklistOverallFindingsViewSet, basename='checklist-overall-findings')
checklists_api.register(r'findings', views.ChecklistFindingsViewSet, basename='checklist-findings')

checklist_overall_findings_api = NestedBulkRouter(checklists_api, r'overall')
checklist_overall_findings_api.register(r'attachments', views.ChecklistOverallAttachmentsViewSet,
                                        basename='checklist-overall-attachments')

app_name = 'field_monitoring_data_collection'
urlpatterns = [
    url(r'^', include(checklist_overall_findings_api.urls)),
    url(r'^', include(checklists_api.urls)),
    url(r'^', include(activities_api.urls)),
    url(r'^', include(root_api.urls)),
]
