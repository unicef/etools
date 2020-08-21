from django.http import Http404

from rest_framework.permissions import IsAuthenticated

from etools.applications.partners.models import Intervention, PartnerOrganization


class PMPBaseViewMixin:
    # TODO need to set correct permissions
    # see ch21937
    permission_classes = [IsAuthenticated]

    def is_partner_staff(self):
        """Flag indicator whether user is a partner"""
        return self.request.user.is_authenticated and self.request.user.profile.partner_staff_member

    def partners(self):
        """List of partners user associated with"""
        if not self.is_partner_staff():
            return []
        return PartnerOrganization.objects.filter(
            staff_members__email=self.request.user.email,
        )

    def get_pd(self, pd_pk):
        try:
            if not self.is_partner_staff():
                return Intervention.objects.get(pk=pd_pk)
            return self.pds().get(pk=pd_pk)
        except Intervention.DoesNotExist:
            return None

    def get_pd_or_404(self, pd_pk):
        pd = self.get_pd(pd_pk)
        if pd is None:
            raise Http404
        return pd

    def pds(self):
        """List of PDs user associated with"""
        if not self.is_partner_staff():
            return []
        return Intervention.objects.filter(
            partner_focal_points__email=self.request.user.email,
        )

    def offices(self):
        """List of Offices user associated with"""
        if not self.is_partner_staff():
            return []
        return Intervention.objects.filter(
            partner_focal_points__email=self.request.user.email,
        )

    def map_serializer(self, serializer):
        default_serializer, partner_serializer = self.SERIALIZER_OPTIONS.get(
            serializer,
            (None, None),
        )
        if self.is_partner_staff():
            return partner_serializer
        return default_serializer
