
from rest_framework import routers

from .views import TravelViewSet, StaticDataViewSet


api = routers.SimpleRouter()

api.register(r'travels', TravelViewSet, base_name='travels')
api.register(r'static_data', StaticDataViewSet, base_name='static_data')
