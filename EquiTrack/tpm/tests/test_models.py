from __future__ import absolute_import, division, print_function, unicode_literals

from EquiTrack.tests.mixins import FastTenantTestCase
from tpm.tests.factories import TPMVisitFactory


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
            report_attachments__count=1,
            report_attachments__file_type__name='overall_report',
            tpm_activities__report_attachments__count=0
        )

        self.assertListEqual(
            [a.pv_applicable for a in visit.tpm_activities.all()],
            [True, True, True]
        )
