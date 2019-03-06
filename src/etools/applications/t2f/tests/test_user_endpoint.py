import json
from unittest.mock import Mock, patch

from django.conf import settings
from django.urls import reverse

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.t2f.models import Travel
from etools.applications.t2f.serializers.mailing import TravelMailSerializer
from etools.applications.t2f.tests.factories import TravelFactory
from etools.applications.users.tests.factories import UserFactory


class UserT2FData(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.unicef_staff = UserFactory(is_staff=True)
        cls.travel = TravelFactory(traveler=cls.unicef_staff,
                                   supervisor=cls.unicef_staff)

    def get_user_t2f_data(self):
        response = self.forced_auth_req('get', '/users/api/profile/',
                                        user=self.unicef_staff)
        response_json = json.loads(response.rendered_content)
        return response_json

    def test_travel_count(self):
        response_json = self.get_user_t2f_data()
        self.assertEqual(response_json['t2f'], {'roles': ['Anyone'], 'business_area': None})

        mock_send = Mock()
        with patch("etools.applications.t2f.models.send_notification", mock_send):
            self.forced_auth_req(
                'post',
                reverse(
                    't2f:travels:details:state_change',
                    kwargs={
                        'travel_pk': self.travel.id,
                        'transition_name': Travel.CANCEL,
                    },
                ),
                user=self.unicef_staff,
            )

        response_json = self.get_user_t2f_data()
        self.assertEqual(response_json['t2f'], {'roles': ['Anyone'], 'business_area': None})
        mock_send.assert_called_with(
            recipients=[
                self.travel.traveler.email,
                self.travel.supervisor.email,
            ],
            from_address=settings.DEFAULT_FROM_EMAIL,
            subject='Travel #{} was cancelled.'.format(
                self.travel.reference_number,
            ),
            html_content_filename='emails/cancelled.html',
            context={
                "travel": TravelMailSerializer(self.travel, context={}).data,
                "url": self.travel.get_object_url(),
            }
        )
