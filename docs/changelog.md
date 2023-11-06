# Changelog

### 1.7.2 - bugfix

 - Fixed `TypeError: Neither typeguard not pytypes is installed` even with `typeguard` installed. 
   Fixed [#91] (https://github.com/smarie/python-pyfields/issues/91)

### 1.7.1 - Compatibility fix for typeguard `3.0.0`

 - Fixed `TypeError: check_type() takes 2 positional arguments but 3 were given` triggering erroneous `FieldTypeError` 
   when `typeguard>=3.0.0` is used. Fixed [#87](https://github.com/smarie/python-pyfields/issues/87)

### 1.7.0 - Better support for non-deep-copiable default values in `@autofields`

 - `@autofields` and `@autoclass` now raise an error when a field definition can not be valid, because the default value can not be deep-copied. This will help users detect issues such as [#84](https://github.com/smarie/python-pyfields/issues/84) earlier. Implementation is done through a new `autocheck` option in the `copy_value` factory.

 - `@autofields` and `@autoclass` now provide an `exclude` (resp. `af_exclude`) list, to list names for fields that should not be created. By default this contains a reserved name from `abc.ABCMeta`, for convenience. Fixes [#84](https://github.com/smarie/python-pyfields/issues/84).


### 1.6.2 - CI/CD migration

 - This is a technical release with no code change, to validate the new Github Actions workflow.

### 1.6.1 - Bugfix

 - Fixed an issue with `autofields` (and therefore `autoclass` too) where a field would be mistakenly recreated on a subclass when that subclass does not define type hints while the parent class defines type hints. Fixes [#81](https://github.com/smarie/python-pyfields/issues/81)

### 1.6.0 - we now have our own version of `@autoclass`

 - Copied the relevant contents from `autoclass` so as to get rid of the dependency. Since we are in a `pyfields` context there were many things that could be dropped and remaining code could be easily copied over. Also took this opportunity to replace the dict view with a `to_dict`/`from_dict` pair of methods, this seems less intrusive in the class design. Finally the parameter names have been simplified, see [API reference](./api_reference.md#autoclass) for details. Fixes [#79](https://github.com/smarie/python-pyfields/issues/79)

### 1.5.0 - updated `@autoclass` signature

 - Improved `@autoclass` so that it is much easier to access the relevant arguments from underlying `@autofields` and `@autoclass`. Fixed [#78](https://github.com/smarie/python-pyfields/issues/78)

### 1.4.0 - new `@autoclass` decorator

 - New `@autoclass` decorator directly available from `pyfields`. It is merely equivalent to the original `@autoclass` with option `autofields=True`, which makes it easier to use on classes with automatic fields. Fixes [#75](https://github.com/smarie/python-pyfields/issues/75)

### 1.3.2 - bugfix

 - Fields order are preserved by `@autofields` even in the case of an explicit `field()` with all others implicit. Fixed [#77](https://github.com/smarie/python-pyfields/issues/77)

### 1.3.1 - bugfix

 - Fields order are preserved by `@autofields` even in the case of a field with just a type annotation. Fixed [#76](https://github.com/smarie/python-pyfields/issues/76)

### 1.3.0 - Support for Forward references, PEP563 and class-level access

 - String forward references in type hints, and PEP563 behaviour, is now supported. When this case happense, the type hint resolution is delayed until the field is first accessed. Fixes [#73](https://github.com/smarie/python-pyfields/issues/73)

 - Accessing a field definition from a class directly is now enabled, since PyCharm [fixed their autocompletion bug](https://youtrack.jetbrains.com/issue/PY-38151). Fixes [#12](https://github.com/smarie/python-pyfields/issues/12)


### 1.2.0 - `getfields` improvements and new `get_field_values`

 - `getfields` can now be executed on an instance, and provides a `public_only` option. Fixes [#69](https://github.com/smarie/python-pyfields/issues/69)
 
 - New `get_field_values` method to get an ordered dict-like of field name: value.  Fixes [#70](https://github.com/smarie/python-pyfields/issues/70)

### 1.1.5 - bugfix

 - `@autofields` now correctly skips `@property` and more generally, descriptor members. Fixes [#67](https://github.com/smarie/python-pyfields/issues/67)

### 1.1.4 - better python 2 packaging

 - packaging improvements: set the "universal wheel" flag to 1, and cleaned up the `setup.py`. In particular removed dependency to `six`. Fixes [#66](https://github.com/smarie/python-pyfields/issues/66)

### 1.1.3 - smaller wheel

 - `tests` folder is now excluded from generated package wheel. Fixed [#65](https://github.com/smarie/python-pyfields/issues/65)

### 1.1.2 - type hint fix (minor)

 - Now `converters={'*': ...}` does not appear as a type hint error. Fixed [#64](https://github.com/smarie/python-pyfields/issues/64)

### 1.1.1 - PEP561 compatibility

 - **Misc**: Package is now PEP561 compatible. Fixed [#61](https://github.com/smarie/python-pyfields/issues/61)

### 1.1.0 - @autofields and default values improvements

 - **New `@autofields` decorator**. This decorator can be used to drastically reduce boilerplate code, similar to `pydantic` and `attrs`. This is compliant with python 2.7 and 3.5+ but is more useful when the type hints can be provided in class member annotations, so from 3.6+. Fixed [#55](https://github.com/smarie/python-pyfields/issues/55)
 
 - **Default values are now validated/converted as normal values**. If the default value is provided in `default=<value>` or as a `default_factory=copy_value(<value>)`, this is done only **once per field**, to accelerate future access. If the value was converted on the way, the converted value is used to replace the default value, or the default value copied by the factory. Fixed [#57](https://github.com/smarie/python-pyfields/issues/57)
 
 - **Misc**: removed `makefun` usage in `validate_n_convert.py` : was overkill. Also fixed a few type hints.

### 1.0.3 - bugfix

 * Fixed bug with `super().__init__` not behaving as expected. Fixed [#53](https://github.com/smarie/python-pyfields/issues/53)

### 1.0.2 - bugfixes

 * User-provided `nonable` status was wrongly overriden automatically when the field was attached to the class. Fixed [#51](https://github.com/smarie/python-pyfields/issues/51) 
 * Fixed an issue with type validation when `typeguard` is used and a tuple of types is provided instead of a `Union`. Fixed [#52](https://github.com/smarie/python-pyfields/issues/52)

### 1.0.1 - `pyproject.toml`

Added `pyproject.toml`

### 1.0.0 - Stable version

Overall behaviour stabilized and compliance with `@autoclass` to cover most use cases.

The only bug that has not yet been fixed is [#12](https://github.com/smarie/python-pyfields/issues/12) 

### 0.14.0 - helpers, bugfix, and ancestor-first option in init makers

**API**

 - new helper methods `get_field`, `yield_fields`, `has_fields` and `get_fields` (new name of `collect_all_fields`) so that other libraries such as `autoclass` can easily access the various information. `fix_fields` removed. Fixed [#48](https://github.com/smarie/python-pyfields/issues/48) 

 - New `ancestor_fields_first` option in all the `__init__` makers (`make_init` and `@init_fields`). Fixed [#50](https://github.com/smarie/python-pyfields/issues/50)

**Bugfixes**

 - Bugfixes in all the `__init__` makers (`make_init` and `@init_fields`):  

    - bugfix in case of inheritance with override: [#49](https://github.com/smarie/python-pyfields/issues/49)

    - the argument order used for fields initialization (inside the generated init method body) was sometimes incorrect. This would trigger a bug when one field was requiring another one to initialize.

    - when the list of fields received by `InitDescriptor` was an empty tuple and not `None`, the constructor was not created properly

### 0.13.0 - `nonable` fields

 - Fields can now be `nonable`, so as to bypass type and value validation when `None` is received. Fixed [#44](https://github.com/smarie/python-pyfields/issues/44)

### 0.12.0 - Minor improvements

 - Now all type validation errors are `FieldTypeError`. Fixed [#40](https://github.com/smarie/python-pyfields/issues/40).
 - Fixed bug with python < 3.6 where fields were not automatically attached to their class when used from within a subclass first. Fixed [#41](https://github.com/smarie/python-pyfields/issues/41)

### 0.11.0 - Better initialization orders in generated `__init__`

Fixed fields initialization order in generated constructor methods:

 - the order is now the same than the order of appearance in the class (and not reversed as it was). Fixed [#36](https://github.com/smarie/python-pyfields/issues/36). 
 - the above is true, even in python < 3.6. Fixed [#38](https://github.com/smarie/python-pyfields/issues/38)
 - the order now takes into account first the ancestors and then the subclasses, for the most intuitive behaviour. Fixed [#37](https://github.com/smarie/python-pyfields/issues/37).
 

### 0.10.0 - Read-only fields + minor improvements

**Read-only fields**

 - Read-only fields are now supported through `field(read_only=True)`. Fixes [#33](https://github.com/smarie/python-pyfields/issues/33).

**Misc**

 - All core exceptions now derive from a common `FieldError`, for easier exception handling. 
 - Now raising an explicit `ValueError` when a descriptor field is used with an old-style class in python 2. Fixes [#34](https://github.com/smarie/python-pyfields/issues/34) 

### 0.9.1 - Minor improvements

 - Minor performance improvement: `Converter.create_from_fun()` does not generate a new `type` everytime a converter needs to be created from a callable - now a single class `ConverterWithFuncs` is used. Fixed [#32](https://github.com/smarie/python-pyfields/issues/32). 

### 0.9.0 - Converters

**converters**

 - Fields can now be equipped with converters by using `field(converters=...)`. Fixes [#5](https://github.com/smarie/python-pyfields/issues/5)
 - New method `trace_convert` to debug conversion issues. It is available both as an independent function and as a method on `Field`. Fixes [#31](https://github.com/smarie/python-pyfields/issues/31)
 - New decorator `@<field>.converter` to add a converter to a field. Fixed [#28](https://github.com/smarie/python-pyfields/issues/28).

**misc**

 - The base `Field` class is now exposed at package level.

### 0.8.0 - PEP484 support

**PEP484 type hints support**

 - Now type hints relying on the `typing` module (PEP484) are correctly checked using whatever 3d party type checking library is available (`typeguard` is first looked for, then `pytypes` as a fallback). If none of these providers are available, a fallback implementation is provided, basically flattening `Union`s and replacing `TypeVar`s before doing `is_instance`. It is not guaranteed to support all `typing` subtelties. Fixes [#7](https://github.com/smarie/python-pyfields/issues/7)


### 0.7.0 - more ways to define validators

**validators**

 - New decorator `@<field>.validator` to add a validator to a field. Fixed [#9](https://github.com/smarie/python-pyfields/issues/9). 
 - Native fields are automatically transformed into descriptor fields when validators are added this way. Fixes [#1](https://github.com/smarie/python-pyfields/issues/1).


### 0.6.0 - default factories and slots

**default value factories**

 - `default_factory` callables now receive one argument: the object instance. Fixes [#6](https://github.com/smarie/python-pyfields/issues/6)
 - New decorator `@<field>.default_factory` to define a default value factory. Fixed [#27](https://github.com/smarie/python-pyfields/issues/27)
 - New `copy_value`, `copy_field` and `copy_attr` helper functions to create default value factories. Fixed [#26](https://github.com/smarie/python-pyfields/issues/26)

**support for slots**

 - `field` now automatically detects when a native field is attached to a class with slots and no `__dict__` is present. In that case, the native field is replaced with a descriptor field. Fixed [#20](https://github.com/smarie/python-pyfields/issues/20).

### 0.5.0 - First public version

**fields**

 - `field()` method to easily define class fields without necessarily defining a `__init__`.
 
 - "native" fields are created by default, or if `native=True` is set. A `NativeField` is a non-data descriptor that replaces itself automatically with a native python attribute after the first read, to get the same performance level on later access. 
 
 - "descriptor" fields are created when type or value validation is required, or if `native=False` is set. A `DescriptorField` uses the standard python descriptor protocol so that type and value can be validated on all future access without messing with the `__setattr__` method.
 
 - support for `type_hint` declaration to declare the type of a field. If `validate_type` provided, the descriptor will *not* be replaced with a native field, and the type will be checked on every value modification. A `TypeError` will be raised if type does not comply. Type hints are correctly defined so that IDEs can pick them. Fixes [#10](https://github.com/smarie/python-pyfields/issues/10)
 
 - support for `validators` relying on `valid8`. Validators can receive `(val)`, `(obj, val)` or `(obj, field, val)` to support validation based on several fields. The only requirement is to return `True` or `None` in case of success. Fixes [#3](https://github.com/smarie/python-pyfields/issues/3)

**init**

 - `make_init` method to create an entire `__init__` method with control of which fields are injected, and with possibility to blend a post-init callback in. Fixes [#14](https://github.com/smarie/python-pyfields/issues/14).

 - `@init_fields` decorator to auto-init fields before your `__init__` method.

 - `@inject_fields` decorator to easily inject `fields` in an init method and perform the assignment precisely when users want (for easy debugging). Fixes [#13](https://github.com/smarie/python-pyfields/issues/13)

**misc**

 - `__weakref__` added in all relevant classes. Fixes [#21](https://github.com/smarie/python-pyfields/issues/21)
 
 - Now using stubs [#17](https://github.com/smarie/python-pyfields/issues/17)
 
 - Fixed bug [#11](https://github.com/smarie/python-pyfields/issues/11).
 
 - Fixed `ValueError` with mini-lambda < 2.2. Fixed [#22](https://github.com/smarie/python-pyfields/issues/22)
 
 - Because of a [limitation in PyCharm type hints](https://youtrack.jetbrains.com/issue/PY-38151) we had to remove support for class-level field access. This created [#12](https://github.com/smarie/python-pyfields/issues/12) which will be fixed as soon as PyCharm issue is fixed.
 
### 0.1.0 - unpublished first draft

Extracted from [`mixture`](https://smarie.github.io/python-mixture/).
