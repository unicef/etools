

from django.utils.translation import ugettext as _

from rest_framework import serializers

from etools.applications.core.mixins import ExportSerializerMixin
from etools.applications.funds.models import FundsReservationHeader, FundsReservationItem
from etools.applications.funds.serializers import Donor, FundsCommitmentItemSerializer, GrantSerializer


class FundsReservationHeaderExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsReservationHeader
        fields = '__all__'


class FundsReservationHeaderExportFlatSerializer(
        ExportSerializerMixin,
        FundsReservationHeaderExportSerializer
):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="intervention.number",
    )


class FundsReservationItemExportSerializer(serializers.ModelSerializer):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="fund_reservation.intervention.pk",
    )

    class Meta:
        model = FundsReservationItem
        fields = "__all__"


class FundsReservationItemExportFlatSerializer(
        ExportSerializerMixin,
        FundsReservationItemExportSerializer
):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="fund_reservation.intervention.number",
    )
    fund_reservation = serializers.CharField(source="fund_reservation.fr_number")


class FundsCommitmentItemExportFlatSerializer(
        ExportSerializerMixin,
        FundsCommitmentItemSerializer
):
    fund_commitment = serializers.CharField(source="fund_commitment.fc_number")


class GrantExportFlatSerializer(ExportSerializerMixin, GrantSerializer):
    donor = serializers.CharField(source="donor.name")


class DonorExportSerializer(serializers.ModelSerializer):
    grant = serializers.SerializerMethodField(label=_("Grant"))

    class Meta:
        model = Donor
        fields = "__all__"

    def get_grant(self, obj):
        return ", ".join(str(pk) for pk in obj.grant_set.values_list('pk', flat=True))


class DonorExportFlatSerializer(ExportSerializerMixin, DonorExportSerializer):
    def get_grant(self, obj):
        return ", ".join(name for name in obj.grant_set.values_list('name', flat=True))
