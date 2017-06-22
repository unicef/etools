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


Python 3 Prep
-------------

To make your code easier to port to Python 3, add the following to the top of
all new files::

	from __future__ import division
	from __future__ import absolute_import
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
