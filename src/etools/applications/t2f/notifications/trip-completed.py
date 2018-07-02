name = 'trips/trip/completed'
defaults = {
    'description': 'The email that is sent to travelller and supervisor  when a trip has been completed',
    'subject': 'eTools {{environment}} - Trip Completed: {{trip_reference}}',
    'content': """
    The following trip has been completed: {{trip_reference}}

    {{url}}

    Action Points:

    {{action_points}}

    Thank you.
    """,
    'html_content': """
    The following trip has been completed: {{trip_reference}}
    <br/>
    {{url}}
    <br/>
    Action Points:
    <br/>
    {{action_points}}
    <br/>
    Thank you.
    """
}
