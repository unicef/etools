import ConfigParser


def read_base_config():
    config = ConfigParser.ConfigParser()
    config.read('behave.ini')
    return config


def read_config(name):
    config = read_base_config()
    return config.get('etools', name)


def update_config(name, value):
    config = read_base_config()
    config.set('etools', name, value)

    with open('behave.ini', 'wb') as configfile:
        config.write(configfile)
