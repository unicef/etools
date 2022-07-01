from model_utils import Choices


def choices_to_json_ready(choices, sort_choices=True):
    if isinstance(choices, dict):
        choice_list = [(k, v) for k, v in choices.items()]
    elif isinstance(choices, Choices):
        choice_list = [(k, v) for k, v in choices]
    elif isinstance(choices, list):
        choice_list = []
        for c in choices:
            if isinstance(c, tuple):
                choice_list.append((c[0], c[1]))
            else:
                choice_list.append((c, c))
    else:
        choice_list = choices

    if sort_choices:
        choice_list = sorted(choice_list, key=lambda tup: tup[1])
    return [{'label': choice[1], 'value': choice[0]} for choice in choice_list]
