__author__ = 'Tarek'


import os
import json
import time
import requests
import datetime

from django.conf import settings
from pymongo import MongoClient
from django.template.defaultfilters import slugify

from requests.auth import HTTPBasicAuth
from django.core.management.base import BaseCommand


class Command(BaseCommand):

    can_import_settings = True


    def handle(self, **options):

        print "test"





