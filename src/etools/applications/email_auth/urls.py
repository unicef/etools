
from django.conf.urls import url

from etools.applications.email_auth import views

app_name = 'email_auth'
urlpatterns = [
    url(r"^login/$", views.TokenAuthView.as_view(), name="login"),
]
