import base64
import json
from typing import Dict

from django.conf import settings

import requests


class PRPAPI(object):
    def __init__(self):
        self.url_prototype = settings.PRP_API_ENDPOINT
        self.username = settings.PRP_API_USER
        self.password = settings.PRP_API_PASSWORD

    def _get_headers(self, data=None):
        headers = {'Content-Type': 'application/json', 'Keep-Alive': '1800'}
        if data:
            headers['Content-Length'] = str(len(data))

        auth_pair_str = '%s:%s' % (self.username, self.password)
        headers['Authorization'] = 'Basic ' + \
                                   base64.b64encode(auth_pair_str.encode()).decode()
        return headers

    def _push_request(self, data=None, timeout=None):
        headers = self._get_headers(data)

        if data:
            r = requests.post(url=self.url, headers=headers, json=data, verify=True, timeout=timeout)
        else:
            r = requests.get(url=self.url, headers=headers, verify=True, timeout=timeout)

        # Any status code answer below 400 is OK
        if r.status_code >= 400:
            if r.status_code == 400:
                print(r.text)  # todo: cleanup
            r.raise_for_status()

        data = json.loads(r.text)
        return data

    def _simple_get_request(self, timeout=None):
        self._gen_auth_headers()
        r = self.http.get(
            url=self.url,
            headers=self.headers,
            verify=True,
            timeout=timeout
        )
        if r.status_code < 400:
            return json.loads(r.text)
        else:
            r.raise_for_status()

    def send_partner_data(self, business_area_code: str, partner_data: Dict):
        self.url = self.url_prototype + '/unicef/pmp/import/{0}/partner/'.format(business_area_code)
        # we send emails during users creation, so timeout increased a bit here
        response_data = self._push_request(data=partner_data, timeout=3000)
        return response_data
