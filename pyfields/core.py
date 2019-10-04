#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

import sys
from textwrap import dedent

from inspect import getmro

from valid8.utils.signature_tools import IsBuiltInError

try:
    from inspect import signature, Parameter
except ImportError:
    from funcsigs import signature, Parameter

from makefun import with_signature
import sentinel

from valid8 import Validator, failure_raiser, ValidationError
from valid8.base import getfullargspec as v8_getfullargspec, get_callable_name, is_mini_lambda
from valid8.common_syntax import FunctionDefinitionError

try:  # python 3.5+
    from typing import Optional, Set, List, Callable, Dict, Type, Any, TypeVar, Union, Iterable, Tuple, Mapping
    from valid8.common_syntax import ValidationFuncs
    use_type_hints = sys.version_info > (3, 0)
except ImportError:
    use_type_hints = False


PY36 = sys.version_info >= (3, 6)
if PY36:
    try:
        from typing import get_type_hints
    except ImportError:
        pass


# PY35 = sys.version_info >= (3, 5)
# if PY35:
#     KEYWORD_ONLY_IF_POSSIBLE = Parameter.KEYWORD_ONLY
# else:
#     KEYWORD_ONLY_IF_POSSIBLE = Parameter.POSITIONAL_OR_KEYWORD

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


class MandatoryFieldInitError(Exception):
    """
    Raised by `field` when a mandatory field is read without being set first.
    """
    __slots__ = 'field_name', 'obj'

    def __init__(self, field_name, obj):
        self.field_name = field_name
        self.obj= obj

    def __str__(self):
        return "Mandatory field '%s' has not been initialized yet on instance %s." % (self.field_name, self.obj)


# a few symbols used in `fields`
EMPTY = sentinel.create('empty')
USE_FACTORY = sentinel.create('use_factory')
_unset = sentinel.create('_unset')
if use_type_hints:
    T = TypeVar('T')
    ValidationFunc = Union[Callable[[Any], Any],
                           Callable[[Any, Any], Any],
                           Callable[[Any, Any, Any], Any]
                           ]
    """A validation function is a callable with signature (val), (obj, val) or (obj, field, val), returning `True` 
    or `None` in case of success"""

    ValidatorDef = Union[ValidationFunc,
                         Tuple[ValidationFunc, str],
                         Tuple[ValidationFunc, Type[Exception]],
                         Tuple[ValidationFunc, str, Type[Exception]]
                     ]
    """A validator is a validation function together with optional error message and error type"""

    ValidatorDefinitionElement = Union[str, Type[Exception], ValidationFunc]
    """One of the elements that can define a validator"""

    Validators = Union[ValidatorDef, Iterable[ValidatorDef],
                       Mapping[ValidatorDefinitionElement,
                               Union[ValidatorDefinitionElement,
                                     Tuple[ValidatorDefinitionElement, ...]
                      ]]]
    """Several validators can be provided as a singleton, iterable, or dict-like. In that case the value can be a 
    single variable or a tuple, and it will be combined with the key to form the validator. So you can use any of the 
    elements defining a validators as the key."""
    # TODO we could reuse valid8's type hints... when they accept to be parametrized with the callables signatures


