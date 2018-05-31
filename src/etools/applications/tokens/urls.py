from django.conf.urls import url

from etools.applications.tokens import views

app_name = 'tokens'
urlpatterns = [
    url(r"^login/$", views.TokenAuthView.as_view(), name="login"),
]
