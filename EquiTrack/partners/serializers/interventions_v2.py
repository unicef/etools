import json
from operator import xor

from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from reports.serializers import SectorLightSerializer, ResultLightSerializer, RAMIndicatorLightSerializer
from locations.models import Location

from partners.models import (
    PCA,
    InterventionBudget,
    SupplyPlan,
    DistributionPlan,
    InterventionPlannedVisits,
    Intervention,
    InterventionAmendment,
    PartnerOrganization,
    PartnerType,
    Agreement,
    PartnerStaffMember,
    InterventionSectorLocationLink,
    InterventionResultLink
)
from locations.serializers import LocationLightSerializer

from partners.serializers.v1 import PCASectorSerializer, DistributionPlanSerializer


class InterventionBudgetNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionBudget
        fields = (
            "id",
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "year",
            "total",
        )


class InterventionBudgetCUSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)
    partner_contribution = serializers.DecimalField(max_digits=20, decimal_places=2)
    unicef_cash = serializers.DecimalField(max_digits=20, decimal_places=2)
    in_kind_amount = serializers.DecimalField(max_digits=20, decimal_places=2)
    partner_contribution_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    unicef_cash_local = serializers.DecimalField(max_digits=20, decimal_places=2)
    in_kind_amount_local = serializers.DecimalField(max_digits=20, decimal_places=2)

    class Meta:
        model = InterventionBudget
        fields = (
            "id",
            "intervention",
            "partner_contribution",
            "unicef_cash",
            "in_kind_amount",
            "partner_contribution_local",
            "unicef_cash_local",
            "in_kind_amount_local",
            "year",
            "total",
        )
        #read_only_fields = [u'total']

    def validate(self, data):
        errors = {}
        try:
            data = super(InterventionBudgetCUSerializer, self).validate(data)
        except ValidationError as e:
            errors.update(e)

        intervention = data.get('intervention', None)

        year = data.get("year", "")
        # To avoid any confusion.. budget year will always be required
        if not year:
            errors.update(year="Budget year is required")

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
            'id',
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
            "id,"
            "item",
            "quantity",
            "site",
        )


class InterventionAmendmentCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = "__all__"


class InterventionAmendmentNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionAmendment
        fields = (
            "amended_at",
            "type",
        )



class PlannedVisitsCUSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionPlannedVisits
        fields = "__all__"


class PlannedVisitsNestedSerializer(serializers.ModelSerializer):

    class Meta:
        model = InterventionPlannedVisits
        fields = (
            "id",
            "year",
            "programmatic",
            "spot_checks",
            "audit",
        )


class InterventionListSerializer(serializers.ModelSerializer):

    partner_name = serializers.CharField(source='agreement.partner.name')

    unicef_budget = serializers.IntegerField(source='total_unicef_cash')
    cso_contribution = serializers.IntegerField(source='total_partner_contribution')
    sectors = serializers.SerializerMethodField()

    def get_sectors(self, obj):
        return [l.sector for l in obj.sector_locations.all()]

    class Meta:
        model = Intervention
        fields = (
            'id', 'reference_number', 'number', 'document_type', 'partner_name', 'status', 'title', 'start', 'end',
            'unicef_budget', 'cso_contribution', 'sectors'
        )

class InterventionLocationSectorNestedSerializer(serializers.ModelSerializer):
    locations = LocationLightSerializer(many=True)
    sector = SectorLightSerializer()
    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'sector', 'locations'
        )

class InterventionSectorLocationCUSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionSectorLocationLink
        fields = (
            'id', 'intervention', 'sector', 'locations'
        )

class InterventionAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Intervention
        fields = (
            'id', 'intervention', 'type', 'attachment'
        )

class InterventionResultNestedSerializer(serializers.ModelSerializer):
    cp_output = ResultLightSerializer()
    ram_indicators = RAMIndicatorLightSerializer(many=True, read_only=True)
    class Meta:
        model = InterventionResultLink
        fields = (
            'id', 'intervention', 'cp_output', 'ram_indicators'
        )
class InterventionResultCUSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterventionResultLink
        fields = "__all__"


