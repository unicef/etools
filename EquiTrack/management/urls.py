from django.conf.urls import url

from .views import (
    ActiveUsersSection,
    TripsStatisticsView,
    AgreementsStatisticsView,
    InterventionsStatisticsView,
    PortalDashView
)

urlpatterns = (
    url(r'^$', PortalDashView.as_view()),
    url(r'^api/stats/usercounts/$', ActiveUsersSection.as_view()),
    url(r'^api/stats/trips/$', TripsStatisticsView.as_view()),
    url(r'^api/stats/agreements/$', AgreementsStatisticsView.as_view()),
    url(r'^api/stats/interventions/$', InterventionsStatisticsView.as_view()),

)
