from unicef_notification.utils import strip_text

name = 'travel/trip/approved'
defaults = {
    'description': 'Email sent to traveller when Travel itinerary approved.',
    'subject': 'Travel Trip ({{ trip.reference_number }} Approved',

    'content': strip_text("""
    Dear {{ traveller }},

    The following trip has been approved: {{trip.number}}

    Description: {{ trip.description }}
    Start Date: {{ trip.start_date }}
    End Date: {{ trip.end_date }}

    Please click this link to review the Travel Trip: {{ url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ traveller }},<br/><br/>

    The following trip has been approved: {{trip.number}}<br/><br/>

    Description: {{ trip.description }}
    Start Date: {{ trip.start_date }}
    End Date: {{ trip.end_date }}

    Please click <a href="{{ url }}">this link</a> to review the Travel Trip.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
