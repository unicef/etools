#!/bin/bash -e

source ./test/test_helper.sh
source ./support/wercker-functions.sh

describe "is_valid_venv_path"

it_returns_falsy_if_path_exists() {
    WERCKER_VIRTUALENV_VIRTUALENV_PATH='/tmp'
    result=$(set +e ; is_valid_venv_path ; echo $?)
    test 1 -eq $result
}

it_returns_truthy_if_path_exists() {
    WERCKER_VIRTUALENV_VIRTUALENV_PATH='/tmp/venv_which_doesnt_exist_yet'
    # WERCKER_VIRTUALENV_VIRTUALENV_PATH= $WERCKER_VIRTUALENV_VIRTUALENV_PATH + '/venv'
    result=$(set +e ; is_valid_venv_path ; echo $?)
    test 0 -eq $result
}