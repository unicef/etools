from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from supplies.views import SuppliesDashboardView


urlpatterns = (
    url(r'^$', login_required(SuppliesDashboardView.as_view()), name='supplies_dashboard'),
)
