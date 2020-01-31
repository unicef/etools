from etools.applications.field_monitoring.data_collection.models import Finding, StartedChecklist
from etools.applications.field_monitoring.data_collection.offline.blueprint import get_blueprint_for_activity_and_method
from etools.applications.field_monitoring.fm_settings.models import Method, Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.users.models import User


def save_values_to_checklist(value: dict, checklist: StartedChecklist):
    for level in dict(MonitoringActivity.RELATIONS_MAPPING).values():
        level_values = value.get(level)
        if not level_values:
            continue

        for target_id, target_value in level_values.items():
            overall_finding = checklist.overall_findings.filter(
                **{Question.get_target_relation_name(level): target_id}
            ).prefetch_related('attachments').get()

            overall_finding.narrative_finding = target_value.get('overall', '')
            overall_finding.save()

            attachments = target_value.get('attachments', [])

            for attachment in attachments:
                print('attachment ', attachment, ' received')

            questions = target_value.get('questions', {})
            for question_id, question_value in questions.items():
                finding = Finding.objects.get(activity_question__question=question_id)
                finding.value = question_value
                finding.save()


def update_checklist(checklist: StartedChecklist, value: dict):
    # validate value with actual blueprint to be sure everything is ok
    blueprint = get_blueprint_for_activity_and_method(checklist.monitoring_activity, checklist.method)
    validated_value = blueprint.validate(value)

    checklist.information_source = validated_value.get('information_source', '')
    checklist.save()

    save_values_to_checklist(validated_value, checklist)

    return checklist


def create_checklist(activity: MonitoringActivity, method: Method, user: User, value: dict):
    # validate value with actual blueprint to be sure everything is ok
    blueprint = get_blueprint_for_activity_and_method(activity, method)
    validated_value = blueprint.validate(value)

    checklist = StartedChecklist.objects.create(
        author=user, monitoring_activity=activity, method=method,
        information_source=validated_value.get('information_source', '')
    )

    save_values_to_checklist(validated_value, checklist)

    return checklist


def get_checklist_form_value(checklist: StartedChecklist) -> dict:
    # todo
    method = checklist.method

    value = {}

    if method.use_information_source:
        value['information_source'] = checklist.information_source

    for overall_finding in checklist.overall_findings.prefetch_related('attachments'):
        block_value = {
            'overall': overall_finding.narrative_finding,
            'attachments': [
                {
                    'url': attachment.url,
                    'id': attachment.id,
                    'file_type': attachment.file_type,
                }
                for attachment in overall_finding.attachments.all()
            ]
        }
        questions_value = []
        for finding in Finding.objects.filter(
            started_checklist=checklist,
            **{'activity_question__{}'.format(overall_finding.related_to_name): overall_finding.related_to}
        ).prefetch_related('activity_question__question'):
            questions_value.append({
                # 'name':
            })
            block_value['question_{}'.format(finding.activity_question.question.id)] = finding.value

        value['{}_{}'.format(
            dict(MonitoringActivity.RELATIONS_MAPPING[overall_finding.related_to_name]),
            overall_finding.related_to.id
        )] = block_value

    return value
