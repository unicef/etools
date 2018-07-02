name = 'trips/trip/representative'
defaults = {
    'description': 'The email that is sent to the rep  to approve a trip',
    'subject': 'eTools {{environment}} - Trip Approval Needed: {{trip_reference}}',
    'content': """
    The following trip needs representative approval: {{trip_reference}}

    {{url}}

    Thank you.
    """,
    'html_content': """
    The following trip needs representative approval: {{trip_reference}}
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
