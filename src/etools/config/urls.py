from django.conf import settings
from django.contrib import admin
from django.urls import include, re_path
from django.views.generic import TemplateView

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
from etools.applications.t2f.urls import urlpatterns as t2f_patterns
from etools.applications.users.views import CountriesViewSet, GroupViewSet, ModuleRedirectView, UserViewSet
# these imports are used to autodiscover admin forms located outside of INSTALLED_APPS(the libraries folder for example)
from etools.libraries.locations import admin as locations_admin  # noqa: ignore=F401
from etools.libraries.locations.views import (
    CartoDBTablesView,
    LocationQuerySetView,
    LocationsLightViewSet,
    LocationsViewSet,
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
api.register(r'offices', OfficeViewSet, basename='offices')

api.register(r'sections', SectionViewSet, basename='sections')

api.register(r'reports/result-types', ResultTypeViewSet, basename='resulttypes')
api.register(r'reports/indicators', IndicatorViewSet, basename='indicators')
api.register(r'reports/results', ResultViewSet, basename='results')
api.register(r'reports/units', UnitViewSet, basename='units')
api.register(r'reports/sectors', SectionViewSet, basename='sectors')  # TODO remove me (keeping this for trips...)

api.register(r'locations', LocationsViewSet, basename='locations')
api.register(r'locations-light', LocationsLightViewSet, basename='locations-light')

urlpatterns = [
    # Used for admin and dashboard pages in django
    re_path(r'^$', ModuleRedirectView.as_view(), name='dashboard'),
    re_path(r'^login/$', MainView.as_view(), name='main'),
    re_path(r'^logout/$', logout_view, name='logout'),

    re_path(r'^api/static_data/$', StaticDataView.as_view({'get': 'list'}), name='public_static'),

    # ***************  API version 1  ********************
    re_path(r'^locations/', include('unicef_locations.urls')),
    re_path(r'^locations/cartodbtables/$', CartoDBTablesView.as_view(), name='cartodbtables'),
    re_path(r'^locations/autocomplete/$', LocationQuerySetView.as_view(), name='locations_autocomplete'),
    re_path(r'^api/v1/field-monitoring/', include('etools.applications.field_monitoring.urls')),

    # GIS API urls
    re_path(r'^api/management/gis/', include('etools.applications.management.urls_gis')),
    re_path(r'^users/', include('etools.applications.users.urls')),
    re_path(r'^api/management/', include(management_urls)),
    re_path(r'^api/', include(api.urls)),
    re_path(r'^api/', include(publics_patterns)),

    # ***************  API version 2  ******************
    re_path(r'^api/locations/pcode/(?P<p_code>\w+)/$',
            LocationsViewSet.as_view({'get': 'retrieve'}),
            name='locations_detail_pcode'),
    re_path(r'^api/t2f/', include(t2f_patterns)),
    re_path(r'^api/tpm/', include('etools.applications.tpm.urls')),
    re_path(r'^api/audit/', include('etools.applications.audit.urls')),
    re_path(r'^api/action-points/', include('etools.applications.action_points.urls')),
    re_path(r'^api/psea/', include('etools.applications.psea.urls')),
    re_path(r'^api/v2/reports/', include('etools.applications.reports.urls_v2')),
    re_path(r'^api/v2/', include('etools.applications.partners.urls_v2', namespace='partners_api')),
    re_path(r'^api/prp/v1/', include('etools.applications.partners.prp_urls', namespace='prp_api_v1')),
    re_path(r'^api/v2/hact/', include('etools.applications.hact.urls')),
    re_path(r'^api/v2/users/', include('etools.applications.users.urls_v2', namespace='users_v2')),
    re_path(r'^api/v2/workspaces/', CountriesViewSet.as_view(http_method_names=['get']), name="list-workspaces"),
    re_path(r'^api/v2/funds/', include('etools.applications.funds.urls')),
    re_path(r'^api/v2/activity/', include('unicef_snapshot.urls')),
    re_path(r'^api/v2/environment/', include('etools.applications.environment.urls_v2')),
    re_path(r'^api/v2/attachments/', include('unicef_attachments.urls')),

    # ***************  API version 3  ******************
    re_path(r'^api/v3/users/', include('etools.applications.users.urls_v3', namespace='users_v3')),


    re_path(r'^api/docs/', schema_view),
    re_path(r'^api/schema/coreapi', schema_view_json_coreapi),
    re_path(r'^api/schema/openapi', schema_view_json_openapi),
    re_path(r'^admin/', admin.site.urls),

    re_path(r'^workspace_inactive/$', TemplateView.as_view(template_name='removed_workspace.html'),
            name='workspace-inactive'),

    re_path(r'^api/jwt/get/$', IssueJWTRedirectView.as_view(), name='issue JWT'),

    re_path('^social/', include('social_django.urls', namespace='social')),
    re_path('^monitoring/', include('etools.libraries.monitoring.urls')),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]
