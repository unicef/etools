ABOUT eTools
============

eTools is a platform to strengthen efficiency and results in UNICEF’s core work processes – work planning, partnership management, implementation monitoring – in development and humanitarian contexts.

The eTools platform has a modular suite of applications that enables the disaggregation of programme processes while still enabling data to be shared across modules.

eTools will enable UNICEF to:

*   Reduce staff time spent on administrative processes and increase staff time spent on achieving results
*   Modernize work processes under a single platform
*   Establish quality control on planning, agreements, and reporting
*   Link data between results monitoring, implementation monitoring and partnership management
*   Improve national civil society mapping and partnerships opportunities
*   Provide transparency in partner selection

EQUITRACK & eTOOLS
------------------

The predecessor to eTools was a system developed in the Lebanon Country Office (LCO)
called Equitrack. The success of Equitrack’s use in LCO drew other country programmes in MENA to also begin using it. With over 20 locally developed systems being used in country offices, FRG and EMOPS convened various stakeholders from the organization to design a universal platform for managing results for children. Equitrack was determined to be the system closest to addressing the common needs of this group. eTools manifested from the foundational elements of Equitrack, and has ever since been introduced with new features.

Today, the eTools team has made three notable restructuring in the way it functions moving forward: Core Project Team has 3 defined work streams for managing the platform from scoping to development to support. External software firms will begin to take on software development activities while the eTools Engineering is concentrating on technical project management and developer operations.

AGILE METHODOLOGY
-----------------

The development of eTools takes on a methodology known as Agile. This methodology takes into account shot, iterative software development cycles that incorporates user feedback.
Development strategy is similar to git flow approach.
New feature and bugfix are merged into development when PR have been approved and CI passes.
Once development is completed, changes are moved to staging for QA testing.
Adjustments and fixes should go direct to staging while new features should go in development.
Once QA is completed staging branch is merged to master.

MODULES
-------

eTools development follows a phased and modular approach to software development, with releases based on an agreed set of prioritized modules and features – new modules and features are released on a monthly basis.

These are modules currently in production for the eTools:
*   Partnership Management Portal (PMP)
*   Dashboard (DASH)
*   Trip Management (T2F)
*   Financial Assurance Module (FAM)
*   Third Party Monitoring (TPM)
*   Action Point Dashboard (APD)


DEVELOPMENT ROADMAP
-------------------

Along with introducing new features, eTools releases will also include refinements to existing features based on feedback received from users and business owners.

Links
-----

+--------------------+----------------+--------------+--------------------+
| Stable             |                | |master-cov| |                    |
+--------------------+----------------+--------------+--------------------+
| Development        |                | |dev-cov|    |                    |
+--------------------+----------------+--------------+--------------------+
| Source Code        |https://github.com/unicef/etools                    |
+--------------------+----------------+-----------------------------------+
| Issue tracker      |https://app.clubhouse.io/unicefetools/stories       |
+--------------------+----------------+-----------------------------------+


.. |master-cov| image:: https://circleci.com/gh/unicef/etools/tree/master.svg?style=svg
                    :target: https://circleci.com/gh/unicef/etools/tree/master


.. |dev-cov| image:: https://circleci.com/gh/unicef/etools/tree/develop.svg?style=svg
                    :target: https://circleci.com/gh/unicef/etools/tree/develop



Testing
-------------------

+---------------------------------+--------------------------------------------------------+
| tox                             | runs flake and checks there are not missing migrations |
+---------------------------------+--------------------------------------------------------+
| tox -r                          | in case you want to reuse the virtualenv               |
+---------------------------------+--------------------------------------------------------+
| python manage.py test <package> | run test related to a specific package                 |
+---------------------------------+--------------------------------------------------------+


Environments
--------------------
+----------------+---------------------------+-------------------------------------------------+
| Development    | etools-dev.unicef.org     | - Development environment for developers        |
|                |                           | - Potentially instable                          |
+----------------+---------------------------+-------------------------------------------------+
| Staging        | etools-staging.unicef.org | - Staging environment for QA testing            |
|                |                           | - Release candidate                             |
+----------------+---------------------------+-------------------------------------------------+
| Demo           | etools-demo.unicef.org    | - Demo environment                              |
|                |                           | - Same version of production                    |
|                |                           | - Used for demo, workshops and troubleshooting  |
+----------------+---------------------------+-------------------------------------------------+
| Test           | etools-test.unicef.org    | - Coming soon                                   |
+----------------+---------------------------+-------------------------------------------------+
| Production     | etools.unicef.org         | - Production environment                        |
+----------------+---------------------------+-------------------------------------------------+


Troubleshoot
--------------------
*  Exception are logged in Sentry: https://sentry.io/unicef-jk/
*  Each container in Rancher allows to access local logs
