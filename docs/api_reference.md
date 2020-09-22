# API reference

In general, `help(symbol)` will provide the latest up-to-date documentation.

## *`field`*

```python
def field(type_hint=None,        # type: Type[T]
          check_type=False,      # type: bool
          default=EMPTY,         # type: T
          default_factory=None,  # type: Callable[[], T]
          validators=None,       # type: Validators
          doc=None,              # type: str
          name=None,             # type: str
          native=None            # type: bool
          ):
    # type: (...) -> T
```

Returns a class-level attribute definition. It allows developers to define an attribute without writing an 
`__init__` method. Typically useful for mixin classes.

**Laziness**

The field will be lazily-defined, so if you create an instance of the class, the field will not have any value 
until it is first read or written.

**Optional/Mandatory**

By default fields are mandatory, which means that you must set them before reading them (otherwise a `MandatoryFieldInitError` will be raised). You can define an optional field by providing a `default` value. This value will not be copied but used "as is" on all instances, following python's classical pattern for default values. If you wish to run specific code to instantiate the default value, you may provide a `default_factory` callable instead. That callable should have no mandatory argument and should return the default value. Alternately you can use the `@<field>.default_factory` decorator.

**Typing**

Type hints for fields can be provided using the standard python typing mechanisms (type comments for python < 3.6 and class member type hints for python >= 3.6). Types declared this way will not be checked at runtime, they are just hints for the IDE. You can also specify a `type_hint` explicitly to override the type hints gathered from the other means indicated above. It supports both a single type or an iterable of alternate types (e.g. `(int, str)`). The corresponding type hint is automatically declared by `field` so your IDE will know about it. Specifying a `type_hint` explicitly is mostly useful if you are running python < 3.6 and wish to use type validation, see below.

By default `check_type` is `False`. This means that the abovementioned `type_hint` is just a hint. If you set `check_type=True` the type declared in the type hint will be validated, and a `TypeError` will be raised if provided values are invalid. Important: if you are running python < 3.6 you have to set the type hint explicitly using `type_hint` if you wish to set `check_type=True`, otherwise you will get an exception. Indeed type comments can not be collected by the code.

Now type hints relying on the `typing` module (PEP484) are correctly checked using whatever 3d party type checking library is available (`typeguard` is first looked for, then `pytypes` as a fallback). If none of these providers are available, a fallback implementation is provided, basically flattening `Union`s and replacing `TypeVar`s before doing `is_instance`. It is not guaranteed to support all `typing` subtleties.

**Documentation**

A docstring can be provided in `doc`for code readability.

**Example**

```python
>>> from pyfields import field
>>> class Foo(object):
...     od = field(default='bar', doc="This is an optional field with a default value")
...     odf = field(default_factory=lambda obj: [], doc="This is an optional with a default value factory")
...     m = field(doc="This is a mandatory field")
...     mt: int = field(check_type=True, doc="This is a type-checked mandatory field")
...
>>> o = Foo()
>>> o.od   # read access with default value
'bar'
>>> o.odf  # read access with default value factory
[]
>>> o.odf = 12  # write access
>>> o.odf
12
>>> o.m  # read access for mandatory attr without init
Traceback (most recent call last):
    ...
pyfields.core.MandatoryFieldInitError: Mandatory field 'm' has not been initialized yet on instance...
>>> o.m = True
>>> o.m  # read access for mandatory attr after init
True
>>> del o.m  # all attributes can be deleted, same behaviour than new object
>>> o.m
Traceback (most recent call last):
    ...
pyfields.core.MandatoryFieldInitError: Mandatory field 'm' has not been initialized yet on instance...
>>> o.mt = 1
>>> o.mt = '1'
Traceback (most recent call last):
    ...
TypeError: Invalid value type ...
```

**Limitations**

Old-style classes are not supported: in python 2, don't forget to inherit from `object`.

**Performance overhead**

