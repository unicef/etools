#!/usr/bin/env python
import codecs
import imp
import os
import sys
from distutils.config import PyPIRCCommand

from setuptools import find_packages, setup

ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__)))
init = os.path.join(ROOT, 'EquiTrack', '__init__.py')
app = imp.load_source('EquiTrack', init)
reqs = 'base.txt'


def read(*files):
    content = ''
    for f in files:
        content += codecs.open(os.path.join(ROOT, 'EquiTrack',
                                            'requirements', f), 'r').read()
    return content


PyPIRCCommand.DEFAULT_REPOSITORY = 'http://pypi.wfp.org/pypi/'


install_requires = read('base.txt', reqs),
tests_requires = read('base.txt')
dev_requires = tests_requires #+ read('local.txt')


setup(
    name=app.NAME,
    version=app.get_version(),
    url='http://pypi.wfp.org/pypi/%s/' % app.NAME,
    author='Unicef',
    author_email='frg@unicef.org',
    license="Unicef Property",
    description='eTools',
    package_dir={'': 'EquiTrack'},
    packages=find_packages(where='EquiTrack'),
    include_package_data=True,
    dependency_links=[
        'https://github.com/robertavram/djangosaml2/releases/tag/0.13.3#egg=djangosaml2-1.13.3',
        'https://github.com/robertavram/django-storages/releases/tag/1.3.1.1#egg=django-storages-redux-1.3.1.1',
        'http://pypi.wfp.org/simple/',
    ],
    install_requires=install_requires,
    extras_require={
        'dev': dev_requires,
        'test': tests_requires,
    },
    platforms=['linux'],
    keywords='sample setuptools development',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: Django',
        'Framework :: Django :: 1.9',
      ],

)
