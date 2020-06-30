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
        self.http = requests.Session()

    def _gen_auth_headers(self, data=None):
        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['Keep-Alive'] = '1800'
        if data:
            headers['Content-Length'] = len(data)

        auth_pair_str = '%s:%s' % (self.username, self.password)
        headers['Authorization'] = 'Basic ' + \
                                   base64.b64encode(auth_pair_str.encode()).decode()
        self.headers = headers

    def _push_request(self, data=None, timeout=None):
        try:
            self._gen_auth_headers(data)
            # POST
            if data:
                self.headers['Content-Type'] = 'application/x-www-form-urlencoded'
                r = self.http.post(
                    url=self.url,
                    headers=self.headers,
                    data=data,
                    verify=True,
                    timeout=timeout
                )
            # GET
            else:
                r = self.http.get(
                    url=self.url,
                    headers=self.headers,
                    verify=True,
                    timeout=timeout
                )
            # Any status code answer below 400 is OK
            if r.status_code < 400:
                content = r.text
            else:
                r.raise_for_status()

            try:
                data = json.loads(content)
            except Exception as e:
                Exception(e)

            return data
        except Exception as e:
            raise Exception(e)

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
        self.url = self.url_prototype + '/unicef/{0}/partners/sync/'.format(business_area_code)
        # we send emails during users creation, so timeout increased a bit here
        response_data = self._push_request(data=partner_data, timeout=3000)
        return response_data
