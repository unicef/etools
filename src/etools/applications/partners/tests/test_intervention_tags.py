
from etools.applications.EquiTrack.tests.cases import BaseTenantTestCase
from etools.applications.partners.templatetags import intervention_tags as tags
from etools.applications.partners.tests.factories import AgreementFactory, InterventionFactory, PartnerFactory


class TestGetInterventions(BaseTenantTestCase):
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
