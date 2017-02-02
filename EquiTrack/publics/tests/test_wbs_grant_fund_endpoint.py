from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from t2f.tests.factories import BusinessAreaFactory


class WBSGrantFundEndpoint(APITenantTestCase):
    def setUp(self):
        super(WBSGrantFundEndpoint, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_urls(self):
        details_url = reverse('wbs_grants_funds')
        self.assertEqual(details_url, '/api/wbs_grants_funds/')

    def test_wbs_grant_fund_view(self):
        business_area = BusinessAreaFactory()

        response = self.forced_auth_req('get', reverse('wbs_grants_funds'),
                                        data={'business_area': business_area.id},
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)

        self.assertKeysIn(['wbs', 'grants', 'funds'], response_json)
