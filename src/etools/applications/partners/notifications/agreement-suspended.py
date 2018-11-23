name = 'partners/agreement/suspended'
defaults = {
    'description': 'PCA Suspended.',
    'subject': 'eTools PCA for {{ vendor_name }} ({{ vendor_number }}) Suspension Notification',
    'content': """
    Dear Colleague,

    Please note that you have suspended the PCA for {{ vendor_name }} ({{ vendor_number }}).
    The following Programme Documents (PDs) were associated with the PCA and they will also be suspended:

        {% for section, pd_number, link in pd_list %}
            {{ section}}, {{ pd_number }}, {{ link }}
        {% endfor %}

    Please note that if you unsuspend the PCA, the PDs will not be automatically unsuspended and thus you will have to go to each of the PD records and manually unsuspend them.

    Please note that this is an automatically generated message and replies to this email address are not monitored.

    """
}
