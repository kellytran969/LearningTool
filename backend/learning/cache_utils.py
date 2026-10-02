"""Small cache helpers used by the API views.

The catalog and dashboard endpoints are read-heavy, so responses are
cached in Redis (or the local-memory fallback). Invalidation happens in
learning/signals.py whenever the underlying data changes.
"""

from django.core.cache import cache


def cache_key(*parts):
    """Build a namespaced cache key from parts.

    Args:
        *parts: Key segments; converted to str and joined with ':'.

    Returns:
        The cache key string.
    """
    safe = [str(p).replace(" ", "_") for p in parts]
    return "learningtool:" + ":".join(safe)


def get_or_set(key, compute, ttl):
    """Return the cached value for key, computing and storing it if absent.

    Args:
        key: Cache key.
        compute: Zero-arg callable producing the value to cache.
        ttl: Time-to-live in seconds.

    Returns:
        The cached or freshly computed value.
    """
    value = cache.get(key)
    if value is None:
        value = compute()
        cache.set(key, value, ttl)
    return value


def safe_delete_pattern(pattern):
    """Delete every cache key matching pattern.

    Uses delete_pattern when the backend supports it (django-redis);
    otherwise falls back to clearing the whole cache. Only used on
    catalog writes, which are rare compared to reads.

    Args:
        pattern: Glob pattern like 'learningtool:courses:*'.
    """
    if hasattr(cache, "delete_pattern"):
        cache.delete_pattern(pattern)
    else:
        cache.clear()


def delete_key(key):
    """Delete a single cache key.

    Args:
        key: The cache key to delete.
    """
    cache.delete(key)
