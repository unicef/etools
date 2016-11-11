
from rest_framework import routers

from et2f.views import CurrentUserViewSet
from .views import TravelViewSet, StaticDataViewSet, PermissionMatrixViewSet


api = routers.SimpleRouter()

api.register(r'travels', TravelViewSet, base_name='travels')
api.register(r'static_data', StaticDataViewSet, base_name='static_data')
api.register(r'permission_matrix', PermissionMatrixViewSet, base_name='permission_matrix')
api.register(r'me', CurrentUserViewSet, base_name='current_user')
