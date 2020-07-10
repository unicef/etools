from etools.applications.partners.models import PartnerOrganization


class PMPBaseViewMixin:
    SERIALIZER_MAP = {}

    def is_partner_staff(self):
        """Flag indicator whether user is a partner"""
        return self.request.user.profile.partner_staff_member

    def partners(self):
        """List of partners user associated with"""
        if not self.is_partner_staff():
            return []
        return PartnerOrganization.objects.filter(
            staff_members__email=self.request.user.email,
        )

    def map_serializer(self, serializer):
        default_serializer, partner_staff_serializer = self.SERIALIZER_MAP.get(
            serializer,
            (None, None),
        )
        if self.is_partner_staff():
            return partner_staff_serializer
        return default_serializer