class Field(object):
    """
    Base class for fields
    """
    __slots__ = '__weakref__', 'is_mandatory', 'default', 'is_default_factory', 'name', 'type_hint', 'doc', 'owner_cls'

    def __init__(self,
                 default=EMPTY,         # type: T
                 default_factory=None,  # type: Callable[[], T]
                 type_hint=EMPTY,       # type: Any
                 doc=None,              # type: str
                 name=None              # type: str
                 ):
        """See help(field) for details"""

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

    def set_as_cls_member(self,
                          owner_cls,
                          name,
                          owner_cls_type_hints
                          ):
        """
        Used in __set_name__ and in `collect_fields` and `fix_field[s]` to update a field with all information
        available concerning how it is attached to the class.

         - its owner class
         - the name under which it is known in that class
         - the type hints (python 3.6)

        :param owner_cls:
        :param name:
        :param owner_cls_type_hints:
        :return:
        """
        # set the owner class
        self.owner_cls = owner_cls

        # check if the name provided as argument differ from the one provided
        if self.name is not None:
            if self.name != name:
                raise ValueError("field name '%s' in class '%s' does not correspond to explicitly declared name '%s' "
                                 "in field constructor" % (name, owner_cls, self.name))
            # already set correctly
        else:
            # set it
            self.name = name

        if owner_cls_type_hints is not None:
            t = owner_cls_type_hints.get(name)
            if t is not None and self.type_hint is EMPTY:
                # only use type hint if not manually overridden
                self.type_hint = t

    def __set_name__(self,
                     owner,  # type: Type[Any]
                     name    # type: str
                     ):
        if owner is not None:
            # fill all the information about how it is attached to the class
            cls_type_hints = get_type_hints(owner)
            self.set_as_cls_member(owner, name, cls_type_hints)

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
        decorator to register the decorated function as the default factory of a field.
        any previously registered default factory will be overridden
        :return:
        """
        self.default = f
        self.is_default_factory = True
        self.is_mandatory = False
        return f


def field(type_hint=None,        # type: Type[T]
          check_type=False,      # type: bool
          default=EMPTY,         # type: T
          default_factory=None,  # type: Callable[[], T]
          validators=None,       # type: Validators
          doc=None,              # type: str
          name=None,             # type: str
          native=None            # type: bool
          ):
    # type: (...) -> Union[T, Field]
    """
    Returns a class-level attribute definition. It allows developers to define an attribute without writing an
    `__init__` method. Typically useful for mixin classes.

    Lazyness
    --------
    The field will be lazily-defined, so if you create an instance of the class, the field will not have any value
    until it is first read or written.

    Optional/Mandatory
    ------------------
    By default fields are mandatory, which means that you must set them before reading them (otherwise a
    `MandatoryFieldInitError` will be raised). You can define an optional field by providing a `default` value.
    This value will not be copied but used "as is" on all instances, following python's classical pattern for default
    values. If you wish to run specific code to instantiate the default value, you may provide a `default_factory`
    callable instead. That callable should have no mandatory argument and should return the default value.

    Typing
    ------
    Type hints for fields can be provided using the standard python typing mechanisms (type comments for python < 3.6
    and class member type hints for python >= 3.6). Types declared this way will not be checked at runtime, they are
    just hints for the IDE. You can also specify a `type_hint` explicitly to override the type hints gathered from the
    other means indicated above. The corresponding type hint is automatically declared by `field` so your IDE will know
    about it. Specifying a `type_hint` explicitly is mostly useful if you are running python < 3.6 and wish to use type
    validation, see below.

    By default `check_type` is `False`. This means that the abovementioned `type_hint` is just a hint. If you set
    `check_type=True` the type declared in the type hint will be validated, and a `TypeError` will be raised if
    provided values are invalid. Important: if you are running python < 3.6 you have to set the type hint explicitly
    using `type_hint` if you wish to set `check_type=True`, otherwise you will get an exception. Indeed type comments
    can not be collected by the code.

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
    TypeError: Invalid value type ...

    Limitations
    -----------
    Old-style classes are not supported: in python 2, don't forget to inherit from `object`.

    Performance overhead
    --------------------
    `field` has two different ways to create your fields. One named `NativeField` is faster but does not permit type
    checking, validation, or converters; besides it does not work with classes using `__slots__`. It is used by default
    everytime where it is possible, except if you use one of the abovementioned features. In that case a
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
     - https://stackoverflow.com/questions/42023852/how-can-i-get-the-attribute-name-when-working-with-descriptor-protocol-in-python
     - attrs / dataclasses

    :param type_hint: an optional explicit type hint for the field, to override the type hint defined by PEP484
        especially on old python versions because type comments can not be captured. By default the type hint is just a
        hint and does not contribute to validation. To enable type validation, set `check_type` to `True`.
    :param check_type: by default (`check_type=False`), the type of a field, provided using PEP484 type hints or
        an explicit `type_hint`, is not validated when you assign a new value to it. You can activate type validation
        by setting `check_type=True`. In that case the field will become a descriptor field.
    :param default: a default value for the field. Providing a `default` makes the field "optional". `default` value
        is not copied on new instances, if you wish a new copy to be created you should provide a `default_factory`
        instead. Only one of `default` or `default_factory` should be provided.
    :param default_factory: a factory that will be called (without arguments) to get the default value for that
        field, everytime one is needed. Providing a `default_factory` makes the field "optional". Only one of `default`
        or `default_factory` should be provided.
    :param validators: a validation function definition, sequence of validation function definitions, or dictionary of
        validation function definitions. See `valid8` "simple syntax" for details
    :param doc: documentation for the field. This is mostly for class readability purposes for now.
    :param name: in python < 3.6 this is mandatory if you do not use any other decorator on the class (such as
        `@inject_fields`). If provided, it should be the same name than the one used used in the class field definition
        (i.e. you should define the field as '<name> = field(name=<name>)').
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
        create_descriptor = check_type or (validators is not None)  # todo or converters is not None
    else:
        # explicit user choice
        if native:
            # explicit `native=True`.
            if check_type or (validators is not None):    # todo or converters is not None
                raise UnsupportedOnNativeFieldError("`native=False` can not be set if a `validators` or "
                                                    "`converters` is provided or if `check_type` is `True`")
            else:
                create_descriptor = False
        else:
            # explicit `native=False`. Force-use a descriptor
            create_descriptor = True

    # Create the correct type of field
    if create_descriptor:
        return DescriptorField(type_hint=type_hint, default=default, default_factory=default_factory,
                               check_type=check_type, validators=validators, doc=doc, name=name)
    else:
        return NativeField(type_hint=type_hint, default=default, default_factory=default_factory,
                           doc=doc, name=name)


