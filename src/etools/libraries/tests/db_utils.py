class CaptureQueries(object):
    """
        Context manager that captures queries executed by the specified connection.
        Mostly copied from django.test.utils.CaptureQueriesContext.
    """

    def __init__(self, connection=None):
        if connection is None:
            from django import db
            connection = db.connection

        self._conn = connection
        self._count_initial = 0
        self.queries = []

    def __enter__(self):
        self.force_debug_cursor = self._conn.force_debug_cursor
        self._conn.force_debug_cursor = True
        self._count_initial = len(self._conn.queries)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._conn.force_debug_cursor = self.force_debug_cursor
        if exc_type is not None:
            return
        self.queries = self._conn.queries[self._count_initial:]
