from __future__ import absolute_import

# Django imports
from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.contrib import admin

# 3rd party imports
from rest_framework_swagger.views import get_swagger_view
from rest_framework_swagger.renderers import OpenAPIRenderer
from rest_framework.schemas import get_schema_view
import rest_framework_jwt.views
from rest_framework_nested import routers
import djangosaml2.views

# Project imports
from EquiTrack.stream_feed.feeds import JSONActivityFeedWithCustomData
from EquiTrack.views import (
    MainView,
    OutdatedBrowserView
)
from locations.views import (
    LocationTypesViewSet,
    LocationsViewSet,
    LocationsLightViewSet,
)
from management.urls import urlpatterns as management_urls
from partners.urls import (
    staffm_api,
)
from partners.views.v1 import (
    FileTypeViewSet,
)
from publics import urls as publics_patterns
from publics.views import StaticDataView
from reports.views.v1 import (
    ResultTypeViewSet,
    SectorViewSet,
    IndicatorViewSet,
    ResultViewSet,
    UnitViewSet
)
from t2f.urls import urlpatterns as t2f_patterns
from users.views import UserViewSet, GroupViewSet, OfficeViewSet, SectionViewSet, ModuleRedirectView
from workplan.views import (
    CommentViewSet,
    WorkplanViewSet,
    WorkplanProjectViewSet,
    LabelViewSet,
    MilestoneViewSet
)


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

api.register(r'comments', CommentViewSet, base_name='comments')
api.register(r'workplans', WorkplanViewSet, base_name='workplans')
api.register(r'workplans/milestones', MilestoneViewSet, base_name='milestones')
api.register(r'workplan_projects', WorkplanProjectViewSet, base_name='workplan_projects')
api.register(r'labels', LabelViewSet, base_name='labels')

urlpatterns = [
    # Used for admin and dashboard pages in django
    url(r'^$', ModuleRedirectView.as_view(), name='dashboard'),
    url(r'^login/$', MainView.as_view(), name='main'),

    url(r'^api/static_data/$', StaticDataView.as_view({'get': 'list'}), name='public_static'),

    # ***************  API version 1  ********************
    url(r'^locations/', include('locations.urls')),
    url(r'^users/', include('users.urls')),
    url(r'^supplies/', include('supplies.urls')),
    url(r'^api/management/', include(management_urls)),
    url(r'^api/', include(api.urls)),
    url(r'^api/', include(staffm_api.urls)),
    url(r'^api/', include(publics_patterns, namespace='public')),

    # ***************  API version 2  ******************
    url(r'^api/locations/pcode/(?P<p_code>\w+)/$',
        LocationsViewSet.as_view({'get': 'retrieve'}),
        name='locations_detail_pcode'),
    url(r'^api/t2f/', include(t2f_patterns)),
    url(r'^api/audit/', include('audit.urls', namespace='audit')),
    url(r'^api/v2/', include('reports.urls_v2')),
    url(r'^api/v2/', include('partners.urls_v2', namespace='partners_api')),
    url(r'^api/v2/users/', include('users.urls_v2')),
    url(r'^api/v2/funds/', include('funds.urls', namespace='funds')),


    # ***************  API version 3  ******************
    url(r'^api/v3/users/', include('users.urls_v3')),


    url(r'^api/docs/', schema_view),
    url(r'^api/schema/coreapi', schema_view_json_coreapi),
    url(r'^api/schema/openapi', schema_view_json_openapi),
    url(r'^admin/', include(admin.site.urls)),

    # helper urls
    url(r'^accounts/', include('allauth.urls')),
    url(r'^saml2/', include('djangosaml2.urls')),
    url(r'^chaining/', include('smart_selects.urls')),
    url(r'^login/token-auth/', rest_framework_jwt.views.obtain_jwt_token),
    # TODO: remove this when eTrips is deployed needed
    url(r'^api-token-auth/', rest_framework_jwt.views.obtain_jwt_token),
    url(r'^outdated_browser', OutdatedBrowserView.as_view(), name='outdated_browser'),
    url(r'^workspace_inactive/$', TemplateView.as_view(template_name='removed_workspace.html'),
        name='workspace-inactive'),

    # Activity stream
    url(r'^activity/(?P<model_name>\w+)/json/$',
        JSONActivityFeedWithCustomData.as_view(name='custom_data_model_stream'),
        name='custom_data_model_stream'),
    url(r'^activity/(?P<model_name>\w+)/(?P<obj_id>\d+)/json/$',
        JSONActivityFeedWithCustomData.as_view(name='custom_data_model_detail_stream'),
        name='custom_data_model_detail_stream'),
    url('^activity/', include('actstream.urls')),
    url('^monitoring/', include('monitoring.urls')),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/', djangosaml2.views.echo_attributes),
    ]
