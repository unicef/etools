__author__ = 'RobertAvram'


from django.conf.urls import patterns, url

from .views import (
    ActiveUsersSection
)

urlpatterns = patterns(
    '',
    url(r'^api/usercounts/$', ActiveUsersSection.as_view()),
)
