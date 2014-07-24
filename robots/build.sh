#!/bin/bash

# Builds a project
VIRTUALENV=.venv

if [ -e "$VIRTUALENV" ]
then
    echo "Re-using existing virtualenv"
    . $VIRTUALENV/bin/activate
else
    virtualenv --no-site-packages $VIRTUALENV || { echo "Virtualenv failed"; exit -1; }
    . $VIRTUALENV/bin/activate
    easy_install -U setuptools
    easy_install pip
    rm -f md5.requirements.last
fi

md5sum requirements.txt > md5.requirements.new

diff md5.requirements.new md5.requirements.last
REQUIREMENTS_DIFF=$?

if [ "$REQUIREMENTS_DIFF" -ne 0 ]
then
    pip install --timeout 300 -r requirements.txt || { echo "pip failed (requirements)"; exit -1; }
    mv md5.requirements.new md5.requirements.last
fi

find . -name "*.pyc" -exec rm {} \;

$VIRTUALENV/bin/pybot --outputdir results .

if [ $? -eq 1 ]
then
    exit 1
fi
