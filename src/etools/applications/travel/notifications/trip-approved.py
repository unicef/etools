from unicef_notification.utils import strip_text

name = 'travel/trip/approved'
defaults = {
    'description': 'Email sent to traveller when Travel has been approved.',
    'subject': 'Travel ({{ trip.reference_number }} Approved',

    'content': strip_text("""
    Hello {{ traveller }},

    Your travel {{trip.reference_number}} has been approved by {{ supervisor }}.

    Description: {{ trip.description }}
    Start Date: {{ trip.start_date }}
    End Date: {{ trip.end_date }}

    Please click this link to review the Travel: {{ url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Hello {{ traveller }},,<br/><br/>

    Your travel {{trip.reference_number}} has been approved by {{ supervisor }}.<br/><br/>

    Description: {{ trip.description }}
    Start Date: {{ trip.start_date }}
    End Date: {{ trip.end_date }}

    Please click <a href="{{ url }}">this link</a> to review the Travel.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
