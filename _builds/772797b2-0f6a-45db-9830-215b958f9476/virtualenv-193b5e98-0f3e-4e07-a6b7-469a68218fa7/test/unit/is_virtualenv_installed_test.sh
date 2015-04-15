#!/bin/bash -e

source ./test/test_helper.sh
source ./support/wercker-functions.sh

describe "is_virtualenv_installed"

it_returns_falsy_if_command_does_not_exist() {
    VIRTUAL_ENV_COMMAND='wrong_virtualenv'
    result=$(set +e ; is_virtualenv_installed ; echo $?)
    test 1 -eq $result
}

it_returns_truthy_if_command_exists() {
    VIRTUAL_ENV_COMMAND='virtualenv'
    result=$(set +e ; is_virtualenv_installed ; echo $?)
    test 0 -eq $result
}