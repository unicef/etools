from django.conf.urls import url

from etools.applications.tokens import views

app_name = 'tokens'
urlpatterns = [
    url(r"^email/login/$", views.TokenEmailAuthView.as_view(), name="login"),
    url(r"^$", views.TokenGetView.as_view(), name="get"),
    url(r"^reset/$", views.TokenResetView.as_view(), name="reset"),
    url(r"^delete/$", views.TokenDeleteView.as_view(), name="delete"),
]
