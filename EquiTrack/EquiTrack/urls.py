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
    PartnershipsView,
    OutdatedBrowserView
)
from locations.views import (
    LocationTypesViewSet,
    LocationsViewSet
)
from trips.views import TripsViewSet, TripFileViewSet, TripActionPointViewSet
from partners.views import PartnerOrganizationsViewSet, AgreementViewSet, PartnerStaffMembersViewSet, FileTypeViewSet
from users.views import UserViewSet, GroupViewSet, OfficeViewSet, SectionViewSet
from funds.views import DonorViewSet, GrantViewSet
from reports.views import (
    ResponsePlanViewSet,
    ResultTypeViewSet,
    SectorViewSet,
    # GoalViewSet,
    IndicatorViewSet,
    MilestoneViewSet,
    ResultViewSet,
    UnitViewSet
)

from partners.urls import (
    simple_interventions_api,
    interventions_api,
    results_api,
    simple_results_api,
    intervention_reports_api,
    bulk_reports_api,
    pcasectors_api,
    pcabudgets_api,
    pcafiles_api,
    pcaamendments_api,
    pcalocations_api,
    pcagrants_api,
    partners_api,
    staffm_api,
    agreement_api,
    simple_agreements_api,
)

from workplan.views import (
    CommentViewSet,
    WorkplanViewSet,
    WorkplanProjectViewSet,
    LabelViewSet,
)

api = routers.SimpleRouter()

trips_api = routers.SimpleRouter()
trips_api.register(r'trips', TripsViewSet, base_name='trips')

tripsfiles_api = routers.NestedSimpleRouter(trips_api, r'trips', lookup='trips')
tripsfiles_api.register(r'files', TripFileViewSet, base_name='files')

actionpoint_api = routers.NestedSimpleRouter(trips_api, r'trips', lookup='trips')
actionpoint_api.register(r'actionpoints', TripActionPointViewSet, base_name='actionpoints')

api.register(r'partners/file-types', FileTypeViewSet, base_name='filetypes')

api.register(r'users', UserViewSet, base_name='users')
api.register(r'groups', GroupViewSet, base_name='groups')
api.register(r'offices', OfficeViewSet, base_name='offices')
api.register(r'sections', SectionViewSet, base_name='sections')

api.register(r'funds/donors', DonorViewSet, base_name='donors')
api.register(r'funds/grants', GrantViewSet, base_name='grants')

api.register(r'reports/hrps', ResponsePlanViewSet, base_name='ResponsePlans')
api.register(r'reports/result-types', ResultTypeViewSet, base_name='resulttypes')
api.register(r'reports/sectors', SectorViewSet, base_name='sectors')
api.register(r'reports/indicators', IndicatorViewSet, base_name='indicators')
api.register(r'reports/milestones', MilestoneViewSet, base_name='milestones')
api.register(r'reports/results', ResultViewSet, base_name='results')
api.register(r'reports/units', UnitViewSet, base_name='units')

api.register(r'locations', LocationsViewSet, base_name='locations')
api.register(r'locations-types', LocationTypesViewSet, base_name='locationtypes')

api.register(r'comments', CommentViewSet, base_name='comments')
api.register(r'workplans', WorkplanViewSet, base_name='workplans')
api.register(r'workplan_projects', WorkplanProjectViewSet, base_name='workplan_projects')
api.register(r'labels', LabelViewSet, base_name='labels')


urlpatterns = patterns(
    '',
    # TODO: overload login_required to staff_required to automatically re-route partners to the parter portal
    url(r'^$', staff_required(UserDashboardView.as_view()), name='dashboard'),
    url(r'^login/$', MainView.as_view(), name='main'),
    url(r'^indicators', login_required(DashboardView.as_view()), name='indicator_dashboard'),
    url(r'^partnerships', login_required(PartnershipsView.as_view()), name='partnerships_dashboard'),
    url(r'^map/$', login_required(MapView.as_view()), name='map'),
    url(r'^cmt/$', login_required(CmtDashboardView.as_view()), name='cmt'),
    url(r'^hact/$', login_required(HACTDashboardView.as_view()), name='hact_dashboard'),

    url(r'^locations/', include('locations.urls')),
    url(r'^management/', include('management.urls')),
    url(r'^partners/', include('partners.urls')),
    url(r'^trips/', include('trips.urls')),
    url(r'^users/', include('users.urls')),
    url(r'^supplies/', include('supplies.urls')),

    url(r'^api/', include(api.urls)),
    url(r'^api/', include(partners_api.urls)),
    url(r'^api/', include(staffm_api.urls)),
    url(r'^api/', include(agreement_api.urls)),
    url(r'^api/', include(simple_agreements_api.urls)),
    url(r'^api/', include(interventions_api.urls)),
    url(r'^api/', include(simple_interventions_api.urls)),
    url(r'^api/', include(simple_results_api.urls)),
    url(r'^api/', include(results_api.urls)),
    url(r'^api/', include(pcasectors_api.urls)),
    url(r'^api/', include(pcabudgets_api.urls)),
    url(r'^api/', include(pcafiles_api.urls)),
    url(r'^api/', include(pcagrants_api.urls)),
    url(r'^api/', include(pcaamendments_api.urls)),
    url(r'^api/', include(pcalocations_api.urls)),
    url(r'^api/', include(intervention_reports_api.urls)),
    url(r'^api/', include(bulk_reports_api.urls)),
    url(r'^api/', include(trips_api.urls)),
    url(r'^api/', include(tripsfiles_api.urls)),
    url(r'^api/', include(actionpoint_api.urls)),
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
    url(r'^outdated_browser', OutdatedBrowserView.as_view(), name='outdated_browser')
)


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += patterns(
        '',
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/', 'djangosaml2.views.echo_attributes'),
    )
