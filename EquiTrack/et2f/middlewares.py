
from django.contrib.auth import authenticate

from et2f import PULI_USER_USERNAME, PULI_USER_PASSWORD


class CSRFExemptMiddleware(object):
    def process_request(self, request):
        """
        Rest framework session based authentication cannot handle csrf_exempt decorator.
        This will prevent csrf related issues with post requests
        """
        request.csrf_processing_done = True


# DEVELOPMENT CODE - START
class TestingAuthMiddleware(object):
    def process_request(self, request):
        user = authenticate(username=PULI_USER_USERNAME, password=PULI_USER_PASSWORD)
        request.user = user
# DEVELOPMENT CODE - END
