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
        return f"{self.field} of {self.instance} was changed during amendment process. " \
               f"Please re-create amendment from updated instance."


def copy_m2m_relations(instance, instance_copy, relations, objects_map):
    for m2m_relation in relations:
        m2m_instances = getattr(instance, m2m_relation).all()
        objects_map[m2m_relation] = [i.pk for i in m2m_instances]
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


def copy_one_to_many(instance, instance_copy, related_name, fields_map, relations_to_copy, exclude_fields, kwargs):
    related_field = [f for f in instance._meta.get_fields() if f.name == related_name][0]

    for item in getattr(instance, related_name).all():
        local_kwargs = copy.deepcopy(kwargs)
        if item._meta.label not in local_kwargs:
            local_kwargs[item._meta.label] = {}
        local_kwargs[item._meta.label][related_field.field.name] = instance_copy

        item_copy, copy_map = copy_instance(item, relations_to_copy, exclude_fields, local_kwargs)
        fields_map.append(copy_map)


def copy_instance(instance, relations_to_copy, exclude_fields, defaults):
    related_fields_to_copy = relations_to_copy.get(instance._meta.label, [])
    instance_defaults = defaults.get(instance._meta.label, {})
    fields_to_exclude = exclude_fields.get(instance._meta.label, []) + list(instance_defaults.keys())

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
            # full copy related instance (if exists use current one)
            # todo: implement copy if object not available
            # todo: not only simple fields can be required
            copy_map[field.name] = {}
            related_instance_copy = getattr(instance_copy, field.name)
            fields_to_exclude = exclude_fields.get(related_instance_copy._meta.label, [])
            copy_simple_fields(
                getattr(instance, field.name),
                related_instance_copy,
                copy_map[field.name],
                exclude=fields_to_exclude,
            )
            related_instance_copy.save()

        if field.one_to_many:
            # copy all related instances
            copy_map[field.name] = []
            copy_one_to_many(instance, instance_copy, field.name, copy_map[field.name], relations_to_copy,
                             exclude_fields, defaults)

        if field.many_to_many:
            # link all related instances with copy
            copy_m2m_relations(instance, instance_copy, [field.name], copy_map)

    return instance_copy, copy_map


def merge_instance(instance, instance_copy, fields_map, relations_to_copy, exclude_fields):
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
            # todo: if one of related objects is missing, raise error

            related_instance = getattr(instance, field.name)
            related_instance_copy = getattr(instance_copy, field.name)
            merge_simple_fields(
                related_instance,
                related_instance_copy,
                fields_map[field.name],
                exclude=exclude_fields.get(instance._meta.label, [])
            )

        if field.one_to_many:
            if field.name not in fields_map:
                continue

            for related_instance_data in fields_map[field.name]:
                related_instance = field.related_model.objects.filter(pk=related_instance_data['original_pk']).first()
                related_instance_copy = field.related_model.objects.filter(pk=related_instance_data['copy_pk']).first()
                if related_instance_copy:
                    if not related_instance:
                        related_field = [f for f in instance._meta.get_fields() if f.name == field.name][0]

                        # todo: allow custom defaults here
                        local_kwargs = {
                            related_instance_copy._meta.label: {
                                related_field.field.name: instance
                            }
                        }

                        copy_instance(related_instance_copy, relations_to_copy, exclude_fields, local_kwargs)
                    else:
                        merge_simple_fields(
                            related_instance,
                            related_instance_copy,
                            fields_map[field.name],
                            exclude=exclude_fields.get(instance._meta.label, [])
                        )
                elif related_instance:
                    related_instance.delete()

        if field.many_to_many:
            if field.name not in fields_map:
                continue

            original_value = fields_map[field.name]
            modified_value = getattr(instance_copy, field.name).values_list('pk', flat=True)

            # no checks at this moment, so m2m fields can be edited in multiple amendments
            new_links = set(modified_value) - set(original_value)
            removed_links = set(original_value) - set(modified_value)
            getattr(instance, field.name).add(*new_links)
            getattr(instance, field.name).remove(*removed_links)


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
            modified_value_serialized = None

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


