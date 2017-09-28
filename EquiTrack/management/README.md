# Management App

This app is currently meant to be used to flag potential issues (either bad data or policy violations).

## Classes involved

The main two important categories of things are *Issue Checks* (subclasses of `BaseIssueCheck`) and
*Flagged Issues* instances of `FlaggedIssue`.
**Both of these names might change soon.**

Issue checks represent *types* of issues that can be raised. Examples of issue checks might include
"an Agreement did not have a signed PCA attached to it" or "an Intervention failed validation".
**Issue checks live in code.**

Flagged issues represent *instances* of an issue.
For example, "*This particular Agreement* did not have a signed PCA attached to it" or
"*this particular Intervention* failed validation".
Flagged issues are associated with an Issue Check by ID, and also point at an associated object in the database.

## High level function

There are two high-level functions - provided both as management commands and celery tasks.

### Check issues

`./manage.py check_issues`

This will run all Issue Checks against the entire database and create (or update) any relevant `FlaggedIssue` objects.
In the future this could be updated to only test since the last check.

### Recheck issues

`./manage.py recheck_issues`

This will re-run all checks against the current set of existing `FlaggedIssue` objects.
If the issue has been addressed the `FlaggedIssue`'s status will be set to "resolved".
Else it will stay active.

## Adding a new check

Adding a new check is a two step process:

1. Create a new subclass of `BaseIssueCheck` and implement the appropriate methods
2. Add the class to the list of `ISSUE_CHECKS` in settings/base.py

### Required methods

The jobs a check has are to:

1. Generate a set of potentially relevant objects that should be checked.
   This is used in the code that runs all checks (`./manage.py check_issues`).
2. Check an individual object.
   This is used both in the code that runs all checks (`./manage.py check_issues`) and the code that rechecks
   individual issues (`./manage.py recheck_issues`).

#### Getting relevant objects

Generally the issue check should return the smallest possible set of potential objects to check.
The `BaseIssueCheck` class provides two ways of implementing this: either by overriding `get_queryset`
or by overriding `get_objects_to_check`.

`get_queryset` should be overridden if the relevant set of objects can be easily represented in a single queryset,
and no additional metadata is required for the check (see below).

`get_objects_to_check` should be overridden if the relevant set of objects to check is too complex to represent
in a single queryset, or if additional metadata is needed (see below).

#### Checking an individual object

All issue checks must implement `run_check`, which takes an object, (optional) metadata, and should either
do nothing (if the check is successful) or raise an `IssueFoundException` if there is something wrong.

As mentioned above, this method is called during checking all issues as well as during rechecks.

#### Metadata

In some instances, the object itself is not enough information to run the check.
For example, when validating an `Intervention`'s lower result data matches the correct `CountryProgramme`
you need to know which `CountryProgramme` you are looking at.
In this scenario you should to include a dictionary of metadata with the check.

The metadata needs to be provided in two places:

1. In the `get_objects_to_check` function - so it can be passed during normal checks.
2. By overriding `get_object_metadata` in the issue check - so the metadata can be reconstructed from
   the `FlaggedIssue` object during rechecks.

See `PdOutputsWrongCheck` for an example of check metadata in use.
