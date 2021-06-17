from unicef_notification.utils import strip_text

name = 'travel/trip/rejected'
defaults = {
    'description': 'Email sent to traveller when Travel itinerary rejected.',
    'subject': 'Travel Trip ({{ itinerary.reference_number }}) Rejected',

    'content': strip_text("""
    Dear {{ itinerary.traveller }},

    Please refer below for additional information.

    Description: {{ itinerary.description }}
    Start Date: {{ itinerary.start_date }}
    End Date: {{ itinerary.end_date }}

    Please click this link to review the itinerary: {{ url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ itinerary.traveller }},<br/><br/>

    Please refer below for additional information.<br/><br/>

    Description: {{ itinerary.description }}
    Start Date: {{ itinerary.start_date }}
    End Date: {{ itinerary.end_date }}

    Please click <a href="{{ url }}">this link</a> to review the itinerary.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
