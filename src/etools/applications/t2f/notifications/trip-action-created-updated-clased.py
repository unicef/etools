name = 'trips/action/created/updated/closed'
defaults = {
    'description': 'Sent when trip action points are created, updated, or closed',
    'subject': 'eTools {{environment}} - Trip action point {{state}} for trip: {{trip_reference}}',
    'content': """
    Trip action point by {{owner_name}} for {{responsible}} was {{state}}:"
    {{url}}

    Thank you.
    """,
    'html_content': """
    Trip action point by {{owner_name}} for {{responsible}} was {{state}}:"
    <br/>
    {{url}}
    <br/>
    Thank you.
    """
}
