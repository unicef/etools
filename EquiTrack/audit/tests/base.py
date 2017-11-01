import os
import tempfile
from datetime import timedelta

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.utils import timezone

from EquiTrack.factories import UserFactory
from attachments.models import FileType, Attachment
from audit.models import RiskBluePrint, UNICEFUser, UNICEFAuditFocalPoint
from utils.groups.wrappers import GroupWrapper
from .factories import RiskFactory, AuditorStaffMemberFactory, AuditPartnerFactory


class AuditTestCaseMixin(object):
    def setUp(self):
        super(AuditTestCaseMixin, self).setUp()

        GroupWrapper.invalidate_instances()

        self.auditor_firm = AuditPartnerFactory()
        self.auditor = self.auditor_firm.staff_members.first().user

        self.unicef_user = UserFactory()
        self.unicef_user.groups = [
            UNICEFUser.as_group()
        ]

        self.unicef_focal_point = UserFactory(first_name='UNICEF Focal Point')
        self.unicef_focal_point.groups = [
            UNICEFUser.as_group(),
            UNICEFAuditFocalPoint.as_group()
        ]

        self.usual_user = UserFactory(first_name='Unknown user')
        self.usual_user.groups = []


class EngagementTransitionsTestCaseMixin(AuditTestCaseMixin):
    engagement_factory = None
    endpoint = ''

    def _fill_category(self, code, **kwargs):
        blueprints = RiskBluePrint.objects.filter(category__code=code)
        for blueprint in blueprints:
            RiskFactory(blueprint=blueprint, engagement=self.engagement, **kwargs)

    def _fill_date_fields(self):
        self.engagement.date_of_field_visit = timezone.now()
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
                file_type, created = FileType.objects.get_or_create(name=name, label='audit', code='audit')

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
        self.engagement.finalize()
        self.engagement.save()

    def _init_cancelled_engagement(self):
        self.engagement.cancel('cancel_comment')
        self.engagement.save()

    def _engagement_url(self, postfix=None):
        if postfix and not postfix.endswith('/'):
            postfix += '/'
        return '/api/audit/{0}/{1}/{2}'.format(self.endpoint, self.engagement.id, postfix or '')

    def setUp(self):
        super(EngagementTransitionsTestCaseMixin, self).setUp()
        call_command('update_audit_permissions', verbosity=0)

        self.engagement = self.engagement_factory(agreement__auditor_firm=self.auditor_firm)

        self.non_engagement_auditor = AuditorStaffMemberFactory(
            user__first_name='Auditor 2',
            auditor_firm=self.auditor_firm
        ).user
