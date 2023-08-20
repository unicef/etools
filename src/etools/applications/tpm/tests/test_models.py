from unicef_attachments.utils import get_denormalize_func

from etools.applications.attachments.tests.factories import AttachmentFactory
from etools.applications.core.tests.cases import BaseTenantTestCase
from etools.applications.tpm.tests.factories import TPMVisitFactory


class TestTPMVisit(BaseTenantTestCase):
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


class TestTPMActivity(BaseTenantTestCase):
    def test_activity_attachment_without_intervention(self):
        visit = TPMVisitFactory(tpm_activities__count=1)
        activity = visit.tpm_activities.first()
        activity.intervention = None
        activity.save()

        attachment = AttachmentFactory(content_object=activity)
        get_denormalize_func()(attachment)
