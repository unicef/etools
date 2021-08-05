from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView

import rest_framework_jwt.views
from rest_framework_nested import routers
from rest_framework_swagger.renderers import OpenAPIRenderer

from etools.applications.core.schemas import get_schema_view, get_swagger_view
from etools.applications.core.views import IssueJWTRedirectView, logout_view, MainView
from etools.applications.management.urls import urlpatterns as management_urls
from etools.applications.partners.views.v1 import FileTypeViewSet
from etools.applications.publics import urls as publics_patterns
from etools.applications.publics.views import StaticDataView
from etools.applications.reports.views.v1 import (
    IndicatorViewSet,
    ResultTypeViewSet,
    ResultViewSet,
    SectionViewSet,
    UnitViewSet,
)
from etools.applications.reports.views.v2 import OfficeViewSet
from etools.applications.reports.views.v3 import PMPOfficeViewSet, PMPSectionViewSet
from etools.applications.t2f.urls import urlpatterns as t2f_patterns
from etools.applications.users.views import CountriesViewSet, GroupViewSet, ModuleRedirectView, UserViewSet
# these imports are used to autodiscover admin forms located outside of INSTALLED_APPS(the libraries folder for example)
from etools.libraries.locations import admin as locations_admin  # noqa: ignore=F401
from etools.libraries.locations.views import (
    CartoDBTablesView,
    LocationQuerySetView,
    LocationsLightViewSet,
    LocationsViewSet,
    LocationTypesViewSet,
)

# ******************  API docs and schemas  ******************************
schema_view = get_swagger_view(title='eTools API')

# coreapi+json (http://www.coreapi.org/)
schema_view_json_coreapi = get_schema_view(title="eTools API")
# openapi+json (https://openapis.org/ aka swagger 2.0)
schema_view_json_openapi = get_schema_view(title="eTools API", renderer_classes=[OpenAPIRenderer])

api = routers.SimpleRouter()

# ******************  API version 1  ******************************
api.register(r'partners/file-types', FileTypeViewSet, basename='filetypes')

api.register(r'users', UserViewSet, basename='users')
api.register(r'groups', GroupViewSet, basename='groups')
api.register(r'offices/v3', PMPOfficeViewSet, basename='offices-pmp')
api.register(r'offices', OfficeViewSet, basename='offices')

api.register(r'sections/v3', PMPSectionViewSet, basename='sections-pmp')
api.register(r'sections', SectionViewSet, basename='sections')

api.register(r'reports/result-types', ResultTypeViewSet, basename='resulttypes')
api.register(r'reports/indicators', IndicatorViewSet, basename='indicators')
api.register(r'reports/results', ResultViewSet, basename='results')
api.register(r'reports/units', UnitViewSet, basename='units')
api.register(r'reports/sectors', SectionViewSet, basename='sectors')  # TODO remove me (keeping this for trips...)

api.register(r'locations', LocationsViewSet, basename='locations')
api.register(r'locations-light', LocationsLightViewSet, basename='locations-light')
api.register(r'locations-types', LocationTypesViewSet, basename='locationtypes')

urlpatterns = [
    # Used for admin and dashboard pages in django
    url(r'^$', ModuleRedirectView.as_view(), name='dashboard'),
    url(r'^login/$', MainView.as_view(), name='main'),
    url(r'^logout/$', logout_view, name='logout'),

    url(r'^api/static_data/$', StaticDataView.as_view({'get': 'list'}), name='public_static'),

    # ***************  API version 1  ********************
    url(r'^locations/', include('unicef_locations.urls')),
    url(r'^locations/cartodbtables/$', CartoDBTablesView.as_view(), name='cartodbtables'),
    url(r'^locations/autocomplete/$', LocationQuerySetView.as_view(), name='locations_autocomplete'),
    url(r'^api/v1/field-monitoring/', include('etools.applications.field_monitoring.urls')),
    url(r'^api/comments/v1/', include('etools.applications.comments.urls')),

    # GIS API urls
    url(r'^api/management/gis/', include('etools.applications.management.urls_gis')),
    url(r'^users/', include('etools.applications.users.urls')),
    url(r'^api/management/', include(management_urls)),
    url(r'^api/', include(api.urls)),
    url(r'^api/', include(publics_patterns)),

    # ***************  API version 2  ******************
    url(r'^api/locations/pcode/(?P<p_code>\w+)/$',
        LocationsViewSet.as_view({'get': 'retrieve'}),
        name='locations_detail_pcode'),
    url(r'^api/t2f/', include(t2f_patterns)),
    url(r'^api/tpm/', include('etools.applications.tpm.urls')),
    url(r'^api/audit/', include('etools.applications.audit.urls')),
    url(r'^api/action-points/', include('etools.applications.action_points.urls')),
    url(r'^api/psea/', include('etools.applications.psea.urls')),
    url(r'^api/v2/reports/', include('etools.applications.reports.urls_v2')),
    url(r'^api/v2/', include('etools.applications.partners.urls_v2', namespace='partners_api')),
    url(r'^api/prp/v1/', include('etools.applications.partners.prp_urls', namespace='prp_api_v1')),
    url(r'^api/v2/hact/', include('etools.applications.hact.urls')),
    url(r'^api/v2/users/', include('etools.applications.users.urls_v2', namespace='users_v2')),
    url(r'^api/v2/workspaces/', CountriesViewSet.as_view(http_method_names=['get']), name="list-workspaces"),
    url(r'^api/v2/funds/', include('etools.applications.funds.urls')),
    url(r'^api/v2/activity/', include('unicef_snapshot.urls')),
    url(r'^api/v2/environment/', include('etools.applications.environment.urls_v2')),
    url(r'^api/v2/attachments/', include('unicef_attachments.urls')),

    # ***************  API version 3  ******************
    url(r'^api/v3/users/', include('etools.applications.users.urls_v3', namespace='users_v3')),
    url(
        r'^api/pmp/v3/',
        include('etools.applications.partners.urls_v3', namespace='pmp_v3'),
    ),
    url(
        r'^api/reports/v3/',
        include('etools.applications.reports.urls_v3', namespace='reports_v3'),
    ),

    url(r'^api/docs/', schema_view),
    url(r'^api/schema/coreapi', schema_view_json_coreapi),
    url(r'^api/schema/openapi', schema_view_json_openapi),
    url(r'^admin/', admin.site.urls),

    # helper urls
    url(r'^login/token-auth/', rest_framework_jwt.views.obtain_jwt_token),
    # TODO: remove this when eTrips is deployed needed
    url(r'^api-token-auth/', rest_framework_jwt.views.obtain_jwt_token),
    url(r'^workspace_inactive/$', TemplateView.as_view(template_name='removed_workspace.html'),
        name='workspace-inactive'),

    url(r'^api/jwt/get/$', IssueJWTRedirectView.as_view(), name='issue JWT'),

    url('^social/', include('social_django.urls', namespace='social')),
    url('^monitoring/', include('etools.libraries.monitoring.urls')),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
