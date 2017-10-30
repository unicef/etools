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


class TestGetToManyFieldNames(TenantTestCase):
    def test_intervention(self):
        intervention = InterventionFactory()
        fields = utils.get_to_many_field_names(intervention.__class__)
        # check many_to_one field
        self.assertIn("frs", fields)
        # check many_to_many field
        self.assertIn("sections", fields)


class TestCreateDictWithRelations(TenantTestCase):
    def test_no_relation(self):
        intervention = InterventionFactory()
        obj_dict = utils.create_dict_with_relations(intervention)
        self.assertEqual(obj_dict["frs"], [])

    def test_relation(self):
        intervention = InterventionFactory()
        fr = FundsReservationHeaderFactory(intervention=intervention)
        obj_dict = utils.create_dict_with_relations(intervention)
        self.assertEqual(obj_dict["frs"], [fr.pk])


class TestCreateChangeDict(TenantTestCase):
    def test_no_prev_dict(self):
        self.assertEqual(utils.create_change_dict(None, {"key": "value"}), {})

    def test_change(self):
        before = {"test": "unknown"}
        after = {"test": "known"}
        change = utils.create_change_dict(before, after)
        self.assertEqual(change, {
            "test": {
                "before": "unknown",
                "after": "known"
            }
        })


class TestCreateSnapshot(TenantTestCase):
    def test_create(self):
        user = UserFactory()
        intervention = InterventionFactory()
        activity = utils.create_snapshot(intervention, {}, user)
        self.assertEqual(activity.target, intervention)
        self.assertEqual(activity.action, activity.CREATE)
        self.assertEqual(activity.by_user, user)
        self.assertEqual(activity.data["title"], intervention.title)
        self.assertEqual(activity.change, {})

    def test_update(self):
        user = UserFactory()
        intervention = InterventionFactory()
        obj_dict = utils.create_dict_with_relations(intervention)
        fr = FundsReservationHeaderFactory(intervention=intervention)
        activity = utils.create_snapshot(intervention, obj_dict, user)
        self.assertEqual(activity.target, intervention)
        self.assertEqual(activity.action, activity.UPDATE)
        self.assertEqual(activity.by_user, user)
        self.assertEqual(activity.data["title"], intervention.title)
        self.assertEqual(activity.change, {
            "frs": {
                "before": [],
                "after": [fr.pk]
            }
        })
