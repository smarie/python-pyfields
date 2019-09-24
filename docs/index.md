# pyfields

*Define fields in python classes. Easily.*

[![Python versions](https://img.shields.io/pypi/pyversions/pyfields.svg)](https://pypi.python.org/pypi/pyfields/) [![Build Status](https://travis-ci.org/smarie/python-pyfields.svg?branch=master)](https://travis-ci.org/smarie/python-pyfields) [![Tests Status](https://smarie.github.io/python-pyfields/junit/junit-badge.svg?dummy=8484744)](https://smarie.github.io/python-pyfields/junit/report.html) [![codecov](https://codecov.io/gh/smarie/python-pyfields/branch/master/graph/badge.svg)](https://codecov.io/gh/smarie/python-pyfields)

[![Documentation](https://img.shields.io/badge/doc-latest-blue.svg)](https://smarie.github.io/python-pyfields/) [![PyPI](https://img.shields.io/pypi/v/pyfields.svg)](https://pypi.python.org/pypi/pyfields/) [![Downloads](https://pepy.tech/badge/pyfields)](https://pepy.tech/project/pyfields) [![Downloads per week](https://pepy.tech/badge/pyfields/week)](https://pepy.tech/project/pyfields) [![GitHub stars](https://img.shields.io/github/stars/smarie/python-pyfields.svg)](https://github.com/smarie/python-pyfields/stargazers)


`pyfields` provides a simple, elegant, extensible and fast way to **define fields in python classes**:

 - with **as little impact on the class as possible** so that it can be used in *any* python class including mix-in classes. In particular not fiddling with `__init__` nor `__setattr__`, not requiring a class decorator, and nor requiring classes to inherit from a specific `BaseModel` or similar class,
 
 - with a **fast native implementation** by default (same speed as usual python after the first attribute access),
 
 - with support for **default values**, **default values factories**, **type hints** and **docstring**,
 
 - with optional support for **validation** and **conversion**. This makes field access obviously slower than the default native implementation but it is done field by field and not on the whole class at once, so fast native fields can coexist with slower validated ones.

If your first reaction is "what about attrs/dataclasses/traitlets/autoclass/pydantic", please have a look [here](why.md).


## Installing

```bash
> pip install pyfields
```

## Usage

### a - basics

TODO

```python
from pyfields import field

class TweeterMixin:
    afraid = field(default=False, 
                   doc="Status of the tweeter. When this is `True`," 
                       "tweets will be less aggressive.")

    def tweet(self):
        how = "lightly" if self.afraid else "loudly"
        print("tweeting %s" % how)
```

!!! success "No performance overhead"
    `field` by default returns a ["non-data" python descriptor](https://docs.python.org/3.7/howto/descriptor.html). So the first time the attribute is read, a small python method call extra cost is paid. *But* afterwards the attribute is replaced with a native attribute inside the object `__dict__`, so subsequent calls use native access without overhead. This was inspired by [werkzeug's @cached_property](https://tedboy.github.io/flask/generated/generated/werkzeug.cached_property.html).


### b - advanced

TODO



## Main features / benefits

**TODO**
 

## See Also

This library was inspired by:

 * [`werkzeug.cached_property`](https://werkzeug.palletsprojects.com/en/0.15.x/utils/#werkzeug.utils.cached_property)
 * [`attrs`](http://www.attrs.org/)
 * [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)
 * [`autoclass`](https://smarie.github.io/python-autoclass/)
 * [`pydantic`](https://pydantic-docs.helpmanual.io/)


### Others

*Do you like this library ? You might also like [my other python libraries](https://github.com/smarie/OVERVIEW#python)* 

## Want to contribute ?

Details on the github page: [https://github.com/smarie/python-pyfields](https://github.com/smarie/python-pyfields)
