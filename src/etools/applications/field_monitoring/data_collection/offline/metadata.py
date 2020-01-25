class Metadata:
    def __init__(self, offline_enabled=True, allow_multiple_responses=True):
        self.options = {}
        self.validations = {}
        self.offline_enabled = offline_enabled
        self.allow_multiple_responses = allow_multiple_responses  # todo: how to validate them?

    def to_dict(self):
        return {
            'options': self.options,
            'validations': self.validations,
            'offline_enabled': self.offline_enabled,
            'allow_multiple_responses': self.allow_multiple_responses,
        }