class InterventionCreateUpdateSerializer(serializers.ModelSerializer):

    planned_budget = InterventionBudgetNestedSerializer(many=True, read_only=True)
    partner = serializers.CharField(source='agreement.partner.name', read_only=True)

    supplies = SupplyPlanCreateUpdateSerializer(many=True, read_only=True, required=False)
    distributions = DistributionPlanCreateUpdateSerializer(many=True, read_only=True, required=False)
    amendments = InterventionAmendmentCUSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    sector_locations = InterventionSectorLocationCUSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultCUSerializer(many=True, read_only=True, required=False)

    class Meta:
        model = Intervention
        # fields = (
        #     "id", "partner", "agreement", "document_type", "hrp", "number",
        #     "title", "status", "start", "end", "submission_date_prc", "review_date_prc",
        #     "prc_review_document", "unicef_signatory", "unicef_focal_points",
        #     "submission_date", "signed_by_unicef_date", "signed_by_partner_date", "partner_focal_points",
        #     "partner_authorized_officer_signatory", "office", "fr_numbers", "planned_visits", "population_focus",
        #     "created", "modified", "planned_budget", #"supply_plans", "distribution_plans",
        #     "amendments"
        # )
        fields = "__all__"

    # @transaction.atomic
    # def create(self, validated_data):
    #     budget_log = validated_data.pop("budget_log", [])
    #     supply_plans = validated_data.pop("supply_plans", [])
    #     distribution_plans = validated_data.pop("distribution_plans", [])
    #     amendments = validated_data.pop("amendments", [])
    #     visits = validated_data.pop("visits", [])
    #
    #     intervention = super(InterventionCreateUpdateSerializer, self).create(validated_data)
    #
    #     # for item in pcasectors:
    #     #     item["pca"] = intervention.id
    #     #     item["sector"] = item["sector"].id
    #     #     serializer = PCASectorCreateUpdateSerializer(data=item)
    #     #     serializer.is_valid(raise_exception=True)
    #     #     serializer.save()
    #     #
    #     # for item in locations:
    #     #     item["pca"] = intervention.id
    #     #     item["location"] = item["location"].id
    #     #     serializer = GwPCALocationCreateUpdateSerializer(data=item)
    #     #     serializer.is_valid(raise_exception=True)
    #     #     serializer.save()
    #
    #     for item in budget_log:
    #         item["partnership"] = intervention.id
    #         serializer = InterventionBudgetCreateUpdateSerializer(data=item)
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()
    #
    #     for item in supply_plans:
    #         item["partnership"] = intervention.id
    #         item["item"] = item["item"].id
    #         serializer = SupplyPlanCreateUpdateSerializer(data=item)
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()
    #
    #     for item in distribution_plans:
    #         item["partnership"] = intervention.id
    #         item["item"] = item["item"].id
    #         item["site"] = item["site"].id
    #         serializer = DistributionPlanCreateUpdateSerializer(data=item)
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()
    #
    #     for item in amendments:
    #         item["partnership"] = intervention.id
    #         serializer = InterventionAmendmentCreateUpdateSerializer(data=item)
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()
    #
    #     for item in visits:
    #         item["partnership"] = intervention.id
    #         serializer = PlannedVisitsCreateUpdateSerializer(data=item)
    #         serializer.is_valid(raise_exception=True)
    #         serializer.save()
    #
    #     return intervention

    @transaction.atomic
    def update(self, instance, validated_data):
        # pcasectors = validated_data.pop("pcasectors", [])
        # locations = validated_data.pop("locations", [])
        # budget_log = validated_data.pop("budget_log", [])
        # supply_plans = validated_data.pop("supply_plans", [])
        # distribution_plans = validated_data.pop("distribution_plans", [])
        # amendments_log = validated_data.pop("amendments_log", [])
        # visits = validated_data.pop("visits", [])

        updated = super(InterventionCreateUpdateSerializer, self).update(instance, validated_data)

        # Sectors
        # ids = [x["id"] for x in pcasectors if "id" in x.keys()]
        # for item in instance.pcasectors.all():
        #     if item.sector.id not in ids:
        #         item.delete()

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
        # ids = [x["id"] for x in budget_log if "id" in x.keys()]
        # for item in instance.budget_log.all():
        #     if item.id not in ids:
        #         item.delete()
        #
        # for item in budget_log:
        #     item["partnership"] = instance.id
        #     serializer = InterventionBudgetCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()
        #
        # # Supply Plan
        # ids = [x["id"] for x in supply_plans if "id" in x.keys()]
        # for item in instance.supply_plans.all():
        #     if item.id not in ids:
        #         item.delete()
        #
        # for item in supply_plans:
        #     item["partnership"] = instance.id
        #     item["item"] = item["item"].id
        #     serializer = SupplyPlanCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()
        #
        # # Distribution Plan
        # ids = [x["id"] for x in distribution_plans if "id" in x.keys()]
        # for item in instance.distribution_plans.all():
        #     if item.id not in ids:
        #         item.delete()
        #
        # for item in distribution_plans:
        #     item["partnership"] = instance.id
        #     item["item"] = item["item"].id
        #     item["site"] = item["site"].id
        #     serializer = DistributionPlanCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()
        #
        # # Amendments log
        # ids = [x["id"] for x in amendments_log if "id" in x.keys()]
        # for item in instance.amendments_log.all():
        #     if item.id not in ids:
        #         item.delete()
        #
        # for item in amendments_log:
        #     item["partnership"] = instance.id
        #     serializer = InterventionAmendmentCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()
        #
        # # Planned visits
        # ids = [x["id"] for x in visits if "id" in x.keys()]
        # for item in instance.visits.all():
        #     if item.id not in ids:
        #         item.delete()
        #
        # for item in visits:
        #     item["partnership"] = instance.id
        #     serializer = PlannedVisitsCreateUpdateSerializer(data=item)
        #     serializer.is_valid(raise_exception=True)
        #     serializer.save()

        return updated
    #
    # def validate(self, data):
    #     errors = {}
    #     try:
    #         data = super(InterventionCreateUpdateSerializer, self).validate(data)
    #     except ValidationError as e:
    #         errors.update(e)
    #
    #     document_type_errors = []
    #     document_type = data.get("document_type", "")
    #     agreement = data.get("agreement", "")
    #     if not document_type:
    #         document_type_errors.append("This field is required.")
    #     if agreement.agreement_type == Agreement.PCA and document_type not in [PCA.PD, PCA.SHPD]:
    #         document_type_errors.append("This field must be PD or SHPD in case of agreement is PCA.")
    #     if agreement.agreement_type == Agreement.SSFA and document_type != PCA.SSFA:
    #         document_type_errors.append("This field must be SSFA in case of agreement is SSFA.")
    #     if document_type_errors:
    #         errors.update(document_type=document_type_errors)
    #
    #     office = data.get("office", "")
    #     if not office:
    #         errors.update(office="This field is required.")
    #
    #     programme_focal_points = data.get("programme_focal_points", "")
    #     status = data.get("status", "")
    #     if not programme_focal_points and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #         errors.update(programme_focal_points="This field is required if PCA status is ACTIVE or IMPLEMENTED.")
    #
    #     unicef_managers = data.get("unicef_managers", "")
    #     if not unicef_managers and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #         errors.update(unicef_managers="This field is required if PCA status is ACTIVE or IMPLEMENTED.")
    #
    #     partner_focal_point = data.get("partner_focal_point", "")
    #     if not partner_focal_point and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #         errors.update(partner_focal_point="This field is required if PCA status is ACTIVE or IMPLEMENTED.")
    #
    #     if xor(bool(data.get("signed_by_partner_date", None)), bool(data.get("partner_manager", None))):
    #         errors.update(partner_manager=["partner_manager and signed_by_partner_date must be provided."])
    #         errors.update(signed_by_partner_date=["signed_by_partner_date and partner_manager must be provided."])
    #
    #     if xor(bool(data.get("signed_by_unicef_date", None)), bool(data.get("unicef_manager", None))):
    #         errors.update(unicef_manager=["unicef_manager and signed_by_unicef_date must be provided."])
    #         errors.update(signed_by_unicef_date=["signed_by_unicef_date and unicef_manager must be provided."])
    #
    #     start_date_errors = []
    #     start_date = data.get("start", None)
    #     signed_by_unicef_date = data.get("signed_by_unicef_date", None)
    #     signed_by_partner_date = data.get("signed_by_partner_date", None)
    #     if not start_date and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #         start_date_errors.append("This field is required.")
    #     if start_date and (signed_by_unicef_date or signed_by_partner_date) and \
    #             start_date < max(signed_by_unicef_date, signed_by_partner_date):
    #         start_date_errors.append("Start date must be after the most recent signoff date (either signed_by_unicef_date or signed_by_partner_date).")
    #     if start_date_errors:
    #         errors.update(start_date=start_date_errors)
    #
    #     end_date_errors = []
    #     end_date = data.get("end", None)
    #     if not end_date and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #         end_date_errors.append("This field is required.")
    #     if end_date and start_date and end_date < start_date:
    #         end_date_errors.append("End date must be after the start date.")
    #     if end_date_errors:
    #         errors.update(end_date=end_date_errors)
    #
    #     population_focus = data.get("population_focus", "")
    #     if not population_focus and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #         errors.update(population_focus="This field is required if PCA status is ACTIVE or IMPLEMENTED.")
    #
    #     # pcasectors = data.get("pcasectors", "")
    #     # if not pcasectors and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #     #     errors.update(pcasectors="This field is required if PCA status is ACTIVE or IMPLEMENTED.")
    #
    #     # locations = data.get("locations", "")
    #     # if not locations and status in [PCA.ACTIVE, PCA.IMPLEMENTED]:
    #     #     errors.update(locations="This field is required if PCA status is ACTIVE or IMPLEMENTED.")
    #
    #     if errors:
    #         raise serializers.ValidationError(errors)
    #
    #     return data


