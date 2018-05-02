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
      'sample[1][_obj][k]': 'val1',
      'sample[2][_obj][k]': 'val2'
    } => [
      ['sample', 1, '_obj', 'k'],
      ['sample', 2, '_obj', 'k']
    ]
    """
    list_of_keys_in_list_format = []
    keys = list(data.keys())
    keys.sort(key=_natural_keys)
    for k in keys:
        key_in_list_format = k.replace('[', ' ').replace(']', '').split(' ')
        key_in_list_format = [_int_or_str(key) for key in key_in_list_format]
        list_of_keys_in_list_format.append(key_in_list_format)
    return list_of_keys_in_list_format


def _create_key(key_in_list_format):
    """Create a key from the list provided

    First element is variable name

    eg: ['sample', 'one', 'two'] => 'sample[one][two]'
    """
    if not key_in_list_format:
        return ""
    keys = ''.join([u'[{}]'.format(item) for item in key_in_list_format[1:]])
    return key_in_list_format[0] + keys


def _init_data(data, key, init_data):
    """Initialize the data at specified key, if needed"""
    if isinstance(key, int):
        try:
            data[key]
        except IndexError:
            data.append(init_data)
    else:
        data[key] = data.get(key, init_data)
    return data


def build_parsed_data(data, key_in_list_format, val):
    """Use recursion to drill down through the keys (in list format)

    Each element in the key list, should become a key in the parsed data,
    and assign the value to the last key.
    Unless the element is an integer, in which case we create a list
    and append the value to the list
    """
    first_key = key_in_list_format[0]
    if len(key_in_list_format) > 1:
        init_data = [] if isinstance(key_in_list_format[1], int) else {}
        data = _init_data(data, first_key, init_data)
        val = build_parsed_data(data[first_key], key_in_list_format[1:], val)

    if isinstance(data, list):
        if val not in data:
            data.append(val)
    else:
        data[first_key] = val

    return data


def parse_multipart_data(data):
    """Convert data in a relatively 'flat' structure into an 'expanded'
    structure

    eg: data arrives in a format similar to {
      'sample[d][obj][str]': 'val2'
    }
    and we return {'sample': {'d': {'str': 'val2'}}}
    something we can easily work with
    """
    parsed_data = {}
    for key_in_list_format in _create_lists_from_dict_keys(data):
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
    return parsed_data
