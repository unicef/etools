import string
import uuid


def generate_username():
    base = 32
    ABC = (string.digits + string.lowercase)[:base]

    uid = uuid.uuid4().int
    digits = []
    while uid:
        digits.append(ABC[uid % base])
        uid /= base

    digits.reverse()
    uid = ''.join(digits)
    return '-'.join([uid[:6], uid[6:10], uid[10:16], uid[16:20], uid[20:]])
