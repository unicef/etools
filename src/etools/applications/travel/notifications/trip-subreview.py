from unicef_notification.utils import strip_text

name = 'travel/trip/subreview'
defaults = {
    'description': 'Email sent to supervisor when Travel itinerary ready for submission review.',
    'subject': 'Travel Trip ({{ trip.reference_number }}) Submission Review',

    'content': strip_text("""
    Hello {{ supervisor }},

    The following Travel has been submitted for review: {{ trip.reference_number }}.
    Please refer below for additional information.

    Description: {{ trip.description }}
    Traveller: {{ traveller }}
    Start Date: {{ trip.start_date }}
    End Date: {{ trip.end_date }}

    Please click this link to review the Travel: {{ url }}

    Thank you.
    """),

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Hello {{ supervisor }},<br/><br/>

    The following Travel has been submitted for review: {{ trip.reference_number }}.<br/>
    Please refer below for additional information.<br/><br/>

    Description: {{ trip.description }}
    Traveller: {{ traveller }}
    Start Date: {{ trip.start_date }}
    End Date: {{ trip.end_date }}

    Please click <a href="{{ url }}">this link</a> to review the Travel.<br/><br/>

    Thank you.
    {% endblock %}
    """
}
