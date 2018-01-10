from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime

from django.core.urlresolvers import reverse
from rest_framework import status

from EquiTrack.factories import (
    ActivityFactory,
    UserFactory,
)
from EquiTrack.tests.mixins import APITenantTestCase as TenantTestCase
from EquiTrack.utils import as_json
from snapshot.models import Activity


class TestActivityListView(TenantTestCase):
    def setUp(self):
        self.url = reverse("snapshot_api:activity-list")
        self.user = UserFactory(is_staff=True)

    def assert_data(self, activity, response):
        self.assertEqual(response["id"], activity.pk)
        self.assertEqual(response["by_user"], activity.by_user.pk)
        self.assertEqual(response["action"], activity.action)
        self.assertEqual(response["data"], activity.data)
        self.assertEqual(response["change"], activity.change)

    def test_empty(self):
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(response_json, [])

    def test_list(self):
        activity = ActivityFactory()
        response = self.forced_auth_req('get', self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_user(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        response = self.forced_auth_req('get', self.url, data={
            "user": activity.by_user.email
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
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
        response_json = as_json(response)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_action(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        response = self.forced_auth_req('get', self.url, data={
            "action": Activity.UPDATE
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_date_from(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2100, 2, 1)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_from": "2100-01-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_date_from_invalid(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2100, 2, 1)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_from": "00-01-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(response_json, [])

    def test_filter_date_to(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2001, 1, 1)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_to": "2001-02-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(len(response_json), 1)
        self.assert_data(activity, response_json[0])

    def test_filter_date_to_invalid(self):
        ActivityFactory(action=Activity.CREATE)
        activity = ActivityFactory(action=Activity.UPDATE)
        activity.created = datetime.datetime(2001, 1, 1)
        activity.save()
        response = self.forced_auth_req('get', self.url, data={
            "date_to": "01-02-01"
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_json = as_json(response)
        self.assertEqual(response_json, [])
