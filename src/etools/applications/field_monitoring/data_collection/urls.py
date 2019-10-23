from django.conf.urls import include, url

from rest_framework_nested import routers
from unicef_restlib.routers import NestedComplexRouter

from etools.applications.field_monitoring.data_collection import views
from etools.applications.field_monitoring.data_collection.routers import NestedBulkRouter

root_api = routers.SimpleRouter()
root_api.register(r'activities', views.ActivityDataCollectionViewSet, base_name='methods')

activities_api = NestedBulkRouter(root_api, r'activities', lookup='monitoring_activity')
activities_api.register(r'attachments', views.ActivityReportAttachmentsViewSet, base_name='activity-report-attachments')
activities_api.register(r'questions', views.ActivityQuestionsViewSet, base_name='activity-questions')
activities_api.register(r'checklists', views.CheckListsViewSet, base_name='checklists')


checklists_api = NestedBulkRouter(activities_api, r'checklists', lookup='started_checklist')
checklists_api.register(r'overall', views.CheckListOverallFindingsViewSet, base_name='checklist-overall-findings')
checklists_api.register(r'findings', views.CheckListFindingsViewSet, base_name='checklist-findings')

checklist_overall_findings_api = NestedComplexRouter(checklists_api, r'overall', lookup='overall_finding')
checklist_overall_findings_api.register(r'attachments', views.CheckListOverallAttachmentsViewSet,
                                        base_name='checklist-overall-attachments')

app_name = 'field_monitoring_data_collection'
urlpatterns = [
    url(r'^', include(checklist_overall_findings_api.urls)),
    url(r'^', include(checklists_api.urls)),
    url(r'^', include(activities_api.urls)),
    url(r'^', include(root_api.urls)),
]
