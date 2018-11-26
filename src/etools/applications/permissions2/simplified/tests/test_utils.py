from django.db import connection

from etools.applications.permissions2.simplified.tests.models import Child, Parent


class TestModelsTestCaseMixin(object):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(Parent)
            editor.create_model(Child)

        super().setUpTestData()
