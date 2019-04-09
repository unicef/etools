from django.conf.urls import url

from etools.libraries.monitoring.views import AppAliveView, AppReadyView

app_name = 'monitoring'
urlpatterns = (
    url(r'^app_alive/$', AppAliveView.as_view(), name="app_alive"),
    url(r'^app_ready/$', AppReadyView.as_view(), name="app_ready"),

)
