# Changelog

### 0.2.1 - bugfix

Fixed [#4](https://github.com/smarie/python-pyfields/issues/4).

### 0.2.0 - `field` improvements

 - New `type` argument in `field` to declare the type of a field. If provided, the descriptor will *not* be replaced with a native field, and the type will be checked on every value modification. A `TypeError` will be raised if type does not comply. Type hints are correctly defined so that IDEs can pick them. Fixes [#3](https://github.com/smarie/python-pyfields/issues/3)

 - New `use_descriptor` argument in `field` to force use a descriptor instead of a native field.

### 0.1.0 - First public version

**Mix-in basics**:

 - `field` class to easily define class fields in a mixin without defining a `__init__`.
 - `@apply_mixins` decorator to apply mixins to a class without inheritance, by copying members (="monkeypatching")
 - Light documentation
 