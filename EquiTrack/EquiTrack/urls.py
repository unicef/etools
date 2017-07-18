from __future__ import absolute_import

# Django imports
from django.conf import settings
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView
# Uncomment the line below to enable the admin:
from django.contrib import admin

# 3rd party imports
from rest_framework_swagger.views import get_swagger_view
import rest_framework_jwt.views
from rest_framework_nested import routers
import djangosaml2.views

# Project imports
from publics.views import StaticDataView
from .stream_feed.feeds import JSONActivityFeedWithCustomData
from .views import (
    MainView,
    OutdatedBrowserView
)
from locations.views import (
    LocationTypesViewSet,
    LocationsViewSet,
    LocationsLightViewSet,
)
from trips.views import TripsViewSet, TripFileViewSet, TripActionPointViewSet

from partners.views.v1 import (
    FileTypeViewSet,
)
from users.views import UserViewSet, GroupViewSet, OfficeViewSet, SectionViewSet
from reports.views.v1 import (
    ResultTypeViewSet,
    SectorViewSet,
    # GoalViewSet,
    IndicatorViewSet,
    ResultViewSet,
    UnitViewSet
)

from partners.urls import (
    # interventions_api,
    # results_api,
    # simple_results_api,
    # intervention_reports_api,
    # pcasectors_api,
    # pcabudgets_api,
    # pcafiles_api,
    # pcaamendments_api,
    # pcalocations_api,
    # pcagrants_api,
    staffm_api,
    # agreement_api,
    # simple_agreements_api,
)

from management.urls import urlpatterns as management_urls

from workplan.views import (
    CommentViewSet,
    WorkplanViewSet,
    WorkplanProjectViewSet,
    LabelViewSet,
    MilestoneViewSet
)

from t2f.urls import urlpatterns as t2f_patterns
from publics import urls as publics_patterns

schema_view = get_swagger_view(title='eTools API')

api = routers.SimpleRouter()

# ******************  API version 1 - not used ******************************

trips_api = routers.SimpleRouter()
trips_api.register(r'trips', TripsViewSet, base_name='trips')
tripsfiles_api = routers.NestedSimpleRouter(trips_api, r'trips', lookup='trips')
tripsfiles_api.register(r'files', TripFileViewSet, base_name='files')
actionpoint_api = routers.NestedSimpleRouter(trips_api, r'trips', lookup='trips')
actionpoint_api.register(r'actionpoints', TripActionPointViewSet, base_name='actionpoints')
# from reports.views.v1 import ResultStructureViewSet
# api.register(r'reports/result-structures', ResultStructureViewSet, base_name='resultstructures')

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

# from django.contrib.auth.decorators import login_required
# from .utils import staff_required
urlpatterns = [
    # TODO: overload login_required to staff_required to automatically re-route partners to the parter portal

    # Used for admin and dashboard pages in django
    url(r'^$', RedirectView.as_view(url='/dash/', permanent=False), name='dashboard'),
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


    # url(r'^trips/', include('trips.urls')),
    url(r'^api/', include(trips_api.urls)),
    url(r'^api/', include(tripsfiles_api.urls)),
    url(r'^api/', include(actionpoint_api.urls)),

    # ***************  API version 2  ******************
    url(r'^api/locations/pcode/(?P<p_code>\w+)/$',
        LocationsViewSet.as_view({'get': 'retrieve'}),
        name='locations_detail_pcode'),
    url(r'^api/t2f/', include(t2f_patterns)),
    url(r'^api/v2/', include('reports.urls_v2')),
    url(r'^api/v2/', include('partners.urls_v2', namespace='partners_api')),
    url(r'^api/v2/users/', include('users.urls_v2')),
    url(r'^api/v2/funds/', include('funds.urls', namespace='funds')),


    url(r'^api/docs/', schema_view),
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

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
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
        url(r'^test/', djangosaml2.views.echo_attributes),
    ]
