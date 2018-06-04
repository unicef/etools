
import datetime
import json

from django.core.urlresolvers import reverse
from django.utils import timezone

from rest_framework import status

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.snapshot.models import Activity
from etools.applications.snapshot.tests.factories import ActivityFactory
from etools.applications.users.tests.factories import UserFactory


class TestActivityListView(BaseTenantTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.url = reverse("snapshot:activity-list")
        cls.user = UserFactory(is_staff=True)
        cls.tz = timezone.get_default_timezone()

    def assert_data(self, activity, response):
        self.assertEqual(response["id"], activity.pk)
        self.assertEqual(response["by_user"], activity.by_user.pk)
        self.assertEqual(response["action"], activity.action)
        self.assertEqual(response["data"], activity.data)
        self.assertEqual(response["change"], activity.change)

    def test_empty(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, [])

    def test_list(self):
        activity = ActivityFactory()
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_user(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        response = self.forced_auth_req('get', self.url, data={
            "user": activity.by_user.email
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_target(self):
        user = UserFactory()
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE, target=user)
        response = self.forced_auth_req('get', self.url, data={
            "target": user.__class__.__name__
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_action(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        response = self.forced_auth_req('get', self.url, data={
            "action": Activity.UPDATE
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_date_from(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2100, 2, 1, tzinfo=self.tz)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_from": "2100-01-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_date_from_invalid(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2100, 2, 1, tzinfo=self.tz)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_from": "00-01-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, [])

    def test_filter_date_to(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2001, 1, 1, tzinfo=self.tz)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_to": "2001-02-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_date_to_invalid(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2001, 1, 1, tzinfo=self.tz)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_to": "01-02-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = json.loads(response.rendered_content)
        self.assertEqual(response_json, [])
