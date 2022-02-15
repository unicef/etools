from typing import Any


def get_recursive_from_dict(source: dict, path: str) -> Any:
    """
    get value recursively from dict. * will use first key available
    example: reviews.*.prc_reviews.*
    """
    if path == '':
        return source

    path_fragments = path.split('.')
    path_fragment = path_fragments[0]
    if path_fragment == '*':
        path_fragment = list(source.keys())[0]

    return get_recursive_from_dict(source[path_fragment], '.'.join(path_fragments[1:]))
