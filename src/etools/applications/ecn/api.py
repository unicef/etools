import json

from django.conf import settings

import jwt
import requests
from requests import HTTPError
from rest_framework_simplejwt.tokens import RefreshToken


class ECNAPI(object):
    def __init__(self, user):
        self.url_prototype = settings.ECN_API_ENDPOINT
        self.enabled = bool(self.url_prototype)
        self.user = user

    def generate_jwt(self):
        # copy from IssueJWTRedirectView
        refresh = RefreshToken.for_user(self.user)
        access = str(refresh.access_token)

        decoded_token = jwt.decode(access,
                                   settings.SIMPLE_JWT['VERIFYING_KEY'],
                                   [settings.SIMPLE_JWT['ALGORITHM']],
                                   audience=settings.SIMPLE_JWT['AUDIENCE'],
                                   leeway=settings.SIMPLE_JWT['LEEWAY'],
                                   )

        decoded_token.update({
            'groups': list(self.user.groups.values_list('name', flat=True)),
            'username': self.user.username,
            'email': self.user.email,
        })

        encoded = jwt.encode(
            decoded_token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithm=settings.SIMPLE_JWT['ALGORITHM']
        )
        # endcopy
        return encoded

    def _get_headers(self, data=None):
        headers = {'Content-Type': 'application/json', 'Keep-Alive': '1800'}
        if data:
            headers['Content-Length'] = str(len(data))

        jwt_token = self.generate_jwt()
        headers['Authorization'] = 'JWT ' + jwt_token
        return headers

    def _push_request(self, data=None, timeout=None):
        if not self.enabled:
            return

        headers = self._get_headers(data)

        if data:
            r = requests.post(url=self.url, headers=headers, json=data, verify=True, timeout=timeout)
        else:
            r = requests.get(url=self.url, headers=headers, verify=True, timeout=timeout)

        # Any status code answer below 400 is OK
        if r.status_code >= 400:
            r.raise_for_status()

        data = json.loads(r.text)
        return data

    def get_intervention(self, number: str) -> json:
        if not self.enabled:
            return

        self.url = self.url_prototype + '/pmp/v3/interventions/{0}/full-export/'.format(number)
        try:
            response_data = self._push_request(timeout=60)
        except HTTPError:
            return None

        return response_data
