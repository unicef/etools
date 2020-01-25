from django.db import connection
from django.utils.translation import ugettext_lazy as _

from etools.applications.field_monitoring.data_collection.offline.blueprint.base import Blueprint
from etools.applications.field_monitoring.data_collection.offline.structure.base import Card, Field
from etools.applications.field_monitoring.fm_settings.models import Method, Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity

# todo: move this file and all fm mentions out of offline app module


answer_type_to_field_types_mapping = {
    Question.ANSWER_TYPES.text: 'text',
    Question.ANSWER_TYPES.number: 'number',
    Question.ANSWER_TYPES.bool: 'dropdown',
    Question.ANSWER_TYPES.likert_scale: 'dropdown',
}


def get_monitoring_activity_blueprints(activity: MonitoringActivity):
    blueprints = {}  # todo: how to map correctly filled form to activity/method? some extra field? extra model?

    for method in Method.objects.filter(
        pk__in=activity.questions.filter(
            is_enabled=True
        ).values_list('question__methods', flat=True)
    ):
        blueprint = Blueprint(
            'fm_data_collection',
            '{} for {}'.format(method.name, activity.reference_number),
        )
        # todo: how configure layout? or leave it for frontend?
        blueprint.add(Field('information_source', 'text', label=_('Source of Information'), extra={'type': ['wide']}))

        for relation, level in activity.RELATIONS_MAPPING:
            for target in getattr(activity, relation).all():
                target_questions = activity.questions.filter(
                    **{Question.get_target_relation_name(level): target},
                    is_enabled=True, question__methods=method
                )
                if not target_questions.exists():
                    continue

                block = Card(
                    '{}_{}'.format(level, target.id),
                    str(target),
                    Field('overall', 'text', label=_('Overall Finding'), extra={'type': ['wide', 'additional']}),
                    Field('attachments', 'file', repeatable=True),
                )
                for question in target_questions.distinct():
                    if question.question.answer_type in [
                        Question.ANSWER_TYPES.bool,
                        Question.ANSWER_TYPES.likert_scale
                    ]:
                        options_key = 'question_{}'.format(question.question.id)
                        blueprint.metadata.options[options_key] = {
                            'options_type': 'local_pairs',
                            'values': list(question.question.options.values('value', 'label'))
                        }
                    else:
                        options_key = None

                    block.add(
                        Field(
                            'question_{}'.format(question.id),
                            answer_type_to_field_types_mapping[question.question.answer_type],
                            label=question.question.text,
                            options_key=options_key,
                            help_text=question.specific_details
                        )
                    )
                blueprint.add(block)

        country_code = connection.tenant.country_short_code or ''
        blueprints[f'fm_{country_code}_{activity.id}_{method.id}'] = blueprint
    return blueprints


def parse_answers(values):
    # todo: go through completed form values and save them into checklist
    pass
