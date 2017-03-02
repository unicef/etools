from __future__ import unicode_literals

from rest_framework_csv import renderers


class ActionPointCSVRenderer(renderers.CSVRenderer):
    header = [
        'action_point_number',
        'trip_reference_number',
        'description',
        'due_date',
        'person_responsible',
        'status',
        'completed_date',
        'actions_taken',
        'flag_for_follow_up',
        'assigned_by',
        'url'
    ]

    labels = {
        'action_point_number': 'Action Point Number',
        'trip_reference_number': 'Trip Reference Number',
        'description': 'Description',
        'due_date': 'Due Date',
        'person_responsible': 'Person Responsible',
        'status': 'Status',
        'completed_date': 'Completed Date',
        'actions_taken': 'Actions Taken',
        'flag_for_follow_up': 'Flag For Follow Up',
        'assigned_by': 'Assigned By',
        'url': 'URL'
    }