`field` has two different ways to create your fields. One named `NativeField` is faster but does not permit type checking, validation, or converters; besides it does not work with classes using `__slots__`. It is used by default everytime where it is possible, except if you use one of the abovementioned features. In that case a `DescriptorField` will transparently be created. You can force a `DescriptorField` to be created by setting `native=False`.
    
The `NativeField` class implements the "non-data" descriptor protocol. So the first time the attribute is read, a small  python method call extra cost is paid. *But* afterwards the attribute is replaced with a native attribute inside the object `__dict__`, so subsequent calls use native access without overhead. 
This was inspired by [werkzeug's @cached_property](https://tedboy.github.io/flask/generated/generated/werkzeug.cached_property.html). 

**Inspired by**

This method was inspired by 

 - `@lazy_attribute` (sagemath)
 - `@cached_property` (werkzeug) and [this post](https://stackoverflow.com/questions/24704147/python-what-is-a-lazy-property)
 - [this post](https://stackoverflow.com/questions/42023852/how-can-i-get-the-attribute-name-when-working-with-descriptor-protocol-in-python)
 - `attrs` / `dataclasses`

**Parameters**

 - `type_hint`: an optional explicit type hint for the field, to override the type hint defined by PEP484 especially on old python versions because type comments can not be captured. It supports both a single type or an iterable of alternate types (e.g. `(int, str)`). By default the type hint is just a hint and does not contribute to validation. To enable type validation, set `check_type` to `True`.
 - `check_type`: by default (`check_type=False`), the type of a field, provided using PEP484 type hints or an explicit `type_hint`, is not validated when you assign a new value to it. You can activate type validation by setting `check_type=True`. In that case the field will become a descriptor field.
 - `default`: a default value for the field. Providing a `default` makes the field "optional". `default` value is not copied on new instances, if you wish a new copy to be created you should provide a `default_factory` instead. Only one of `default` or `default_factory` should be provided.
 - `default_factory`: a factory that will be called (without arguments) to get the default value for that field, everytime one is needed. Providing a `default_factory` makes the field "optional". Only one of `default` or `default_factory` should be provided.
 - `validators`: a validation function definition, sequence of validation function definitions, or dictionary of validation function definitions. See `valid8` "simple syntax" for details.
 - `doc`: documentation for the field. This is mostly for class readability purposes for now.
 - `name`: in python < 3.6 this is mandatory if you do not use any other decorator or constructor creation on the class (such as `make_init`). If provided, it should be the same name than the one used used in the class field definition (i.e. you should define the field as `<name> = field(name=<name>)`).
 - `native`: a boolean that can be turned to `False` to force a field to be a descriptor field, or to `True` to force it to be a native field. Native fields are faster but can not support type and value validation nor conversions or callbacks. `None` (default) automatically sets `native=True` if no `validators` nor `check_type=True` nor `converters` are provided ; and `native=False` otherwise. In general you should not set this option manually except for experiments.

### `@<field>.default_factory`

Decorator to register the decorated function as the default factory of a field. Any previously registered 
default factory will be overridden.

The decorated function should accept a single argument `(obj/self)`, and should return a value to use as the
default.

```python
>>> class Pocket:
...     items = field()
...
...     @items.default_factory
...     def default_items(self):
...         print("generating default value for %s" % self)
...         return []
...
>>> p = Pocket()
>>> p.items
generating default value for <pyfields.core.Pocket object ...
[]
```

Several helper functions are available to create default factories:

 - `copy_value(<value>)` returns a factory that creates a copy of the provided `val` everytime it is called. Handy if you wish to use mutable
    objects as default values for your fields ; for example lists.
  
 - `copy_attr(<att_name>, deep=True)` returns a factory that creates a (deep or not) copy of the value in the given attribute everytime it is called.

 - `copy_field(<field_or_name>, deep=True)` is similar to `copy_attr` but you can provide a `field` instead of a name.

### `@<field>.validator`

A decorator to add a validator to a field.

```python
>>> class Foo(object):
...     m = field()
...     @m.validator
...     def m_is_positive(self, m_value):
...         return m_value > 0
...
>>> o = Foo()
>>> o.m = 0  # doctest: +NORMALIZE_WHITESPACE
Traceback (most recent call last):
...
valid8.entry_points.ValidationError[ValueError]: Error validating [Foo.m=0]. InvalidValue:
    Function [m_is_positive] returned [False] for value 0.
```

The decorated function should have a signature of `(val)`, `(obj/self, val)`, or `(obj/self, field, val)`. It should return `True` or `None` in case of success.

You can use several of these decorators on the same function so as to share implementation across multiple
fields:

```python
>>> class Foo(object):
...     m = field()
...     m2 = field()
...
...     @m.validator
...     @m2.validator
...     def is_positive(self, field, value):
...         print("validating %s" % field.qualname)
...         return value > 0
...
>>> o = Foo()
>>> o.m2 = 12
validating Foo.m2
>>> o.m = 0  # doctest: +NORMALIZE_WHITESPACE
Traceback (most recent call last):
...
valid8.entry_points.ValidationError[ValueError]: Error validating [Foo.m=0]. InvalidValue:
    Function [is_positive] returned [False] for value 0.
```

## Constructors

### `make_init`

```python
def make_init(*fields: Union[Field, Any],
              post_init_fun: Callable = None,
              post_init_args_before: bool = True
              ) -> Callable:
```

Creates a constructor based on the provided fields.

If `fields` is empty, all fields from the class will be used in order of appearance, then the ancestors (following the mro)

```python
>>> from pyfields import field, make_init
>>> class Wall:
...     height = field(doc="Height of the wall in mm.")
...     color = field(default='white', doc="Color of the wall.")
...     __init__ = make_init()
>>> w = Wall(1, color='blue')
>>> assert vars(w) == {'color': 'blue', 'height': 1}
```

If `fields` is not empty, only the listed fields will appear in the constructor and will be initialized upon init.

```python
>>> class Wall:
...     height = field(doc="Height of the wall in mm.")
...     color = field(default='white', doc="Color of the wall.")
...     __init__ = make_init(height)
>>> w = Wall(1, color='blue')
Traceback (most recent call last):
...
TypeError: __init__() got an unexpected keyword argument 'color'
```

`fields` can contain fields that do not belong to this class: typically they can be fields defined in a parent class. Note however that any field can be used, it is not mandatory to use class or inherited fields.

```python
>>> class Wall:
...     height: int = field(doc="Height of the wall in mm.")
...
>>> class ColoredWall(Wall):
...     color: str = field(default='white', doc="Color of the wall.")
...     __init__ = make_init(Wall.__dict__['height'])
...
>>> w = ColoredWall(1)
>>> vars(w)
{'height': 1}
```

If a `post_init_fun` is provided, it should be a function with `self` as first argument. This function will be executed after all declared fields have been initialized. The signature of the resulting `__init__` function created will be constructed by blending all mandatory/optional fields with the mandatory/optional args in the `post_init_fun` signature. The ones from the `post_init_fun` will appear first except if `post_init_args_before` is set to `False`

```python
>>> class Wall:
...     height: int = field(doc="Height of the wall in mm.")
...     color: str = field(default='white', doc="Color of the wall.")
...
...     def post_init(self, msg='hello'):
...         print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
...         self.non_field_attr = msg
...
...     # only `height` and `foo` will be in the constructor
...     __init__ = make_init(height, post_init_fun=post_init)
...
>>> w = Wall(1, 'hey')
post init ! height=1, color=white, msg=hey
>>> assert vars(w) == {'height': 1, 'color': 'white', 'non_field_attr': 'hey'}
```

**Parameters**

 - `fields`: the fields to include in the generated constructor signature. If no field is provided, all fields defined in the class will be included, as well as inherited ones following the mro.
 - `post_init_fun`: (default: `None`) an optional function to call once all fields have been initialized. This function should have `self` as first argument. The rest of its signature will be blended with the fields in the generated constructor signature.
 - `post_init_args_before`: boolean. Defines if the arguments from the `post_init_fun` should appear before (default: `True`) or after (`False`) the fields in the generated signature. Of course in all cases, mandatory arguments will appear after optional arguments, so as to ensure that the created signature is valid.
        
**Outputs:** a constructor method to be used as `__init__`



### `@init_fields`

```python
def init_fields(*fields: Union[Field, Any],
                init_args_before: bool = True
                ):
```

Decorator for an init method, so that fields are initialized before entering the method.

By default, when the decorator is used without arguments or when `fields` is empty, all fields defined in the class are initialized. Fields inherited from parent classes are included, following the mro. The signature of the init method is modified so that it can receive values for these fields:

```python
>>> from pyfields import field, init_fields
>>> class Wall:
...     height: int = field(doc="Height of the wall in mm.")
...     color: str = field(default='white', doc="Color of the wall.")
...
...     @init_fields
...     def __init__(self, msg: str = 'hello'):
...         print("post init ! height=%s, color=%s, msg=%s" % (self.height, self.color, msg))
...         self.non_field_attr = msg
...
>>> help(Wall.__init__)
Help on function __init__ in module pyfields.init_makers:
<BLANKLINE>
__init__(self, height: int, msg: str = 'hello', color: str = 'white')
    The `__init__` method generated for you when you use `@init_fields`
    or `make_init` with a non-None `post_init_fun` method.
<BLANKLINE>
>>> w = Wall(2)
post init ! height=2, color=white, msg=hello
```

The list of fields can be explicitly provided in `fields`.

By default the init arguments will appear before the fields in the signature, wherever possible (mandatory args before mandatory fields, optional args before optional fields). You can change this behaviour by setting `init_args_before` to `False`.


**Parameters:**

 - `fields`: list of fields to initialize before entering the decorated `__init__` method. For each of these fields a corresponding argument will be added in the method's signature. If an empty list is provided, all fields from the class will be used including inherited fields following the mro.
 - `init_args_before`: If set to `True` (default), arguments from the decorated init method will appear before the fields when possible. If set to `False` the contrary will happen.


### `@inject_fields`

```python
def inject_fields(*fields: Union[Field, Any],
                  ):
```

A decorator for `__init__` methods, to make them automatically expose arguments corresponding to all `*fields`.
It can be used with or without arguments. If the list of fields is empty, it means "all fields from the class".

The decorated `__init__` method should have an argument named `'fields'`. This argument will be injected with an
object so that users can manually execute the fields initialization. This is done with `fields.init()`.

```python
>>> from pyfields import field, inject_fields
>>> class Wall(object):
...     height = field(doc="Height of the wall in mm.")
...     color = field(default='white', doc="Color of the wall.")
...
...     @inject_fields(height, color)
...     def __init__(self, fields):
...         # initialize all fields received
...         fields.init(self)
...
...     def __repr__(self):
...         return "Wall<height=%r, color=%r>" % (self.height, self.color)
...
>>> Wall()
Traceback (most recent call last):
...
TypeError: __init__() missing 1 required positional argument: 'height'
>>> Wall(1)
Wall<height=1, color='white'>
```

**Parameters:**

 - `fields`: list of fields to initialize before entering the decorated `__init__` method. For each of these fields a corresponding argument will be added in the method's signature. If an empty list is provided, all fields from the class will be used including inherited fields following the mro.


## `@autofields`

```python
def autofields(check_types=False,     # type: bool
               include_upper=False,   # type: bool
               include_dunder=False,  # type: bool
               make_init=True         # type: bool
               ):
```

Decorator to automatically create fields and constructor on a class.

When a class is decorated with `@autofields`, all of its members are automatically transformed to fields.
More precisely: members that only contain a type annotation become mandatory fields, while members that contain a value (with or without type annotation) become optional fields with a `copy_value` default_factory.

By default, the following members are NOT transformed into fields:

 * members with upper-case names. This is because this kind of name formatting usually denotes class constants. They
   can be transformed to fields by setting `include_upper=True`.
 * members with dunder-like names. They can be included using `include_dunder=True`. Note that reserved python
   dunder names such as `__name__`, `__setattr__`, etc. can not be transformed to fields, even when
   `include_dunder=True`.
 * members that are classes or methods defined in the class (that is, where their `.__name__` is the same name than
   the member name).
 * members that are already fields. Therefore you can continue to use `field()` on certain members explicitly if
   you need to add custom validators, converters, etc.

All created fields have their `type_hint` filled with the type hint associated with the member, and have
`check_type=False` by default. This can be changed by setting `check_types=True`.

Finally, in addition, an init method (constructor) is generated for the class, using `make_init()`. This may be
disabled by setting `make_init=False`.

```python
>>> @autofields
... class Pocket:
...     SENTENCE = "hello world"  # uppercase: not a field
...     size: int   # mandatory field
...     items = []  # optional - default value will be a factory
...
>>> p = Pocket(size=10)
>>> p.items
[]
>>> Pocket(size=10, SENTENCE="hello")
Traceback (most recent call last):
...
TypeError: __init__() got an unexpected keyword argument 'SENTENCE'
```

## `@autoclass`

```python
def autoclass(include=None,      # type: Union[str, Tuple[str]]
              exclude=None,      # type: Union[str, Tuple[str]]
              autoargs=_AUTO,    # type: bool
              autoprops=_AUTO,   # type: bool
              autodict=True,     # type: bool
              autorepr=_AUTO,    # type: bool
              autoeq=_AUTO,      # type: bool
              autohash=True,     # type: bool
              autoslots=False,   # type: bool
              autoinit=_AUTO,    # type: bool
              autofields=True,   # type: bool
              ):
```

Decorator to automatically create fields and constructor on a class, as well as to add string representation, equality methods, dict view, etc. This is similar to the one from `autoclass` library with the single difference that by default `autofields=True`. See [autoclass documentation](https://smarie.github.io/python-autoclass/) for details.


## API

### `has_fields`

```python
def has_fields(cls,
               include_inherited=True  # type: bool
               )
```

Returns True if class `cls` defines at least one `pyfields` field.
If `include_inherited` is `True` (default), the method will return `True` if at least a field is defined in the class or one of its ancestors. If `False`, the fields need to be defined on the class itself.

### `get_fields`

```python
def get_fields(cls_or_obj,
               include_inherited=True,  # type: bool
               remove_duplicates=True,  # type: bool
               ancestors_first=True,    # type: bool
               public_only=False,       # type: bool
               container_type=tuple,    # type: Type[T]
               )
```

Utility method to collect all fields defined in a class, including all inherited or not, in definition order.
By default duplicates are removed and ancestor fields are included and appear first. If a field is overridden, it will appear at the position of the overridden field in the order.

If an object is provided, `getfields` will be executed on its class.

### `yield_fields`

```python
def yield_fields(cls,
                 include_inherited=True,  # type: bool
                 remove_duplicates=True,  # type: bool
                 ancestors_first=True,    # type: bool
                 public_only=False,       # type: bool
                 )
```

Similar to `get_fields` but as a generator.

### `get_field`

```python
def get_field(cls, name)
```

Utility method to return the field member with name `name` in class `cls`.
If the member is not a field, a `NotAFieldError` is raised.

### `get_field_values`

```python
def get_field_values(obj,
                     include_inherited=True,  # type: bool
                     remove_duplicates=True,  # type: bool
                     ancestors_first=True,    # type: bool
                     public_only=False,       # type: bool
                     container_type=ODict,    # type: Type[T]
                     )
```

Utility method to collect all field names and values defined on an object, including all inherited or not.

By default duplicates are removed and ancestor fields are included and appear first. If a field is overridden, it will appear at the position of the overridden field in the order.

The result is an ordered dictionary (a `dict` in python 3.7, an `OrderedDict` otherwise) of {name: value} pairs. One can change the container type with the `container_type` attribute though, that will receive an iterable of (key, value) pairs.
