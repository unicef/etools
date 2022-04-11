import copy
import datetime
import decimal

from django.db.models import DateField, DateTimeField, DecimalField, FileField
from django.db.models.fields.files import FieldFile


class MergeError(Exception):
    def __init__(self, instance, field):
        self.instance = instance
        self.field = field

    def __str__(self):
        return f"{self.field} of {self.instance} ({type(self.instance).__name__}) was changed " \
               f"during amendment process. Please re-create amendment from updated instance."


def serialize_instance(instance):
    if hasattr(instance, 'get_amended_name'):
        name = instance.get_amended_name()
    else:
        name = str(instance)

    return {'pk': instance.pk, 'name': name}


def copy_m2m_relations(instance, instance_copy, relations, objects_map):
    for m2m_relation in relations:
        m2m_instances = getattr(instance, m2m_relation).all()
        objects_map[m2m_relation] = [serialize_instance(i) for i in m2m_instances]
        getattr(instance_copy, m2m_relation).add(*m2m_instances)


def copy_simple_fields(instance, instance_copy, fields_map, exclude=None):
    exclude = exclude or []
    for field in instance._meta.get_fields():
        field_is_simple = not (field.many_to_many or field.many_to_one or field.one_to_many or field.one_to_one)
        if field.name not in exclude and field.concrete and field_is_simple and not field.auto_created:
            value = getattr(instance, field.name)
            setattr(instance_copy, field.name, value)

            if value is not None:
                if isinstance(field, DateTimeField):
                    value = value.isoformat()
                elif isinstance(field, DateField):
                    value = value.isoformat()
                elif isinstance(field, DecimalField) and isinstance(value, decimal.Decimal):
                    # decimal field can contain float from default
                    value = value.to_eng_string()
                elif isinstance(field, FileField):
                    value = value.name
            fields_map[field.name] = value


def merge_simple_fields(instance, instance_copy, fields_map, exclude=None):
    exclude = exclude or []
    for field in instance._meta.get_fields():
        field_is_simple = not (field.many_to_many or field.many_to_one or field.one_to_many or field.one_to_one)
        if field.name not in exclude and field.concrete and field_is_simple and not field.auto_created:
            if field.name not in fields_map:
                # field added after amendment created
                continue

            original_value = fields_map[field.name]
            current_value = getattr(instance, field.name)
            modified_value = getattr(instance_copy, field.name)

            if original_value:
                if isinstance(field, DateTimeField):
                    original_value = datetime.datetime.fromisoformat(original_value)
                elif isinstance(field, DateField):
                    try:
                        original_value = datetime.date.fromisoformat(original_value)
                    except ValueError:
                        original_value = datetime.datetime.fromisoformat(original_value).date()
                elif isinstance(field, DecimalField):
                    original_value = decimal.Decimal(original_value)
                elif isinstance(field, FileField):
                    original_value = FieldFile(instance, field, original_value)

            if original_value == modified_value:
                # nothing changed
                continue

            if modified_value == current_value:
                # same field changes already performed
                continue

            if current_value != original_value:
                # value changed in both objects, cannot be merged automatically
                raise MergeError(instance, field.name)

            setattr(instance, field.name, modified_value)

        instance.save()


def copy_one_to_many(
    instance, instance_copy, related_name, fields_map,
    relations_to_copy, exclude_fields, defaults, post_effects,
):
    related_field = [f for f in instance._meta.get_fields() if f.name == related_name][0]

    for item in getattr(instance, related_name).all():
        local_kwargs = copy.deepcopy(defaults)
        if item._meta.label not in local_kwargs:
            local_kwargs[item._meta.label] = {}
        local_kwargs[item._meta.label][related_field.field.name] = instance_copy

        item_copy, copy_map = copy_instance(item, relations_to_copy, exclude_fields, local_kwargs, post_effects)
        fields_map.append(copy_map)


def copy_one_to_one(
    instance, instance_copy, related_name, fields_map,
    relations_to_copy, exclude_fields, defaults, post_effects,
):
    related_field = [f for f in instance._meta.get_fields() if f.name == related_name][0]

    item = getattr(instance, related_name)
    item_copy = getattr(instance_copy, related_name)
    local_kwargs = copy.deepcopy(defaults)
    if item._meta.label not in local_kwargs:
        local_kwargs[item._meta.label] = {}
    local_kwargs[item._meta.label][related_field.field.name] = instance_copy

    item_copy, copy_map = copy_instance(
        item, relations_to_copy, exclude_fields, local_kwargs, post_effects,
        instance_copy=item_copy,
    )
    fields_map.update(copy_map)


