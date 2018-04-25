
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView

import djangosaml2.views
import rest_framework_jwt.views
from rest_framework.schemas import get_schema_view
from rest_framework_nested import routers
from rest_framework_swagger.renderers import OpenAPIRenderer
from rest_framework_swagger.views import get_swagger_view

from email_auth.urls import urlpatterns as email_auth_patterns
from EquiTrack.views import IssueJWTRedirectView, MainView, OutdatedBrowserView
from locations.views import LocationsLightViewSet, LocationsViewSet, LocationTypesViewSet
from management.urls import urlpatterns as management_urls
from partners.views.v1 import FileTypeViewSet
from publics import urls as publics_patterns
from publics.views import StaticDataView
from reports.views.v1 import IndicatorViewSet, ResultTypeViewSet, ResultViewSet, SectorViewSet, UnitViewSet
from t2f.urls import urlpatterns as t2f_patterns
from users.views import GroupViewSet, ModuleRedirectView, OfficeViewSet, SectionViewSet, UserViewSet, CountriesViewSet

# ******************  API docs and schemas  ******************************
schema_view = get_swagger_view(title='eTools API')

# coreapi+json (http://www.coreapi.org/)
schema_view_json_coreapi = get_schema_view(title="eTools API")
# openapi+json (https://openapis.org/ aka swagger 2.0)
schema_view_json_openapi = get_schema_view(title="eTools API",
                                           renderer_classes=[OpenAPIRenderer])

api = routers.SimpleRouter()

# ******************  API version 1  ******************************
api.register(r'partners/file-types', FileTypeViewSet, base_name='filetypes')

api.register(r'users', UserViewSet, base_name='users')
api.register(r'groups', GroupViewSet, base_name='groups')
api.register(r'offices', OfficeViewSet, base_name='offices')
api.register(r'sections', SectionViewSet, base_name='sections')

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
    url(r'^email-auth/', include(email_auth_patterns, namespace='email_auth')),

    url(r'^api/static_data/$', StaticDataView.as_view({'get': 'list'}), name='public_static'),

    # ***************  API version 1  ********************
    url(r'^locations/', include('locations.urls')),
    # GIS API urls
    url(r'^api/management/gis/', include('management.urls_gis')),
    url(r'^users/', include('users.urls')),
    url(r'^api/management/', include(management_urls)),
    url(r'^api/', include(api.urls)),
    url(r'^api/', include(publics_patterns, namespace='public')),

    # ***************  API version 2  ******************
    url(r'^api/locations/pcode/(?P<p_code>\w+)/$',
        LocationsViewSet.as_view({'get': 'retrieve'}),
        name='locations_detail_pcode'),
    url(r'^api/t2f/', include(t2f_patterns)),
    url(r'^api/tpm/', include('tpm.urls', namespace='tpm')),
    url(r'^api/audit/', include('audit.urls', namespace='audit')),
    url(r'^api/v2/reports/', include('reports.urls_v2')),
    url(r'^api/v2/', include('partners.urls_v2', namespace='partners_api')),
    url(r'^api/prp/v1/', include('partners.prp_urls', namespace='prp_api_v1')),
    url(r'^api/v2/hact/', include('hact.urls', namespace='hact_api')),
    url(r'^api/v2/users/', include('users.urls_v2', namespace='users_v2')),
    url(r'^api/v2/workspaces/', CountriesViewSet.as_view(http_method_names=['get']), name="list-workspaces"),
    url(r'^api/v2/funds/', include('funds.urls', namespace='funds')),
    url(
        r'^api/v2/activity/',
        include('snapshot.urls', namespace='snapshot_api')
    ),
    url(r'^api/v2/environment/', include('environment.urls_v2', namespace='environment')),
    url(
        r'^api/v2/attachments/',
        include('attachments.urls', namespace='attachments')
    ),

    # ***************  API version 3  ******************
    url(r'^api/v3/users/', include('users.urls_v3', namespace='users_v3')),


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

    url('^monitoring/', include('monitoring.urls')),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/', djangosaml2.views.echo_attributes),
    ]
