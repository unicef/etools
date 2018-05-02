from django.conf.urls import url

from etools.libraries.monitoring.views import CheckView

app_name = 'monitoring'
urlpatterns = (
    url(r'^$', CheckView.as_view(), name="monitoring"),
)