def copy_instance(instance, relations_to_copy, exclude_fields, defaults, post_effects, instance_copy=None):
    related_fields_to_copy = relations_to_copy.get(instance._meta.label, [])
    instance_defaults = defaults.get(instance._meta.label, {})
    fields_to_exclude = exclude_fields.get(instance._meta.label, [])
    local_post_effects = post_effects.get(instance._meta.label, [])

    if not instance_copy:
        instance_copy = type(instance)(**instance_defaults)

    copy_map = {
        'original_pk': instance.pk,
    }
    copy_simple_fields(instance, instance_copy, copy_map, exclude=fields_to_exclude)

    for field in instance._meta.get_fields():
        if field.name in fields_to_exclude or field.name not in related_fields_to_copy:
            continue

        if field.many_to_one:
            # just set foreign key
            value = getattr(instance, field.name)
            setattr(instance_copy, field.name, value)
            copy_map[field.name] = value.pk if value else None

    instance_copy.save()
    copy_map['copy_pk'] = instance_copy.pk

    for field in instance._meta.get_fields():
        if field.name in fields_to_exclude or field.name not in related_fields_to_copy:
            continue

        if field.one_to_one:
            copy_map[field.name] = {}
            copy_one_to_one(instance, instance_copy, field.name, copy_map[field.name], relations_to_copy,
                            exclude_fields, defaults, post_effects)

        if field.one_to_many:
            # copy all related instances
            copy_map[field.name] = []
            copy_one_to_many(instance, instance_copy, field.name, copy_map[field.name], relations_to_copy,
                             exclude_fields, defaults, post_effects)

        if field.many_to_many:
            # link all related instances with copy
            copy_m2m_relations(instance, instance_copy, [field.name], copy_map)

    for post_effect in local_post_effects:
        post_effect(instance, instance_copy, copy_map)

    return instance_copy, copy_map


def merge_instance(
    instance, instance_copy, fields_map, relations_to_copy, exclude_fields,
    copy_post_effects, merge_post_effects,
):
    related_fields_to_copy = relations_to_copy.get(instance._meta.label, [])
    fields_to_exclude = exclude_fields.get(instance._meta.label, [])

    merge_simple_fields(instance, instance_copy, fields_map, exclude=fields_to_exclude)

    for field in instance._meta.get_fields():
        if field.name not in fields_map:
            # field added after amendment
            continue

        if field.many_to_one:
            value = fields_map[field.name]
            if value:
                original_value = field.related_model.objects.get(pk=value)
            else:
                original_value = None

            modified_value = getattr(instance_copy, field.name)
            current_value = getattr(instance, field.name)
            if original_value == modified_value:
                # nothing changed
                continue

            if modified_value == current_value:
                # same field changes already performed
                continue

            if current_value != original_value:
                # value changed in both objects, cannot be merged automatically
                raise MergeError(instance, field.name)

            setattr(instance, field.name, modified_value)

    instance.save()

    for field in instance._meta.get_fields():
        if field.name in fields_to_exclude or field.name not in related_fields_to_copy:
            continue

        if field.one_to_one:
            related_instance = getattr(instance, field.name)
            related_instance_copy = getattr(instance_copy, field.name)
            merge_instance(
                related_instance,
                related_instance_copy,
                fields_map[field.name],
                relations_to_copy,
                exclude_fields,
                copy_post_effects,
                merge_post_effects,
            )

        if field.one_to_many:
            if field.name not in fields_map:
                continue

            copied_instances = []
            for related_instance_data in fields_map[field.name]:
                related_instance = field.related_model.objects.filter(pk=related_instance_data['original_pk']).first()
                related_instance_copy = field.related_model.objects.filter(pk=related_instance_data['copy_pk']).first()
                copied_instances.append(related_instance_data['copy_pk'])
                if related_instance_copy:
                    if not related_instance:
                        # original object already deleted
                        continue
                    else:
                        merge_instance(
                            related_instance,
                            related_instance_copy,
                            related_instance_data,
                            relations_to_copy,
                            exclude_fields,
                            copy_post_effects,
                            merge_post_effects,
                        )
                elif related_instance:
                    related_instance.delete()

            related_field = [f for f in instance._meta.get_fields() if f.name == field.name][0]
            local_kwargs = {
                field.related_model._meta.label: {
                    related_field.field.name: instance
                }
            }
            related_instances = field.related_model.objects.filter(
                **{f'{related_field.field.name}__pk': instance_copy.pk}
            )
            for related_instance_copy in related_instances.exclude(pk__in=copied_instances):
                copy_instance(related_instance_copy, relations_to_copy, exclude_fields, local_kwargs, copy_post_effects)

        if field.many_to_many:
            if field.name not in fields_map:
                continue

            original_value = [i['pk'] for i in fields_map[field.name]]
            modified_value = getattr(instance_copy, field.name).values_list('pk', flat=True)

            # no checks at this moment, so m2m fields can be edited in multiple amendments
            new_links = set(modified_value) - set(original_value)
            removed_links = set(original_value) - set(modified_value)
            getattr(instance, field.name).add(*new_links)
            getattr(instance, field.name).remove(*removed_links)

    for merge_post_effect in merge_post_effects.get(instance._meta.label, []):
        merge_post_effect(instance, instance_copy, fields_map)


