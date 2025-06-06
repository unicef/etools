from rest_framework.test import APIRequestFactory

from etools.applications.governments.permissions import PartnershipManagerPermission
from etools.applications.governments.tests.factories import GDDFactory
from etools.applications.governments.tests.test_gdds import BaseGDDTestCase
from etools.applications.organizations.models import OrganizationType
from etools.applications.organizations.tests.factories import OrganizationFactory
from etools.applications.partners.tests.factories import PartnerFactory
from etools.applications.users.tests.factories import UserFactory


class DummyView:
    def __init__(self, gdd_pk):
        self.kwargs = {"gdd_pk": gdd_pk}


class TestPartnershipManagerPermissionTestCase(BaseGDDTestCase):

    def _make_request(self, user):
        request = APIRequestFactory().get("/dummy/")
        request.user = user
        return request

    def test_user_is_partner_staff__returns_true(self):
        partner = PartnerFactory(
            organization=OrganizationFactory(
                name='Government Org 1', vendor_number="VP1 GDD", organization_type=OrganizationType.GOVERNMENT)
        )

        gdd = GDDFactory(partner=partner, date_sent_to_partner=None)
        staff_member = UserFactory(
            realms__data=['IP Viewer'],
            profile__organization=gdd.partner.organization,
        )

        gdd.partner_focal_points.add(staff_member)

        self.assertTrue(partner.user_is_staff_member(staff_member))

        perm = PartnershipManagerPermission()
        view = DummyView(gdd.pk)
        request = self._make_request(staff_member)

        self.assertTrue(perm._is_partner_staff_for_gdd(request, view))

    def test_user_not_partner_staff__returns_false(self):
        partner = PartnerFactory()
        gdd = GDDFactory(partner=partner)

        outsider = UserFactory()
        perm = PartnershipManagerPermission()
        request = self._make_request(outsider)
        view = DummyView(gdd.pk)

        self.assertFalse(perm._is_partner_staff_for_gdd(request, view))
