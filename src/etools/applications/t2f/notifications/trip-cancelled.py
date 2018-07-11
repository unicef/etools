name = 'trips/trip/approved'
defaults = {
    'description': 'The email that is sent to the traveller if a trip has been approved',
    'subject': 'eTools {{environment}} - Trip Approved: {{trip_reference}}',
    'content': """
    The following trip has been approved: {{trip_reference}}

    {{url}}

    Thank you.
    """,
    'html_content': """
    The following trip has been approved: {{trip_reference}}
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