def calculate_simple_fields_difference(instance, instance_copy, fields_map, exclude=None):
    changes_map = {}
    exclude = exclude or []
    for field in instance._meta.get_fields():
        field_is_simple = not (field.many_to_many or field.many_to_one or field.one_to_many or field.one_to_one)
        if field.name not in exclude and field.concrete and field_is_simple and not field.auto_created:
            if field.name not in fields_map:
                # field added after amendment created
                continue

            original_value_serialized = fields_map[field.name]
            original_value = fields_map[field.name]
            current_value = getattr(instance, field.name)
            modified_value = getattr(instance_copy, field.name)
            modified_value_serialized = modified_value

            if original_value is not None:
                if isinstance(field, DateTimeField):
                    original_value = datetime.datetime.fromisoformat(original_value)
                elif isinstance(field, DateField):
                    try:
                        original_value = datetime.date.fromisoformat(original_value)
                    except ValueError:
                        original_value = datetime.datetime.fromisoformat(original_value).date()
                elif isinstance(field, DecimalField):
                    original_value = decimal.Decimal(original_value)
                elif isinstance(field, FileField):
                    original_value = FieldFile(instance, field, original_value)

            if modified_value is not None:
                if isinstance(field, DateTimeField):
                    modified_value_serialized = modified_value.isoformat()
                elif isinstance(field, DateField):
                    modified_value_serialized = modified_value.isoformat()
                elif isinstance(field, DecimalField) and isinstance(modified_value, decimal.Decimal):
                    # decimal field can contain float from default
                    modified_value_serialized = modified_value.to_eng_string()
                elif isinstance(field, FileField):
                    modified_value_serialized = modified_value.name

            if original_value == modified_value:
                # nothing changed
                continue

            if modified_value == current_value:
                # same field changes already performed
                continue

            if current_value != original_value:
                # value changed in both objects, cannot be merged automatically
                raise MergeError(instance, field.name)

            changes_map[field.name] = {'type': 'simple', 'diff': (original_value_serialized, modified_value_serialized)}

    return changes_map


