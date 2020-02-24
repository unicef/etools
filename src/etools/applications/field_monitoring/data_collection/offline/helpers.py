from typing import Dict, List

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from unicef_attachments.models import AttachmentLink

from etools.applications.field_monitoring.data_collection.models import ChecklistOverallFinding, StartedChecklist
from etools.applications.field_monitoring.data_collection.offline.blueprint import get_blueprint_for_activity_and_method
from etools.applications.field_monitoring.fm_settings.models import Method, Question
from etools.applications.field_monitoring.planning.models import MonitoringActivity
from etools.applications.users.models import User


def _link_attachments(attachments_data: List[Dict], overall_finding: ChecklistOverallFinding):
    for attachment_data in attachments_data:
        attachment = attachment_data['attachment']
        attachment.file_type_id = attachment_data['file_type']
        attachment.content_object = overall_finding
        attachment.code = 'attachments'
        attachment.save()
        AttachmentLink.objects.get_or_create(
            attachment=attachment,
            content_type=ContentType.objects.get_for_model(ChecklistOverallFinding),
            object_id=overall_finding.id
        )

    for attachment in overall_finding.attachments.exclude(pk__in=[a['attachment'].id for a in attachments_data]):
        attachment.delete()


def _save_values_to_checklist(value: dict, checklist: StartedChecklist) -> None:
    for level in dict(MonitoringActivity.RELATIONS_MAPPING).values():
        level_values = value.get(level)
        if not level_values:
            continue

        relation_name = Question.get_target_relation_name(level)

        for target_id, target_value in level_values.items():
            overall_finding = checklist.overall_findings.filter(
                **{relation_name: target_id}
            ).prefetch_related('attachments').get()

            overall_finding.narrative_finding = target_value.get('overall', '')
            overall_finding.save()

            attachments = target_value.get('attachments', [])

            _link_attachments(attachments, overall_finding)

            questions = target_value.get('questions', {})
            for question_id, question_value in questions.items():
                finding = checklist.findings.get(
                    **{f'activity_question__{relation_name}': target_id},
                    activity_question__question=question_id
                )
                finding.value = question_value
                finding.save()


def update_checklist(checklist: StartedChecklist, value: dict) -> StartedChecklist:
    # validate value with actual blueprint to be sure everything is ok
    blueprint = get_blueprint_for_activity_and_method(checklist.monitoring_activity, checklist.method)
    validated_value = blueprint.validate(value)

    checklist.information_source = validated_value.get('information_source', {}).get('name', '')
    checklist.save()

    _save_values_to_checklist(validated_value, checklist)

    return checklist


def create_checklist(activity: MonitoringActivity, method: Method, user: User, value: dict) -> StartedChecklist:
    # validate value with actual blueprint to be sure everything is ok
    blueprint = get_blueprint_for_activity_and_method(activity, method)
    validated_value = blueprint.validate(value)

    checklist = StartedChecklist.objects.create(
        author=user, monitoring_activity=activity, method=method,
        information_source=validated_value.get('information_source', {}).get('name', '')
    )

    _save_values_to_checklist(validated_value, checklist)

    return checklist


def get_checklist_form_value(checklist: StartedChecklist) -> dict:
    method = checklist.method

    value = {}

    if method.use_information_source:
        value['information_source'] = {'name': checklist.information_source}

    for level in dict(MonitoringActivity.RELATIONS_MAPPING).values():
        relation_name = Question.get_target_relation_name(level)

        level_value = {}
        for overall_finding in checklist.overall_findings.filter(
            **{f'{relation_name}__isnull': False}
        ).select_related(relation_name).prefetch_related('attachments'):
            target_id = getattr(overall_finding, f'{relation_name}_id')
            target_value = {
                'overall': overall_finding.narrative_finding,
                'attachments': [
                    {
                        'attachment': str(attachment.pk),
                        'file_type': str(attachment.file_type_id),
                        'url': reverse('attachments:file', args=[attachment.pk]),
                        'filename': attachment.filename,
                    }
                    for attachment in overall_finding.attachments.all()
                ],
                'questions': {},
            }

            for finding in checklist.findings.filter(
                **{f'activity_question__{relation_name}': target_id}
            ).values('value', 'activity_question__question_id'):
                target_value['questions'][str(finding['activity_question__question_id'])] = finding['value']

            level_value[str(target_id)] = target_value

        if level_value:
            value[level] = level_value

    return value
