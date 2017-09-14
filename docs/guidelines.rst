Developer Guidelines
====================

This document lists guidelines that we expect developers to follow when contributing to eTools. It
is always a work-in-progress.


Code Style
----------

We follow `PEP-8 <https://www.python.org/dev/peps/pep-0008/>`_, as amended on 01-Aug-2013. Please
read it. It has a lot of useful advice that won't be repeated here. We use `flake8
<https://pypi.python.org/pypi/flake8>`_ to enforce this. Flake8 is run during continuous integration
and developers should run it locally prior to submitting a PR for review.


Flake8 exceptions
~~~~~~~~~~~~~~~~~

We allow the following flake8 "rules" to be violated:

* max-line-length: The default maximum is 80 characters, which we have increased to 120 characters.
  Allowing unlimited line lengths makes PRs difficult to review in the Github interface.


Organizing imports
~~~~~~~~~~~~~~~~~~

We organize imports into the following groups, in the following order. (This is an extension of
`PEP-8's guidance <https://www.python.org/dev/peps/pep-0008/#imports>`_).

* Imports from ``__future__``
* Imports from the Python standard library
* Anything not in the other categories goes here - possibly subdivided.
* Imports from code in the same project/repository.

Within a group, lines are alphabetized, ignoring the first word ("from" or "import").
E.g.::

    from datetime import timedelta
    import os
    from os.path import abspath
    from sys import exit

Per PEP-8, "You should put a blank line between each group of imports.".


Author annotations
~~~~~~~~~~~~~~~~~~

Some editors add author annotations to files when they are created: ``__author__ = 'vkurup'`` We
prefer that those not be added to new files, and they can be removed from existing files.


Python 3 Prep
-------------

To make your code easier to port to Python 3, add the following to the top of
all new files::

	from __future__ import absolute_import
	from __future__ import division
	from __future__ import print_function
	from __future__ import unicode_literals

You can also add them to existing files, but be aware that they may change
the behavior of your code (particularly the default use of unicode literals).


Testing
-------


Coverage
~~~~~~~~

Automated tests are essential for maintaining a quality code base. We use the `coverage
<https://coverage.readthedocs.io/>`_ tool to quantify what percentage of our code is covered by our
automated tests. Our current acceptable level is set in ``.coveragerc`` using the ``fail_under``
parameter. That level should never be dropped, and we should aim to increase it to at least 90%
across the code base. In order to do so, we follow these guidelines.

1. All new code should be covered by tests.
2. Before a new bug is fixed, a test should be written that exhibits the bug.
3. Code that is not used should be removed.

If your PR pushes our overall coverage to a level 5 points (7-8 to be safe) above the current
``fail_under`` value, then you can update the value to the new higher level.

Remember that code coverage is just one metric. It is possible to have 100% code coverage, but still
have bugs because the tests are not asserting all of the various decisions that the code is making.
An unfortunately common example is a test for a REST API endpoint that merely checks that the
response code is 200. Don’t aim for coverage, aim for quality.


Commented-out code
------------------

We prefer to avoid commenting out code. Keeping commented code lying around is often an attempt to
do homemade version control, and it's better to use git for this. There are a few cases where it is
reasonable to keep commented code in the codebase.

1. To make it easy for developers to turn on rarely used development features. For example:
   'Uncomment the next 4 lines to temporarily turn on local caching'
2. To keep code that you know will be coming back soon. In this case, there should be a clear
   comment at the top of the block indicating at what point the code will be uncommented. For
   example: 'The following is commented out until issue #42 is resolved'.

Even those cases are weak. There's often ways to implement developer switches using
environment variables for case #1, and it is not guaranteed that the person who fixes issue #42 will
remember to look for the commented-out code and uncomment it. It's usually better to remove the code
and make it clear in issue #42 what steps need to be taken before the issue is marked done.


Exception Handling
------------------

* Minimize what you ``try``
* Minimize what you catch
* Minimize what you ``except``
* Don't forget the ``else``

Code in ``try`` blocks should be limited to the code you suspect will raise an exception. Usually that's
just one line of code. Limiting the code in a ``try`` block ensures that unexpected
exceptions won't get mishandled. It also clarifies the intent of the ``try`` block to anyone reading
the code.

You should only catch the exceptions you expect will be raised. This can almost always be limited
to one or two exceptions. Catching all exceptions can be the right thing to do, but that's rare.
Catch-all handlers are misused far more often than they're used appropriately.

Code in ``except`` blocks should be limited to the minimum required to handle the exception.
Complicated ``except`` blocks run the risk of raising errors of their own.

Exception handlers have an underused ``else`` clause that executes if no exception is raised. It's
the appropriate place for the code you might be tempted to put in the ``try`` block after the
suspect code.


Django Settings
---------------

Add new Django settings to the `base.py` settings module. If a customization is needed for a
specific environment, keep the production value in `base.py` and add an override for local
development in `local.py`. This allows a developer to mimic a production environment by simply
commenting out a setting in `local.py`. It may sometimes be reasonable to do the reverse, for
example, if you want to avoid importing a package that is only needed on production. In those cases,
you should add the override only to production.py. We should try to avoid having both local
overrides and production overrides of the same setting.

Order of settings
~~~~~~~~~~~~~~~~~

Within base.py, settings should be organized in the following order: Django core settings, Django
contrib settings, Third-party app settings, and finally eTools-specific settings. You are strongly
encouraged to add detailed comments, with links, explaining the intended purpose of the setting.

Use str2bool for Boolean env vars
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Using environment variables as settings is a good practice that allows flexibility in deployment.
This is generally straightforward, unless the setting is a Boolean value. If you write: ``ENABLE_FOO
= os.environ.get(‘ENABLE_FOO’, True)``, and then set ``ENABLE_FOO=False`` in the environment, the
python variable ``ENABLE_FOO`` gets set to the string ``‘False’`` and if it is treated like a
Boolean in other parts of the code then ``bool(‘False’)`` equals ``True``, which is probably not
what you wanted. We have a helper function called ``str2bool`` that converts commonly used boolean
representations from a string to a proper Python Boolean value, which allows us to write ``ENABLE_FOO
= str2bool(os.environ.get(‘ENABLE_FOO’, True))``.
