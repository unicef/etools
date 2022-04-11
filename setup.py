#!/usr/bin/env python
# -*- coding: utf-8 -*-
import ast
import os.path
import re
import sys
from codecs import open

from setuptools import find_packages, setup

ROOT = os.path.realpath(os.path.dirname(__file__))
init = os.path.join(ROOT, 'src', 'etools', '__init__.py')
_version_re = re.compile(r'__version__\s+=\s+(.*)')
_name_re = re.compile(r'NAME\s+=\s+(.*)')

sys.path.insert(0, os.path.join(ROOT, 'src'))

with open(init, 'rb') as f:
    content = f.read().decode('utf-8')
    VERSION = str(ast.literal_eval(_version_re.search(content).group(1)))
    NAME = str(ast.literal_eval(_name_re.search(content).group(1)))

dependency_links = set()

setup(
    name=NAME,
    version=VERSION,
    author='UNICEF',
    author_email='etools@unicef.org',
    url='',
    description='',
    long_description=open(os.path.join(ROOT, 'README.rst')).read(),
    package_dir={'': 'src'},
    packages=find_packages('src'),
    zip_safe=False,
    dependency_links=list(dependency_links),
    license='BSD',
    include_package_data=True,
    classifiers=[
        'Framework :: Django',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
    ],
)