class UnsupportedOnNativeFieldError(Exception):
    """
    Exception raised whenever someone tries to perform an operation that is not supported on a "native" field.
    """
    pass


class ClassFieldAccessError(Exception):
    """
    Error raised when you use <cls>.<field>. This is currently put in place because otherwise the
    type hints in pycharm get messed up. See below.
    """
    __slots__ = 'field',

    def __init__(self, field):
        self.field = field

    def __str__(self):
        return "Accessing a `field` from the class is not yet supported. " \
               "See https://github.com/smarie/python-pyfields/issues/12"


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
        if not PY36 and self.name is None:
            # __set_name__ was not called yet. lazy-fix the name and type hints
            fix_field(obj_type, self)

        if obj is None:
            # class-level call ?
            # TODO put back when https://youtrack.jetbrains.com/issue/PY-38151 is solved
            # return self
            # even this does not work
            # exec("o = self", globals(), locals())
            # return locals()['o']
            raise ClassFieldAccessError(self)

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

    def validator(self):
        raise UnsupportedOnNativeFieldError("defining validators is not supported on native fields. Please set "
                                            "`native=True` on field '%s' to enable this feature."
                                            % (self.name,))


# Python 3+: load the 'more explicit api'
if use_type_hints:
    new_sig = """(self,
                  validated_field: 'DescriptorField',
                  *validation_func: ValidationFuncs,
                  error_type: 'Type[ValidationError]' = None,
                  help_msg: str = None,
                  none_policy: int = None,
                  **kw_context_args):"""
else:
    new_sig = None


