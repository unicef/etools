name = 'trips/trip/created/updated'
defaults = {
    'description': 'The email that is sent to the supervisor, budget owner, traveller for any update',
    'subject': 'eTools {{environment}} - Trip {{number}} has been {{state}} for {{owner_name}}',
    'content': """
    Dear Colleague,

    Trip {{number}} has been {{state}} for {{owner_name}} here:
    {{url}}
    Purpose of travel: {{ purpose_of_travel }}

    Thank you.
    """,
    'html_content': """
    Dear Colleague,
    <br/>
    Trip {{number}} has been {{state}} for {{owner_name}} here:
    <br/>
    {{url}}
    <br/>
    Purpose of travel: {{ purpose_of_travel }}
    <br/>
    Thank you.
    """
}
