import hashlib


def h11(w):
    return hashlib.md5(w).hexdigest()[:9]
