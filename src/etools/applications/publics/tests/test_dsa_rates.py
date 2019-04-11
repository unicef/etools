import json
from datetime import date, datetime
from decimal import Decimal

from django.urls import reverse
from django.utils.timezone import now

from freezegun import freeze_time
from pytz import UTC

from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.publics.models import DSARate
from etools.applications.publics.tests.factories import (
    PublicsBusinessAreaFactory,
    PublicsCountryFactory,
    PublicsDSARateFactory,
    PublicsDSARegionFactory,
)
from etools.applications.users.tests.factories import UserFactory


class DSARateTest(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)

    def test_new_rate_addition(self):
        region = PublicsDSARegionFactory(rates=[])

        rate_1 = PublicsDSARateFactory(
            region=region,
            effective_from_date=date(2017, 4, 17)
        )
        self.assertEqual(rate_1.effective_to_date, DSARate.DEFAULT_EFFECTIVE_TILL)

        rate_2 = PublicsDSARateFactory(
            region=region,
            effective_from_date=date(2017, 4, 18)
        )
        rate_1.refresh_from_db()

        self.assertNotEqual(rate_1.effective_to_date, DSARate.DEFAULT_EFFECTIVE_TILL)
        self.assertNotEqual(rate_1.effective_to_date, DSARate.DEFAULT_EFFECTIVE_TILL)
        self.assertLess(rate_1.effective_to_date, rate_2.effective_from_date)

    def test_dsa_regions_view(self):
        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = '1234'
        workspace.save()

        business_area = PublicsBusinessAreaFactory(code=workspace.business_area_code)
        country = PublicsCountryFactory(business_area=business_area)

        region = PublicsDSARegionFactory(country=country, rates=[])

        with self.assertNumQueries(1):
            response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                            user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

        rate = PublicsDSARateFactory(region=region)

        response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assertEqual(response_json[0]['id'], region.id)

        # Expire rate - region should be excluded
        rate.delete()

        response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

    def test_values_history_retrieval(self):
        workspace = self.unicef_staff.profile.country
        workspace.business_area_code = '1234'
        workspace.save()

        business_area = PublicsBusinessAreaFactory(code=workspace.business_area_code)
        country = PublicsCountryFactory(business_area=business_area)

        region = PublicsDSARegionFactory(country=country, rates=[])

        with freeze_time('2017-04-01'):
            rate_1 = PublicsDSARateFactory(
                region=region,
                effective_from_date=date(2017, 4, 1),
                dsa_amount_usd=50
            )
        with freeze_time('2017-04-10'):
            rate_2 = PublicsDSARateFactory(
                region=region,
                effective_from_date=date(2017, 4, 10),
                dsa_amount_usd=80
            )

        date_str = date(2017, 4, 12).isoformat()
        response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(Decimal(response_json[0]['dsa_amount_usd']), rate_2.dsa_amount_usd)

        date_str = date(2017, 4, 6).isoformat()
        response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(Decimal(response_json[0]['dsa_amount_usd']), rate_1.dsa_amount_usd)

        date_str = date(2017, 3, 31).isoformat()
        response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

        rate_2.effective_to_date = date(2017, 4, 15)
        rate_2.save()

        date_str = datetime(2017, 4, 16, tzinfo=UTC).isoformat()
        response = self.forced_auth_req('get', reverse('publics:dsa_regions'),
                                        data={'values_at': date_str}, user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 0)

    def test_effective_from_date(self):
        region = PublicsDSARegionFactory(rates=[])

        now_date = now().date()
        rate_1 = PublicsDSARateFactory(
            region=region,
            effective_from_date=None
        )

        self.assertEqual(rate_1.effective_from_date, now_date)

        effective_from_date = date(2017, 4, 1)
        rate_2 = PublicsDSARateFactory(
            region=region,
            effective_from_date=effective_from_date
        )

        self.assertEqual(rate_2.effective_from_date, effective_from_date)