class FieldValidator(Validator):
    """
    Represents a `Validator` responsible to validate a `field`
    """
    __slots__ = '__weakref__', 'validated_field'

    @with_signature(new_sig)
    def __init__(self,
                 validated_field,   # type: DescriptorField
                 *args,
                 **kwargs
                 ):
        """

        :param validated_field: the field being validated.
        :param validation_func: the base validation function or list of base validation functions to use. A callable, a
            tuple(callable, help_msg_str), a tuple(callable, failure_type), tuple(callable, help_msg_str, failure_type)
            or a list of several such elements.
            Tuples indicate an implicit `failure_raiser`.
            [mini_lambda](https://smarie.github.io/python-mini-lambda/) expressions can be used instead
            of callables, they will be transformed to functions automatically.
        :param error_type: a subclass of ValidationError to raise in case of validation failure. By default a
            ValidationError will be raised with the provided help_msg
        :param help_msg: an optional help message to be used in the raised error in case of validation failure.
        :param none_policy: describes how None values should be handled. See `NonePolicy` for the various possibilities.
            Default is `NonePolicy.VALIDATE`, meaning that None values will be treated exactly like other values and follow
            the same validation process.
        :param kw_context_args: optional contextual information to store in the exception, and that may be also used
            to format the help message
        """
        # store this additional info about the function been validated
        self.validated_field = validated_field
        super(FieldValidator, self).__init__(*args, **kwargs)

    def get_callables_creator(self):
        def make_validator_callable(validation_callable,  # type: ValidationCallableOrLambda
                                    help_msg=None,        # type: str
                                    failure_type=None,    # type: Type[Failure]
                                    **kw_context_args):
            """

            :param validation_callable:
            :param help_msg: custom help message for failures to raise
            :param failure_type: type of failures to raise
            :param kw_context_args: contextual arguments for failures to raise
            :return:
            """
            if is_mini_lambda(validation_callable):
                validation_callable = validation_callable.as_function()

            # support several cases for the validation function signature
            # `f(val)`, `f(obj, val)` or `f(obj, field, val)`
            # the validation function has two or three (or more but optional) arguments.
            # valid8 requires only 1.
            try:
                args, varargs, varkwargs, defaults = v8_getfullargspec(validation_callable, skip_bound_arg=True)[0:4]

                nb_args = len(args) if args is not None else 0
                nbvarargs = 1 if varargs is not None else 0
                # nbkwargs = 1 if varkwargs is not None else 0
                # nbdefaults = len(defaults) if defaults is not None else 0
            except IsBuiltInError:
                # built-ins: TypeError: <built-in function isinstance> is not a Python function
                # assume signature with a single positional argument
                nb_args = 1
                nbvarargs = 0
                # nbkwargs = 0
                # nbdefaults = 0

            if nb_args == 0 and nbvarargs == 0:
                raise ValueError(
                    "validation function should accept 1, 2, or 3 arguments at least. `f(val)`, `f(obj, val)` or "
                    "`f(obj, field, val)`")
            elif nb_args == 1 or (nb_args == 0 and nbvarargs >= 1):  # varargs default to one argument (compliance with old mini lambda)
                # `f(val)`
                def new_validation_callable(val, **ctx):
                    return validation_callable(val)
            elif nb_args == 2:
                # `f(obj, val)`
                def new_validation_callable(val, **ctx):
                    return validation_callable(ctx['obj'], val)
            else:
                # `f(obj, field, val, *opt_args, **ctx)`
                def new_validation_callable(val, **ctx):
                    # note: field is available both from **ctx and self. Use the "fastest" way
                    return validation_callable(ctx['obj'], self.validated_field, val)

            # preserve the name
            new_validation_callable.__name__ = get_callable_name(validation_callable)

            return failure_raiser(new_validation_callable, help_msg=help_msg, failure_type=failure_type,
                                  **kw_context_args)

        return make_validator_callable

    def get_additional_info_for_repr(self):
        return 'validated_field=%s' % self.validated_field.qualname

    def _get_name_for_errors(self,
                             name  # type: str
                             ):
        """ override this so that qualname is only called if an error is raised, not before """
        return self.validated_field.qualname

    def assert_valid(self,
                     obj,              # type: Any
                     value,            # type: Any
                     error_type=None,  # type: Type[ValidationError]
                     help_msg=None,    # type: str
                     **ctx):
        # do not use qualname here so as to save time.
        super(FieldValidator, self).assert_valid(self.validated_field.name, value,
                                                 error_type=error_type, help_msg=help_msg,
                                                 # context info contains obj and field
                                                 obj=obj, field=self.validated_field, **ctx)


