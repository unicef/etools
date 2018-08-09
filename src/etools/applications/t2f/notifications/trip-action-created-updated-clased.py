name = 'trips/action/created/updated/closed'
defaults = {
    'description': 'Sent when trip action points are created, updated, or closed',
    'subject': 'eTools {{environment}} - Trip action point {{state}} for trip: {{trip_reference}}',
    'content': """
    Trip action point by {{action_point.assigned_by}} for {{action_point.person_responsible}} was {{action_point.status}}:"
    {{action_point.object_url}}

    Thank you.
    """,
    'html_content': """
    Trip action point by {{action_point.assigned_by}} for {{action_point.person_responsible}} was {{action_point.status}}:"

    <br/>
    Reference Number: {{action_point.assigned_by}}
    Status: {{action_point.status}}
    Description: {{action_point.description}}
    Due Date: {{action_point.due_date}}
    Link: {{action_point.object_url}}

    {{action_point.object_url}}
    <br/>
    <br/>
    Thank you.
    """
}
