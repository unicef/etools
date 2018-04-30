# -*- coding: utf-8 -*-
#!/usr/bin/env python
import ast
import os.path
import re
import sys
from codecs import open

from setuptools import setup, find_packages

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

def get_requirements(env):
    ret = []
    with open(f'src/requirements/{env}.txt') as fp:
        for line in fp.readlines():
            if line.startswith('#'):
                continue
            line = line[:-1]
            if line.startswith('-e git+'):
                url = line.replace('-e ', '')
                groups = re.match(".*@(?P<version>.*)#egg=(?P<name>.*)", line).groupdict()
                version = groups['version'].replace('v', '')
                egg = line.partition('egg=')[2]
                ret.append(f"{egg}=={version}")
                dependency_links.add(f"{url}-{version}")
            else:
                dep = line.partition('#')[0]
                ret.append(dep.strip())
    return ret


install_requires = get_requirements('production')
dev_requires = get_requirements('local')
test_requires = get_requirements('test')

# djangosaml2 has a wrong version. It has declared as 0.16.11.2 but internally is has 0.16.11
# this make pip fails. Until not fixed (or better any dependecy properly packaged) we cannot
# rely on setuptools/distutils dependency management
install_requires = []
dev_requires = []
test_requires = []

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
    install_requires=install_requires,
    dependency_links=list(dependency_links),
    license='BSD',
    include_package_data=True,
    extras_require={
        'dev': dev_requires,
        'test': test_requires,
    },
    classifiers=[
        'Framework :: Django',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],
)
