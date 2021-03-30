from django.conf.urls import url
from django.urls import include

from etools.applications.field_monitoring.analyze import views

app_name = 'field_monitoring_analyze'
urlpatterns = [
    url(r'overall/$', views.OverallView.as_view(), name='overall'),
    url(r'coverage/', include([
        url(r'partners/$', views.CoveragePartnersView.as_view(), name='coverage-partners'),
        url(r'interventions/$', views.CoverageInterventionsView.as_view(), name='coverage-interventions'),
        url(r'cp-outputs/$', views.CoverageCPOutputsView.as_view(), name='coverage-cp_outputs'),
        url(r'geographic/$', views.CoverageGeographicView.as_view(), name='coverage-geographic'),
    ])),
    url(r'hact/$', views.HACTView.as_view(), name='hact'),
    url(r'issues/', include([
        url(r'partners/$', views.IssuesPartnersView.as_view(), name='issues-partners'),
        url(r'cp-outputs/$', views.IssuesCPOutputsView.as_view(), name='issues-cp_outputs'),
        url(r'locations/$', views.IssuesLocationsView.as_view(), name='issues-locations'),
    ])),
]
