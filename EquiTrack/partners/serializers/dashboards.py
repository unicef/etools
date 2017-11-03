from __future__ import unicode_literals

from rest_framework import serializers


from partners.models import (
    Intervention,
)


class InterventionDashSerializer(serializers.ModelSerializer):
    intervention_id = serializers.CharField(source='id', read_only=True)
    partner_name = serializers.CharField(source='agreement.partner.name', read_only=True)
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    sections = serializers.SerializerMethodField()
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

    disbursement_percent = serializers.SerializerMethodField()
    days_last_pv = serializers.SerializerMethodField()
    last_pv_date = serializers.SerializerMethodField()

    def get_disbursement_percent(self, obj):
        percent = obj.total_frs["total_actual_amt"] / obj.total_unicef_cash * 100 \
            if obj.total_unicef_cash and obj.total_unicef_cash > 0 else 0
        return "%.1f" % percent

    def get_days_last_pv(self, obj):
        return obj.days_since_last_pv.days if obj.days_since_last_pv else None

    def get_last_pv_date(self, obj):
        return obj.last_pv_date

    def get_offices_names(self, obj):
        return ",".join(o.name for o in obj.offices.all())

    def get_sections(self, obj):
        return ", ".join([l.name for l in obj.sections.all()])

    def get_partner_name(self, obj):
        return obj.partner_name

    class Meta:
        model = Intervention
        fields = ('intervention_id', 'partner_id', 'partner_name', 'number', 'status', 'start', 'end',
                  'sections', 'offices_names',
                  'total_budget', 'cso_contribution', 'unicef_cash', 'unicef_supplies',
                  'frs_total_frs_amt', 'disbursement', 'disbursement_percent', 'last_pv_date', 'days_last_pv')
