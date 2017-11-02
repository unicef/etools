from EquiTrack.tests.mixins import FastTenantTestCase
from .factories import TPMVisitFactory, TPMActivityFactory


class TestTPMVisit(FastTenantTestCase):
    def test_attachments_pv_applicable(self):
        visit = TPMVisitFactory(status='tpm_reported', tpm_activities__count=3)
        visit.tpm_activities.first().report_attachments.all().delete()

        self.assertListEqual(
            [a.pv_applicable for a in visit.tpm_activities.all()],
            [False, True, True]
        )

    def test_visit_attachments_pv_applicable(self):
        visit = TPMVisitFactory(
            status='tpm_reported',
            tpm_activities__count=3,
            report_attachments__reports_count=1,
            tpm_activities__report_attachments__reports_count=0
        )

        self.assertListEqual(
            [a.pv_applicable for a in visit.tpm_activities.all()],
            [True, True, True]
        )
