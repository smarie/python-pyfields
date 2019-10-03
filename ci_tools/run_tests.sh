#!/usr/bin/env bash

cleanup() {
    rv=$?
    # on exit code 1 this is normal (some tests failed), do not stop the build
    if [ "$rv" = "1" ]; then
        exit 0
    else
        exit $rv
    fi
}

trap "cleanup" INT TERM EXIT

if [ "${TRAVIS_PYTHON_VERSION}" = "3.5" ]; then
   # full
   # Run tests with "python -m pytest" to use the correct version of pytest
   echo -e "\n\n****** Running tests ******\n\n"
   coverage run --source pyfields -m pytest --junitxml=reports/junit/junit.xml --html=reports/junit/report.html -s -v pyfields/  # and not pyfields/tests/: we want DocTest too
   # buggy
   # python -m pytest --junitxml=reports/junit/junit.xml --html=reports/junit/report.html --cov-report term-missing --cov=./pyfields -v pyfields/tests/
else
   # faster - skip coverage and html report but keep junit (because used in validity threshold)
    echo -e "\n\n****** Running tests******\n\n"
    python -m pytest --junitxml=reports/junit/junit.xml -s -v pyfields/  # and not pyfields/tests/: we want DocTest too
fi
