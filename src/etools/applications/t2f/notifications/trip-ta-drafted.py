name = 'trips/trip/TA_drafted'
defaults = {
    'description': 'This email is sent to the relevant colleague to approve the TA for the staff in concern'
    ' after the TA has been drafted in VISION.',
    'subject': 'eTools {{environment}} - Travel Authorization drafted for {{owner_name}}',
    'content': """
    Dear {{vision_approver}},"

    Kindly approve my Travel Authorization ({{ta_ref}}) in VISION based on the approved trip:

    {{url}}"

    Thanks,
    {{owner_name}}
    """,
    'html_content': """
    Dear {{vision_approver}},"
    <br/>
    Kindly approve my Travel Authorization ({{ta_ref}}) in VISION based on the approved trip:
    <br/>
    {{url}}"
    <br/>
    Thanks,
    <br/>
    {{owner_name}}
    """
}
