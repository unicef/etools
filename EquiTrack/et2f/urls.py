
from rest_framework import routers

from .views import TravelViewSet


api = routers.SimpleRouter()

api.register(r'travels', TravelViewSet, base_name='travels')