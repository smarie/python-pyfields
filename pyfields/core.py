# Authors: Sylvain MARIE <sylvain.marie@se.com>
#          + All contributors to <https://github.com/smarie/python-pyfields>
#
# License: 3-clause BSD, <https://github.com/smarie/python-pyfields/blob/master/LICENSE>
import sys
from enum import Enum
from textwrap import dedent
from inspect import getmro

try:
    from inspect import signature, Parameter
except ImportError:
    # noinspection PyUnresolvedReferences,PyPackageRequirements
    from funcsigs import signature, Parameter  # noqa

from valid8 import ValidationFailure, is_pep484_nonable

from pyfields.typing_utils import assert_is_of_type, FieldTypeError, get_type_hints
from pyfields.validate_n_convert import FieldValidator, make_converters_list, trace_convert

try:  # python 3.5+
    # noinspection PyUnresolvedReferences
    from typing import Callable, Type, Any, Union, Iterable, Tuple, TypeVar
    _NoneType = type(None)
    use_type_hints = sys.version_info > (3, 0)
    if use_type_hints:
        T = TypeVar('T')
        # noinspection PyUnresolvedReferences
        from pyfields.validate_n_convert import ValidatorDef, Validators, Converters, ConverterFuncDefinition,\
            DetailedConversionResults, ValidationFuncOrLambda, ValidType

except ImportError:
    use_type_hints = False


USE_ADVANCED_TYPE_CHECKER = assert_is_of_type is not None


PY36 = sys.version_info >= (3, 6)
PY2 = sys.version_info < (3, 0)
# PY35 = sys.version_info >= (3, 5)

try:
    object.__qualname__
except AttributeError:
    # old python without __qualname__
    import re
    RE_CLASS_NAME = re.compile("<class '(.*)'>")

    def qualname(cls):
        cls_str = str(cls)
        match = RE_CLASS_NAME.match(cls_str)
        if match:
            return match.groups()[0]
        else:
            return cls_str


class FieldError(Exception):
    """
    Base class for exceptions related to fields
    """
    pass


class MandatoryFieldInitError(FieldError):
    """
    Raised by `field` when a mandatory field is read without being set first.
    """
    __slots__ = 'field_name', 'obj'

    def __init__(self, field_name, obj):
        self.field_name = field_name
        self.obj = obj

    def __str__(self):
        return "Mandatory field '%s' has not been initialized yet on instance %s." % (self.field_name, self.obj)


class ReadOnlyFieldError(FieldError):
    """
    Raised by descriptor field when a read-only attribute is accessed for writing
    """
    __slots__ = 'field_name', 'obj'

    def __init__(self, field_name, obj):
        self.field_name = field_name
        self.obj = obj

    def __str__(self):
        return "Read-only field '%s' has already been initialized on instance %s and cannot be modified anymore." \
               % (self.field_name, self.obj)


class Symbols(Enum):
    """
    A few symbols used in `fields` for signatures

    note: we used to use the great `sentinel` package to create these symbols one by one, but since we have
    now quite a number of symbols, it seemed overkill to create one anonymous class for each.

    Still, I am not sure if this made a perf difference actually.
    """
    GUESS = 0
    UNKNOWN = 1
    EMPTY = 2  # type: Any
    USE_FACTORY = 3
    _unset = 4
    DELAYED = 5

    def __repr__(self):
        """ More compact representation for signatures readability"""
        return self.name


# GUESS = sentinel.create('guess')
GUESS = Symbols.GUESS

# UNKNOWN = sentinel.create('unknown')
UNKNOWN = Symbols.UNKNOWN

# EMPTY = sentinel.create('empty')
EMPTY = Symbols.EMPTY
DELAYED = Symbols.DELAYED

# USE_FACTORY = sentinel.create('use_factory')
USE_FACTORY = Symbols.USE_FACTORY

# _unset = sentinel.create('_unset')
_unset = Symbols._unset


if not PY36:
    # a thread-safe lock for the global instance counter
    from threading import Lock
    threadLock = Lock()


