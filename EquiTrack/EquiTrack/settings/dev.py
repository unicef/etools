__author__ = 'jcranwellward'

from .local import *


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': 'equitrack',
        'USER': 'equitrack',
        'HOST': 'localhost',

    }
}
########## END DATABASE CONFIGURATION