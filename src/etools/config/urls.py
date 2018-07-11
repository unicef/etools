
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView

import djangosaml2.views
import rest_framework_jwt.views
from rest_framework_nested import routers
from rest_framework_swagger.renderers import OpenAPIRenderer

from etools.applications.EquiTrack.views import IssueJWTRedirectView, MainView, OutdatedBrowserView
from etools.applications.locations.views import LocationsLightViewSet, LocationsViewSet, LocationTypesViewSet
from etools.applications.management.urls import urlpatterns as management_urls
from etools.applications.partners.views.v1 import FileTypeViewSet
from etools.applications.publics import urls as publics_patterns
from etools.applications.publics.views import StaticDataView
from etools.applications.reports.views.v1 import (IndicatorViewSet, ResultTypeViewSet,
                                                  ResultViewSet, SectorViewSet, UnitViewSet,)
from etools.applications.t2f.urls import urlpatterns as t2f_patterns
from etools.applications.users.views import (CountriesViewSet, GroupViewSet, ModuleRedirectView,
                                             OfficeViewSet, UserViewSet,)
from etools.applications.utils.common.schemas import get_schema_view, get_swagger_view

# ******************  API docs and schemas  ******************************
schema_view = get_swagger_view(title='eTools API')

# coreapi+json (http://www.coreapi.org/)
schema_view_json_coreapi = get_schema_view(title="eTools API")
# openapi+json (https://openapis.org/ aka swagger 2.0)
schema_view_json_openapi = get_schema_view(title="eTools API", renderer_classes=[OpenAPIRenderer])

api = routers.SimpleRouter()

# ******************  API version 1  ******************************
api.register(r'partners/file-types', FileTypeViewSet, base_name='filetypes')

api.register(r'users', UserViewSet, base_name='users')
api.register(r'groups', GroupViewSet, base_name='groups')
api.register(r'offices', OfficeViewSet, base_name='offices')

api.register(r'reports/result-types', ResultTypeViewSet, base_name='resulttypes')
api.register(r'reports/sectors', SectorViewSet, base_name='sectors')
api.register(r'reports/indicators', IndicatorViewSet, base_name='indicators')
api.register(r'reports/results', ResultViewSet, base_name='results')
api.register(r'reports/units', UnitViewSet, base_name='units')

api.register(r'locations', LocationsViewSet, base_name='locations')
api.register(r'locations-light', LocationsLightViewSet, base_name='locations-light')
api.register(r'locations-types', LocationTypesViewSet, base_name='locationtypes')

urlpatterns = [
    # Used for admin and dashboard pages in django
    url(r'^$', ModuleRedirectView.as_view(), name='dashboard'),
    url(r'^login/$', MainView.as_view(), name='main'),
    url(r'^tokens/', include('etools.applications.tokens.urls')),

    url(r'^api/static_data/$', StaticDataView.as_view({'get': 'list'}), name='public_static'),

    # ***************  API version 1  ********************
    url(r'^locations/', include('etools.applications.locations.urls')),
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
    url(r'^api/v2/reports/', include('etools.applications.reports.urls_v2')),
    url(r'^api/v2/', include('etools.applications.partners.urls_v2', namespace='partners_api')),
    url(r'^api/prp/v1/', include('etools.applications.partners.prp_urls', namespace='prp_api_v1')),
    url(r'^api/v2/hact/', include('etools.applications.hact.urls')),
    url(r'^api/v2/users/', include('etools.applications.users.urls_v2', namespace='users_v2')),
    url(r'^api/v2/workspaces/', CountriesViewSet.as_view(http_method_names=['get']), name="list-workspaces"),
    url(r'^api/v2/funds/', include('etools.applications.funds.urls')),
    url(r'^api/v2/activity/', include('unicef_snapshot.urls')),
    url(r'^api/v2/environment/', include('etools.applications.environment.urls_v2')),
    url(r'^api/v2/attachments/', include('etools.applications.attachments.urls')),

    # ***************  API version 3  ******************
    url(r'^api/v3/users/', include('etools.applications.users.urls_v3', namespace='users_v3')),


    url(r'^api/docs/', schema_view),
    url(r'^api/schema/coreapi', schema_view_json_coreapi),
    url(r'^api/schema/openapi', schema_view_json_openapi),
    url(r'^admin/', admin.site.urls),

    # helper urls
    url(r'^saml2/', include('djangosaml2.urls')),
    url(r'^login/token-auth/', rest_framework_jwt.views.obtain_jwt_token),
    # TODO: remove this when eTrips is deployed needed
    url(r'^api-token-auth/', rest_framework_jwt.views.obtain_jwt_token),
    url(r'^outdated_browser', OutdatedBrowserView.as_view(), name='outdated_browser'),
    url(r'^workspace_inactive/$', TemplateView.as_view(template_name='removed_workspace.html'),
        name='workspace-inactive'),

    url(r'^api/jwt/get/$', IssueJWTRedirectView.as_view(), name='issue JWT'),

    url('^monitoring/', include('etools.libraries.monitoring.urls')),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/', djangosaml2.views.echo_attributes),
    ]
