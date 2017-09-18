from django.conf.urls import url

from .views import CheckView


urlpatterns = (
    # api
    url(r'^$', CheckView.as_view()),
)
