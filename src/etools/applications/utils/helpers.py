import hashlib


def generate_hash(hashable, max_length=8):
    hash_object = hashlib.md5(hashable.encode())
    # Get the hexadecimal representation of the hash
    full_hash = hash_object.hexdigest()
    if max_length:
        return full_hash[:max_length]
    return full_hash