class Field(object):
    """
    Base class for fields
    """
    __slots__ = ('__weakref__', 'is_mandatory', 'default', 'is_default_factory', 'name', 'type_hint', 'nonable', 'doc',
                 'owner_cls', 'pending_validators', 'pending_converters')
    if not PY36:
        # we need to count the instances created, so as to be able to track their order in classes
        # indeed in python < 3.6, class members are not sorted by order of appearance.
        __slots__ += ('__fieldinstcount__', )
        __field_global_inst_counter__ = 0

    def __init__(self,
                 default=EMPTY,         # type: T
                 default_factory=None,  # type: Callable[[], T]
                 type_hint=EMPTY,       # type: Any
                 nonable=UNKNOWN,       # type: Union[bool, Symbols]
                 doc=None,              # type: str
                 name=None              # type: str
                 ):
        """See help(field) for details"""

        if not PY36:
            with threadLock:
                # remember the instance creation number, and increment the counter
                self.__fieldinstcount__ = Field.__field_global_inst_counter__
                Field.__field_global_inst_counter__ += 1

        # default
        if default_factory is not None:
            self.is_mandatory = False
            if default is not EMPTY:
                raise ValueError("Only one of `default` and `default_factory` should be provided")
            else:
                self.default = default_factory
                self.is_default_factory = True
        else:
            self.is_mandatory = default is EMPTY
            self.default = default
            self.is_default_factory = False

        # name
        self.name = name
        self.owner_cls = None

        # doc
        self.doc = dedent(doc) if doc is not None else None

        # type hints
        if type_hint is not EMPTY and type_hint is not None:
            self.type_hint = type_hint
        else:
            self.type_hint = EMPTY

        # nonable
        if nonable is GUESS:
            if self.default is None:
                self.nonable = True
            elif type_hint is not EMPTY and type_hint is not None:
                if is_pep484_nonable(type_hint):
                    self.nonable = True
                else:
                    self.nonable = UNKNOWN
            else:
                # set as unknown until type hint is set (in set_as_cls_member)
                self.nonable = UNKNOWN
        else:
            self.nonable = nonable

        # pending validators and converters
        self.pending_validators = None
        self.pending_converters = None

    def set_as_cls_member(self,
                          owner_cls,
                          name,
                          owner_cls_type_hints=None,
                          type_hint=None
                          ):
        """
        Updates a field with all information available concerning how it is attached to the class.

         - its owner class
         - the name under which it is known in that class
         - the type hints (python 3.6)

        In python 3.6+ this is called directly at class creation time through the `__set_name__` callback.

        In older python versions this is called whenever we have the opportunity :(, through `collect_fields`,
        `fix_fields` and `fix_field`. We currently use the following strategies in python 2 and 3.5-:

         - When users create a init method, `collect_fields` will be called when the init method is first accessed
         - When users GET a native field, or GET or SET a descriptor field, `fix_field` will be called.

        :param owner_cls:
        :param name:
        :param owner_cls_type_hints:
        :param type_hint: you can provide the type hint directly
        :return:
        """
        # set the owner class
        self.owner_cls = owner_cls

        if PY2 and isinstance(self, DescriptorField) and not issubclass(owner_cls, object):
            raise ValueError("descriptor fields can not be used on old-style classes under python 2.")

        # check if the name provided as argument differ from the one provided
        if self.name is not None:
            if self.name != name:
                raise ValueError("field name '%s' in class '%s' does not correspond to explicitly declared name '%s' "
                                 "in field constructor" % (name, owner_cls, self.name))
            # already set correctly
        else:
            # set it
            self.name = name

        # if not already manually overridden, get the type hints if there are some in the owner class annotations
        if self.type_hint is EMPTY or self.type_hint is DELAYED:
            # first reconciliate both ways to get the hint
            if owner_cls_type_hints is not None:
                if type_hint is not None:
                    raise ValueError("Provide either owner_cls_type_hints or type_hint, not both")
                type_hint = owner_cls_type_hints.get(name)

            # then use it
            if type_hint is not None:
                # only use type hint if not empty
                self.type_hint = type_hint
                # update the 'nonable' status - only if not already explicitly set.
                # note: if this is UNKNOWN, we already saw that self.default is not None. No need to check again.
                if self.nonable is UNKNOWN:
                    if is_pep484_nonable(type_hint):
                        self.nonable = True
                    else:
                        self.nonable = UNKNOWN

        # detect a validator or a converter on a native field
        if self.pending_validators is not None or self.pending_converters is not None:
            # create a descriptor field to replace this native field
            new_field = DescriptorField.create_from_field(self, validators=self.pending_validators,
                                                          converters=self.pending_converters)
            # register it on the class in place of self
            setattr(self.owner_cls, self.name, new_field)

        # detect classes with slots
        elif not isinstance(self, DescriptorField) and '__slots__' in vars(owner_cls) \
                and '__dict__' not in owner_cls.__slots__:
            # create a descriptor field to replace of this native field
            new_field = DescriptorField.create_from_field(self)
            # register it on the class in place of self
            setattr(owner_cls, name, new_field)

    def __set_name__(self,
                     owner,  # type: Type[Any]
                     name    # type: str
                     ):
        if owner is not None:
            # fill all the information about how it is attached to the class
            # resolve type hint strings and get "optional" type hint automatically
            # note: we need to pass an appropriate local namespace so that forward refs work.
            # this seems like a bug in `get_type_hints` ?
            try:
                cls_type_hints = get_type_hints(owner)
            except NameError:
                # probably an issue of forward reference, or PEP563 is activated. Delay checking for later
                self.set_as_cls_member(owner, name, type_hint=DELAYED)
            else:
                # nominal usage
                self.set_as_cls_member(owner, name, owner_cls_type_hints=cls_type_hints)

    @property
    def qualname(self):
        # type: (...) -> str

        if self.owner_cls is not None:
            try:
                owner_qualname = self.owner_cls.__qualname__
            except AttributeError:
                # python 2: no __qualname__
                owner_qualname = qualname(self.owner_cls)
        else:
            owner_qualname = "<unknown_cls>"

        return "%s.%s" % (owner_qualname, self.name)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__, self.qualname)

    def default_factory(self, f):
        """
        Decorator to register the decorated function as the default factory of a field. Any previously registered
        default factory will be overridden.

        The decorated function should accept a single argument `(obj/self)`, and should return a value to use as the
        default.

        >>> import sys, pytest
        >>> if sys.version_info < (3, 6): pytest.skip("doctest skipped for python < 3.6")
        ...
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

        """
        self.default = f
        self.is_default_factory = True
        self.is_mandatory = False
        return f

    def validator(self,
                  help_msg=None,     # type: str
                  failure_type=None  # type: Type[ValidationFailure]
                  ):
        """
        A decorator to add a validator to a field.

        >>> import sys, pytest
        >>> if sys.version_info < (3, 6): pytest.skip('skipped on python <3.6')
        ...
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

        The decorated function should have a signature of `(val)`, `(obj/self, val)`, or `(obj/self, field, val)`. It
        should return `True` or `None` in case of success.

        You can use several of these decorators on the same function so as to share implementation across multiple
        fields:

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

        :param help_msg:
        :param failure_type:
        :return:
        """
        if help_msg is not None and callable(help_msg) and failure_type is None:
            # used without parenthesis @<field>.validator:  validation_callable := help_msg
            self.add_validator(help_msg)
            return help_msg
        else:
            # used with parenthesis @<field>.validator(...): return a decorator
            def decorate_f(f):
                # create the validator definition
                if help_msg is None:
                    if failure_type is None:
                        validator = f
                    else:
                        validator = (f, failure_type)
                else:
                    if failure_type is None:
                        validator = (f, help_msg)
                    else:
                        validator = (f, help_msg, failure_type)
                self.add_validator(validator)
                return f

            return decorate_f

    def add_validator(self,
                      validator  # type: ValidatorDef
                      ):
        """
        Adds a validator to the set of validators on that field.
        This is the implementation for native fields

        :param validator:
        :return:
        """
        if self.owner_cls is not None:
            # create a descriptor field instead of this native field
            new_field = DescriptorField.create_from_field(self, validators=(validator, ))

            # register it on the class
            setattr(self.owner_cls, self.name, new_field)
        else:
            if not PY36:
                raise UnsupportedOnNativeFieldError(
                    "defining validators is not supported on native fields in python < 3.6."
                    " Please set `native=False` on field '%s' to enable this feature."
                    % (self,))

            # mark as pending
            if self.pending_validators is None:
                self.pending_validators = [validator]
            else:
                self.pending_validators.append(validator)

    def converter(self,
                  _decorated_fun=None,  # type: _NoneType
                  accepts=None,         # type: Union[ValidationFuncOrLambda, ValidType]
                  ):
        """
        A decorator to add a validator to a field.

        >>> import sys, pytest
        >>> if sys.version_info < (3, 6): pytest.skip('skipped on python <3.6')
        ...
        >>> class Foo(object):
        ...     m = field()
        ...     @m.converter
        ...     def m_from_anything(self, m_value):
        ...         return int(m_value)
        ...
        >>> o = Foo()
        >>> o.m = '0'
        >>> o.m
        0

        The decorated function should have a signature of `(val)`, `(obj/self, val)`, or `(obj/self, field, val)`. It
        should return a converted value in case of success.

        You can explicitly declare which values are accepted by the converter, by providing an `accepts` argument.
        It may either contain a `<validation_callable>`, an `<accepted_type>` or a wildcard (`'*'` or `None`). Passing
        a wildcard is equivalent to calling the decorator without parenthesis as seen above.
        WARNING: this argument needs to be provided as keyword for the converter to work properly.

        You can use several of these decorators on the same function so as to share implementation across multiple
        fields:

        >>> class Foo(object):
        ...     m = field(type_hint=int, check_type=True)
        ...     m2 = field(type_hint=int, check_type=True)
        ...
        ...     @m.converter(accepts=str)
        ...     @m2.converter
        ...     def from_anything(self, field, value):
        ...         print("converting a value for %s" % field.qualname)
        ...         return int(value)
        ...
        >>> o = Foo()
        >>> o.m2 = '12'
        converting a value for Foo.m2
        >>> o.m2 = 1.5
        converting a value for Foo.m2
        >>> o.m = 1.5  # doctest: +NORMALIZE_WHITESPACE
        Traceback (most recent call last):
        ...
        pyfields.typing_utils.FieldTypeError: Invalid value type provided for 'Foo.m'. Value should be of type
          <class 'int'>. Instead, received a 'float': 1.5

        :param _decorated_fun: internal, the decorated function. Do not fill this argument!
        :param accepts: a `<validation_callable>`, an `<accepted_type>` or a wildcard (`'*'` or `None`) defining on
            which values this converter will have a chance to succeed. Default is `None`.
        :return:
        """
        if accepts is None and _decorated_fun is not None:
            # used without parenthesis @<field>.converter:
            self.add_converter(_decorated_fun)
            return _decorated_fun
        else:
            # used with parenthesis @<field>.converter(...): return a decorator
            def decorate_f(f):
                # create the converter definition
                self.add_converter((accepts, f))
                return f

            return decorate_f

    def add_converter(self,
                      converter_def  # type: ConverterFuncDefinition
                      ):
        """
        Adds a converter to the set of converters on that field.
        This is the implementation for native fields.

        :param converter_def:
        :return:
        """
        if self.owner_cls is not None:
            # create a descriptor field instead of this native field
            new_field = DescriptorField.create_from_field(self, converters=(converter_def, ))

            # register it on the class as a replacement for this native field
            setattr(self.owner_cls, self.name, new_field)
        else:
            if not PY36:
                raise UnsupportedOnNativeFieldError(
                    "defining converters is not supported on native fields in python < 3.6."
                    " Please set `native=False` on field '%s' to enable this feature."
                    % (self,))

            # mark as pending
            if self.pending_converters is None:
                self.pending_converters = [converter_def]
            else:
                self.pending_converters.append(converter_def)

    def trace_convert(self, value, obj=None):
        # type: (...) -> Tuple[Any, DetailedConversionResults]
        """
        Can be used to debug conversion problems.
        Instead of just returning the converted value, it also returns conversion details.

        Note that this method does not set the field value, it simply returns the conversion results.
        In case no converter is able to convert the provided value, a `ConversionError` is raised.

        :param obj:
        :param value:
        :return: a tuple (converted_value, details).
        """
        raise UnsupportedOnNativeFieldError("Native fields do not have converters.")


