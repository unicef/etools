name = 'locations/import_completed'
defaults = {
    'description': 'Import locations completed',
    'subject': '[eTools] Import locations completed',

    'content': """
    Dear {{ recipient }},

    Location import for {{ table.table_name }} - {{ table.location_type.name }} has been completed.
    """,

    'html_content': """
    {% extends "email-templates/base" %}

    {% block content %}
    Dear {{ recipient }},<br/><br/>

    Location import for {{ table.display_name }} - {{ table.location_type.name }} has been completed.<br/>
    {% endblock %}
    """
}
