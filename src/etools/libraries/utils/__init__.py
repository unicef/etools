# -*- coding: utf-8 -*-
from inspect import isclass


def fqn(o):
    """Returns the fully qualified class name of an object or a class

    :param o: object or class
    :return: class name
    """
    parts = []
    if isinstance(o, str):
        return o
    if not hasattr(o, '__module__'):
        raise ValueError('Invalid argument `%s`. Class or object expected' % o)
    parts.append(o.__module__)
    if isclass(o):
        parts.append(o.__name__)
    else:
        parts.append(o.__class__.__name__)
    return ".".join(parts)
