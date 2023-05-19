import json

from django.conf import settings

from requests import HTTPError

from etools.applications.core.jwt_api import BaseJWTAPI


class ECNAPI(BaseJWTAPI):
    def __init__(self, user):
        super().__init__(user, url=settings.ECN_API_ENDPOINT)

    def get_intervention(self, number: str) -> json:
        if not self.enabled:
            return

        self.url = self.url_prototype + '/pmp/v3/interventions/{0}/full-export/'.format(number)
        try:
            response_data = self._push_request(timeout=60)
        except HTTPError:
            return None

        return response_data
