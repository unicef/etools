import functools
import hashlib

from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

from rest_framework import status


def generate_hash(hashable, max_length=8):
    hash_object = hashlib.md5(hashable.encode())
    # Get the hexadecimal representation of the hash
    full_hash = hash_object.hexdigest()
    if max_length:
        return full_hash[:max_length]
    return full_hash


def lock_request(view_func):
    @functools.wraps(view_func)
    def wrapper(self, request, *args, **kwargs):
        pk = kwargs.get('pk')
        schema_name = connection.tenant.schema_name
        # Dynamically get class name and method name
        class_name = self.__class__.__name__
        method_name = view_func.__name__

        lock_id = f"{schema_name}:{class_name}:{method_name}:{pk}"

        # Try to acquire the lock
        if not cache.add(lock_id, "true", timeout=600):  # Lock expires after 600 seconds
            return JsonResponse({'error': 'This resource is currently being processed.'},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)

        try:
            response = view_func(self, request, *args, **kwargs)
        finally:
            # Always release the lock after processing
            cache.delete(lock_id)

        return response

    return wrapper
