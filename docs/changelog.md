# Changelog

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
