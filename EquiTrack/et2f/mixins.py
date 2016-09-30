
from django.contrib.auth import authenticate


class TestingAuthMixin(object):
    def process_request(self, request):
        user = authenticate(username='puli', password='lab')
        request.user = user