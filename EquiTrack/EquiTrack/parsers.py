
def int_or_str(c):
    try:
        return int(c)
    except ValueError:
        return c


def list_or_dict(a):
    return '[]' if isinstance(a, int) else '{}'


def l_o_k(myd):
    r = []
    myl = list(myd.keys())
    myl.sort()
    for k in myl:
        split_c = k.replace('[', ' ').replace(']', '').split(' ')
        split_c = map(int_or_str, split_c)
        r.append(split_c)

    return r


def form_path_from_list(p_l, list=False, end=False):
    r = ''
    p_l = [x for x in p_l if x != u'_obj']
    for i in range(0, len(p_l)):
        k = p_l[i]
        if isinstance(k, int):
            if list and i == len(p_l) - 1:
                r += '.append({})'
            else:
                r += '[' + str(k) + ']'
        else:
            r += '["' + str(k) + '"]'
    return r


def set_current_path_in_dict(r, path, next_value, end=False):
    # the last element in the path will need attention
    l_e = path[-1]

    if isinstance(l_e, int):
        # we have to append to previous path
        pth = form_path_from_list(path, list=True)
        exec_str = 'r' + pth
        exec exec_str in globals(), locals()
    else:
        pth = form_path_from_list(path)
        exec_str = 'r' + pth + ' = ' + next_value
        exec exec_str in globals(), locals()
    return r


def path_in_dict_exists(r, pth):

    try:
        exec_str = 'r' + pth
        exec exec_str in globals(), locals()
    except Exception as e:
        return False
    return True


def form_myd_path(path):
    mys = ''
    for i in range(0, len(path)):
        if i == 0:
            mys += str(path[i])
        else:
            mys += '[' + str(path[i]) + ']'
    return mys


def parse_multipart_data(myd):
    r = {}
    lok = l_o_k(myd)

    def set_in_path(r, path, next_value, original_list):
        # 'strip the _obj elements before set'
        pth = form_path_from_list(path)

        if path_in_dict_exists(r, pth):
            # move to the next bit
            pass
        else:
            r = set_current_path_in_dict(r, path, list_or_dict(next_value))

        return r

    for k in lok:
        i = 0
        parcurs = []
        if i >= len(k) - 1:
            r[k[i]] = myd[k[i]]
        while i < len(k) - 1:
            parcurs.append(k[i])
            e = k[i]
            r = set_in_path(r, parcurs, k[i + 1], k)
            if i == len(k) - 2:
                if not isinstance(k[i + 1], int):
                    parcurs.append(k[i + 1])
                    pth = form_path_from_list(parcurs)
                    exec_str = 'r' + pth + ' = ' + 'myd[form_myd_path(parcurs)]'
                    exec exec_str in globals(), locals()
                else:
                    pth = form_path_from_list(parcurs)
                    parcurs.append(k[i + 1])
                    exec_str = 'r' + pth + '.append(myd[form_myd_path(parcurs)])'
                    exec exec_str in globals(), locals()
            i += 1

    return r
