from django.conf.urls import url

from monitoring.views import CheckView

urlpatterns = (
    url(r'^$', CheckView.as_view(), name="monitoring"),
)
