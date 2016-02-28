from django.test.runner import DiscoverRunner
from django.db import connection


class TestRunner(DiscoverRunner):

    def setup_databases(self, **kwargs):
        """
        Override the setup to install some extensions
        :param kwargs:
        :return:
        """
        names, mirros = super(TestRunner, self).setup_databases(**kwargs)
        cursor = connection.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS hstore;")

        return names, mirros

