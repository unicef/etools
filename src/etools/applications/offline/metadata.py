class Metadata:
    def __init__(self, offline_enabled=True, allow_multiple_responses=True):
        self.options = {}  # Todo: make them structured
        self.validations = {}
        self.offline_enabled = offline_enabled
        self.allow_multiple_responses = allow_multiple_responses  # todo: how to validate them?

    def to_dict(self):
        return {
            'options': {name: opt.to_dict() for name, opt in self.options.items()},
            'validations': {k: v.to_dict() for k, v in self.validations.items()},
            'offline_enabled': self.offline_enabled,
            'allow_multiple_responses': self.allow_multiple_responses,
        }
