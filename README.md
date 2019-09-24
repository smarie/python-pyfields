# python-pyfields

*Define fields in python classes. Easily.*

[![Python versions](https://img.shields.io/pypi/pyversions/pyfields.svg)](https://pypi.python.org/pypi/pyfields/) [![Build Status](https://travis-ci.org/smarie/python-pyfields.svg?branch=master)](https://travis-ci.org/smarie/python-pyfields) [![Tests Status](https://smarie.github.io/python-pyfields/junit/junit-badge.svg?dummy=8484744)](https://smarie.github.io/python-pyfields/junit/report.html) [![codecov](https://codecov.io/gh/smarie/python-pyfields/branch/master/graph/badge.svg)](https://codecov.io/gh/smarie/python-pyfields)

[![Documentation](https://img.shields.io/badge/doc-latest-blue.svg)](https://smarie.github.io/python-pyfields/) [![PyPI](https://img.shields.io/pypi/v/pyfields.svg)](https://pypi.python.org/pypi/pyfields/) [![Downloads](https://pepy.tech/badge/pyfields)](https://pepy.tech/project/pyfields) [![Downloads per week](https://pepy.tech/badge/pyfields/week)](https://pepy.tech/project/pyfields) [![GitHub stars](https://img.shields.io/github/stars/smarie/python-pyfields.svg)](https://github.com/smarie/python-pyfields/stargazers)

**This is the readme for developers.** The documentation for users is available here: [https://smarie.github.io/python-pyfields/](https://smarie.github.io/python-pyfields/)

## Want to contribute ?

Contributions are welcome ! Simply fork this project on github, commit your contributions, and create pull requests.

Here is a non-exhaustive list of interesting open topics: [https://github.com/smarie/python-pyfields/issues](https://github.com/smarie/python-pyfields/issues)

## Requirements for builds

Install requirements for setup beforehand using 

```bash
pip install -r ci_tools/requirements-pip.txt
```

## Running the tests

This project uses `pytest`.

```bash
pytest -v pyfields/tests/
```


## Packaging

This project uses `setuptools_scm` to synchronise the version number. Therefore the following command should be used for development snapshots as well as official releases: 

```bash
python setup.py egg_info bdist_wheel rotate -m.whl -k3
```

## Generating the documentation page

This project uses `mkdocs` to generate its documentation page. Therefore building a local copy of the doc page may be done using:

```bash
mkdocs build -f docs/mkdocs.yml
```

## Generating the test reports

The following commands generate the html test report and the associated badge. 

```bash
pytest --junitxml=junit.xml -v pyfields/tests/
ant -f ci_tools/generate-junit-html.xml
python ci_tools/generate-junit-badge.py
```

### PyPI Releasing memo

This project is now automatically deployed to PyPI when a tag is created. Anyway, for manual deployment we can use:

```bash
twine upload dist/* -r pypitest
twine upload dist/*
```
