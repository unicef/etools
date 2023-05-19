import json
from typing import Dict, Iterable, NamedTuple

from django.conf import settings
from django.contrib.auth import get_user_model

import requests

from etools.applications.core.jwt_api import BaseJWTAPI


# TODO cleanup
class PRPPartnerResponse(NamedTuple):
    id: int
    external_id: str
    unicef_vendor_number: str
    name: str


# TODO cleanup
class PRPPartnerUserResponse(NamedTuple):
    email: str
    title: str
    first_name: str
    last_name: str
    phone_number: str
    is_active: bool


class PRPAPI(BaseJWTAPI):
    def __init__(self, user=None):
        if not user:
            user = get_user_model().objects.get(pk=settings.PRP_API_USER)
        super().__init__(user, url=settings.PRP_API_ENDPOINT)

    def _simple_get_request(self, timeout=None):
        if not self.enabled:
            return

        r = requests.get(url=self.url, headers=self._get_headers(), verify=True, timeout=timeout)
        if r.status_code >= 400:
            r.raise_for_status()

        return json.loads(r.text)

    # TODO clean up: endpoint removed in prp
    def send_partner_data(self, business_area_code: str, partner_data: Dict):
        if not self.enabled:
            return

        self.url = self.url_prototype + '/unicef/pmp/import/{0}/partner/'.format(business_area_code)
        # we send emails during users creation, so timeout increased a bit here
        response_data = self._push_request(data=partner_data, timeout=3000)
        return response_data

    # TODO clean up: endpoint removed in prp
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

    # TODO clean up: endpoint removed in prp
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

    def send_user_realms(self, data: dict):
        if not self.enabled:
            return

        self.url = self.url_prototype + '/unicef/users/realms/import/'
        response_data = self._push_request(data=data)
        return response_data
