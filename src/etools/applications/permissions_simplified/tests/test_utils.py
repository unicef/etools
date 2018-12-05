from django.db import connection

from etools.applications.permissions_simplified.tests.models import SimplifiedTestChild, SimplifiedTestParent, SimplifiedTestModelWithFSMField


class TestModelsTestCaseMixin(object):
    @classmethod
    def setUpTestData(cls):
        # We disable synchronisation of test models. So we need to create it manually.
        with connection.schema_editor() as editor:
            editor.create_model(SimplifiedTestParent)
            editor.create_model(SimplifiedTestChild)
            editor.create_model(SimplifiedTestModelWithFSMField)

        super().setUpTestData()
