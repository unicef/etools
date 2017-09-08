from __future__ import unicode_literals
from django.contrib.auth import get_user_model

from rest_framework import serializers
from rest_framework.renderers import JSONRenderer

from partners.models import (
    Intervention,
    PartnerStaffMember,
    PartnerOrganization, InterventionResultLink)
from reports.models import Indicator
from reports.serializers.v2 import LowerResultSerializer


class PDDetailsWrapperRenderer(JSONRenderer):
    """
    The sole purpose of this class is just to format the root api inside a wrapper like this:
    { "pd-details": [actual data ] }
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = {'pd-details': data}
        return super(PDDetailsWrapperRenderer, self).render(data, accepted_media_type, renderer_context)


class PartnerSerializer(serializers.ModelSerializer):
    unicef_vendor_number = serializers.CharField(source='vendor_number', read_only=True)

    class Meta:
        model = PartnerOrganization
        depth = 1
        fields = ('name', 'unicef_vendor_number', 'short_name')


class AuthOfficerSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='get_full_name', read_only=True)
    phone_num = serializers.CharField(source='phone', read_only=True)

    class Meta:
        model = PartnerStaffMember
        depth = 1
        fields = ('name', 'title', 'phone_num', 'email')


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


class PRPIndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = (
            'id',
        )


class PRPResultSerializer(serializers.ModelSerializer):
    # todo: fix / change to new formats
    indicators = PRPIndicatorSerializer(many=True, read_only=True, source='ram_indicators')

    class Meta:
        model = InterventionResultLink
        fields = (
            'id',
            # 'title',
            'cp_output',
            'indicators',
        )


class PRPResultWrapperSerializer(serializers.Serializer):
    """
    The sole purpose of this class is just to format the results like
    { "pd_output": { [actual data ] } }
    """
    pd_output = PRPResultSerializer(many=False, read_only=True, source='*')

    class Meta:
        model = InterventionResultLink
        fields = (
            'pd_output',
        )


class PRPInterventionListSerializer(serializers.ModelSerializer):

    offices = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')  # todo: do these need to be lowercased?
    partner_org = PartnerSerializer(read_only=True, source='agreement.partner')
    unicef_focal_points = UserFocalPointSerializer(many=True, read_only=True)
    agreement_auth_officers = AuthOfficerSerializer(many=True, read_only=True, source='agreement.authorized_officers')
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
    expected_results = PRPResultWrapperSerializer(many=True, read_only=True, required=False,
                                                  source='result_links')

    class Meta:
        model = Intervention
        fields = (
            'id', 'title',
            'offices',  # todo: convert to names, not ids
            'number',
            'partner_org',
            'unicef_focal_points',
            'agreement_auth_officers',
            'focal_points',
            'start_date', 'end_date',
            'cso_budget', 'cso_budget_currency',
            'unicef_budget', 'unicef_budget_currency',
            'funds_received', 'funds_received_currency',
            # 'reporting_frequencies',  # todo: figure out where this comes from
            'expected_results',
        )