class DescriptorField(Field):
    """
    General-purpose implementation for fields that require type-checking or validation or converter
    """
    __slots__ = 'validator', 'check_type'

    def __init__(self,
                 type_hint=None,        # type: Type[T]
                 default=EMPTY,         # type: T
                 default_factory=None,  # type: Callable[[], T]
                 check_type=False,   # type: bool
                 validators=None,       # type: Validators
                 doc=None,              # type: str
                 name=None              # type: str
                 ):
        """See help(field) for details"""
        super(DescriptorField, self).__init__(type_hint=type_hint, default=default, default_factory=default_factory,
                                              doc=doc, name=name)

        # type validation
        self.check_type = check_type

        # validators
        if validators is not None:
            try:  # dict ?
                validators.keys()
            except (AttributeError, FunctionDefinitionError):
                if isinstance(validators, tuple):
                    # single tuple
                    validators = (validators, )
                else:
                    try:  # iterable
                        iter(validators)
                    except (TypeError, FunctionDefinitionError):
                        # single
                        validators = (validators, )
            else:
                # dict
                validators = (validators,)
            self.validator = FieldValidator(self, *validators)
        else:
            self.validator = None

    def __get__(self, obj, obj_type):
        # type: (...) -> T

        # do this first, because a field might be referenced from its class the first time it will be used
        # for example if in `make_init` we use a field defined in another class, that was not yet accessed on instance.
        if not PY36 and self.name is None:
            # __set_name__ was not called yet. lazy-fix the name and type hints
            fix_field(obj_type, self)

        if obj is None:
            # class-level call ?
            # TODO put back when https://youtrack.jetbrains.com/issue/PY-38151 is solved
            # return self
            raise ClassFieldAccessError(self)

        privatename = '_' + self.name

        # Check if the field is already set in the object
        value = getattr(obj, privatename, _unset)

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
            setattr(obj, privatename, value)

        return value

    def __set__(self,
                obj,
                value  # type: T
                ):

        # do this first, because a field might be referenced from its class the first time it will be used
        # for example if in `make_init` we use a field defined in another class, that was not yet accessed on instance.
        if not PY36 and self.name is None:
            # __set_name__ was not called yet. lazy-fix the name and type hints
            fix_field(obj.__class__, self)

        if obj is None:
            # class-level call ?
            # TODO put back when https://youtrack.jetbrains.com/issue/PY-38151 is solved
            # return self
            raise ClassFieldAccessError(self)

        # speedup for vars used several time
        t = self.type_hint
        privatename = "_" + self.name

        # check the type
        if self.check_type:
            if t is EMPTY:
                raise ValueError("`check_type` is enabled on field '%s' but no type hint is available. Please provide"
                                 "type hints or set `field.check_type` to `False`. Note that python code is not able to"
                                 " read type comments so if you wish to be compliant with python < 3.6 you'll have to"
                                 "set the type hint explicitly in `field.type_hint` instead")

            # TODO anything specific rather than `isinstance` to do when 'typing' type hints are used ?
            if not isinstance(value, t):
                # representing the object might fail, protect ourselves
                # noinspection PyBroadException
                try:
                    val_repr = repr(value)
                except Exception as e:
                    val_repr = "<error while trying to represent object: %s>" % e

                raise TypeError("Invalid value type provided for '%s.%s'. "
                                "Value should be of type '%s'. "
                                "Instead, received a '%s': %s"
                                % (obj.__class__.__name__, privatename[1:],
                                   t.__name__, value.__class__.__name__, val_repr))

        # run the validators
        if self.validator is not None:
            self.validator.assert_valid(obj, value)

        # set the new value
        setattr(obj, privatename, value)

    def __delete__(self, obj):
        # privatename = "_" + self.name
        delattr(obj, "_" + self.name)


