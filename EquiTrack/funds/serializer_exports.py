from __future__ import unicode_literals

from django.utils.translation import ugettext as _
from rest_framework import serializers

from funds.models import (
    FundsReservationHeader,
    FundsReservationItem,
)
from funds.serializers import (
    Donor,
    FundsCommitmentItemSerializer,
    GrantSerializer,
)


class FundsReservationHeaderExportSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundsReservationHeader
        fields = '__all__'


class FundsReservationHeaderExportFlatSerializer(FundsReservationHeaderExportSerializer):
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


class FundsReservationItemExportFlatSerializer(FundsReservationItemExportSerializer):
    intervention = serializers.CharField(
        label=_("Reference Number"),
        source="fund_reservation.intervention.number",
    )
    fund_reservation = serializers.CharField(source="fund_reservation.fr_number")


class FundsCommitmentItemExportFlatSerializer(FundsCommitmentItemSerializer):
    fund_commitment = serializers.CharField(source="fund_commitment.fc_number")


class GrantExportFlatSerializer(GrantSerializer):
    donor = serializers.CharField(source="donor.name")


class DonorExportSerializer(serializers.ModelSerializer):
    grant = serializers.SerializerMethodField(label=_("Grant"))

    class Meta:
        model = Donor
        fields = "__all__"

    def get_grant(self, obj):
        return ", ".join([str(g.pk) for g in obj.grant_set.all()])


class DonorExportFlatSerializer(DonorExportSerializer):
    def get_grant(self, obj):
        return ", ".join([g.name for g in obj.grant_set.all()])
