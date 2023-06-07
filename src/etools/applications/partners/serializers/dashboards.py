import datetime

from rest_framework import serializers

from etools.applications.partners.models import Intervention


class InterventionDashSerializer(serializers.ModelSerializer):
    intervention_id = serializers.CharField(source='id', read_only=True)
    partner_name = serializers.CharField(source='agreement.partner.organization.name', read_only=True)
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    partner_blocked = serializers.BooleanField(source='agreement.partner.blocked', read_only=True)
    partner_marked_for_deletion = serializers.BooleanField(source='agreement.partner.deleted_flag', read_only=True)
    sections = serializers.SerializerMethodField()
    offices_names = serializers.SerializerMethodField()
    budget_currency = serializers.CharField(source='planned_budget.currency', read_only=True)

    unicef_cash = serializers.DecimalField(source='total_unicef_cash', read_only=True, max_digits=20, decimal_places=2)
    unicef_supplies = serializers.DecimalField(source='total_in_kind_amount', read_only=True, max_digits=20,
                                               decimal_places=2)
    cso_contribution = serializers.DecimalField(source='total_partner_contribution', read_only=True, max_digits=20,
                                                decimal_places=2)

    total_budget = serializers.DecimalField(read_only=True, max_digits=20, decimal_places=2)

    disbursement = serializers.DecimalField(source='frs__actual_amt_local__sum', read_only=True,
                                            max_digits=20,
                                            decimal_places=2)

    frs_total_frs_amt = serializers.DecimalField(source='frs__total_amt_local__sum', read_only=True,
                                                 max_digits=20,
                                                 decimal_places=2)

    disbursement_percent = serializers.SerializerMethodField()
    days_last_pv = serializers.SerializerMethodField()
    last_pv_date = serializers.DateField()

    fr_currencies_are_consistent = serializers.SerializerMethodField()
    all_currencies_are_consistent = serializers.SerializerMethodField()
    fr_currency = serializers.SerializerMethodField()

    partner_vendor_number = serializers.CharField(source='agreement.partner.vendor_number', read_only=True)
    outstanding_dct = serializers.DecimalField(source='frs__outstanding_amt_local__sum', read_only=True,
                                               max_digits=20, decimal_places=2)
    frs_total_frs_amt_usd = serializers.DecimalField(source='frs__total_amt__sum', read_only=True,
                                                     max_digits=20, decimal_places=2)
    disbursement_usd = serializers.DecimalField(source='frs__actual_amt__sum',
                                                read_only=True, max_digits=20, decimal_places=2)
    outstanding_dct_usd = serializers.DecimalField(source='frs__outstanding_amt__sum',
                                                   read_only=True, max_digits=20, decimal_places=2)
    multi_curr_flag = serializers.BooleanField()
    has_final_partnership_review = serializers.SerializerMethodField()
    action_points = serializers.IntegerField()

    link = serializers.SerializerMethodField()

    def fr_currencies_ok(self, obj):
        return obj.frs__currency__count == 1 if obj.frs__currency__count else None

    def get_fr_currencies_are_consistent(self, obj):
        return self.fr_currencies_ok(obj)

    def get_all_currencies_are_consistent(self, obj):
        if not hasattr(obj, 'planned_budget'):
            return False
        return self.fr_currencies_ok(obj) and obj.max_fr_currency == obj.planned_budget.currency

    def get_fr_currency(self, obj):
        return obj.max_fr_currency if self.fr_currencies_ok(obj) else ''

    def get_disbursement_percent(self, obj):
        if obj.frs__actual_amt_local__sum is None:
            return None

        if not (self.fr_currencies_ok(obj) and obj.max_fr_currency == obj.planned_budget.currency):
            return "!Error! (currencies do not match)"
        percent = obj.frs__actual_amt_local__sum / obj.total_unicef_cash * 100 \
            if obj.total_unicef_cash and obj.total_unicef_cash > 0 else 0
        return "%.1f" % percent

    def get_days_last_pv(self, obj):
        if obj.last_pv_date:
            duration = datetime.date.today() - obj.last_pv_date
            return duration.days
        return None

    def get_has_final_partnership_review(self, obj):
        return bool(obj.has_final_partnership_review)

    def get_offices_names(self, obj):
        return ",".join(o.name for o in obj.offices.all())

    def get_sections(self, obj):
        return ",".join([section.name for section in obj.sections.all()])

    def get_link(self, obj):
        host_name = self.context['request'].get_host()
        return f'https://{host_name}/pmp/partners/{obj.pk}/details'

    class Meta:
        model = Intervention
        fields = (
            'intervention_id',
            'partner_blocked',
            'partner_id',
            'partner_name',
            'partner_marked_for_deletion',
            'number',
            'status',
            'start',
            'end',
            'sections',
            'offices_names',
            'total_budget',
            'cso_contribution',
            'unicef_cash',
            'unicef_supplies',
            'frs_total_frs_amt',
            'disbursement',
            'disbursement_percent',
            'last_pv_date',
            'days_last_pv',
            'fr_currencies_are_consistent',
            'all_currencies_are_consistent',
            'fr_currency',
            'budget_currency',
            'partner_vendor_number',
            'outstanding_dct',
            'frs_total_frs_amt_usd',
            'disbursement_usd',
            'outstanding_dct_usd',
            'multi_curr_flag',
            'has_final_partnership_review',
            'action_points',
            'link',
            'unicef_focal_points',
        )