def calculate_difference(instance, instance_copy, fields_map, relations_to_copy, exclude_fields, diff_post_effects):
    related_fields_to_copy = relations_to_copy.get(instance._meta.label, [])
    fields_to_exclude = exclude_fields.get(instance._meta.label, [])
    local_post_effects = diff_post_effects.get(instance._meta.label, [])

    changes_map = calculate_simple_fields_difference(instance, instance_copy, fields_map, exclude=fields_to_exclude)

    for field in instance._meta.get_fields():
        if field.name not in fields_map:
            # field added after amendment
            continue

        if field.many_to_one:
            value = fields_map[field.name]
            if value:
                original_value = field.related_model.objects.get(pk=value)
            else:
                original_value = None

            modified_value = getattr(instance_copy, field.name)
            current_value = getattr(instance, field.name)
            if original_value == modified_value:
                # nothing changed
                continue

            if modified_value == current_value:
                # same field changes already performed
                continue

            if current_value != original_value:
                # value changed in both objects, cannot be merged automatically
                raise MergeError(instance, field.name)

            changes_map[field.name] = {
                'type': 'many_to_one',
                'diff': (
                    serialize_instance(original_value),
                    serialize_instance(modified_value),
                ),
            }

    for field in instance._meta.get_fields():
        if field.name in fields_to_exclude or field.name not in related_fields_to_copy:
            continue

        if field.one_to_one:
            # todo: if one of related objects is missing, raise error

            related_instance = getattr(instance, field.name)
            related_instance_copy = getattr(instance_copy, field.name)
            related_object_changes_map = calculate_difference(
                related_instance, related_instance_copy, fields_map[field.name], relations_to_copy,
                exclude_fields, diff_post_effects
            )

            if related_object_changes_map:
                changes_map[field.name] = {'type': 'one_to_one', 'diff': related_object_changes_map}

        if field.one_to_many:
            if field.name not in fields_map:
                continue

            related_changes_map = {
                'type': 'one_to_many',
                'diff': {
                    'create': [],
                    'remove': [],
                    'update': [],
                }
            }

            copied_instances = []
            for related_instance_data in fields_map[field.name]:
                related_instance = field.related_model.objects.filter(pk=related_instance_data['original_pk']).first()
                related_instance_copy = field.related_model.objects.filter(pk=related_instance_data['copy_pk']).first()
                copied_instances.append(related_instance_data['copy_pk'])

                if not related_instance:
                    # original object already deleted
                    continue

                if related_instance_copy:
                    related_object_changes_map = calculate_difference(
                        related_instance, related_instance_copy, related_instance_data, relations_to_copy,
                        exclude_fields, diff_post_effects
                    )
                    if related_object_changes_map:
                        data = serialize_instance(related_instance)
                        data['diff'] = related_object_changes_map
                        related_changes_map['diff']['update'].append(data)
                else:
                    related_changes_map['diff']['remove'].append(serialize_instance(related_instance))

            related_field = [f for f in instance_copy._meta.get_fields() if f.name == field.name][0]
            related_instances = field.related_model.objects.filter(
                **{f'{related_field.field.name}__pk': instance_copy.pk}
            )
            for related_instance_copy in related_instances.exclude(pk__in=copied_instances):
                related_changes_map['diff']['create'].append(serialize_instance(related_instance_copy))

            if any([
                related_changes_map['diff']['create'],
                related_changes_map['diff']['remove'],
                related_changes_map['diff']['update'],
            ]):
                changes_map[field.name] = related_changes_map

        if field.many_to_many:
            if field.name not in fields_map:
                continue

            original_serialized_objects = fields_map[field.name]
            original_value = [i['pk'] for i in original_serialized_objects]
            modified_serialized_objects = [serialize_instance(i) for i in getattr(instance_copy, field.name).all()]
            modified_value = [obj['pk'] for obj in modified_serialized_objects]

            # no checks at this moment, so m2m fields can be edited in multiple amendments
            new_links = [
                obj for obj in modified_serialized_objects
                if obj['pk'] in (set(modified_value) - set(original_value))
            ]
            removed_links = [
                obj for obj in original_serialized_objects
                if obj['pk'] in (set(original_value) - set(modified_value))
            ]

            if not (new_links or removed_links):
                continue

            changes_map[field.name] = {
                'type': 'many_to_many',
                'diff': {
                    'original': original_serialized_objects,
                    'add': list(new_links),
                    'remove': list(removed_links),
                }
            }

    for post_effect in local_post_effects:
        post_effect(instance, instance_copy, fields_map, changes_map)

    return changes_map