def calculate_difference(instance, instance_copy, fields_map, relations_to_copy, exclude_fields):
    related_fields_to_copy = relations_to_copy.get(instance._meta.label, [])
    fields_to_exclude = exclude_fields.get(instance._meta.label, [])

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
                'diff': (original_value, modified_value),
            }

    for field in instance._meta.get_fields():
        if field.name in fields_to_exclude or field.name not in related_fields_to_copy:
            continue

        if field.one_to_one:
            # todo: if one of related objects is missing, raise error

            related_instance = getattr(instance, field.name)
            related_instance_copy = getattr(instance_copy, field.name)
            related_changes_map = calculate_simple_fields_difference(
                related_instance,
                related_instance_copy,
                fields_map[field.name],
                exclude=exclude_fields.get(instance._meta.label, [])
            )
            if related_changes_map:
                changes_map[field.name] = {'type': 'one_to_one', 'diff': related_changes_map}

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

            for related_instance_data in fields_map[field.name]:
                related_instance = field.related_model.objects.filter(pk=related_instance_data['original_pk']).first()
                related_instance_copy = field.related_model.objects.filter(pk=related_instance_data['copy_pk']).first()
                if related_instance_copy:
                    if not related_instance:
                        related_changes_map['diff']['create'].append({
                            'pk': related_instance_copy.pk,
                            'name': str(related_instance_copy),
                        })
                    else:
                        related_object_changes_map = calculate_difference(
                            related_instance, related_instance_copy, related_instance_data, relations_to_copy, exclude_fields=exclude_fields
                        )
                        if related_object_changes_map:
                            related_changes_map['diff']['update'].append({
                                'pk': related_instance.pk,
                                'name': str(related_instance),
                                'diff': related_object_changes_map
                            })
                elif related_instance:
                    related_changes_map['diff']['remove'].append({
                        'pk': related_instance.pk,
                        'name': str(related_instance)
                    })

            if related_changes_map['diff']['create'] or related_changes_map['diff']['remove'] or related_changes_map['diff']['update']:
                changes_map[field.name] = related_changes_map

        if field.many_to_many:
            if field.name not in fields_map:
                continue

            original_value = fields_map[field.name]
            modified_value = getattr(instance_copy, field.name).values_list('pk', flat=True)

            # no checks at this moment, so m2m fields can be edited in multiple amendments
            new_links = set(modified_value) - set(original_value)
            removed_links = set(original_value) - set(modified_value)

            if not (new_links or removed_links):
                continue

            changes_map[field.name] = {
                'type': 'many_to_many',
                'diff': {
                    'original': original_value,
                    'add': list(new_links),
                    'remove': list(removed_links),
                }
            }

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
        'country_programmes', 'unicef_focal_points', 'partner_focal_points',
        'sections', 'offices', 'flat_locations'
    ],
    'partners.InterventionResultLink': [
        # one to many
        'll_results',

        # many to many
        'ram_indicators',
    ],
    'reports.LowerResult': [
        # one to many
        'activities',
    ]
}
INTERVENTION_AMENDMENT_IGNORED_FIELDS = {
    'partners.Intervention': [
        'created', 'modified',
        'number',
        # signatures
        'signed_by_unicef_date',
        'signed_by_partner_date',
    ],
    'partners.InterventionBudget': [
        'created', 'modified',
        # auto calculated fields
        'partner_contribution_local',
        'total_unicef_cash_local_wo_hq',
        'unicef_cash_local',
        'in_kind_amount_local',
        'total',
        'total_local',
        'programme_effectiveness',
    ],
    'partners.InterventionManagementBudget': ['created', 'modified'],
    'reports.ReportingRequirement': ['created', 'modified'],
    'partners.InterventionResultLink': ['created', 'modified'],
    'reports.LowerResult': ['created', 'modified'],
    'partners.InterventionSupplyItem': ['total_price'],
}
INTERVENTION_AMENDMENT_DEFAULTS = {
    'partners.Intervention': {
        'status': 'draft',
        'is_amendment': True,
    }
}
