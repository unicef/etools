from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from funds.serializers import FRsSerializer
from partners.permissions import InterventionPermissions
from reports.serializers.v1 import SectorLightSerializer
from reports.serializers.v2 import LowerResultSerializer, LowerResultCUSerializer
from locations.models import Location

from partners.models import (
    InterventionBudget,
    SupplyPlan,
    DistributionPlan,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    InterventionAttachment,
    InterventionSectorLocationLink,
    InterventionResultLink,
)
from reports.models import LowerResult
from locations.serializers import LocationLightSerializer
from funds.models import FundsCommitmentItem, FundsReservationHeader


class InterventionDashSerializer(serializers.ModelSerializer):
    partner_name = serializers.CharField(source='agreement.partner.name', read_only=True)

    sectors = serializers.SerializerMethodField()
    offices_names = serializers.SerializerMethodField()

    unicef_cash = serializers.DecimalField(source='total_unicef_cash', read_only=True, max_digits=20, decimal_places=2)
    unicef_supplies = serializers.DecimalField(source='total_in_kind_amount', read_only=True, max_digits=20,
                                               decimal_places=2)
    cso_contribution = serializers.DecimalField(source='total_partner_contribution', read_only=True, max_digits=20,
                                                decimal_places=2)

    total_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)

    disbursement = serializers.DecimalField(source='total_frs.total_actual_amt', read_only=True,
                                             max_digits=20,
                                             decimal_places=2)

    frs_total_frs_amt = serializers.DecimalField(source='total_frs.total_frs_amt', read_only=True,
                                                 max_digits=20,
                                                 decimal_places=2)

    days_last_pv = serializers.SerializerMethodField()


    def get_days_last_pv(self, obj):
        return 0

    def get_offices_names(self, obj):
        return [o.name for o in obj.offices.all()]

    def get_sectors(self, obj):
        return [l.sector.name for l in obj.sector_locations.all()]



    class Meta:
        model = Intervention
        fields = ('partner_name', 'number', 'sectors', 'offices_names', 'status', 'start', 'end',
                  'days_last_pv', 'frs_total_frs_amt', 'disbursement', 'total_budget', 'cso_contribution',
                  'unicef_cash', 'unicef_supplies', )
