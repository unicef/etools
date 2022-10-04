import os
import tempfile
from datetime import timedelta
from unittest.mock import Mock, patch

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.utils import timezone

from unicef_attachments.models import Attachment
from unicef_notification.models import EmailTemplate

from etools.applications.attachments.tests.factories import AttachmentFileTypeFactory
from etools.applications.audit.models import RiskBluePrint
from etools.applications.audit.tests.factories import (
    AuditFocalPointUserFactory,
    AuditorStaffMemberFactory,
    AuditorUserFactory,
    AuditPartnerFactory,
    RiskFactory,
)
from etools.applications.users.tests.factories import SimpleUserFactory, UserFactory
from etools.libraries.djangolib.models import GroupWrapper


class AuditTestCaseMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command('update_notifications')
        call_command('update_audit_permissions', verbosity=0)

        # ensure media directory exists
        if not os.path.exists(settings.MEDIA_ROOT):
            os.makedirs(settings.MEDIA_ROOT)

    def setUp(self):
        super().setUp()
        EmailTemplate.objects.get_or_create(name='audit/staff_member/invite')
        EmailTemplate.objects.get_or_create(name='audit/engagement/submit_to_auditor')
        EmailTemplate.objects.get_or_create(name='audit/engagement/reported_by_auditor')

        GroupWrapper.invalidate_instances()

        self.auditor_firm = AuditPartnerFactory()

        self.auditor = AuditorUserFactory(partner_firm=self.auditor_firm)
        self.unicef_user = UserFactory(first_name='UNICEF User')
        self.unicef_focal_point = AuditFocalPointUserFactory(first_name='UNICEF Audit Focal Point')
        self.usual_user = SimpleUserFactory(first_name='Unknown user')


class EngagementTransitionsTestCaseMixin(AuditTestCaseMixin):
    engagement_factory = None
    endpoint = ''
    mock_filepath = Mock(return_value="{}test.pdf".format(settings.MEDIA_ROOT))
    filepath = "etools.applications.audit.utils.generate_file_path"

    def _fill_category(self, code, **kwargs):
        blueprints = RiskBluePrint.objects.filter(category__code=code)
        for blueprint in blueprints:
            RiskFactory(blueprint=blueprint, engagement=self.engagement, **kwargs)

    def _fill_date_fields(self):
        self.engagement.date_of_field_visit = timezone.now().date()
        self.engagement.date_of_draft_report_to_ip = self.engagement.date_of_field_visit + timedelta(days=1)
        self.engagement.date_of_comments_by_ip = self.engagement.date_of_draft_report_to_ip + timedelta(days=1)
        self.engagement.date_of_draft_report_to_unicef = self.engagement.date_of_comments_by_ip + timedelta(days=1)
        self.engagement.date_of_comments_by_unicef = self.engagement.date_of_draft_report_to_unicef + timedelta(days=1)
        self.engagement.save()

    def _add_attachment(self, code, name='audit'):
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix=".trash",
                                         dir=settings.MEDIA_ROOT) as temporary_file:
            try:
                temporary_file.write(b'\x04\x02')
                temporary_file.seek(0)
                file_type = AttachmentFileTypeFactory(
                    name=name,
                    label='audit',
                    group=['audit'],
                )

                attachment = Attachment(
                    content_object=self.engagement,
                    code=code,
                    file_type=file_type
                )

                attachment.file.save(
                    temporary_file.name,
                    File(temporary_file)
                )
                attachment.save()

            finally:
                if os.path.exists(temporary_file.name):
                    os.remove(temporary_file.name)

    def _init_filled_engagement(self):
        self._fill_date_fields()
        self._add_attachment('audit_report', name='report')

    def _init_submitted_engagement(self):
        self._init_filled_engagement()
        self.engagement.submit()
        self.engagement.save()

    def _init_finalized_engagement(self):
        self._init_submitted_engagement()
        with patch(self.filepath, self.mock_filepath):
            self.engagement.finalize()
            self.engagement.save()

    def _init_cancelled_engagement(self):
        self.engagement.cancel('cancel_comment')
        self.engagement.save()

    def engagements_url(self):
        return '/api/audit/{0}/'.format(self.endpoint)

    def engagement_url(self, postfix=None):
        if postfix and not postfix.endswith('/'):
            postfix += '/'
        return '{0}{1}/{2}'.format(self.engagements_url(), self.engagement.id, postfix or '')

    def setUp(self):
        super().setUp()

        self.engagement = self.engagement_factory(agreement__auditor_firm=self.auditor_firm)
        self.engagement.users_notified.add(SimpleUserFactory(first_name='To be Notified'))

        self.non_engagement_auditor = AuditorStaffMemberFactory(
            user__first_name='Auditor 2',
            auditor_firm=self.auditor_firm,
            user__profile__organization=self.auditor_firm.organization
        ).user
