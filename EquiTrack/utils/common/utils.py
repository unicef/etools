def pop_keys(d, keys):
    res, rem = dict(), dict()
    for key, value in d.items():
        if key in keys:
            res[key] = value
        else:
            rem[key] = value
    return res, rem
