from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from email_auth import views


urlpatterns = [
    url(r"^login/$", views.TokenAuthView.as_view(), name="login"),
]