INTERVENTION_AMENDMENT_RELATED_FIELDS = {
    'partners.Intervention': [
        # one to many
        'result_links',
        'supply_items',
        'risks',
        'reporting_requirements',

        # 1 to 1
        'planned_budget',
        'management_budgets',

        # many to one
        'agreement',
        'budget_owner',

        # many to many
        'country_programmes', 'unicef_focal_points', 'partner_focal_points', 'sites',
        'sections', 'offices', 'flat_locations'
    ],
    'partners.InterventionResultLink': [
        # one to many
        'll_results',

        # many to many
        'ram_indicators',

        # one to one
        'cp_output',
    ],
    'reports.LowerResult': [
        # one to many
        'activities',
        'applied_indicators',
    ],
    'reports.AppliedIndicator': [
        # many to one
        'indicator',
        'section',

        # many to many
        'disaggregation',
        'locations',
    ],
    'partners.InterventionSupplyItem': [
        # many to one
        'result',
    ],
    'reports.InterventionActivity': [
        # one to many
        'items',
    ],
    'partners.InterventionManagementBudget': [
        # one to many
        'items',
    ],
}
INTERVENTION_AMENDMENT_IGNORED_FIELDS = {
    'partners.Intervention': [
        'modified',
        'number', 'status', 'in_amendment',
        'title',
        'sites',

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
    'partners.InterventionBudget': [
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
    'partners.InterventionManagementBudget': ['modified'],
    'partners.InterventionResultLink': ['modified'],
    'reports.ReportingRequirement': ['modified'],
    'reports.InterventionActivity': ['modified'],
    'reports.AppliedIndicator': ['modified'],
    'reports.LowerResult': ['modified'],
    'partners.InterventionRisk': ['modified'],
    'partners.InterventionSupplyItem': [
        'modified',
        'total_price', 'result'
    ],
    'reports.InterventionActivityItem': ['modified'],
}
INTERVENTION_AMENDMENT_DEFAULTS = {
    'partners.Intervention': {
        'status': 'draft',
        'in_amendment': True,
        'partner_accepted': False,
        'unicef_accepted': False,
    }
}


# activity quarters
def copy_activity_quarters(activity, activity_copy, fields_map):
    quarters = list(activity.time_frames.values_list('quarter', flat=True))
    activity_copy.time_frames.add(*activity_copy.result.result_link.intervention.quarters.filter(quarter__in=quarters))
    fields_map['quarters'] = quarters


def merge_activity_quarters(activity, activity_copy, fields_map):
    quarters = list(activity_copy.time_frames.values_list('quarter', flat=True))
    activity.time_frames.clear()
    activity.time_frames.add(*activity.result.result_link.intervention.quarters.filter(quarter__in=quarters))


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
            intervention=item_copy.intervention,
            cp_output=result.cp_output,
        ).first()
        item_copy.save()
    fields_map['result__cp_output'] = serialize_instance(result.cp_output) if result else None


def merge_supply_item_result(item, item_copy, fields_map):
    result = item_copy.result
    if result:
        item.result = item_copy.result.__class__.objects.filter(
            intervention=item.intervention,
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


# choices_key it's the key where choices can be found in Dropdowns api (PMPDropdownsListApiView)
def transform_to_choices_list(field_name, choices_key):
    def transform_field(instance, instance_copy, fields_map, difference):
        if field_name in difference:
            difference[field_name]['type'] = 'list[choices]'
            difference[field_name]['choices_key'] = choices_key
    return transform_field


def transform_to_choices(field_name, choices_key):
    def transform_field(instance, instance_copy, fields_map, difference):
        if field_name in difference:
            difference[field_name]['type'] = 'choices'
            difference[field_name]['choices_key'] = choices_key
    return transform_field


INTERVENTION_AMENDMENT_MERGE_POST_EFFECTS = {
    'reports.InterventionActivity': [
        merge_activity_quarters,
    ],
    'partners.InterventionSupplyItem': [
        merge_supply_item_result,
    ],
}
INTERVENTION_AMENDMENT_COPY_POST_EFFECTS = {
    'reports.InterventionActivity': [
        copy_activity_quarters,
    ],
    'partners.InterventionSupplyItem': [
        copy_supply_item_result,
    ],
}
INTERVENTION_AMENDMENT_DIFF_POST_EFFECTS = {
    'reports.InterventionActivity': [
        render_quarters_difference,
    ],
    'partners.Intervention': [
        transform_to_choices_list('cash_transfer_modalities', 'cash_transfer_modalities'),
        transform_to_choices('document_type', 'intervention_doc_type'),
        transform_to_choices('gender_rating', 'gender_rating'),
        transform_to_choices('equity_rating', 'equity_rating'),
        transform_to_choices('sustainability_rating', 'sustainability_rating'),
    ],
    'partners.InterventionRisk': [
        transform_to_choices('risk_type', 'risk_types'),
    ],
    'partners.InterventionSupplyItem': [
        render_supply_item_result_difference,
        transform_to_choices('provided_by', 'supply_item_provided_by'),
    ],
}
