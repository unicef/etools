from datetime import datetime


def get_current_year():
    return datetime.today().year


def get_quarter(retrieve_date=None):
    if not retrieve_date:
        retrieve_date = datetime.today()
    quarter = (retrieve_date.month - 1) // 3 + 1
    return 'q{}'.format(quarter)
