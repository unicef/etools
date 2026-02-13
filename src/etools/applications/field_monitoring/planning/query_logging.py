"""
Context manager to log all database queries executed within a block.
Use to profile and reduce DB hits for the visit PDF endpoint.

Enabled by default when DEBUG=True. Override: FM_PDF_LOG_QUERIES=0 to disable.

Example:
    python manage.py runserver  # in DEBUG mode, logs appear automatically
    # Hit GET /api/v1/field-monitoring/planning/activities/31/pdf/
"""
import logging
import os
from contextlib import contextmanager

from django.conf import settings
from django.db import connection, reset_queries

logger = logging.getLogger(__name__)

_env = str(os.environ.get("FM_PDF_LOG_QUERIES", "")).lower()
FM_PDF_LOG_QUERIES = (_env in ("1", "true", "yes")) or (_env != "0" and getattr(settings, "DEBUG", False))


@contextmanager
def log_db_queries(label="block"):
    """
    Execute a block and log all DB queries (count, total time, and per-query SQL + time).
    Works regardless of DEBUG; controlled by FM_PDF_LOG_QUERIES env var.
    """
    if not FM_PDF_LOG_QUERIES:
        yield
        return

    try:
        saved = getattr(connection, "force_debug_cursor", None)
        connection.force_debug_cursor = True
    except Exception:
        saved = None

    reset_queries()
    try:
        yield
    finally:
        try:
            if saved is not None:
                connection.force_debug_cursor = saved
        except Exception:
            pass

        queries = getattr(connection, "queries", [])
        total_time = sum(float(q.get("time", 0)) for q in queries)
        count = len(queries)

        logger.warning(
            "[FM PDF query_log] %s: %d queries, total %.3fs",
            label,
            count,
            total_time,
        )
        for i, q in enumerate(queries, 1):
            sql = q.get("sql", "")
            time_ms = float(q.get("time", 0)) * 1000
            # Truncate long SQL for readability
            sql_preview = sql[:200] + "..." if len(sql) > 200 else sql
            logger.warning(
                "[FM PDF query_log]   #%d (%.1fms): %s",
                i,
                time_ms,
                sql_preview.replace("\n", " "),
            )
