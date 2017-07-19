from EquiTrack.settings.local import *  # noqa

# This settings file is meant for a developer's local customizations.
# If these settings are generally useful to all developers, they should be moved to local.py

# To use this file:
# 1. Copy this file to custom.py
# 2. Add any settings that are custom for your workflow.
# 3. set the DJANGO_SETTINGS_MODULE env var to EquiTrack.settings.custom before running manage.py

# Example: Use a Postgres server on a nondefault port
DATABASES['default']['PORT'] = '5433'
