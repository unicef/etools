from __future__ import unicode_literals
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from partners.models import (
    Intervention,
    PartnerStaffMember,
)


class PDDetailsWrapperRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = {'pd-details': data}
        return super(PDDetailsWrapperRenderer, self).render(data, accepted_media_type, renderer_context)


class UserFocalPointSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = get_user_model()
        depth = 1
        fields = ('name', 'email')


class PartnerFocalPointSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = PartnerStaffMember
        depth = 1
        fields = ('name', 'email')


class PRPInterventionListSerializer(serializers.ModelSerializer):

    unicef_focal_points = UserFocalPointSerializer(many=True, read_only=True)
    focal_points = PartnerFocalPointSerializer(many=True, read_only=True,source='partner_focal_points')
    start_date = serializers.DateField(source='start')
    end_date = serializers.DateField(source='end')
    cso_budget = serializers.DecimalField(source='total_partner_contribution', read_only=True,
                                          max_digits=20, decimal_places=2)
    cso_budget_currency = serializers.CharField(source='default_budget_currency', read_only=True)

    unicef_budget = serializers.DecimalField(source='total_unicef_budget', read_only=True,
                                             max_digits=20, decimal_places=2)
    unicef_budget_currency = serializers.CharField(source='default_budget_currency', read_only=True)
    # todo: is this the right field?
    funds_received = serializers.DecimalField(source='total_budget', read_only=True,
                                              max_digits=20, decimal_places=2)
    funds_received_currency = serializers.CharField(source='default_budget_currency', read_only=True)

    class Meta:
        model = Intervention
        fields = (
            'id', 'title',
            'offices',  # todo: convert to names, not ids
            'number',
            # 'partner_org',
            'unicef_focal_points',
            'focal_points',
            # 'agreement_auth_officers',
            # 'focal_points',
            'start_date', 'end_date',
            'cso_budget', 'cso_budget_currency',
            'unicef_budget', 'unicef_budget_currency',
            'funds_received', 'funds_received_currency',
            # 'reporting_frequencies',
            # 'expected_results',
        )
