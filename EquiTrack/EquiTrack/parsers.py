def int_or_str(c):
    """Return parameter as type interger, if possible
    otherwise as type string
    """
    try:
        return int(c)
    except ValueError:
        return c


def list_or_dict(a):
    """If value provided is an integer then return a list
    otherwise return a dictionary
    """
    return '[]' if isinstance(a, int) else '{}'


def create_lists_from_keys(myd):
    """Convert string list into a list

    eg: '[1 2 3]' => ['', 1, 2, 3]

    Leave leading space in list
    """
    r = []
    myl = list(myd.keys())
    myl.sort()
    for k in myl:
        split_c = k.replace('[', ' ').replace(']', '').split(' ')
        split_c = map(int_or_str, split_c)
        r.append(split_c)

    return r


def form_path_from_list(p_l, list=False, end=False):
    """Form key from list provided

    If last element and is type int, then append dictionary
    """
    r = ''
    p_l = [x for x in p_l if x != u'_obj']
    for i in range(0, len(p_l)):
        k = p_l[i]
        if isinstance(k, int):
            if list and i == len(p_l)-1:
                r += '.append({})'
            else:
                r += '[' + str(k) + ']'
        else:
            r += '["' + str(k) + '"]'
    return r


def set_current_path_in_dict(r, path, next_value, end=False):
    """Set path in dictionary

    If last element is type integer then append dictionory
    otherwise set the element to provided next value
    """
    # the last element in the path will need attention
    last_element = path[-1]

    if isinstance(last_element, int):
        # we have to append to previous path
        pth = form_path_from_list(path, list=True)
        exec_str = 'r' + pth
    else:
        pth = form_path_from_list(path)
        exec_str = 'r' + pth + ' = ' + next_value

    exec exec_str in globals(), locals()
    return r


def path_in_dict_exists(r, pth):
    """Check if path exists in dictionary"""
    try:
        exec_str = 'r' + pth
        exec exec_str in globals(), locals()
    except Exception as e:
        return False
    return True


def form_data_path(path):
    """Create a key from list provided

    eg: ['one', 'two'] => '[one][two]'
    """
    mys = ''
    for i in range(0, len(path)):
        if i == 0:
            mys += str(path[i])
        else:
            mys += '[' + str(path[i]) + ']'
    return mys


def set_in_path(r, path, next_value):
    # 'strip the _obj elements before set'
    pth = form_path_from_list(path)

    if not path_in_dict_exists(r, pth):
        r = set_current_path_in_dict(r, path, list_or_dict(next_value))

    return r


def parse_multipart_data(data):
    r = {}
    list_of_keys = create_lists_from_keys(data)

    for k in list_of_keys:
        i = 0
        parcurs = []
        if i >= len(k)-1:
            r[k[i]] = data[k[i]]
        while i < len(k)-1:
            parcurs.append(k[i])
            e = k[i]
            r = set_in_path(r, parcurs, k[i+1])
            if i == len(k) - 2:
                if not isinstance(k[i+1], int):
                    parcurs.append(k[i + 1])
                    pth = form_path_from_list(parcurs)
                    exec_str = 'r' + pth + ' = ' + 'data[form_data_path(parcurs)]'
                else:
                    pth = form_path_from_list(parcurs)
                    parcurs.append(k[i + 1])
                    exec_str = 'r' + pth + '.append(data[form_data_path(parcurs)])'

                exec exec_str in globals(), locals()
            i += 1

    return r
