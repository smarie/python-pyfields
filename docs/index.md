# pyfields

*Define fields in python classes. Easily.*

[![Python versions](https://img.shields.io/pypi/pyversions/pyfields.svg)](https://pypi.python.org/pypi/pyfields/) [![Build Status](https://travis-ci.org/smarie/python-pyfields.svg?branch=master)](https://travis-ci.org/smarie/python-pyfields) [![Tests Status](https://smarie.github.io/python-pyfields/junit/junit-badge.svg?dummy=8484744)](https://smarie.github.io/python-pyfields/junit/report.html) [![codecov](https://codecov.io/gh/smarie/python-pyfields/branch/master/graph/badge.svg)](https://codecov.io/gh/smarie/python-pyfields)

[![Documentation](https://img.shields.io/badge/doc-latest-blue.svg)](https://smarie.github.io/python-pyfields/) [![PyPI](https://img.shields.io/pypi/v/pyfields.svg)](https://pypi.python.org/pypi/pyfields/) [![Downloads](https://pepy.tech/badge/pyfields)](https://pepy.tech/project/pyfields) [![Downloads per week](https://pepy.tech/badge/pyfields/week)](https://pepy.tech/project/pyfields) [![GitHub stars](https://img.shields.io/github/stars/smarie/python-pyfields.svg)](https://github.com/smarie/python-pyfields/stargazers)


`pyfields` provides a simple and elegant way to define fields in python classes. With `pyfields` you explicitly define all aspects of a field (default value, type, documentation...) in a single place, and can refer to it from other places.

It is designed with **development freedom** as primary target: 

 - *code segregation*. Everything is in the field, not in `__init__`, not in `__setattr__`.

 - *absolutely no constraints*. Your class does not need to use type hints. You can use python 2 and 3.5. Your class is not modified behind your back: `__init__` and `__setattr__` are untouched. You do not need to decorate your class. You do not need your class to inherit from anything. This is particularly convenient for mix-in classes, and in general for users wishing to stay in control of their class design.
 
 - *no performance loss by default*. If you use `pyfields` to declare fields without adding validators nor converters, instance attributes will be replaced with a native python attribute on first access, preserving the same level of performance than what you are used to.

It provides **many optional features** that will make your object-oriented developments easier:

 - all field declarations support *type hints* and *docstring*,

 - optional fields can have *default values* but also *default values factories* (such as *"if no value is provided, copy this other field"*)
 
 - adding *validators* and *converters* to a field does not require you to write complex logic nor many lines of code. This makes field access obviously slower than the default native implementation but it is done field by field and not on the whole class at once, so fast native fields can coexist with slower validated ones (segregation principle).

 - initializing fields in your *constructor* is very easy and highly customizable

If your first reaction is "what about `attrs` / `dataclasses` / `pydantic` / `characteristic` / `traits` / `traitlets` / `autoclass` / ...", please have a look [here](why.md).


## Installing

```bash
> pip install pyfields
```

## Usage

### 1. Defining a field

A field is defined as a class member using the `field()` method. The idea (not new) is that you declare in a single place all aspects related to each field. For mandatory fields you do not need to provide any argument. For optional fields, you will typically provide a `default` value or a `default_factory` (we will see that later).

For example let's create a `Wall` class with one *mandatory* `height` and one *optional* `color` field:

```python
from pyfields import field

class Wall:
    height: int = field(doc="Height of the wall in mm.")
    color: str = field(default='white', doc="Color of the wall.")
```

!!! info "Compliance with python < 3.6"
    If you use python < `3.6` you know that PEP484 type hints can not be declared as shown above. However you can provide them as [type comments](https://www.python.org/dev/peps/pep-0484/#type-comments), or using the `type_hint` argument.

#### Field vs. Python attribute

By default when you use `field()`, nothing more than a "lazy field" is created on your class. This field will only be activated when you access it on an instance. That means that you are free to implement `__init__` as you wish, or even to rely on the default `object` constructor to create instances:

```python
# instantiate using the default `object` constructor
w = Wall()
```

No exception here even if we did not provide any value for the mandatory field `height` ! Although this default behaviour can look surprising, you will find that this feature is quite handy to define mix-in classes *with* attributes but *without* constructor. See [mixture](https://smarie.github.io/python-mixture/) for discussion. Of course if you do not like this behaviour you can very easily [add a constructor](#2-adding-a-constructor).

Until it is accessed for the first time, a field is visible on an instance with `dir()` (because its definition is inherited from the class) but not with `vars()` (because it has not been initialized on the object):

```python
>>> dir(w)[-2:]
['color', 'height']
>>> vars(w)
{}
```

As soon as you access it, a field is replaced with a standard native python attribute, visible in `vars`:

```python
>>> w.color  # optional field: tdefault value is used
'white'

>>> vars(w)
{'color': 'white'}
```

Of course mandatory fields must be initialized:

```python
>>> w.height
pyfields.core.MandatoryFieldInitError: \
   Mandatory field 'height' has not been initialized yet on instance <...>.

>>> w.height = 12
>>> vars(w)
{'color': 'white', 'height': 12}
```

Your IDE (e.g. PyCharm) should recognize the name and type of the field, so you can already refer to it easily in other code using autocompletion:

![pycharm_autocomplete1.png](imgs/autocomplete1.png)

#### Type validation

You can add type validation to a field by setting `check_type=True`.

```python
class Wall(object):
    height: int = field(check_type=True, doc="Height of the wall in mm.")
    color: str = field(check_type=True, default='white', doc="Color of the wall.")
```

yields

```
>>> w = Wall()
>>> w.height = 1
>>> w.height = '1'
TypeError: Invalid value type provided for 'Wall.height'. \ 
  Value should be of type 'int'. Instead, received a 'str': '1'
```

!!! info "Compliance with python < 3.6"
    If you use python < `3.6` and require type validation you should not use [type comments](https://www.python.org/dev/peps/pep-0484/#type-comments) but rather use the `type_hint` argument in `field`. Indeed it is not possible for python code to access type comments without source code inspection.


#### Value validation

You can add value (and type) validation to a field by providing `validators`. `pyfields` relies on `valid8` for validation, so the supported syntax is the same:

 - For a single validator, either provide a `<callable>` or a tuple `(<callable>, <error_msg>)`, `(<callable>, <failure_type>)` or `(<callable>, <error_msg>, <failure_type>)`. See [here](https://smarie.github.io/python-valid8/validation_funcs/c_simple_syntax/#1-one-validation-function) for details.
 
 - For several validators, either provide a list or a dictionary. See [here](https://smarie.github.io/python-valid8/validation_funcs/c_simple_syntax/#2-several-validation-functions) for details.

For example:

```python
from mini_lambda import x
from valid8.validation_lib import is_in

colors = {'white', 'blue', 'red'}

class Wall(object):
    height: int = field(validators={'should be a positive number': x > 0,
                                    'should be a multiple of 100': x % 100 == 0}, 
                        doc="Height of the wall in mm.")
    color: str = field(validators=is_in(colors), 
                       default='white', 
                       doc="Color of the wall.")
```

yields

```
>>> w = Wall()
>>> w.height = 100
>>> w.height = 1
valid8.entry_points.ValidationError[ValueError]: 
    Error validating [<...>.Wall.height=1]. 
    At least one validation function failed for value 1. 
    Successes: ['x > 0'] / Failures: {
      'x % 100 == 0': 'InvalidValue: should be a multiple of 100. Returned False.'
    }.
>>> w.color = 'magenta'
valid8.entry_points.ValidationError[ValueError]: 
    Error validating [<...>.Wall.color=magenta]. 
    NotInAllowedValues: x in {'blue', 'red', 'white'} does not hold 
    for x=magenta. Wrong value: 'magenta'.
```

See `valid8` documentation for details about the [syntax](https://smarie.github.io/python-valid8/validation_funcs/c_simple_syntax/) and available [validation lib](https://smarie.github.io/python-valid8/validation_funcs/b_base_validation_lib/).

**todo** In addition to the above syntax, `pyfields` support that you add validators to a field after creation, using the `@field.validator` decorator:

Finally, for advanced validation scenarios you might with your validation callables to receive a bit of context. `pyfields` supports that the callables accept one, two or three arguments for this (where `valid8` supports only 1): `f(val)`, `f(obj, val)`, and `f(obj, field, val)`.

For example we can define walls where the width is a multiple of the length:

```python
from valid8 import ValidationFailure

class InvalidWidth(ValidationFailure):
    help_msg = 'should be a multiple of the height ({height})'

def validate_width(obj, width):
    if width % obj.height != 0:
        raise InvalidWidth(width, height=obj.height)

class Wall(object):
    height: int = field(doc="Height of the wall in mm.")
    width: str = field(validators=validate_width,
                       doc="Width of the wall in mm.")
```

#### Converters

*todo*

#### Native vs. Descriptor fields

`field()` by default creates a so-called **native field**. This special construct is designed to be as fast as a normal python attribute after the first access, so that performance is not impacted. This high level of performance has a drawback: validation and conversion are not possible on a native field. 

So when you add type or value validation, or conversion, to a field, `field()` will automatically create a **descriptor field** instead of a native field. This is an object relying on the [python descriptor protocol](https://docs.python.org/howto/descriptor.html). Such objects have slower access time than native python attributes but provide convenient hooks necessary to perform validation and conversion.

For experiments, you can force a field to be a descriptor by setting `native=False`:

```python
from pyfields import field

class Foo:
    a = field()               # a native field
    b = field(native=False)   # a descriptor field
```

We can easily see the difference (note: direct class access `Foo.a` is currently forbidden because of [this issue](https://github.com/smarie/python-pyfields/issues/12)):

```python
>>> Foo.__dict__['a']
<NativeField: <...>.Foo.a>

>>> Foo.__dict__['b']
<DescriptorField: <...>.Foo.a>
```

And measure the difference in access time:

```python
import timeit

f = Foo()

def set_a(): f.a = 12

def set_b(): f.b = 12

def set_c(): f.c = 12

ta = timeit.Timer(set_a).timeit()
tb = timeit.Timer(set_b).timeit()
tc = timeit.Timer(set_c).timeit()

print("Average time (ns) setting the field:")
print("%0.2f (normal python) ; %0.2f (native field) ;" 
      " %0.2f (descriptor field)" % (tc, ta, tb))
```

yields (results depend on your machine):

```
Average time (ns) setting the field:
0.09 (normal python) ; 0.09 (native field) ; 0.44 (descriptor field)
```

!!! info "Why are native fields so fast ?"
    Native fields are implemented as a ["non-data" python descriptor](https://docs.python.org/3.7/howto/descriptor.html) that overrides itself on first access. So the first time the attribute is read, a small python method call extra cost is paid but the attribute is immediately replaced with a normal attribute inside the object `__dict__`. That way, subsequent calls use native python attribute access without overhead. This trick was inspired by [werkzeug's @cached_property](https://tedboy.github.io/flask/generated/generated/werkzeug.cached_property.html).


### 2. Adding a constructor

`pyfields` provides you with several alternatives to add a constructor to a class equipped with fields. The reason why we do not follow the [Zen of python](https://www.python.org/dev/peps/pep-0020/#the-zen-of-python) here (*"There should be one-- and preferably only one --obvious way to do it."*) is to recognize that different developers may have different coding style or philosophies, and to be as much as possible agnostic in front of these.

#### a - `make_init`

`make_init` is the **most compact** way to add a constructor to a class with fields. With it you create your `__init__` method in one line:

```python hl_lines="6"
from pyfields import field, make_init

class Wall:
    height: int = field(doc="Height of the wall in mm.")
    color: str = field(default='white', doc="Color of the wall.")
    __init__ = make_init()
```

By default, all fields will appear in the constructor, in the order of appearance in the class and its parents, following the `mro` (method resolution order, the order in which python looks for a method in the hierarchy of classes). Since it is not possible for mandatory fields to appear *after* optional fields in the signature, all mandatory fields will appear first, and then all optional fields will follow.

The easiest way to see the result is probably to look at the help on your class:

``` hl_lines="5"
>>> help(Wall)
Help on class Wall in module <...>:

class Wall(builtins.object)
 |  Wall(height, color='white')
 |  (...)
```

or you can inspect the method:

``` hl_lines="4"
>>> help(Wall.__init__)
Help on function __init__ in module <...>:

__init__(self, height, color='white')
    The `__init__` method generated for you when you use `make_init`
```

You can check that your constructor works as expected:

```python
>>> w = Wall(2)
>>> vars(w)
{'color': 'white', 'height': 2}

>>> w = Wall(color='blue', height=12)
>>> vars(w)
{'color': 'blue', 'height': 12}

>>> Wall(color='blue')
TypeError: __init__() missing 1 required positional argument: 'height'
```

If you do not wish the generated constructor to expose all fields, you can customize it by providing an **explicit** ordered list of fields. For example below only `height` will be in the constructor:

```python hl_lines="8"
from pyfields import field, make_init

class Wall:
    height: int = field(doc="Height of the wall in mm.")
    color: str = field(default='white', doc="Color of the wall.")

    # only `height` will be in the constructor
    __init__ = make_init(height)
```

The list can contain fields defined in another class, typically a parent class: 

```python hl_lines="9"
from pyfields import field, make_init

class Wall:
    height: int = field(doc="Height of the wall in mm.")

class ColoredWall(Wall):
    color: str = field(default='white', doc="Color of the wall.")
    __init__ = make_init(Wall.height)
```

Note: a pending [issue](https://github.com/smarie/python-pyfields/issues/12) prevents the above example to work, you have to use `Wall.__dict__['height']` instead of `Wall.height` to reference the field from the other class.

Finally, you can customize the created constructor by declaring a post-init method as the `post_init_fun` argument. This is roughly equivalent to `@init_fields` so we do not present it here, see [documentation](api_reference.md#make_init).


#### b - `@init_fields`

If you prefer to write an init function as usual, you can use the `@init_fields` decorator to augment this init function's signature with all or some fields.

```python  hl_lines="7"
from pyfields import field, init_fields

class Wall:
    height = field(doc="Height of the wall in mm.")  # type: int
    color = field(default='white', doc="Color of the wall.")  # type: str

    @init_fields
    def __init__(self, msg='hello'):
        """
        Constructor. After initialization, some print message is done

        :param msg: the message details to add
        """
        print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
        self.non_field_attr = msg
```

Note: as you can see in this example, you can of course create other attributes in this init function (done in the last line here with `self.non_field_attr = msg`). Indeed, declaring fields in a class do not "pollute" the class, so you can do anything you like as usual.

You can check that the resulting constructor works as expected:

```
>>> help(Wall)
Help on class Wall in module <...>:
class Wall(builtins.object)
 |  Wall(height, msg='hello', color='white')
...

>>> w = Wall(1, 'hey')
post init ! height=1, color=white, msg=hey

>>> vars(w)
{'height': 1, 'color': 'white', 'non_field_attr': 'hey'}
```

Note on the order of arguments in the resulting `__init__` signature: as you can see, `msg` appears between `height` and `color` in the signature. This corresponds to the 


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
