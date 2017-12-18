from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from EquiTrack.tests.mixins import FastTenantTestCase as TenantTestCase
from partners.templatetags import intervention_tags as tags
from partners.tests.factories import (
    AgreementFactory,
    InterventionFactory,
    PartnerFactory,
)


class TestGetInterventions(TenantTestCase):
    def test_get(self):
        partner = PartnerFactory()
        agreement = AgreementFactory(partner=partner)
        intervention_1 = InterventionFactory(agreement=agreement)
        intervention_2 = InterventionFactory(agreement=agreement)
        intervention_3 = InterventionFactory()
        res = tags.get_interventions(partner.pk)
        self.assertIn(intervention_1.number, res)
        self.assertIn(intervention_2.number, res)
        self.assertNotIn(intervention_3.number, res)
