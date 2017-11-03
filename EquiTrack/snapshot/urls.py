from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.conf.urls import url

from snapshot.views import ActivityListView

urlpatterns = (
    url(r'^activity/$', view=ActivityListView.as_view(), name='activity-list'),
)
