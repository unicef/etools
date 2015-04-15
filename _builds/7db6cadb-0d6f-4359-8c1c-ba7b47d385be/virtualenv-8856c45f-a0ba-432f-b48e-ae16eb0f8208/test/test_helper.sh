#!/bin/bash -e

source ./test/support/stub.sh

#Search argument 1 for substring in argument 2
search_substring() {
  if echo "$1" | grep -q "$2"; then
    echo 'found'
  else
    echo 'missing'
  fi;
}

should_succeed() {
  if [[ $? = 0 ]]; then
    return 0
  else
    return 1
  fi;
}

should_fail() {
  ! should_succeed
}