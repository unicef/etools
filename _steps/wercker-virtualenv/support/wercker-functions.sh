#!/bin/bash -e

# Returns true if python version is at version 2.x or 3.x
is_python_version() {
  if [ -f $WERCKER_VIRTUALENV_PYTHON_LOCATION ] ; then
      case "$($WERCKER_VIRTUALENV_PYTHON_LOCATION --version 2>&1)" in
          *" 3."*)
              return 0
              ;;
          *" 2."*)
              return 0
              ;;
          *)
              return 1
              ;;
      esac
  fi

  return 1
}

# Returns true if virtual env path is not a directory
is_valid_venv_path() {
  if [ -d "$WERCKER_VIRTUALENV_VIRTUALENV_PATH" ] ; then
    return 1
  fi

  return 0
}

is_virtualenv_installed() {
  if hash $VIRTUAL_ENV_COMMAND 2>/dev/null; then
    return 0
  fi

  return 1
}