def field(type_hint=None,        # type: Union[Type[T], Iterable[Type[T]]]
          nonable=GUESS,         # type: Union[bool, Type[GUESS]]
          check_type=False,      # type: bool
          default=EMPTY,         # type: T
          default_factory=None,  # type: Callable[[], T]
          validators=None,       # type: Validators
          converters=None,       # type: Converters
          read_only=False,       # type: bool
          doc=None,              # type: str
          name=None,             # type: str
          native=None            # type: bool
          ):
    # type: (...) -> Union[T, Field]
    """
    Returns a class-level attribute definition. It allows developers to define an attribute without writing an
    `__init__` method. Typically useful for mixin classes.

    Laziness
    --------
    The field will be lazily-defined, so if you create an instance of the class, the field will not have any value
    until it is first read or written.

    Optional/Mandatory
    ------------------
    By default fields are mandatory, which means that you must set them before reading them (otherwise a
    `MandatoryFieldInitError` will be raised). You can define an optional field by providing a `default` value.
    This value will not be copied but used "as is" on all instances, following python's classical pattern for default
    values. If you wish to run specific code to instantiate the default value, you may provide a `default_factory`
    callable instead. That callable should have no mandatory argument and should return the default value. Alternately
    you can use the `@<field>.default_factory` decorator.

    Read-only
    ---------
    TODO

    Typing
    ------
    Type hints for fields can be provided using the standard python typing mechanisms (type comments for python < 3.6
    and class member type hints for python >= 3.6). Types declared this way will not be checked at runtime, they are
    just hints for the IDE. You can also specify a `type_hint` explicitly to override the type hints gathered from the
    other means indicated above. It supports both a single type or an iterable of alternate types (e.g. `(int, str)`).
    The corresponding type hint is automatically declared by `field` so your IDE will know about it. Specifying a
    `type_hint` explicitly is mostly useful if you are running python < 3.6 and wish to use type validation, see below.

    By default `check_type` is `False`. This means that the above mentioned `type_hint` is just a hint. If you set
    `check_type=True` the type declared in the type hint will be validated, and a `FieldTypeError` will be raised if
    provided values are invalid. Important: if you are running python < 3.6 you have to set the type hint explicitly
    using `type_hint` if you wish to set `check_type=True`, otherwise you will get an exception. Indeed type comments
    can not be collected by the code.

    Type hints relying on the `typing` module (PEP484) are correctly checked using whatever 3d party type checking
    library is available (`typeguard` is first looked for, then `pytypes` as a fallback). If none of these providers
    are available, a fallback implementation is provided, basically flattening `Union`s and replacing `TypeVar`s before
    doing `is_instance`. It is not guaranteed to support all `typing` subtleties.

    Validation
    ----------
    TODO

    Nonable
    -------
    TODO
    see also: https://stackoverflow.com/a/57390124/7262247

    Conversion
    ----------
    TODO

    Documentation
    -------------
    A docstring can be provided for code readability.

    Example
    -------

    >>> import sys, pytest
    >>> if sys.version_info < (3, 6): pytest.skip('skipped on python <3.6')
    ...
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
    pyfields.typing_utils.FieldTypeError: Invalid value type ...

    Limitations
    -----------
    Old-style classes are not supported: in python 2, don't forget to inherit from `object`.

    Performance overhead
    --------------------
    `field` has two different ways to create your fields. One named `NativeField` is faster but does not permit type
    checking, validation, or converters; besides it does not work with classes using `__slots__`. It is used by default
    everytime where it is possible, except if you use one of the above mentioned features. In that case a
    `DescriptorField` will transparently be created. You can force a `DescriptorField` to be created by setting
    `native=False`.

    The `NativeField` class implements the "non-data" descriptor protocol. So the first time the attribute is read, a
    small python method call extra cost is paid. *But* afterwards the attribute is replaced with a native attribute
    inside the object `__dict__`, so subsequent calls use native access without overhead.
    This was inspired by
    [werkzeug's @cached_property](https://tedboy.github.io/flask/generated/generated/werkzeug.cached_property.html).

    Inspired by
    -----------
    This method was inspired by

     - @lazy_attribute (sagemath)
     - @cached_property (werkzeug) and https://stackoverflow.com/questions/24704147/python-what-is-a-lazy-property
     - https://stackoverflow.com/q/42023852/7262247
     - attrs / dataclasses

    :param type_hint: an optional explicit type hint for the field, to override the type hint defined by PEP484
        especially on old python versions because type comments can not be captured. Both a single type or an iterable
        of alternate types (e.g. `(int, str)`) are supported. By default the type hint is just a
        hint and does not contribute to validation. To enable type validation, set `check_type` to `True`.
    :param nonable: a boolean that can be used to explicitly declare that a field can contain `None`. When this is set
        to an explicit `True` or `False` value, usual type checking and validation (*if any*) are not anymore executed
        on `None` values. Instead ; if this is `True`, type checking and validation will be *deactivated* when the field
        is set to `None` so as to always accept the value. If this is `False`, an `None`error will be raised when `None`
        is set on the field.
        When this is left as `GUESS` (default), the behaviour is "automatic". This means that
         - if the field (a) is optional with default value `None` or (b) has type hint `typing.Optional[]`, the
           behaviour will be the same as with `nonable=True`.
         - otherwise, the value will be the same as `nonable=UNKNOWN` and no special behaviour is put in place. `None`
           values will be treated as any other value. This can be particularly handy if a field accepts `None` ONLY IF
           another field is set to a special value. This can be done in a custom validator.
    :param check_type: by default (`check_type=False`), the type of a field, provided using PEP484 type hints or
        an explicit `type_hint`, is not validated when you assign a new value to it. You can activate type validation
        by setting `check_type=True`. In that case the field will become a descriptor field.
    :param default: a default value for the field. Providing a `default` makes the field "optional". `default` value
        is not copied on new instances, if you wish a new copy to be created you should provide a `default_factory`
        instead. Only one of `default` or `default_factory` should be provided.
    :param default_factory: a factory that will be called (without arguments) to get the default value for that
        field, everytime one is needed. Providing a `default_factory` makes the field "optional". Only one of `default`
        or `default_factory` should be provided.
    :param validators: a validation function definition, sequence of validation function definitions, or dict-like of
        validation function definitions. See `valid8` "simple syntax" for details
    :param converters: a sequence of (<type_def>, <converter>) pairs or a dict-like of such pairs. `<type_def>` should
        either be a type, a tuple of types, or the '*' string indicating "any other case".
    :param read_only: a boolean (default `False`) stating if a field can be modified after initial value has been
        provided.
    :param doc: documentation for the field. This is mostly for class readability purposes for now.
    :param name: in python < 3.6 this is mandatory if you do not use any other decorator or constructor creation on the
        class (such as `make_init`). If provided, it should be the same name than the one used used in the class field
        definition (i.e. you should define the field as `<name> = field(name=<name>)`).
    :param native: a boolean that can be turned to `False` to force a field to be a descriptor field, or to `True` to
        force it to be a native field. Native fields are faster but can not support type and value validation
        nor conversions or callbacks. `None` (default) automatically sets `native=True` if no `validators` nor
        `check_type=True` nor `converters` are provided ; and `native=False` otherwise. In general you should not
        set this option manually except for experiments.
    :return:
    """
    # Should we create a Native or a Descriptor field ?
    if native is None:
        # default: choose automatically according to user-provided options
        create_descriptor = check_type or (validators is not None) or (converters is not None) or read_only
    else:
        # explicit user choice
        if native:
            # explicit `native=True`.
            if check_type or (validators is not None) or (converters is not None) or read_only:
                raise UnsupportedOnNativeFieldError("`native=False` can not be set "
                                                    "if a `validators` or `converters` is provided "
                                                    "or if `check_type` or `read_only` is `True`")
            else:
                create_descriptor = False
        else:
            # explicit `native=False`. Force-use a descriptor
            create_descriptor = True

    # Create the correct type of field
    if create_descriptor:
        return DescriptorField(type_hint=type_hint, nonable=nonable, default=default, default_factory=default_factory,
                               check_type=check_type, validators=validators, converters=converters,
                               read_only=read_only, doc=doc, name=name)
    else:
        return NativeField(type_hint=type_hint, nonable=nonable, default=default, default_factory=default_factory,
                           doc=doc, name=name)


