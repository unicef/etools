from django.urls import include, re_path

from etools.applications.field_monitoring.analyze import views

app_name = 'field_monitoring_analyze'
urlpatterns = [
    re_path(r'overall/$', views.OverallView.as_view(), name='overall'),
    re_path(r'coverage/', include([
        re_path(r'partners/$', views.CoveragePartnersView.as_view(), name='coverage-partners'),
        re_path(r'interventions/$', views.CoverageInterventionsView.as_view(), name='coverage-interventions'),
        re_path(r'cp-outputs/$', views.CoverageCPOutputsView.as_view(), name='coverage-cp_outputs'),
        re_path(r'geographic/$', views.CoverageGeographicView.as_view(), name='coverage-geographic'),
    ])),
    re_path(r'hact/$', views.HACTView.as_view(), name='hact'),
    re_path(r'issues/', include([
        re_path(r'partners/$', views.IssuesPartnersView.as_view(), name='issues-partners'),
        re_path(r'cp-outputs/$', views.IssuesCPOutputsView.as_view(), name='issues-cp_outputs'),
        re_path(r'locations/$', views.IssuesLocationsView.as_view(), name='issues-locations'),
    ])),
]
