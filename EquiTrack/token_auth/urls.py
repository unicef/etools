from __future__ import absolute_import, division, print_function, unicode_literals

from django.conf.urls import url

from token_auth import views


urlpatterns = [
    url(r"^login/$", views.login, name="login"),
]