def collect_all_fields(cls,
                       include_inherited=True,
                       auto_fix_fields=False
                       ):
    """
    Utility method to collect all fields defined in a class, including all inherited or not.
    If `auto_set_names` is set to True, all field names will be updated. This can be convenient under python 3.5-
    where the `__setname__` callback did not exist.

    :param cls:
    :param auto_fix_fields:
    :param include_inherited:
    :return: a list of fields
    """
    result = []
    if include_inherited:
        where = ordereddir(cls)
    else:
        where = vars(cls)

    if auto_fix_fields and PY36:
        cls_type_hints = get_type_hints(cls)
    else:
        cls_type_hints = None

    for member_name in where:
        if not member_name.startswith('__'):
            try:
                member = getattr(cls, member_name)
                if isinstance(member, Field):
                    if auto_fix_fields:
                        # take this opportunity to set the name and type hints
                        member.set_as_cls_member(cls, member_name, cls_type_hints)
                    result.append(member)
            except ClassFieldAccessError as e:
                # we know it is a field :)
                if auto_fix_fields:
                    # take this opportunity to set the name
                    e.field.set_as_cls_member(cls, member_name, cls_type_hints)
                result.append(e.field)

    return result


def ordereddir(cls):
    """
    since `dir` does not preserve order, lets have our own implementation

    :param cls:
    :return:
    """
    for parent in getmro(cls):
        for k in vars(parent):
            yield k


def fix_fields(cls,                 # type: Type[Any]
               fix_type_hints=PY36  # type: bool
               ):
    """
    Fixes all field names and type hints at once on the given class

    :param cls:
    :param fix_type_hints:
    :return:
    """
    if fix_type_hints:
        cls_type_hints = get_type_hints(cls)
    else:
        cls_type_hints = None

    for member_name, member in vars(cls).items():
        if not member_name.startswith('__'):
            try:
                member = getattr(cls, member_name)
                if isinstance(member, Field):
                    # do the same than in __set_name__
                    member.set_as_cls_member(cls, member_name, cls_type_hints)

            except ClassFieldAccessError as e:
                e.field.name = member_name


def fix_field(cls,                 # type: Type[Any]
              field,               # type: Field
              fix_type_hints=PY36  # type: bool
              ):
    """
    Fixes the given field name and type hint on the given class

    :param cls:
    :param field:
    :param fix_type_hints:
    :return:
    """
    if fix_type_hints:
        cls_type_hints = get_type_hints(cls)
    else:
        cls_type_hints = None

    for member_name, member in vars(cls).items():
        if not member_name.startswith('__'):
            if member is field:
                # do the same than in __set_name__
                field.set_as_cls_member(cls, member_name, cls_type_hints)
                # found: no need to look further
                break


def pop_kwargs(kwargs,
               names_with_defaults,  # type: List[Tuple[str, Any]]
               allow_others=False
               ):
    """
    Internal utility method to extract optional arguments from kwargs.

    :param kwargs:
    :param names_with_defaults:
    :param allow_others: if False (default) then an error will be raised if kwargs still contains something at the end.
    :return:
    """
    all_arguments = []
    for name, default_ in names_with_defaults:
        try:
            val = kwargs.pop(name)
        except KeyError:
            val = default_
        all_arguments.append(val)

    if not allow_others and len(kwargs) > 0:
        raise ValueError("Unsupported arguments: %s" % kwargs)

    if len(names_with_defaults) == 1:
        return all_arguments[0]
    else:
        return all_arguments
