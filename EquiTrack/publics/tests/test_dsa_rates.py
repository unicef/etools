from __future__ import unicode_literals

from datetime import datetime
from decimal import Decimal
from freezegun import freeze_time
import json
from pytz import UTC

from django.core.urlresolvers import reverse

from EquiTrack.factories import UserFactory
from EquiTrack.tests.mixins import APITenantTestCase
from publics.models import DSARate
from publics.tests.factories import DSARegionFactory, DSARateFactory, BusinessAreaFactory, CountryFactory


class DSARateTest(APITenantTestCase):

    def setUp(self):
        super(DSARateTest, self).setUp()
        self.unicef_staff = UserFactory(is_staff=True)

    def test_attribute_fallback(self):
        region = DSARegionFactory()
        rate = DSARateFactory(region=region)

        self.assertEqual(region.area_code, rate.area_code)
        self.assertEqual(region.area_name, rate.area_name)
        self.assertEqual(region.country, rate.country)
        self.assertEqual(region.unique_name, rate.unique_name)
        self.assertEqual(region.unique_id, rate.unique_id)
        self.assertEqual(region.dsa_amount_usd, rate.dsa_amount_usd)
        self.assertEqual(region.dsa_amount_60plus_usd, rate.dsa_amount_60plus_usd)
        self.assertEqual(region.dsa_amount_local, rate.dsa_amount_local)
        self.assertEqual(region.dsa_amount_60plus_local, rate.dsa_amount_60plus_local)
        self.assertEqual(region.room_rate, rate.room_rate)
        self.assertEqual(region.finalization_date, rate.finalization_date)
        self.assertEqual(region.eff_date, rate.eff_date)

        with self.assertRaises(AttributeError):
            region.not_a_fallback_attribute
            
        with self.assertRaises(AttributeError):
            rate.nonexisting_attribute

    def test_new_rate_addition(self):
        region = DSARegionFactory()

        rate_1 = DSARateFactory(region=region,
                                valid_from=datetime(2017, 4, 17, tzinfo=UTC))
        self.assertEqual(rate_1.valid_to, DSARate.DEFAULT_VALID_TO)

        rate_2 = DSARateFactory(region=region,
                                valid_from=datetime(2017, 4, 18, tzinfo=UTC))
        rate_1.refresh_from_db()

        self.assertNotEqual(rate_1.valid_to, DSARate.DEFAULT_VALID_TO)
        self.assertLess(rate_1.valid_to, rate_2.valid_from)

    def test_dsa_regions_view(self):
        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = '1234'
        workspace.save()

        business_area = BusinessAreaFactory(code=workspace.business_area_code)
        country = CountryFactory(business_area=business_area)

        region = DSARegionFactory(country=country)

        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                            user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

        rate = DSARateFactory(region=region)

        response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[0]['id'], region.id)

        # Expire rate - region should be excluded
        rate.valid_to = UTC.localize(datetime.utcnow())
        rate.save()

        response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

    def test_dsa_regions_in_static_view(self):
        # TODO remove this test after static endpoint is split on frontend too
        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = '1234'
        workspace.save()

        business_area = BusinessAreaFactory(code=workspace.business_area_code)
        country = CountryFactory(business_area=business_area)

        region = DSARegionFactory(country=country)

        response = self.forced_auth_req('get', reverse('public:static'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['dsa_regions']), 0)

        rate = DSARateFactory(region=region)

        response = self.forced_auth_req('get', reverse('public:static'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['dsa_regions']), 1)
        self.assertEqual(response_json['dsa_regions'][0]['id'], region.id)

        # Expire rate - region should be excluded
        rate.valid_to = UTC.localize(datetime.utcnow())
        rate.save()

        response = self.forced_auth_req('get', reverse('public:static'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json['dsa_regions']), 0)

    def test_values_history_retrieval(self):
        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = '1234'
        workspace.save()

        business_area = BusinessAreaFactory(code=workspace.business_area_code)
        country = CountryFactory(business_area=business_area)

        region = DSARegionFactory(country=country)

        with freeze_time('2017-04-01'):
            rate_1 = DSARateFactory(region=region,
                                    valid_from=datetime(2017, 4, 1, tzinfo=UTC),
                                    dsa_amount_usd=50)
        with freeze_time('2017-04-10'):
            rate_2 = DSARateFactory(region=region,
                                    valid_from=datetime(2017, 4, 10, tzinfo=UTC),
                                    dsa_amount_usd=80)

        date_str = datetime(2017, 4, 12, tzinfo=UTC).isoformat()
        response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(Decimal(response_json[0]['dsa_amount_usd']), rate_2.dsa_amount_usd)

        date_str = datetime(2017, 4, 6, tzinfo=UTC).isoformat()
        response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(Decimal(response_json[0]['dsa_amount_usd']), rate_1.dsa_amount_usd)

        date_str = datetime(2017, 3, 31, tzinfo=UTC).isoformat()
        response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

        rate_2.valid_to = datetime(2017, 4, 15, tzinfo=UTC)
        rate_2.save()

        date_str = datetime(2017, 4, 16, tzinfo=UTC).isoformat()
        response = self.forced_auth_req('get', reverse('public:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)
