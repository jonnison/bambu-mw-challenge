"""
Database connection and configuration utilities.
"""
import logging
from django.db import connection
from django.core.cache import cache

logger = logging.getLogger(__name__)


def check_database_health():
    """Check if database connection is healthy."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def check_cache_health():
    """Check if cache is healthy."""
    try:
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        return result == 'ok'
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return False


def get_database_stats():
    """Get database connection statistics."""
    try:
        from django.db import connections
        db_stats = {}
        
        for alias, conn in connections.all():
            if hasattr(conn, 'queries'):
                db_stats[alias] = {
                    'query_count': len(conn.queries),
                    'vendor': conn.vendor,
                    'is_connected': conn.connection is not None
                }
        
        return db_stats
    except Exception as e:
        logger.error(f"Failed to get database stats: {e}")
        return {}