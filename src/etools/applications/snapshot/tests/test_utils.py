
from django.forms import model_to_dict

from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.funds.tests.factories import FundsReservationHeaderFactory
from etools.applications.partners.tests.factories import (AgreementFactory, InterventionFactory,
                                                          PartnerFactory, PartnerStaffFactory,)
from etools.applications.snapshot import utils
from etools.applications.users.tests.factories import UserFactory


class TestJsonify(BaseTenantTestCase):
    def test_jsonify(self):
        intervention = InterventionFactory()
        j = utils.jsonify(model_to_dict(intervention))
        self.assertEqual(j["title"], intervention.title)

    def test_jsonify_unicode(self):
        staff = PartnerStaffFactory(first_name=u'R\xe4dda')
        agreement = AgreementFactory(agreement_type=u'R\xe4dda')
        agreement.authorized_officers.add(staff)
        j = utils.jsonify(model_to_dict(agreement))
        self.assertEqual(j["agreement_type"], agreement.agreement_type)


class TestGetToManyFieldNames(BaseTenantTestCase):
    def test_intervention(self):
        intervention = InterventionFactory()
        fields = utils.get_to_many_field_names(intervention.__class__)
        # check many_to_one field
        self.assertIn("frs", fields)
        # check many_to_many field
        self.assertIn("sections", fields)

    def test_partner(self):
        partner = PartnerFactory()
        fields = utils.get_to_many_field_names(partner.__class__)
        # check many_to_one field
        self.assertIn("staff_members", fields)

    def test_partner_staff(self):
        partner = PartnerFactory()
        partner_staff = PartnerStaffFactory(partner=partner)
        fields = utils.get_to_many_field_names(partner_staff.__class__)
        # check many_to_one field
        self.assertIn("signed_interventions", fields)
        # check many_to_many field
        self.assertIn("agreement_authorizations", fields)

    def test_agreement(self):
        agreement = AgreementFactory()
        fields = utils.get_to_many_field_names(agreement.__class__)
        # check many_to_one field
        self.assertIn("amendments", fields)


class TestCreateDictWithRelations(BaseTenantTestCase):
    def test_no_relation(self):
        intervention = InterventionFactory()
        obj_dict = utils.create_dict_with_relations(intervention)
        self.assertEqual(obj_dict["frs"], [])

    def test_relation(self):
        intervention = InterventionFactory()
        fr = FundsReservationHeaderFactory(intervention=intervention)
        obj_dict = utils.create_dict_with_relations(intervention)
        self.assertEqual(obj_dict["frs"], [fr.pk])

    def test_obj_none(self):
        obj_dict = utils.create_dict_with_relations(None)
        self.assertEqual(obj_dict, {})


class TestCreateChangeDict(BaseTenantTestCase):
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


class TestCreateSnapshot(BaseTenantTestCase):
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
