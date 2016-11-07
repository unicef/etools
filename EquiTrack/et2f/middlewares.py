
from django.contrib.auth import authenticate

from et2f import PULI_USER_USERNAME, PULI_USER_PASSWORD


# DEVELOPMENT CODE - START
class TestingAuthMiddleware(object):
    def process_request(self, request):
        user = authenticate(username=PULI_USER_USERNAME, password=PULI_USER_PASSWORD)
        request.user = user
# DEVELOPMENT CODE - END
