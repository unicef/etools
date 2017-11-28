def int_or_str(c):
    """Return parameter as type integer, if possible
    otherwise as type string
    """
    try:
        return int(c)
    except ValueError:
        return c


def create_lists_from_keys(data):
    """Convert string list into a list

    eg: '[1 2 3]' => ['', 1, 2, 3]

    Leave leading space in list
    """
    r = []
    keys = data.keys()
    keys.sort()
    for k in keys:
        split_c = k.replace('[', ' ').replace(']', '').split(' ')
        split_c = map(int_or_str, split_c)
        r.append(split_c)

    return r


def create_key(path):
    """Create a key from list provided

    eg: ['one', 'two'] => '[one][two]'
    """
    result = ''
    for i in range(0, len(path)):
        if i == 0:
            result += str(path[i])
        else:
            result += '[' + str(path[i]) + ']'
    return result


def build_dict(data, keys, val):
    """Use recursion to drill down through the keys

    Building up the data variable based on the keys
    Assign the val parameter to the last element in keys

    If element in keys is an integer then we create a list
    otherwise we use a dictionary type
    """
    if len(keys) > 1 and not isinstance(keys[0], int):
        init_type = [] if isinstance(keys[1], int) else {}
        data[keys[0]] = data.get(keys[0], init_type)

    res = build_dict(data[keys[0]], keys[1:], val) if len(keys) > 1 else val
    if isinstance(data, list):
        if res not in data:
            data.append(res)
    else:
        data[keys[0]] = res
    return data


def parse_multipart_data(data):
    r = {}
    list_of_keys = create_lists_from_keys(data)

    for k in list_of_keys:
        if len(k) == 1:
            r[k[0]] = data[k[0]]
        else:
            val = data[create_key(k)]
            keys = [x for x in k if x != "_obj"]
            r = build_dict(r, keys, val)
    return r
