from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import REDIRECT_FIELD_NAME

from autocomplete_light import shortcuts as autocomplete_light
# import every app/autocomplete_light_registry.py
autocomplete_light.autodiscover()

from rest_framework_nested import routers

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

from .utils import staff_required
from .views import (
    MainView,
    MapView,
    DashboardView,
    UserDashboardView,
    CmtDashboardView,
    HACTDashboardView,
)
from locations.views import (
    LocationTypesViewSet,
    LocationsViewSet
)
from trips.views import TripsViewSet, Trips2ViewSet, TripFileViewSet
from partners.views import PartnerOrganizationsViewSet, AgreementViewSet, PartnerStaffMembersViewSet, FileTypeViewSet
from users.views import UserViewSet, GroupViewSet, OfficeViewSet, SectionViewSet
from funds.views import DonorViewSet, GrantViewSet
from reports.views import (
    ResultStructureViewSet,
    ResultTypeViewSet,
    SectorViewSet,
    GoalViewSet,
    IndicatorViewSet,
    OutputViewSet,
    UnitViewSet
)

from partners.urls import (
    interventions_api,
    results_api,
    reports_api,
    pcasectors_api,
    pcabudgets_api,
    pcafiles_api,
    pcaamendments_api,
    pcalocations_api,
    pcagrants_api
)

api = routers.SimpleRouter()
api.register(r'trips', TripsViewSet, base_name='trip')

trips2_api = routers.SimpleRouter()
trips2_api.register(r'trips2', Trips2ViewSet, base_name='trips2')

trips2files_api = routers.NestedSimpleRouter(trips2_api, r'trips2', lookup='trips2')
trips2files_api.register(r'files', TripFileViewSet, base_name='trips2files')

api.register(r'partners/organizations', PartnerOrganizationsViewSet, base_name='partnerorganizations')
api.register(r'partners/staff-members', PartnerStaffMembersViewSet, base_name='partnerstaffmembers')
api.register(r'partners/agreements', AgreementViewSet, base_name='agreements')
api.register(r'partners/file-types', FileTypeViewSet, base_name='filetypes')

api.register(r'users', UserViewSet, base_name='users')
api.register(r'groups', GroupViewSet, base_name='groups')
api.register(r'offices', OfficeViewSet, base_name='offices')
api.register(r'sections', SectionViewSet, base_name='sections')

api.register(r'funds/donors', DonorViewSet, base_name='donors')
api.register(r'funds/grants', GrantViewSet, base_name='grants')

api.register(r'reports/result-structures', ResultStructureViewSet, base_name='resultstructures')
api.register(r'reports/result-types', ResultTypeViewSet, base_name='resulttypes')
api.register(r'reports/sectors', SectorViewSet, base_name='sectors')
api.register(r'reports/goals', GoalViewSet, base_name='goals')
api.register(r'reports/indicators', IndicatorViewSet, base_name='indicators')
api.register(r'reports/outputs', OutputViewSet, base_name='outputs')
api.register(r'reports/units', UnitViewSet, base_name='units')

api.register(r'locations', LocationsViewSet, base_name='locations')
api.register(r'locations-types', LocationTypesViewSet, base_name='locationtypes')


urlpatterns = patterns(
    '',
    # TODO: overload login_required to staff_required to automatically re-route partners to the parter portal
    url(r'^$', staff_required(UserDashboardView.as_view()), name='dashboard'),
    url(r'^login/$', MainView.as_view(), name='main'),
    url(r'^indicators', login_required(DashboardView.as_view()), name='indicator_dashboard'),
    url(r'^map/$', login_required(MapView.as_view()), name='map'),
    url(r'^cmt/$', login_required(CmtDashboardView.as_view()), name='cmt'),
    url(r'^hact/$', login_required(HACTDashboardView.as_view()), name='hact'),

    url(r'^locations/', include('locations.urls')),
    url(r'^management/', include('management.urls')),
    url(r'^partners/', include('partners.urls')),
    url(r'^trips/', include('trips.urls')),
    url(r'^users/', include('users.urls')),
    url(r'^supplies/', include('supplies.urls')),

    url(r'^api/', include(api.urls)),
    url(r'^api/partners/', include(interventions_api.urls)),
    url(r'^api/', include(results_api.urls)),
    url(r'^api/partners/', include(pcasectors_api.urls)),
    url(r'^api/partners/', include(pcabudgets_api.urls)),
    url(r'^api/partners/', include(pcafiles_api.urls)),
    url(r'^api/partners/', include(pcagrants_api.urls)),
    url(r'^api/partners/', include(pcaamendments_api.urls)),
    url(r'^api/partners/', include(pcalocations_api.urls)),
    url(r'^api/', include(reports_api.urls)),
    url(r'^api/', include(trips2_api.urls)),
    url(r'^api/', include(trips2files_api.urls)),
    url(r'^api/docs/', include('rest_framework_swagger.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # helper urls
    url(r'^accounts/', include('allauth.urls')),
    url(r'^saml2/', include('djangosaml2.urls')),
    url(r'^chaining/', include('smart_selects.urls')),
    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^login/token-auth/', 'rest_framework_jwt.views.obtain_jwt_token'),
    url(r'^api-token-auth/', 'rest_framework_jwt.views.obtain_jwt_token'),  # TODO: remove this when eTrips is deployed needed
)


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/', 'djangosaml2.views.echo_attributes'),
    )
