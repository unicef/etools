import os
import tempfile

from django.core.files import File

from attachments.models import FileType, Attachment
from tpm.models import PME, ThirdPartyMonitor, UNICEFUser, TPMVisit
from EquiTrack.factories import UserFactory, LocationFactory, SectionFactory
from utils.groups.wrappers import GroupWrapper
from .factories import TPMVisitFactory, TPMPartnerFactory, TPMPartnerStaffMemberFactory


class TPMTestCaseMixin(object):
    def _do_transition(self, visit, action, user, data={}):
        return self.forced_auth_req(
            'post',
            '/api/tpm/visits/{0}/{1}/'.format(visit.id, action),
            user=user,
            data=data
        )

    def _refresh_tpm_visit_instace(self, visit):
        # Calling refresh_from_db will cause an exception.
        return TPMVisit.objects.get(id=visit.id)

    def _add_attachment(self, code, instance):
        with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix=".trash") as temporary_file:
            try:
                temporary_file.write(b'\x04\x02')
                temporary_file.seek(0)
                file_type, created = FileType.objects.get_or_create(name='tpm', code='tpm')

                attachment = Attachment(
                    content_object=instance,
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

    def setUp(self):
        super(TPMTestCaseMixin, self).setUp()

        # clearing groups cache
        GroupWrapper.invalidate_instances()

        self.tpm_partner = TPMPartnerFactory()
        self.tpm_staff = TPMPartnerStaffMemberFactory(tpm_partner=self.tpm_partner)

        self.sections = [SectionFactory() for x in xrange(3)]
        for section in self.sections:
            section.sections.add(self.tenant)

        self.tpm_visit = TPMVisitFactory(tpm_partner=self.tpm_partner, sections=self.sections)

        self.unicef_user = UserFactory()
        self.unicef_user.groups = [
            UNICEFUser.as_group()
        ]
        self.pme_user = UserFactory()
        self.pme_user.groups = [
            PME.as_group(),
        ]

        self.tpm_user = self.tpm_staff.user
        self.tpm_user.groups = [
            ThirdPartyMonitor.as_group(),
        ]

        self.unicef_focal_point = UserFactory(first_name='UNICEF Focal Point')

        self.tpm_visit.unicef_focal_points.add(self.unicef_focal_point)

        for activity in self.tpm_visit.tpm_activities.all():
            activity.locations.add(*[LocationFactory() for x in xrange(3)])

        activity = self.tpm_visit.tpm_activities.first()
        activity.save()

        self.usual_user = UserFactory(first_name='Unknown user')
        self.usual_user.groups = []
