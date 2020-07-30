from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from unicef_attachments.fields import AttachmentSingleFileField

from etools.applications.partners.models import Intervention
from etools.applications.partners.permissions import InterventionPermissions
from etools.applications.partners.serializers.interventions_v2 import (
    FRsSerializer,
    InterventionAmendmentCUSerializer,
    InterventionAttachmentSerializer,
    InterventionBudgetCUSerializer,
    InterventionResultNestedSerializer,
    PlannedVisitsNestedSerializer,
)
from etools.applications.partners.utils import get_quarters_range
from etools.applications.reports.models import InterventionActivityTimeFrame


class InterventionDetailSerializer(serializers.ModelSerializer):
    activation_letter_attachment = AttachmentSingleFileField(read_only=True)
    activation_letter_file = serializers.FileField(source='activation_letter', read_only=True)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    available_actions = serializers.SerializerMethodField()
    cluster_names = serializers.SerializerMethodField()
    days_from_review_to_signed = serializers.CharField(read_only=True)
    days_from_submission_to_signed = serializers.CharField(read_only=True)
    donor_codes = serializers.SerializerMethodField()
    donors = serializers.SerializerMethodField()
    flagged_sections = serializers.SerializerMethodField(read_only=True)
    frs_details = FRsSerializer(source='frs', read_only=True)
    grants = serializers.SerializerMethodField()
    location_names = serializers.SerializerMethodField()
    location_p_codes = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    partner = serializers.CharField(source='agreement.partner.name')
    partner_id = serializers.CharField(source='agreement.partner.id', read_only=True)
    partner_vendor = serializers.CharField(source='agreement.partner.vendor_number')
    permissions = serializers.SerializerMethodField(read_only=True)
    planned_budget = InterventionBudgetCUSerializer(read_only=True)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    prc_review_attachment = AttachmentSingleFileField(read_only=True)
    prc_review_document_file = serializers.FileField(source='prc_review_document', read_only=True)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    section_names = serializers.SerializerMethodField(read_only=True)
    signed_pd_attachment = AttachmentSingleFileField(read_only=True)
    signed_pd_document_file = serializers.FileField(source='signed_pd_document', read_only=True)
    submitted_to_prc = serializers.ReadOnlyField()
    termination_doc_attachment = AttachmentSingleFileField(read_only=True)
    termination_doc_file = serializers.FileField(source='termination_doc', read_only=True)
    quarters = serializers.SerializerMethodField()

    def get_location_p_codes(self, obj):
        return [location.p_code for location in obj.flat_locations.all()]

    def get_donors(self, obj):
        donors = set()
        for fr_item_qs in obj.frs.all():
            for fr_li in fr_item_qs.fr_items.all():
                donors.add(fr_li.donor)
        return donors

    def get_donor_codes(self, obj):
        donor_codes = set()
        for fr_item_qs in obj.frs.all():
            for fr_li in fr_item_qs.fr_items.all():
                donor_codes.add(fr_li.donor_code)
        return donor_codes

    def get_grants(self, obj):
        grants = set()
        for fr_item_qs in obj.frs.all():
            for fr_li in fr_item_qs.fr_items.all():
                grants.add(fr_li.grant_number)
        return grants

    def get_permissions(self, obj):
        user = self.context['request'].user
        ps = Intervention.permission_structure()
        permissions = InterventionPermissions(
            user=user,
            instance=self.instance,
            permission_structure=ps,
        )
        return permissions.get_permissions()

    def get_locations(self, obj):
        return [l.id for l in obj.flat_locations.all()]

    def get_location_names(self, obj):
        return [
            '{} [{} - {}]'.format(
                l.name,
                l.gateway.name,
                l.p_code
            ) for l in obj.flat_locations.all()
        ]

    def get_section_names(self, obj):
        return [l.name for l in obj.sections.all()]

    def get_flagged_sections(self, obj):
        return [l.id for l in obj.sections.all()]

    def get_cluster_names(self, obj):
        return [c for c in obj.intervention_clusters()]

    def _is_management(self):
        return get_user_model().objects.filter(
            groups__name__in=['Senior Management Team'],
            profile__country=self.context['request'].user.profile.country
        ).exists()

    def _is_partner_user(self, obj, user):
        return user.email in [o.email for o in obj.partner_focal_points.all()]

    def get_available_actions(self, obj):
        available_actions = [
            "download_comments",
            "export",
            "generate_pdf",
        ]
        user = self.context['request'].user

        # available actions only provided in Development status
        if obj.status != obj.DEVELOPMENT:
            return available_actions

        # PD is assigned to UNICEF
        if obj.unicef_court:
            # UNICEF User with Senior Management Team
            if self._is_management():
                available_actions.append("cancel")

            # budget owner
            if obj.budget_owner == user:
                available_actions.append("accept")
                available_actions.append("review")
                available_actions.append("signature")

            # any unicef focal point user
            if user in obj.unicef_focal_points.all():
                available_actions.append("accept")
                available_actions.append("cancel")
                available_actions.append("send_to_partner")
                available_actions.append("signature")
                if obj.partner_accepted:
                    available_actions.append("unlock")
                    # TODO confirm that this is focal point
                    # and not just any UNICEF user
                    available_actions.append("accept_and_review")

        # PD is assigned to Partner
        else:
            # any partner focal point user
            if self._is_partner_user(obj, user):
                if not obj.partner_accepted:
                    available_actions.append("accept")
                if obj.unicef_accepted:
                    available_actions.append("unlock")

        return list(set(available_actions))

    def get_quarters(self, obj: Intervention):
        return [
            {
                'name': 'Q{}'.format(i + 1),
                'start': quarter[0].strftime('%Y-%m-%d'),
                'end': quarter[1].strftime('%Y-%m-%d')
            }
            for i, quarter in enumerate(get_quarters_range(obj.start, obj.end))
        ]

    def validate(self, attrs):
        validated_data = super().validate(attrs)
        if self.instance and ('start' in validated_data or 'end' in validated_data):
            start = validated_data.get('start', self.instance.start)
            end = validated_data.get('end', self.instance.end)
            old_quarters = get_quarters_range(self.instance.start, self.instance.end)
            new_quarters = get_quarters_range(start, end)

            if len(old_quarters) > len(new_quarters):
                if InterventionActivityTimeFrame.objects.filter(
                    activity__result__result_link__intervention=self.instance,
                    start_date__gte=old_quarters[len(new_quarters)][0]
                ).exists():
                    names_to_be_removed = ', '.join([
                        'Q{}'.format(i + 1)
                        for i in range(len(old_quarters), len(new_quarters))
                    ])
                    error_text = _('Please adjust activities to not use the quarters to be removed ({}).').format(
                        names_to_be_removed
                    )
                    bad_keys = set(validated_data.keys()).union({'start', 'end'})
                    raise ValidationError({key: [error_text] for key in bad_keys})

        return validated_data

    class Meta:
        model = Intervention
        fields = (
            "activation_letter_attachment",
            "activation_letter_file",
            "agreement",
            "amendments",
            "attachments",
            "available_actions",
            "budget_owner",
            "capacity_development",
            "cfei_number",
            "cluster_names",
            "context",
            "contingency_pd",
            "country_programme",
            "created",
            "days_from_review_to_signed",
            "days_from_submission_to_signed",
            "document_type",
            "donor_codes",
            "donors",
            "end",
            "equity_narrative",
            "equity_rating",
            "flagged_sections",
            "flat_locations",
            "frs",
            "frs_details",
            "gender_narrative",
            "gender_rating",
            "grants",
            "humanitarian_flag",
            "id",
            "implementation_strategy",
            "in_amendment",
            "ip_program_contribution",
            "location_names",
            "location_p_codes",
            "locations",
            "metadata",
            "modified",
            "number",
            "offices",
            "other_info",
            "other_partners_involved",
            "partner",
            "partner_authorized_officer_signatory",
            "partner_focal_points",
            "partner_id",
            "partner_vendor",
            "permissions",
            "planned_budget",
            "planned_visits",
            "population_focus",
            "prc_review_attachment",
            "prc_review_document",
            "prc_review_document_file",
            "quarters",
            "reference_number_year",
            "result_links",
            "review_date_prc",
            "section_names",
            "sections",
            "signed_by_partner_date",
            "signed_by_unicef_date",
            "signed_pd_attachment",
            "signed_pd_document",
            "signed_pd_document_file",
            "start",
            "status",
            "submission_date",
            "submission_date_prc",
            "submitted_to_prc",
            "sustainability_narrative",
            "sustainability_rating",
            "technical_guidance",
            "termination_doc_attachment",
            "termination_doc_file",
            "title",
            "unicef_focal_points",
            "unicef_signatory",
        )
