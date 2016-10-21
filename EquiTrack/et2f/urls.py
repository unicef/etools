
from rest_framework import routers

from .views import TravelViewSet, TravelDetailsView


api = routers.SimpleRouter()

api.register(r'travels', TravelViewSet, base_name='travels')
# api.register(r'travels/(?P<travel_pk>[0-9]+)/', TravelDetailsView.as_view(), base_name='travel_details')