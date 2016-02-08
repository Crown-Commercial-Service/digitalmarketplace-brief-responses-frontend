#!/bin/bash
#
# Run project tests
#
# NOTE: This script expects to be run from the project root with
# ./scripts/run_tests.sh

set -o pipefail

function display_result {
  RESULT=$1
  EXIT_STATUS=$2
  TEST=$3

  if [ $RESULT -ne 0 ]; then
    echo -e "\033[31m$TEST failed\033[0m"
    exit $EXIT_STATUS
  else
    echo -e "\033[32m$TEST passed\033[0m"
  fi
}

pep8 .
display_result $? 2 "Code style check"

npm run --silent frontend-build:production
display_result $? 1 "Build of front end static assets"

py.test $@
display_result $? 3 "Python Unit tests"

npm test
display_result $? 4 "JavaScript Unit tests"