class InterventionDetailSerializer(serializers.ModelSerializer):
    planned_budget = InterventionBudgetNestedSerializer(many=True, read_only=True)
    partner = serializers.CharField(source='agreement.partner.name')

    supplies = SupplyPlanNestedSerializer(many=True, read_only=True, required=False)
    distributions = DistributionPlanNestedSerializer(many=True, read_only=True, required=False)
    amendments = InterventionAmendmentNestedSerializer(many=True, read_only=True, required=False)
    planned_visits = PlannedVisitsNestedSerializer(many=True, read_only=True, required=False)
    sector_locations = InterventionLocationSectorNestedSerializer(many=True, read_only=True, required=False)
    attachments = InterventionAttachmentSerializer(many=True, read_only=True, required=False)
    result_links = InterventionResultNestedSerializer(many=True, read_only=True, required=False)
    class Meta:
        model = Intervention
        fields = (
            "id", "partner", "agreement", "document_type", "hrp", "number",
            "title", "status", "start", "end", "submission_date_prc", "review_date_prc",
            "submission_date", "prc_review_document", "signed_by_unicef_date", "signed_by_partner_date",
            "unicef_signatory", "unicef_focal_points", "partner_focal_points", "partner_authorized_officer_signatory",
            "offices", "fr_numbers", "planned_visits", "population_focus", "sector_locations",
            "created", "modified", "planned_budget", "result_links",
            "amendments", "planned_visits", "attachments", "supplies", "distributions"
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
    unicef_signatory = serializers.SerializerMethodField()
    hrp_name = serializers.CharField(source='hrp.name')
    partner_focal_points = serializers.SerializerMethodField()
    visits = PlannedVisitsNestedSerializer(many=True, required=False)
    supply_plans = SupplyPlanNestedSerializer(many=True, required=False)
    distribution_plans = DistributionPlanNestedSerializer(many=True, required=False)
    unicef_focal_points = serializers.SerializerMethodField()
    fr_numbers_list = serializers.SerializerMethodField()

    class Meta:
        model = Intervention
        fields = (
            "id", "status", "partner_name", "agreement_name", "document_type", "number", "title",
            "start", "end", "offices", "unicef_focals",
            "partner_auth_officials", "unicef_focals", "intervention_programme_focals", "population_focus",
            "hrp_name", "fr_numbers_list", "planned_budget_local", "unicef_budget", "unicef_cash_local", "cso_contribution",
            "partner_contribution_local", "visits", "submission_date", "submission_date_prc", "review_date_prc",
            "unicef_signatory", "signed_by_unicef_date", "signed_by_partner_date", "supply_plans", "distribution_plans",
        )

    def get_unicef_signatory(self, obj):
        return obj.unicef_signatory.get_full_name()

    def get_offices(self, obj):
        return ', '.join([o.name for o in obj.office.all()])

    def get_sectors(self, obj):
        return ', '.join([l.sector.name for l in obj.sector_locations.all()])

    def get_locations(self, obj):
        ll = Location.objects.\
            filter(intervention_sector_locations__intervention=obj.id).order_by('name').\
            value_list('name', flat=True).distinct()
        return ', '.join(ll)

    def get_partner_authorized_officer_signatory(self, obj):
        return obj.partner_authorized_officer_signatory.get_full_name()

    def get_partner_focal_points(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.partner_focal_points.all()])

    def get_unicef_focal_points(self, obj):
        return ', '.join([pf.get_full_name() for pf in obj.unicef_focal_points.all()])

    def get_fr_numbers_list(self, obj):
        return ', '.join([f for f in obj.fr_numbers])

