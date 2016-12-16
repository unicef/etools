import json
from operator import xor

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import serializers

from reports.serializers import IndicatorSerializer, OutputSerializer
from partners.serializers.v1 import (
    PartnerOrganizationSerializer,
    PartnerStaffMemberEmbedSerializer,
    InterventionSerializer,
)
from locations.models import Location

from partners.models import (
    PCA,
    PartnershipBudget,
    SupplyPlan,
    DistributionPlan,
    PlannedVisits,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
    Agreement,
    PartnerStaffMember,

)
from partners.serializers.v1 import PCASectorSerializer, DistributionPlanSerializer


class InterventionListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='agreement.partner.name')

    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')

    class Meta:
        model = Intervention
        fields = (
            'id', 'reference_number', 'number', 'document_type', 'partner_name', 'status', 'title', 'start_date', 'end_date',
            'sector', 'unicef_budget', 'cso_contribution',
        )


class PartnershipBudgetNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnershipBudget
        fields = (
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "year",
            "total",
        )


class PartnershipBudgetCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnershipBudget
        fields = "__all__"

    def validate(self, data):
        errors = {}
        try:
            data = super(PartnershipBudgetCreateUpdateSerializer, self).validate(data)
        except ValidationError, e:
            errors.update(e)

        status = data.get("status", "")
        year = data.get("year", "")
        if not year and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(year="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        partner_contribution = data.get("partner_contribution", "")
        if not partner_contribution and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(partner_contribution="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        unicef_cash = data.get("unicef_cash", "")
        if not unicef_cash and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(unicef_cash="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        if errors:
            raise serializers.ValidationError(errors)

        return data


class SupplyPlanCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupplyPlan
        fields = "__all__"


class SupplyPlanNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = SupplyPlan
        fields = (
            "item",
            "quantity",
        )


class DistributionPlanCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = DistributionPlan
        fields = "__all__"


class DistributionPlanNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = DistributionPlan
        fields = (
            "item",
            "quantity",
            "site",
        )


class AmendmentLogCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class AmendmentLogNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = (
            "amended_at",
            "type",
        )


class PlannedVisitsCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlannedVisits
        fields = "__all__"


class PlannedVisitsNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlannedVisits
        fields = (
            "year",
            "programmatic",
            "spot_checks",
            "audit",
        )


class InterventionCreateUpdateSerializer(serializers.ModelSerializer):

    budget_log = PartnershipBudgetNestedSerializer(many=True)
    partner = serializers.CharField(source='agreement.partner.name')
    supply_plans = SupplyPlanNestedSerializer(many=True, required=False)
    distribution_plans = DistributionPlanNestedSerializer(many=True, required=False)
    amendments = AmendmentLogNestedSerializer(many=True, required=False)
    visits = PlannedVisitsNestedSerializer(many=True, required=False)

    class Meta:
        model = Intervention
        fields = (
            "id", "partner", "agreement", "document_type", "hrp", "number",
            "title", "status", "start_date", "end_date", "submission_date_prc", "review_date_prc",
            "prc_review_document", "signed_by_unicef", "unicef_focal_points",
            "submission_date", "signed_by_unicef_date", "signed_by_partner_date", "intervention_programme_focal_points",
            "partner_authorized_officials", "office", "fr_numbers", "planned_visits", "population_focus",
            "created_at", "updated_at", "budget_log", "supply_plans",
            "distribution_plans", "amendments", "sector", "location", "visits",
        )
        read_only_fields = ("id",)

    @transaction.atomic
    def create(self, validated_data):
        budget_log = validated_data.pop("budget_log", [])
        supply_plans = validated_data.pop("supply_plans", [])
        distribution_plans = validated_data.pop("distribution_plans", [])
        amendments = validated_data.pop("amendments", [])
        visits = validated_data.pop("visits", [])

        intervention = super(InterventionCreateUpdateSerializer, self).create(validated_data)

        # for item in pcasectors:
        #     item["pca"] = intervention.id
        #     item["sector"] = item["sector"].id
        #     serializer = PCASectorCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()
        #
        # for item in locations:
        #     item["pca"] = intervention.id
        #     item["location"] = item["location"].id
        #     serializer = GwPCALocationCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()

        for item in budget_log:
            item["partnership"] = intervention.id
            serializer = PartnershipBudgetCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in supply_plans:
            item["partnership"] = intervention.id
            item["item"] = item["item"].id
            serializer = SupplyPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in distribution_plans:
            item["partnership"] = intervention.id
            item["item"] = item["item"].id
            item["site"] = item["site"].id
            serializer = DistributionPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in amendments:
            item["partnership"] = intervention.id
            serializer = AmendmentLogCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        for item in visits:
            item["partnership"] = intervention.id
            serializer = PlannedVisitsCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return intervention

    @transaction.atomic
    def update(self, instance, validated_data):
        pcasectors = validated_data.pop("pcasectors", [])
        locations = validated_data.pop("locations", [])
        budget_log = validated_data.pop("budget_log", [])
        supply_plans = validated_data.pop("supply_plans", [])
        distribution_plans = validated_data.pop("distribution_plans", [])
        amendments_log = validated_data.pop("amendments_log", [])
        visits = validated_data.pop("visits", [])

        updated = super(InterventionCreateUpdateSerializer, self).update(instance, validated_data)

        # Sectors
        ids = [x["id"] for x in pcasectors if "id" in x.keys()]
        for item in instance.pcasectors.all():
            if item.sector.id not in ids:
                item.delete()

        # for item in pcasectors:
        #     item["pca"] = instance.id
        #     item["sector"] = item["sector"].id
        #     serializer = PCASectorCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()

        # Locations
        # ids = [x["id"] for x in locations if "id" in x.keys()]
        # for item in instance.locations.all():
        #     if item.location.id not in ids:
        #         item.delete()

        # for item in locations:
        #     item["pca"] = instance.id
        #     item["location"] = item["location"].id
        #     serializer = GwPCALocationCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()

        # Budget Log
        ids = [x["id"] for x in budget_log if "id" in x.keys()]
        for item in instance.budget_log.all():
            if item.id not in ids:
                item.delete()

        for item in budget_log:
            item["partnership"] = instance.id
            serializer = PartnershipBudgetCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Supply Plan
        ids = [x["id"] for x in supply_plans if "id" in x.keys()]
        for item in instance.supply_plans.all():
            if item.id not in ids:
                item.delete()

        for item in supply_plans:
            item["partnership"] = instance.id
            item["item"] = item["item"].id
            serializer = SupplyPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Distribution Plan
        ids = [x["id"] for x in distribution_plans if "id" in x.keys()]
        for item in instance.distribution_plans.all():
            if item.id not in ids:
                item.delete()

        for item in distribution_plans:
            item["partnership"] = instance.id
            item["item"] = item["item"].id
            item["site"] = item["site"].id
            serializer = DistributionPlanCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Amendments log
        ids = [x["id"] for x in amendments_log if "id" in x.keys()]
        for item in instance.amendments_log.all():
            if item.id not in ids:
                item.delete()

        for item in amendments_log:
            item["partnership"] = instance.id
            serializer = AmendmentLogCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        # Planned visits
        ids = [x["id"] for x in visits if "id" in x.keys()]
        for item in instance.visits.all():
            if item.id not in ids:
                item.delete()

        for item in visits:
            item["partnership"] = instance.id
            serializer = PlannedVisitsCreateUpdateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return updated

    def validate(self, data):
        errors = {}
        try:
            data = super(InterventionCreateUpdateSerializer, self).validate(data)
        except ValidationError as e:
            errors.update(e)

        document_type_errors = []
        document_type = data.get("document_type", "")
        agreement = data.get("agreement", "")
        if not document_type:
            document_type_errors.append("This field is required.")
        if agreement.agreement_type == Agreement.PCA and document_type not in [PCA.PD, PCA.SHPD]:
            document_type_errors.append("This field must be PD or SHPD in case of agreement is PCA.")
        if agreement.agreement_type == Agreement.SSFA and document_type != PCA.SSFA:
            document_type_errors.append("This field must be SSFA in case of agreement is SSFA.")
        if document_type_errors:
            errors.update(document_type=document_type_errors)

        office = data.get("office", "")
        if not office:
            errors.update(office="This field is required.")

        programme_focal_points = data.get("programme_focal_points", "")
        status = data.get("status", "")
        if not programme_focal_points and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(programme_focal_points="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        unicef_managers = data.get("unicef_managers", "")
        if not unicef_managers and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(unicef_managers="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        partner_focal_point = data.get("partner_focal_point", "")
        if not partner_focal_point and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(partner_focal_point="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        if xor(bool(data.get("signed_by_partner_date", None)), bool(data.get("partner_manager", None))):
            errors.update(partner_manager=["partner_manager and signed_by_partner_date must be provided."])
            errors.update(signed_by_partner_date=["signed_by_partner_date and partner_manager must be provided."])

        if xor(bool(data.get("signed_by_unicef_date", None)), bool(data.get("unicef_manager", None))):
            errors.update(unicef_manager=["unicef_manager and signed_by_unicef_date must be provided."])
            errors.update(signed_by_unicef_date=["signed_by_unicef_date and unicef_manager must be provided."])

        start_date_errors = []
        start_date = data.get("start_date", None)
        signed_by_unicef_date = data.get("signed_by_unicef_date", None)
        signed_by_partner_date = data.get("signed_by_partner_date", None)
        if not start_date and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            start_date_errors.append("This field is required.")
        if start_date and (signed_by_unicef_date or signed_by_partner_date) and \
                start_date < max(signed_by_unicef_date, signed_by_partner_date):
            start_date_errors.append("Start date must be after the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).")
        if start_date_errors:
            errors.update(start_date=start_date_errors)

        end_date_errors = []
        end_date = data.get("end_date", None)
        if not end_date and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            end_date_errors.append("This field is required.")
        if end_date and start_date and end_date < start_date:
            end_date_errors.append("End date must be after the start date.")
        if end_date_errors:
            errors.update(end_date=end_date_errors)

        population_focus = data.get("population_focus", "")
        if not population_focus and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(population_focus="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        pcasectors = data.get("pcasectors", "")
        if not pcasectors and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(pcasectors="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        locations = data.get("locations", "")
        if not locations and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
            errors.update(locations="This field is required if PCA status is ACTIVE or IMPLEMENTED.")

        if errors:
            raise serializers.ValidationError(errors)

        return data


class InterventionDetailSerializer(serializers.ModelSerializer):

    budget_log = PartnershipBudgetNestedSerializer(many=True)
    supply_plans = SupplyPlanNestedSerializer(many=True, required=False)
    distribution_plans = DistributionPlanNestedSerializer(many=True, required=False)
    amendments_log = AmendmentLogNestedSerializer(many=True, required=False)
    visits = PlannedVisitsNestedSerializer(many=True, required=False)
    partner = serializers.CharField(source='agreement.partner')

    class Meta:
        model = Intervention
        fields = (
            "id", "partner", "agreement", "document_type", "hrp", "number",
            "title", "status", "start_date", "end_date", "submission_date_prc", "review_date_prc",
            "submission_date", "prc_review_document", "signed_by_unicef_date", "signed_by_partner_date",
            "signed_by_unicef", "unicef_focal_points", "intervention_programme_focal_points", "partner_authorized_officials",
            "office", "fr_numbers", "planned_visits", "population_focus",
            "created_at", "updated_at", "budget_log", "supply_plans",
            "distribution_plans", "amendments_log", "sector", "location", "visits",
        )


class InterventionExportSerializer(serializers.ModelSerializer):

    # TODO CP Outputs, RAM Indicators, Fund Commitment(s), Supply Plan, Distribution Plan, URL

    partner_name = serializers.CharField(source='agreement.partner.name')
    agreement_name = serializers.CharField(source='agreement.agreement_number')
    offices = serializers.SerializerMethodField()
    sectors = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    partner_auth_officials = serializers.SerializerMethodField()
    planned_budget_local = serializers.IntegerField(source='total_budget_local')
    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')
    partner_contribution_local = serializers.IntegerField(source='total_partner_contribution_local')
    unicef_cash_local = serializers.IntegerField(source='total_unicef_cash_local')
    signed_by_unicef_name = serializers.SerializerMethodField()
    hrp_name = serializers.CharField(source='hrp.name')
    intervention_programme_focals = serializers.SerializerMethodField()
    visits = PlannedVisitsNestedSerializer(many=True, required=False)
    supply_plans = SupplyPlanNestedSerializer(many=True, required=False)
    distribution_plans = DistributionPlanNestedSerializer(many=True, required=False)
    unicef_focals = serializers.SerializerMethodField()
    fr_numbers_list = serializers.SerializerMethodField()

    class Meta:
        model = Intervention
        fields = (
            "id", "status", "partner_name", "agreement_name", "document_type", "number", "title",
            "start_date", "end_date", "offices", "sectors", "locations", "unicef_focals",
            "partner_auth_officials", "unicef_focals", "intervention_programme_focals", "population_focus",
            "hrp_name", "fr_numbers_list", "planned_budget_local", "unicef_budget", "unicef_cash_local", "cso_contribution",
            "partner_contribution_local", "visits", "submission_date", "submission_date_prc", "review_date_prc",
            "signed_by_unicef_name", "signed_by_unicef_date", "signed_by_partner_date", "supply_plans", "distribution_plans",
        )

    def get_signed_by_unicef_name(self, obj):
        return obj.signed_by_unicef.get_full_name()

    def get_offices(self, obj):
        return ', '.join([o.name for o in obj.office.all()])

    def get_sectors(self, obj):
        return ', '.join([l.name for l in obj.sector.all()])

    def get_locations(self, obj):
        return ', '.join([l.name for l in obj.location.all() if l.name])

    def get_partner_auth_officials(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.partner_authorized_officials.all()])

    def get_intervention_programme_focals(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.intervention_programme_focal_points.all()])

    def get_unicef_focals(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.unicef_focal_points.all()])

    def get_fr_numbers_list(self, obj):
        return ', '.join([f for f in obj.fr_numbers])


class PartnerStaffMemberDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class PartnerStaffMemberCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def validate(self, data):
        data = super(PartnerStaffMemberCreateSerializer, self).validate(data)
        email = data.get('email', "")
        active = data.get('active', "")
        existing_user = None

        # user should be active first time it's created
        if not active:
            raise ValidationError({'active': 'New Staff Member needs to be active at the moment of creation'})
        try:
            existing_user = User.objects.filter(Q(username=email) | Q(email=email)).get()
            if existing_user.profile.partner_staff_member:
                raise ValidationError("This user already exists under a different partnership: {}".format(email))
        except User.DoesNotExist:
            pass

        return data


class PartnerStaffMemberNestedSerializer(PartnerStaffMemberCreateSerializer):
    """
    A serilizer to be used for nested staff member handling. The 'partner' field
    is removed in this case to avoid validation errors for e.g. when creating
    the partner and the member at the same time.
    """
    class Meta:
        model = PartnerStaffMember
        fields = (
            "title",
            "first_name",
            "last_name",
            "email",
            "phone",
            "active",
        )


class PartnerStaffMemberUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"

    def validate(self, data):
        data = super(PartnerStaffMemberUpdateSerializer, self).validate(data)
        email = data.get('email', "")
        active = data.get('active', "")
        existing_user = None

        # make sure email addresses are not editable after creation.. user must be removed and re-added
        if email != self.instance.email:
            raise ValidationError("User emails cannot be changed, please remove the user and add another one: {}".format(email))

        # when adding the active tag to a previously untagged user
        # make sure this user has not already been associated with another partnership.
        if active and not self.instance.active and \
                existing_user and existing_user.partner_staff_member and \
                existing_user.partner_staff_member != self.instance.pk:
            raise ValidationError(
                {'active': 'The Partner Staff member you are trying to activate is associated with a different partnership'}
            )

        return data


class PartnerOrganizationExportSerializer(serializers.ModelSerializer):

    # pca_set = InterventionSerializer(many=True, read_only=True)
    agreement_count = serializers.SerializerMethodField()
    intervention_count = serializers.SerializerMethodField()
    active_staff_members = serializers.SerializerMethodField()

    class Meta:

        model = PartnerOrganization
        # TODO add missing fields:
        #   Bank Info (just the number of accounts synced from VISION)
        fields = ('vendor_number', 'vision_synced', 'deleted_flag', 'blocked', 'name', 'short_name', 'alternate_id',
                  'alternate_name', 'partner_type', 'cso_type', 'shared_partner', 'address', 'email', 'phone_number',
                  'rating', 'type_of_assessment', 'last_assessment_date', 'total_ct_cp', 'total_ct_cy',
                  'agreement_count', 'intervention_count', 'active_staff_members')

    def get_agreement_count(self, obj):
        return obj.agreement_set.count()

    def get_intervention_count(self, obj):
        if obj.partner_type == PartnerType.GOVERNMENT:
            return obj.work_plans.count()
        return obj.documents.count()

    def get_active_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.staff_members.all()])


class PartnerOrganizationListSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerOrganization
        fields = (
            "id",
            "vendor_number",
            "deleted_flag",
            "blocked",
            "name",
            "short_name",
            "partner_type",
            "rating",
            "shared_partner",
            "email",
            "phone_number",
            "total_ct_cp",
            "total_ct_cy",
        )


class PartnerOrganizationDetailSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberDetailSerializer(many=True, read_only=True)

    class Meta:
        model = PartnerOrganization
        fields = "__all__"


class PartnerOrganizationCreateUpdateSerializer(serializers.ModelSerializer):

    staff_members = PartnerStaffMemberNestedSerializer(many=True)

    class Meta:
        model = PartnerOrganization
        fields = "__all__"

    @transaction.atomic
    def create(self, validated_data):
        staff_members = validated_data.pop("staff_members", [])
        partner = super(PartnerOrganizationCreateUpdateSerializer, self).create(validated_data)
        for item in staff_members:
            item["partner"] = partner.id
            # Utilize extra validation logic in this serializer
            serializer = PartnerStaffMemberCreateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return partner

    @transaction.atomic
    def update(self, instance, validated_data):
        staff_members = validated_data.pop("staff_members", [])
        updated = PartnerOrganization(id=instance.id, **validated_data)
        updated.save()

        # Create or update new/changed members.
        for item in staff_members:
            item["partner"] = instance.id
            if "id" in item.keys():
                # Utilize extra validation logic in this serializer
                serializer = PartnerStaffMemberUpdateSerializer(data=item)
            else:
                # Utilize extra validation logic in this serializer
                serializer = PartnerStaffMemberCreateSerializer(data=item)
            serializer.is_valid(raise_exception=True)
            serializer.save()

        return updated


class AgreementListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "reference_number",
            "partner_name",
            "agreement_type",
            "end",
            "start",
            "signed_by_unicef_date",
            "signed_by_partner_date",
            "status",
            "partner_manager",
            "signed_by",
        )


class AgreementExportSerializer(serializers.ModelSerializer):

    staff_members = serializers.SerializerMethodField()
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_manager_name = serializers.CharField(source='partner_manager.get_full_name')
    signed_by_name = serializers.CharField(source='signed_by.get_full_name')

    class Meta:
        model = Agreement
        fields = (
            "reference_number",
            "status",
            "partner_name",
            "agreement_type",
            "start",
            "end",
            "partner_manager_name",
            "signed_by_partner_date",
            "signed_by_name",
            "signed_by_unicef_date",
            "staff_members",
        )

    def get_staff_members(self, obj):
        return ', '.join([sm.get_full_name() for sm in obj.authorized_officers.all()])


class AgreementRetrieveSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='partner.name', read_only=True)
    authorized_officers = PartnerStaffMemberEmbedSerializer(many=True)

    class Meta:
        model = Agreement
        fields = (
            "id",
            "partner",
            "authorized_officers",
            "partner_name",
            "agreement_type",
            "agreement_number",
            "attached_agreement",
            "start",
            "end",
            "signed_by_unicef_date",
            "signed_by",
            "signed_by_partner_date",
            "partner_manager",
            "status",
            "year",
            "reference_number",
        )


class AgreementCreateUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Agreement
        fields = "__all__"

    def validate(self, data):
        data = super(AgreementCreateUpdateSerializer, self).validate(data)
        errors = {}

        start_errors = []
        if data.get("end", None) and not data.get("start", None):
            start_errors.append("Start date must be provided along with end date.")
        if data.get("start", None) != max(data.get("signed_by_unicef_date", None), data.get("signed_by_partner_date", None)):
            start_errors.append("Start date must equal to the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).")
        if start_errors:
            errors.update(start=start_errors)

        if xor(bool(data.get("signed_by_partner_date", None)), bool(data.get("partner_manager", None))):
            errors.update(partner_manager=["partner_manager and signed_by_partner_date must be provided."])
            errors.update(signed_by_partner_date=["signed_by_partner_date and partner_manager must be provided."])

        if xor(bool(data.get("signed_by_unicef_date", None)), bool(data.get("signed_by", None))):
            errors.update(signed_by=["signed_by and signed_by_unicef_date must be provided."])
            errors.update(signed_by_unicef_date=["signed_by_unicef_date and signed_by must be provided."])

        if data.get("agreement_type", None) in [Agreement.PCA, Agreement.SSFA] and data.get("partner", None):
            partner = data.get("partner", None)
            if not partner.partner_type == "Civil Society Organization":
                errors.update(partner=["Partner type must be CSO for PCA or SSFA agreement types."])

        if errors:
            raise serializers.ValidationError(errors)
        return data


class PartnerStaffMemberPropertiesSerializer(serializers.ModelSerializer):

    partner = PartnerOrganizationSerializer()
    agreement_set = AgreementRetrieveSerializer(many=True)

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"


class PartnerStaffMemberExportSerializer(serializers.ModelSerializer):

    class Meta:
        model = PartnerStaffMember
        fields = "__all__"