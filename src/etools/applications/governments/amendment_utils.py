import copy

from etools.applications.partners.amendment_utils import (
    serialize_instance,
    transform_to_choices,
    transform_to_choices_list,
)

GDD_AMENDMENT_RELATED_FIELDS = {
    'governments.GDD': [
        # one to many
        'result_links',
        'supply_items',
        'risks',
        'reporting_requirements',

        # 1 to 1
        'planned_budget',

        # many to one
        'agreement',
        'budget_owner',

        # many to many
        'country_programme', 'unicef_focal_points', 'partner_focal_points', 'sites',
        'sections', 'offices', 'flat_locations'
    ],
    'governments.GDDResultLink': [
        # one to many
        'gdd_key_interventions',

        # many to many
        'ram_indicators',

        # one to one
        'cp_output',
    ],
    'governments.GDDKeyIntervention': [
        # one to many
        'activities',
    ],
    'governments.GDDSupplyItem': [
        # many to one
        'result',
    ],
    'governments.GDDActivity': [
        # one to many
        'items',
    ]
}

GDD_AMENDMENT_IGNORED_FIELDS = {
    'governments.GDD': [
        'modified',
        'number', 'status', 'in_amendment',
        'sites', 'tpmconcern',

        # submission
        'unicef_court',
        'partner_accepted',
        'unicef_accepted',
        'date_sent_to_partner',
        'submission_date',
        'accepted_on_behalf_of_partner',

        # signatures
        'signed_by_unicef_date',
        'signed_by_partner_date',

        # timing
        'submission_date_prc',
        'review_date_prc',
    ],
    'governments.GDDBudget': [
        'modified',
        # auto calculated fields
        'partner_contribution_local',
        'total_unicef_cash_local_wo_hq',
        'unicef_cash_local',
        'partner_supply_local',
        'total_partner_contribution_local',
        'in_kind_amount_local',
        'total',
        'total_local',
        'programme_effectiveness',
    ],
    'governments.GDDResultLink': ['modified'],
    'governments.GDDReportingRequirement': ['modified'],
    'governments.GDDActivity': ['modified'],
    'governments.GDDKeyIntervention': ['modified'],
    'governments.GDDRisk': ['modified'],
    'governments.GDDSupplyItem': [
        'modified',
        'total_price', 'result'
    ],
    'governments.GDDActivityItem': ['modified'],
}
GDD_AMENDMENT_DEFAULTS = {
    'governments.GDD': {
        'status': 'draft',
        'in_amendment': True,
        'partner_accepted': False,
        'unicef_accepted': False,
    }
}

# full snapshot related modifications to fields list.
# as an example we don't need to copy intervention reviews, as they have custom flow,
# although for full snapshot they are required
GDD_FULL_SNAPSHOT_RELATED_FIELDS = copy.deepcopy(GDD_AMENDMENT_RELATED_FIELDS)
GDD_FULL_SNAPSHOT_RELATED_FIELDS['governments.GDD'].extend([
    'reviews',
])
GDD_FULL_SNAPSHOT_RELATED_FIELDS['governments.GDDReview'] = [
    'gdd_prc_reviews',
    'submitted_by',
    'prc_officers',
    'overall_approver',
    'authorized_officer',
]
GDD_FULL_SNAPSHOT_RELATED_FIELDS['governments.GDDPRCOfficerReview'] = [
    'user',
]
GDD_FULL_SNAPSHOT_IGNORED_FIELDS = copy.deepcopy(GDD_AMENDMENT_IGNORED_FIELDS)
GDD_FULL_SNAPSHOT_IGNORED_FIELDS['governments.GDDBudget'] = [
    'modified',
]


# activity quarters
def copy_activity_quarters(activity, activity_copy, fields_map):
    quarters = list(activity.time_frames.values_list('quarter', flat=True))
    activity_copy.time_frames.add(*activity_copy.result.result_link.gdd.quarters.filter(quarter__in=quarters))
    fields_map['quarters'] = quarters


def merge_activity_quarters(activity, activity_copy, fields_map):
    quarters = list(activity_copy.time_frames.values_list('quarter', flat=True))
    activity.time_frames.clear()
    activity.time_frames.add(*activity.result.result_link.gdd.quarters.filter(quarter__in=quarters))


def render_quarters_difference(activity, activity_copy, fields_map, difference):
    old_quarters = list(activity.time_frames.values_list('quarter', flat=True))
    new_quarters = list(activity_copy.time_frames.values_list('quarter', flat=True))
    if set(old_quarters).symmetric_difference(set(new_quarters)):
        difference['quarters'] = {
            'type': 'simple',
            'diff': (old_quarters, new_quarters)
        }


# supply items results
def copy_supply_item_result(item, item_copy, fields_map):
    result = item.result
    if result:
        item_copy.result = item.result.__class__.objects.filter(
            gdd=item_copy.gdd,
            cp_output=result.cp_output,
        ).first()
        item_copy.save()
    fields_map['result__cp_output'] = serialize_instance(result.cp_output) if result else None


def merge_supply_item_result(item, item_copy, fields_map):
    result = item_copy.result
    if result:
        item.result = item_copy.result.__class__.objects.filter(
            gdd=item.gdd,
            cp_output=result.cp_output,
        ).first()
    else:
        item.result = None
    item.save()


def render_supply_item_result_difference(item, item_copy, fields_map, difference):
    old_output = getattr(item.result, 'cp_output', None)
    new_output = getattr(item_copy.result, 'cp_output', None)
    if old_output != new_output:
        difference['result__cp_output'] = {
            'type': 'simple',
            'diff': (
                str(old_output) if old_output else None,
                str(new_output) if new_output else None
            )
        }


GDD_AMENDMENT_MERGE_POST_EFFECTS = {
    'governments.GDDActivity': [
        merge_activity_quarters,
    ],
    'governments.GDDSupplyItem': [
        merge_supply_item_result,
    ],
}
GDD_AMENDMENT_COPY_POST_EFFECTS = {
    'governments.GDDActivity': [
        copy_activity_quarters,
    ],
    'governments.GDDSupplyItem': [
        copy_supply_item_result,
    ],
}
GDD_AMENDMENT_DIFF_POST_EFFECTS = {
    'governments.GDDActivity': [
        render_quarters_difference,
    ],
    'governments.GDD': [
        transform_to_choices_list('cash_transfer_modalities', 'cash_transfer_modalities'),
        transform_to_choices('gender_rating', 'gender_rating'),
        transform_to_choices('equity_rating', 'equity_rating'),
        transform_to_choices('sustainability_rating', 'sustainability_rating'),
    ],
    'governments.GDDRisk': [
        transform_to_choices('risk_type', 'risk_types'),
    ],
    'governments.GDDSupplyItem': [
        render_supply_item_result_difference,
        transform_to_choices('provided_by', 'supply_item_provided_by'),
    ],
}
