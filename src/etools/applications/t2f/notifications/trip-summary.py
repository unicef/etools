name = 'trips/trip/summary'
defaults = {
    'description': 'A summary of trips sent to the owner',
    'subject': 'eTools {{environment}} - Trip Summary',
    'html_content': """
    The following is a trip summary for this week:
    <br/>
    <br/>
    <b>Trips Coming up:</b>
    <ul>
    {% for key, value in trips_coming_text.items %}
    <li><a href='{{ value.0. }}'>{{key}}</a> - started on {{ value.1 }}</li>
    {% endfor %}
    </ul>

    <b>Overdue Trips:</b>
    <ul>
    {% for key, value in trips_overdue_text.items %}
    <li><a href='{{ value.0 }}'>{{key}}</a> - ended on {{ value.1 }} </li>
    {% endfor %}
    </ul>

    Thank you.
    """
}
