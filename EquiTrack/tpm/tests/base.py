from tpm.models import UNICEFFocalPoint, PME, ThirdPartyMonitor, UNICEFUser
from EquiTrack.factories import UserFactory
from .factories import TPMVisitFactory, TPMPartnerFactory, TPMPartnerStaffMemberFactory


class TPMTestCaseMixin(object):
    def setUp(self):
        super(TPMTestCaseMixin, self).setUp()

        # clearing groups cache
        ThirdPartyMonitor._group = None
        UNICEFUser._group = None
        UNICEFFocalPoint._group = None
        PME._group = None

        self.tpm_partner = TPMPartnerFactory()
        self.tpm_staff = TPMPartnerStaffMemberFactory(tpm_partner=self.tpm_partner)

        self.tpm_visit = TPMVisitFactory(tpm_partner=self.tpm_partner)

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
        self.unicef_focal_point.groups = [
            UNICEFFocalPoint.as_group()
        ]
        self.tpm_visit.unicef_focal_points.add(self.unicef_focal_point)

        self.usual_user = UserFactory(first_name='Unknown user')
        self.usual_user.groups = []
