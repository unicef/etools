from django.conf.urls import url

from .views import CountryProgrammeListView, CountryProgrammeRetrieveView

urlpatterns = (
    url(r'^reports/countryprogramme/$', view=CountryProgrammeListView.as_view(),
        name='country-programme-list-views'),
    url(r'^reports/countryprogramme/(?P<pk>\d+)/$',
        view=CountryProgrammeRetrieveView.as_view(), name='country-programme-retriev-views'),

)

