from django.urls import re_path

from etools.libraries.monitoring.views import AppAliveView, AppReadyView

app_name = 'monitoring'
urlpatterns = (
    re_path(r'^app_alive/$', AppAliveView.as_view(), name="app_alive"),
    re_path(r'^app_ready/$', AppReadyView.as_view(), name="app_ready"),

)
