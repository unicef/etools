import base64
import json
from typing import Dict, Iterable, NamedTuple

from django.conf import settings

import requests


class PRPPartnerResponse(NamedTuple):
    id: int
    external_id: str
    unicef_vendor_number: str
    name: str


class PRPPartnerUserResponse(NamedTuple):
    email: str
    title: str
    first_name: str
    last_name: str
    phone_number: str
    is_active: bool


class PRPAPI(object):
    def __init__(self):
        self.url_prototype = settings.PRP_API_ENDPOINT
        self.username = settings.PRP_API_USER
        self.password = settings.PRP_API_PASSWORD
        self.enabled = bool(self.url_prototype)

    def _get_headers(self, data=None):
        headers = {'Content-Type': 'application/json', 'Keep-Alive': '1800'}
        if data:
            headers['Content-Length'] = str(len(data))

        auth_pair_str = '%s:%s' % (self.username, self.password)
        headers['Authorization'] = 'Basic ' + \
                                   base64.b64encode(auth_pair_str.encode()).decode()
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

    def _simple_get_request(self, timeout=None):
        if not self.enabled:
            return

        r = requests.get(url=self.url, headers=self._get_headers(), verify=True, timeout=timeout)
        if r.status_code >= 400:
            r.raise_for_status()

        return json.loads(r.text)

    def send_partner_data(self, business_area_code: str, partner_data: Dict):
        if not self.enabled:
            return

        self.url = self.url_prototype + '/unicef/pmp/import/{0}/partner/'.format(business_area_code)
        # we send emails during users creation, so timeout increased a bit here
        response_data = self._push_request(data=partner_data, timeout=3000)
        return response_data

    def get_partners_list(self) -> Iterable[PRPPartnerResponse]:
        if not self.enabled:
            return []

        base_url = self.url_prototype + '/unicef/pmp/export/partners/?page={0}&page_size={1}'
        page = 1
        page_size = 50
        while True:
            self.url = base_url.format(page, page_size)
            response_data = self._simple_get_request(timeout=300)
            yield from (PRPPartnerResponse(**data) for data in response_data['results'])

            if response_data['count'] <= page * page_size:
                break

            page += 1

    def get_partner_staff_members(self, partner_id: int) -> Iterable[PRPPartnerUserResponse]:
        if not self.enabled:
            return []

        base_url = self.url_prototype + '/unicef/pmp/export/partners/{0}/staff-members/?page={1}&page_size={2}'
        page = 1
        page_size = 50
        while True:
            self.url = base_url.format(partner_id, page, page_size)
            response_data = self._simple_get_request(timeout=300)
            yield from (PRPPartnerUserResponse(**data) for data in response_data['results'])

            if response_data['count'] <= page * page_size:
                break

            page += 1
