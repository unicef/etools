from unicef_notification.utils import strip_text

name = 'travel/trip/submitted'
defaults = {
    'description': 'Email sent to supervisor when Travel itinerary ready for review.',
    'subject': 'Travel Trip ({{ itinerary.reference_number }}) Submitted',

    'content': strip_text("""
    Dear {{ itinerary.supervisor }},

    UNICEF is granting you access to the Travel Module in eTools.
    Please refer below for additional information.

    Description: {{ itinerary.description }}
    Traveller: {{ itinerary.traveller }}
    Start Date: {{ itinerary.start_date }}
    End Date: {{ itinerary.end_date }}

    Please click this link to review the itinerary: {{ url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ itinerary.supervisor }},<br/><br/>

    UNICEF is granting you access to the Travel Module in eTools.<br/>
    Please refer below for additional information.<br/><br/>

    Description: {{ itinerary.description }}
    Traveller: {{ itinerary.traveller }}
    Start Date: {{ itinerary.start_date }}
    End Date: {{ itinerary.end_date }}

    Please click <a href="{{ url }}">this link</a> to review the itinerary.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
