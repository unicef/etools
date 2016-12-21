from django.conf.urls import url

from .views import InterventionsView

urlpatterns = (
    url(r'^partners/interventions/$', view=InterventionsView.as_view(), name='interventions-list'),
)

