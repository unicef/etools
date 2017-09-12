from django.conf.urls import url

from .views import check_everything


urlpatterns = (
    # api
    url(r'^$', check_everything),
)
