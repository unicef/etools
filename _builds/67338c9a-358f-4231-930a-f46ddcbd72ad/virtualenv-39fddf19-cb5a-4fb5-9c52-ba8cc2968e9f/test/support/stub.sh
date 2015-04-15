# https://gist.github.com/jimeh/5886795
# Stub commands printing it's name and arguments to STDOUT or STDERR.
stub() {
  local cmd="$1"
  if [ "$2" == "STDERR" ]; then
    local redirect=" 1>&2";
  fi

  if [[ "$(type "$cmd" | head -1)" == *"is a function" ]]; then
    local source="$(type "$cmd" | tail -n +2)"
    source="${source/$cmd/original_${cmd}}"
    eval "$source"
  fi
  eval "$(echo -e "${1}() {\n  echo \"$1 stub: \$@\"$redirect\n}")"
}

# Restore the original command/function that was stubbed with stub.
restore() {
  local cmd="$1"
  unset -f "$cmd"
  if type "original_${cmd}" &>/dev/null; then
    if [[ "$(type "original_${cmd}" | head -1)" == *"is a function" ]]; then
      local source="$(type "original_$cmd" | tail -n +2)"
      source="${source/original_${cmd}/$cmd}"
      eval "$source"
      unset -f "original_${cmd}"
    fi
  fi
}