
from django.conf.urls import url

from snapshot.views import ActivityListView

urlpatterns = (
    url(r'^activity/$', view=ActivityListView.as_view(), name='activity-list'),
)
