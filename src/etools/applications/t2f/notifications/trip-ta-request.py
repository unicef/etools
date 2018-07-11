name = 'trips/trip/TA_request'
defaults = {
    'description': 'This email is sent to the relevant programme assistant to create the TA for the staff'
    ' in concern after the approval of the supervisor.',
    'subject': 'eTools {{environment}} - Travel Authorization request for {{owner_name}}',
    'content': """
    Dear {{pa_assistant}},

    Kindly draft my Travel Authorization in Vision based on the approved trip:

    {{url}}

    Thanks,
    {{owner_name}}
    """,
    'html_content': """
    Dear {{pa_assistant}},
    <br/>
    Kindly draft my Travel Authorization in Vision based on the approved trip:
    <br/>
    {{url}}
    <br/>
    Thanks,
    <br/>
    {{owner_name}}
    """
}
