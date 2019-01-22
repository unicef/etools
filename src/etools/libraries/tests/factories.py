import factory


class InheritedTrait(factory.Trait):
    def __init__(self, *parents, **kwargs):
        overrides = {}

        for parent in parents:
            overrides.update(parent.overrides)

        overrides.update(kwargs)

        super().__init__(**overrides)