class UnsupportedOnNativeFieldError(FieldError):
    """
    Exception raised whenever someone tries to perform an operation that is not supported on a "native" field.
    """
    pass


class ClassFieldAccessError(FieldError):
    """
    Error raised when you use <cls>.<field>. This is currently put in place because otherwise the
    type hints in pycharm get messed up. See below.
    """
    __slots__ = 'field',

    # noinspection PyShadowingNames
    def __init__(self, field):
        self.field = field

    def __str__(self):
        return "Accessing a `field` from the class is not yet supported. You can use %s.__dict__['%s'] as a " \
               "workaround. See https://github.com/smarie/python-pyfields/issues/12" \
               % (self.field.owner_cls.__name__, self.field.name)


class NativeField(Field):
    """
    A field that is replaced with a native python attribute on first read or write access.
    Faster but provides not much flexibility (no validator, no type check, no converter)
    """
    __slots__ = ()

    def __get__(self, obj, obj_type):
        # type: (...) -> T

        # do this first, because a field might be referenced from its class the first time it will be used
        # for example if in `make_init` we use a field defined in another class, that was not yet accessed on instance.
        if self.name is None or self.type_hint is DELAYED:
            # __set_name__ was not called yet. lazy-fix the name and type hints
            fix_field(obj_type, self)

        if obj is None:
            # class-level call: https://youtrack.jetbrains.com/issue/PY-38151 is solved, we can now return self
            return self

        # Check if the field is already set in the object __dict__
        value = obj.__dict__.get(self.name, _unset)

        if value is _unset:
            # mandatory field: raise an error
            if self.is_mandatory:
                raise MandatoryFieldInitError(self.name, obj)

            # optional: get default
            if self.is_default_factory:
                value = self.default(obj)
            else:
                value = self.default

            # nominal initialization on first read: we set the attribute in the object __dict__
            # so that next reads will be pure native field access
            obj.__dict__[self.name] = value

        # else:
            # this was probably a manual call of __get__ (or a concurrent call of the first access)

        return value

    # not needed apparently
    # def __delete__(self, obj):
    #     try:
    #         del obj.__dict__[self.name]
    #     except KeyError:
    #         # silently ignore: the field has not been set on that object yet,
    #         # and we wont delete the class `field` anyway...
    #         pass


