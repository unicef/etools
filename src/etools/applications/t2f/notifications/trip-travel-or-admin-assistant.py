name = 'travel/trip/travel_or_admin_assistant'
defaults = {
    'description': 'This e-mail will be sent when the trip is approved by the supervisor. It will go to the'
    'travel assistant to prompt them to organise the travel (vehicles, flights etc.) and'
    'request security clearance.',
    'subject': 'eTools {{environment}} - Travel for {{owner_name}}',
    'content': """
    Dear {{travel_assistant}},

    Please organise the travel and security clearance (if needed) for the following trip:

    {{url}}

    Thanks,
    {{owner_name}}
    """,
    'html_content': """
    Dear {{travel_assistant}},
    <br/>
    Please organise the travel and security clearance (if needed) for the following trip:
    <br/>
    {{url}}
    <br/>
    Thanks,
    <br/>
    {{owner_name}}
    """
}
