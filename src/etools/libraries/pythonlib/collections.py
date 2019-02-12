def to_choices_list(value):
    if isinstance(value, dict):
        return value.items()

    return value


class Vividict(dict):
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class HashableDict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))