class NoneError(TypeError, ValueError, FieldError):
    """
    Error raised when `None` is set on an explicitly not-nonable field. It is both a `TypeError` and a `ValueError`.
    """
    __slots__ = ('field', )

    def __init__(self, field):
        super(NoneError, self).__init__()
        self.field = field

    def __str__(self):
        return "Received invalid value `None` for '%s'. This field is explicitely declared as non-nonable."\
               % (self.field.qualname, )


# default value policies
_NO = None
_NO_BUT_CAN_CACHE_FIRST_RESULT = False
_YES = True


class DescriptorField(Field):
    """
    General-purpose implementation for fields that require type-checking or validation or converter
    """
    __slots__ = 'root_validator', 'check_type', 'converters', 'read_only', '_default_is_safe'

    @classmethod
    def create_from_field(cls,
                          other_field,      # type: Field
                          validators=None,  # type: Iterable[ValidatorDef]
                          converters=None   # type: Iterable[ConverterFuncDefinition]
                          ):
        # type: (...) -> DescriptorField
        """
        Creates a descriptor field by copying the information from the given other field, typically a native field

        :param other_field:
        :param validators: validators to add to the field definition
        :param converters: converters to add to the field definition
        :return:
        """
        if other_field.is_default_factory:
            default = EMPTY
            default_factory = other_field.default
        else:
            default_factory = None
            default = other_field.default

        new_field = DescriptorField(type_hint=other_field.type_hint, default=default, default_factory=default_factory,
                                    doc=other_field.doc, name=other_field.name, validators=validators,
                                    converters=converters)

        # copy the owner class info too
        new_field.owner_cls = other_field.owner_cls
        return new_field

    def __init__(self,
                 type_hint=None,        # type: Type[T]
                 nonable=UNKNOWN,       # type: Union[bool, Symbols]
                 default=EMPTY,         # type: T
                 default_factory=None,  # type: Callable[[], T]
                 check_type=False,      # type: bool
                 validators=None,       # type: Validators
                 converters=None,       # type: Converters
                 read_only=False,       # type: bool
                 doc=None,              # type: str
                 name=None              # type: str
                 ):
        """See help(field) for details"""
        super(DescriptorField, self).__init__(type_hint=type_hint, nonable=nonable,
                                              default=default, default_factory=default_factory, doc=doc, name=name)

        # type validation
        self.check_type = check_type

        # validators
        if validators is not None:
            self.root_validator = FieldValidator(self, validators)
        else:
            self.root_validator = None

        # converters
        if converters is not None:
            self.converters = list(make_converters_list(converters))
        else:
            self.converters = None

        # read-only
        self.read_only = read_only

        # self._default_is_safe is used to know if we should validate/convert the default value before use
        #  - None means "always". This is the case when there is a default factory we can't modify
        #  - False means "once", and then True means "not anymore" (after first validation). This is the case
        #    when we can modify the default value so that we can replace it with the possibly converted one
        if default is not EMPTY:
            # a fixed default value is here, we'll validate it once and for all
            self._default_is_safe = _NO_BUT_CAN_CACHE_FIRST_RESULT
        elif default_factory is not None:
            # noinspection PyBroadException
            try:
                # is this the `copy_value` factory ?
                default_factory.clone_with_new_val
            except Exception:
                # No: the factory can be anything else
                self._default_is_safe = _NO
            else:
                # Yes: we can replace the value that it uses on first
                self._default_is_safe = _NO_BUT_CAN_CACHE_FIRST_RESULT
        else:
            # no default at all
            self._default_is_safe = _NO

    def add_validator(self,
                      validator  # type: ValidatorDef
                      ):
        """
        Add a validation function to the set of validation functions.

        :param validator:
        :return:
        """
        if self.root_validator is None:
            self.root_validator = FieldValidator(self, validator)
        else:
            self.root_validator.add_validator(validator)

    def add_converter(self,
                      converter_def  # type: ConverterFuncDefinition
                      ):
        converters = make_converters_list(converter_def)
        if self.converters is None:
            # use the new list
            self.converters = list(converters)
        else:
            # concatenate the lists
            self.converters += converters

    def __get__(self, obj, obj_type):
        # type: (...) -> T

        # do this first, because a field might be referenced from its class the first time it will be used
        # for example if in `make_init` we use a field defined in another class, that was not yet accessed on instance.
        if self.name is None or self.type_hint is DELAYED:
            # __set_name__ was not called yet. lazy-fix the name and type hints
            fix_field(obj_type, self)

        if obj is None:
            # class-level call: https://youtrack.jetbrains.com/issue/PY-38151 is solved, we can now return self
            return self

        private_name = '_' + self.name

        # Check if the field is already set in the object
        value = getattr(obj, private_name, _unset)

        if value is _unset:
            # mandatory field: raise an error
            if self.is_mandatory:
                raise MandatoryFieldInitError(self.name, obj)

            # optional: get default
            if self.is_default_factory:
                value = self.default(obj)
            else:
                value = self.default

            # nominal initialization on first read: we set the attribute in the object
            if self._default_is_safe is _YES:
                # no need to validate/convert the default value, fast track (use the private name directly)
                setattr(obj, private_name, value)
            else:
                # we need conversion and validation - go through the setter (same as using the public name)
                possibly_converted_value = self.__set__(obj, value, _return=True)

                if self._default_is_safe is _NO_BUT_CAN_CACHE_FIRST_RESULT:
                    # there is a possibility to remember the new default and skip this next time

                    # If there was a conversion, use the converted value as the new default
                    if possibly_converted_value is not value:
                        if self.is_default_factory:
                            # Modify the `copy_value` factory
                            self.default = self.default.clone_with_new_val(possibly_converted_value)
                        else:
                            # Modify the value
                            self.default = possibly_converted_value
                    # else:
                    #     # no conversion: we can continue to use the same default value, it is valid
                    #     pass

                    # mark the default as safe now, so that this is skipped next time
                    self._default_is_safe = _YES

                return possibly_converted_value

        return value

    def trace_convert(self, value, obj=None):
        """Overrides the method in `Field` to provide a valid implementation."""
        return trace_convert(field=self, value=value, obj=obj)

    def __set__(self,
                obj,
                value,         # type: T
                _return=False  # type: bool
                ):

        # do this first, because a field might be referenced from its class the first time it will be used
        # for example if in `make_init` we use a field defined in another class, that was not yet accessed on instance.
        if self.name is None or self.type_hint is DELAYED:
            # __set_name__ was not called yet. lazy-fix the name and type hints
            fix_field(obj.__class__, self)

        # if obj is None:
        #     # class-level call: this never happens
        #     # https://youtrack.jetbrains.com/issue/PY-38151 is solved, but what do we wish to do here actually ?
        #     raise ClassFieldAccessError(self)

        if self.converters is not None:
            # this is an inlined version of `trace_convert` with no capture of details
            for converter in self.converters:
                # noinspection PyBroadException
                try:
                    # does the converter accept this input ?
                    accepted = converter.accepts(obj, self, value)
                except Exception:  # noqa
                    # ignore all exceptions from converters
                    continue
                else:
                    if accepted is None or accepted:
                        # if so, let's try to convert
                        try:
                            converted_value = converter.convert(obj, self, value)
                        except Exception:  # noqa
                            # ignore all exceptions from converters
                            continue
                        else:
                            # successful conversion: use the converted value
                            value = converted_value
                            break
                    else:
                        continue

        # speedup for vars used several time
        t = self.type_hint
        nonable = self.nonable
        private_name = "_" + self.name

        # read-only check
        if self.read_only:
            # Check if the field is already set in the object
            _v = getattr(obj, private_name, _unset)
            if _v is not _unset:
                raise ReadOnlyFieldError(self.qualname, obj)

        # type checker and validators
        if value is not None or nonable is UNKNOWN:
            # check the type
            if self.check_type:
                if t is EMPTY:
                    raise ValueError("`check_type` is enabled on field '%s' but no type hint is available. Please "
                                     "provide type hints or set `field.check_type` to `False`. Note that python code is"
                                     " not able to read type comments so if you wish to be compliant with python < 3.6 "
                                     "you'll have to set the type hint explicitly in `field.type_hint` instead")

                if USE_ADVANCED_TYPE_CHECKER:
                    # take into account all the subtleties from `typing` module by relying on 3d party providers.
                    assert_is_of_type(self, value, t)

                elif not isinstance(value, t):
                    raise FieldTypeError(self, value, t)

            # run the validators
            if self.root_validator is not None:
                self.root_validator.assert_valid(obj, value)

        elif not nonable:
            # value is None and field is not nonable: raise an error
            # note: the root validator might not even exist, so do not reuse valid8 none rejecter here
            raise NoneError(self)
        # else:
        #     # value is None and field is nonable: nothing to do
        #     pass

        # set the new value
        setattr(obj, private_name, value)

        # return it for the callers that need it
        if _return:
            return value

    def __delete__(self, obj):
        # private_name = "_" + self.name
        delattr(obj, "_" + self.name)


# noinspection PyShadowingNames
def fix_field(cls,                     # type: Type[Any]
              field,                   # type: Field
              include_inherited=True,  # type: bool
              fix_type_hints=PY36      # type: bool
              ):
    """
    Fixes the given field name and type hint on the given class

    :param cls:
    :param field:
    :param include_inherited: should the field be looked for in parent classes following the mro. Default = True
    :param fix_type_hints:
    :return:
    """
    if fix_type_hints:
        cls_type_hints = get_type_hints(cls)
    else:
        cls_type_hints = None

    where_cls = getmro(cls) if include_inherited else (cls, )

    found = False
    for _cls in where_cls:
        for member_name, member in vars(_cls).items():
            # if not member_name.startswith('__'):   not stated in the doc: too dangerous to have such implicit filter
            if member is field:
                # do the same than in __set_name__
                field.set_as_cls_member(_cls, member_name, owner_cls_type_hints=cls_type_hints)
                # found: no need to look further
                found = True
                break
        if found:
            break
    else:
        raise ValueError("field %s was not found on class %s%s"
                         % (field, cls, 'or its ancestors' if include_inherited else ''))
