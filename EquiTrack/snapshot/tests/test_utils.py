from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from EquiTrack.factories import (
    FundsReservationHeaderFactory,
    InterventionFactory,
    UserFactory,
)
from django.forms import model_to_dict
from snapshot import utils


class TestJsonify(TenantTestCase):
    def test_jsonify(self):
        intervention = InterventionFactory()
        j = utils.jsonify(model_to_dict(intervention))
        self.assertEqual(j["title"], intervention.title)


class TestSetRelationValues(TenantTestCase):
    def test_no_relation(self):
        intervention = InterventionFactory()
        obj_dict, data = utils.set_relation_values(intervention, {})
        self.assertEqual(obj_dict["frs"], [])
        self.assertEqual(data, {})

    def test_data_relation(self):
        intervention = InterventionFactory()
        fr = FundsReservationHeaderFactory(intervention=None)
        obj_dict, data = utils.set_relation_values(intervention, {"frs": [fr]})
        self.assertEqual(obj_dict["frs"], [])
        self.assertDictEqual(data, {"frs": [fr.pk]})

    def test_obj_relation(self):
        intervention = InterventionFactory()
        fr = FundsReservationHeaderFactory(intervention=intervention)
        obj_dict, data = utils.set_relation_values(intervention, {})
        self.assertEqual(obj_dict["frs"], [fr.pk])
        self.assertDictEqual(data, {})

    def test_both_relation(self):
        intervention = InterventionFactory()
        fr = FundsReservationHeaderFactory(intervention=intervention)
        obj_dict, data = utils.set_relation_values(intervention, {"frs": [fr]})
        self.assertEqual(obj_dict["frs"], [fr.pk])
        self.assertDictEqual(data, {"frs": [fr.pk]})


class TestCreateChangeDict(TenantTestCase):
    def test_no_target_before(self):
        self.assertEqual(utils.create_change_dict(None, {"key": "value"}), {})

    def test_no_data(self):
        intervention = InterventionFactory()
        change = utils.create_change_dict(intervention, {})
        self.assertEqual(change, {})

    def test_change(self):
        intervention = InterventionFactory()
        fr = FundsReservationHeaderFactory(intervention=None)
        change = utils.create_change_dict(intervention, {"frs": [fr]})
        self.assertEqual(change, {"frs": {"before": [], "after": [fr.pk]}})


class TestCreateSnapshot(TenantTestCase):
    def test_create(self):
        user = UserFactory()
        intervention = InterventionFactory()
        activity = utils.create_snapshot(intervention, user, {})
        self.assertEqual(activity.target, intervention)
        self.assertEqual(activity.action, activity.CREATE)
        self.assertEqual(activity.by_user, user)
        self.assertEqual(activity.data["title"], intervention.title)
        self.assertEqual(activity.change, "")

    def test_update(self):
        user = UserFactory()
        intervention = InterventionFactory()
        change = {"title": {"before": "Random", "after": intervention.title}}
        activity = utils.create_snapshot(intervention, user, change)
        self.assertEqual(activity.target, intervention)
        self.assertEqual(activity.action, activity.UPDATE)
        self.assertEqual(activity.by_user, user)
        self.assertEqual(activity.data["title"], intervention.title)
        self.assertEqual(activity.change, change)
