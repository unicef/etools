Feature Flags
=============

The term 'Feature Flags' refers to the ability to turn off features of the web application based on
attributes of the user accessing the web application. It is also sometimes called 'feature flipping',
'feature gating', or 'A/B testing'.

Background
----------

We use the `django-waffle <https://github.com/jsocol/django-waffle>`_ library to provide this
functionality. Please read its `documentation <https://waffle.readthedocs.io/en/stable/>`_ for more
details.


Feature Flags in eTools
-----------------------

In addition to the functionality provided by django-waffle, we add the ability to turn flags or
switches on based on the user's ``country`` value. (This is sometimes also called "Tenant" or
"Workspace").

Note: the main difference between a *switch* and a *flag* is that a switch is not dependent on a
request object. It uses the tenant value set in the DB connection, while a flag uses the tenant
value from the request. Flags are also more versatile because they can be activated by a variety of
conditions, while switches are either ON or OFF based on the tenant.

Superuser workflow
------------------

The eTools-specific changes to django-waffle are in the ``environment`` app, but the administration is
done through the Django admin in the 'waffle' app.

To create a flag, go to ``/admin/waffle/flag/add/``. There are multiple configuration options, but
the two important ones are *Name* (which is at the top of the form) and *Countries* (which is at the
bottom of the form). Every flag needs a *Name*, and that name will be returned by the API, described
below. The *Countries* field allows you to attach one or more countries to this flag. If a country is
attached to a flag, then the flag will be active for users with that country attribute.

All of the other fields in the form are directly from django-waffle and are explained in its
documentation.

As it stands now, flags do not alter ANY functionality in the eTools backend. They are only Boolean
values which are meant to be used by frontend applications to alter the behavior of the frontend
application.


API
---

The API for feature flags and switches is read-only, and is available at
``/api/v2/environment/flags/`` . An authenticated GET request to that URL will return a JSON object
with a single ``active_flags`` key whose value will be a list of the Flag names and Switch names
that are active for that request. It is up to the caller to do something useful with the result.

Example result::

    {"active_flags":["can_view_t2f","can_access_whizbang_feature"]}


Note that this single API returns all active Flags and Switches. It never returns duplicate values,
so if a flag and a switch have the same name, the caller will not be able to differentiate between
them. If you make the choice to use the same name for a Flag and for a Switch, be sure to set the
'countries' list identically, otherwise you will have confusing results.

A/B Testing
-----------

As mentioned, feature flags can be used to set up A/B testing, but there is currently no
infrastructure within eTools to evaluate the results of an A/B test set up in this way.
