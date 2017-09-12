from django.conf.urls import url
from django.views.generic import TemplateView

from .views import check_everything



urlpatterns = (
    # api
    url(r'^$', check_everything),
)
