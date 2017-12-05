import re


def _int_or_str(c):
    """Return parameter as type integer, if possible
    otherwise as type string
    """
    try:
        return int(c)
    except ValueError:
        return c


def _natural_keys(text):
    return [_int_or_str(c) for c in re.split('(\d+)', text)]


def _create_lists_from_dict_keys(data):
    """Convert dictionary keys into lists
    returning a list of these keys in list format

    eg: {
      '[1 2 3]': 'val1',
      '[d _obj str]': 'val2'
    } => [
      ['', 1, 2, 3],
      ['', 'd', '_obj', 'str']
    ]

    Add leading empty string to list
    """
    list_of_keys_in_list_format = []
    keys = list(data.keys())
    keys.sort(key=_natural_keys)
    for k in keys:
        key_in_list_format = k.replace('[', ' ').replace(']', '').split(' ')
        key_in_list_format = map(_int_or_str, key_in_list_format)
        list_of_keys_in_list_format.append(key_in_list_format)
    return list_of_keys_in_list_format


def _create_key(key_in_list_format):
    """Create a key from the list provided

    Expect first element to be an empty string

    eg: ['', 'one', 'two'] => '[one][two]'
    """
    return ''.join([u'[{}]'.format(item) for item in key_in_list_format[1:]])


def build_parsed_data(data, key_in_list_format, val):
    """Use recursion to drill down through the keys (in list format)

    Each element in the key list, should become a key in the parsed data,
    and assign the value to the last key.
    Unless the element is an integer, in which case we create a list
    and append the value to the list
    """
    if len(key_in_list_format) > 1:
        first_key = key_in_list_format[0]
        if not isinstance(first_key, int):
            init_type = [] if isinstance(key_in_list_format[1], int) else {}
            data[first_key] = data.get(first_key, init_type)

        val = build_parsed_data(data[first_key], key_in_list_format[1:], val)

    if isinstance(data, list):
        if val not in data:
            data.append(val)
    else:
        data[key_in_list_format[0]] = val

    return data


def parse_multipart_data(data):
    """Convert data in a relatively 'flat' structure into an 'expanded'
    structure

    eg: data arrives in a format similar to {
      '[d _obj str]': 'val2',
      '[d][obj][str]': 'val2'
    }
    and we return {'d': {'str': 'val2'}}
    something we can easily work with
    """
    parsed_data = {}
    for key_in_list_format in _create_lists_from_dict_keys(data):
        if key_in_list_format[0] == "":
            val = data[_create_key(key_in_list_format)]
            # remove _obj from key
            # as we don't want this in the final parsed data
            key_in_list_format_scrubbed = [
                x for x in key_in_list_format if x != "_obj"
            ]
            parsed_data = build_parsed_data(
                parsed_data,
                key_in_list_format_scrubbed,
                val
            )
        else:
            parsed_data[key_in_list_format[0]] = data[key_in_list_format[0]]
    return parsed_data
