#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

import sys
from textwrap import dedent

from makefun import with_signature
import sentinel

from valid8 import Validator, failure_raiser
from valid8.base import getfullargspec as v8_getfullargspec, get_callable_name
from valid8.common_syntax import FunctionDefinitionError

try:  # python 3.5+
    from typing import Optional, Set, List, Callable, Dict, Type, Any, TypeVar, Union, Iterable, Tuple, Mapping
    from valid8 import ValidationFuncs, ValidationError
    use_type_hints = True
except ImportError:
    use_type_hints = False


PY36 = sys.version_info >= (3, 6)
if PY36:
    try:
        from typing import get_type_hints
    except ImportError:
        pass


class MandatoryFieldInitError(Exception):
    """
    Raised by `field` when a mandatory field is read without being set first.
    """
    __slots__ = 'field_name', 'obj'

    def __init__(self, field_name, obj):
        self.field_name = field_name
        self.obj= obj

    def __str__(self):
        return "Mandatory field '%s' was not set before first access on " \
               "object '%s'." % (self.field_name, self.obj)


# a few symbols used in `fields`
NO_DEFAULT = sentinel.create('NO_DEFAULT')
_unset = sentinel.create('_unset')
if use_type_hints:
    T = TypeVar('T')
    ANY_TYPE = Any
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

else:
    ANY_TYPE = sentinel.create('ANY_TYPE')


def field(type=ANY_TYPE,  # type: Type[T]
          default=NO_DEFAULT,  # type: T
          default_factory=None,  # type: Callable[[], T]
          validators=None,  # type: Validators
          doc=None,  # type: str
          name=None,  # type: str
          native=None  # type: bool
          ):
    # type: (...) -> T
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
    just hints for the IDE.

    Instead, you can specify a `type` to declare that type should be checked. In that case the type will be validated
    everytime a new value is provided, and a `TypeError` will be raised if invalid. The corresponding type hint is
    automatically declared by `field` so your IDE will know about it, no need to use additional type hints.

    If you wish to specify a type hint without validating it, you should specify `native=True`.

    Documentation
    -------------
    A docstring can be provided for code readability.

    Example
    -------

    >>> import sys, pytest
    >>> if sys.version_info < (3, 6):
    ...     pytest.skip('this doctest does not work on python <3.6 beacause `name` is mandatory')
    ...
    >>> class Foo(object):
    ...     od = field(default='bar', doc="This is an optional field with a default value")
    ...     odf = field(default_factory=list, doc="This is an optional with a default value factory")
    ...     m = field(doc="This is a mandatory field")
    ...     mt = field(type=int, doc="This is a typed mandatory field")
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
    pyfields.core.MandatoryFieldInitError: Mandatory field 'm' was not set before first access on object...
    >>> o.m = True
    >>> o.m  # read access for mandatory attr after init
    True
    >>> del o.m  # all attributes can be deleted, same behaviour than new object
    >>> o.m
    Traceback (most recent call last):
        ...
    pyfields.core.MandatoryFieldInitError: Mandatory field 'm' was not set before first access on object...
    >>> o.mt = 1

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
            In python < 3.6 the `name` attribute is mandatory and should be the same name than the one used used in the
        class field definition (i.e. you should define the field as '<name> = field(name=<name>)').

    :param type: an optional type for the field. If one is provided, it will be checked by default. The field will
        therefore not be a simple (fast) field any more but will be a descriptor (slower) field. You can disable the
        check by forcing `native=True`
    :param default: a default value for the field. Providing a `default` makes the field "optional". `default` value
        is not copied on new instances, if you wish a new copy to be created you should provide a `default_factory`
        instead. Only one of `default` or `default_factory` should be provided.
    :param default_factory: a factory that will be called (without arguments) to get the default value for that
        field, everytime one is needed. Providing a `default_factory` makes the field "optional". Only one of `default`
        or `default_factory` should be provided.
    :param validators: a validation function definition, sequence of validation function definitions, or dictionary of
        validation function definitions. See `valid8` "simple syntax" for details
    :param doc: documentation for the field. This is mostly for class readability purposes for now.
    :param name: in python < 3.6 this is mandatory, and should be the same name than the one used used in the class
        definition (typically, `class Foo:    <name> = field(name=<name>)`).
    :param native: a boolean that can be turned to `False` to force a field to be a descriptor field, or to
        `True` to force it to be a native field. Native fields are faster but can not support type and value validation
         not conversions or callbacks. `None` (default) automatically sets `native=True` if no `validators` nor
         `type` nor `converters` are provided ; and `native=False` otherwise. In general you should not set this
         manually except if (1) you provide `type` but do not wish the type to be enforced ; in which case you would set
         `native=True`. (2) your class does not have `__dict__` (instead it has `__slots__`) ; in which case you would
         set `native=False`.
    :return:
    """
    # check the conditions when we can not go with a fast native field
    if native is not None:
        if native:
            # explicit `native=False`
            if validators is not None:
                raise UnsupportedOnNativeFieldError("`native=False` can not be set if a `validators` or "
                                                    "`converters` is provided")
            else:
                # IMPORTANT: `type *can* still be provided but will not be validated`
                needs_descriptor = False
        else:
            # explicit `native=True`
            needs_descriptor = True
    else:
        needs_descriptor = (type is not ANY_TYPE) or (validators is not None) or native

    # finally create the correct descriptor type
    if needs_descriptor:
        return DescriptorField(type=type, default=default, default_factory=default_factory, validators=validators,
                               doc=doc, name=name)
    else:
        return NativeField(default=default, default_factory=default_factory, doc=doc, name=name)


class UnsupportedOnNativeFieldError(Exception):
    """
    Exception raised whenever someone tries to perform an operation that is not supported on a "native" field.
    """
    pass


class Field(object):
    """
    Base class for fields
    """
    __slots__ = 'default', 'is_default_factory', 'name', 'doc', 'owner_cls'

    def __init__(self,
                 default=NO_DEFAULT,    # type: Any
                 default_factory=None,  # type: Callable[[], Any]
                 doc=None,              # type: str
                 name=None              # type: str
                 ):
        """See help(field) for details"""

        # default
        if default_factory is not None:
            if default is not NO_DEFAULT:
                raise ValueError("Only one of `default` and `default_factory` should be provided")
            else:
                self.default = default_factory
                self.is_default_factory = True
        else:
            self.default = default
            self.is_default_factory = False

        # name
        if not PY36 and name is None:
            raise ValueError("`name` is mandatory in python < 3.6")
        self.name = name
        self.owner_cls = None

        # doc
        self.doc = dedent(doc) if doc is not None else None

    def __set_name__(self, owner, name):
        # called at class creation time
        self.owner_cls = owner

        if self.name is not None:
            if self.name != name:
                raise ValueError("field name '%s' in class '%s' does not correspond to explicitly declared name '%s' "
                                 "in field constructor" % (name, owner.__class__, self.name))
        else:
            self.name = name

    @property
    def qualname(self):
        if self.owner_cls is not None:
            try:
                owner_qualname = self.owner_cls.__qualname__
            except AttributeError:
                owner_qualname = str(self.owner_cls)
        else:
            owner_qualname = "<unknown_cls>"
        return "%s.%s" % (owner_qualname, self.name)


class NativeField(Field):
    """
    Implements fields that are replaced with a native python one on first read or write access.
    Faster but provides not much flexibility (no validator, no type check, no converter)
    """
    def __get__(self, obj, objtype):
        if obj is None:
            # class-level call ?
            return self

        # Check if the field is already set in the object __dict__
        value = obj.__dict__.get(self.name, _unset)

        if value is _unset:
            # mandatory field: raise an error
            if self.default is NO_DEFAULT:
                raise MandatoryFieldInitError(self.name, obj)

            # optional: get default
            if self.is_default_factory:
                value = self.default()
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
    __slots__ = 'validated_field',

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
            # support several cases for the validation function signature
            # `f(val)`, `f(obj, val)` or `f(obj, field, val)`
            # the validation function has two or three (or more but optional) arguments.
            # valid8 requires only 1.

            nb_args = len(v8_getfullargspec(validation_callable, skip_bound_arg=True)[0])
            if nb_args == 0:
                raise ValueError(
                    "validation function should accept 1, 2, or 3 arguments at least. `f(val)`, `f(obj, val)` or "
                    "`f(obj, field, val)`")
            elif nb_args == 1:
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
    __slots__ = 'type', 'validator'

    def __init__(self,
                 type=ANY_TYPE,         # type: Type[T]
                 default=NO_DEFAULT,    # type: Any
                 default_factory=None,  # type: Callable[[], Any]
                 validators=None,       # type: Validators
                 doc=None,              # type: str
                 name=None              # type: str
                 ):
        """See help(field) for details"""
        super(DescriptorField, self).__init__(default=default, default_factory=default_factory, doc=doc, name=name)

        # type
        self.type = type

        # validators
        if validators is not None:
            try:  # dict ?
                validators.keys()
            except (AttributeError, FunctionDefinitionError):
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

    def __get__(self, obj, objtype):
        if obj is None:
            # class-level call ?
            return self

        privatename = '_' + self.name

        # Check if the field is already set in the object
        value = getattr(obj, privatename, _unset)

        if value is _unset:
            # mandatory field: raise an error
            if self.default is NO_DEFAULT:
                raise MandatoryFieldInitError(self.name, obj)

            # optional: get default
            if self.is_default_factory:
                value = self.default()
            else:
                value = self.default

            # nominal initialization on first read: we set the attribute in the object
            setattr(obj, privatename, value)

        return value

    def __set__(self, obj, value):
        # speedup for vars used several time
        t = self.type
        privatename = "_" + self.name

        # check the type
        if t is ANY_TYPE and self.owner_cls is not None and PY36:
            t = get_type_hints(self.owner_cls).get(self.name)
            # TODO actually the type checking part should be handled properly.

        if t is not ANY_TYPE:
            if not isinstance(value, t):
                # representing the object might fail, protect ourselves
                try:
                    val_repr = str(value)
                except:
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
        privatename = "_" + self.name
        delattr(obj, privatename)


# class FieldValidator(Validator):
#     """
#     Extends valid8's Validator to handle the extra (obj, field) context arguments provided on validation
#     """
#     def __init__(self, *all_validators):
#         # dont call super
#         # super(FieldValidator, self).__init__(error_type=None, help_msg=None, none_policy=None)
#         self.error_type = ValidationError
#         self.help_msg = None
#         self.none_policy = NonePolicy.VALIDATE
#         self.kw_context_args = dict()
#
#         # set main function to be an "and" of all functions
#         self.main_function = and_with_additional_args(*all_validators)
#
#     def validate(self, obj, field, value):
#         # first set the validation context to (obj, field)
#         main_function_bak = self.main_function
#
#         # create a partial dynamically
#         self.main_function = partialize(main_function_bak, obj, field)
#
#         # then call validation
#         try:
#             self.assert_valid(field.name[1:], value)
#         finally:
#             # put back the main function
#             self.main_function = main_function_bak


# def partialize(f, *args):
#     fp = partial(f, *args)
#     fp.__name__ = f.__name__
#     return fp


# def and_with_additional_args(*all_validators):
#     """similar to valid8.and_(*validators) but here our validators have context"""
#
#     if len(all_validators) == 1:
#         return all_validators[0]
#     else:
#         def and_v_(obj, field, x):
#             for validator in all_validators:
#                 try:
#                     res = validator(obj, field, x)
#                 except Exception as e:
#                     # one validator was unhappy > raise
#                     partials = [partialize(v, obj, field) for v in all_validators]
#                     raise AtLeastOneFailed(partials, x, cause=e)
#                 # if not result_is_success(res): <= DO NOT REMOVE THIS COMMENT
#                 if (res is not None) or (res is not True):
#                     # one validator was unhappy > raise
#                     partials = [partialize(v, obj, field) for v in all_validators]
#                     raise AtLeastOneFailed(partials, x)
#
#             return True
#
#         and_v_.__name__ = 'and({})'.format(get_callable_names(all_validators))
#         return and_v_


# def make_validators(validators  # type: Validators
#                     ):
#     """
#     Converts the provided validators into the structures that will be used internally for validation.
#
#      - `validators` should either be `None`, a single `Validator`, an iterable of `Validator`s, or a dictionary of
#        validators (in which case many syntaxes are allowed, see below). See `Validators` type hint.
#
#      - A `Validator` is a validation function together with optional error messages and optional error types. See
#        `make_validator(validator)` for details.
#
#     TODO Dict syntax
#
#     :param validators: `None`, a single validator, an iterable of validators, or a dict-like of validators
#     :return: a list of validators or `None`
#     """
#     if validators is not None:
#         try:
#             # mapping ?
#             v_items = validators.items()
#         except AttributeError as e:
#             try:
#                 # iterable ?
#                 v_iter = iter(validators)
#             except TypeError as e:
#                 # single validator
#                 all_validators = (make_validator(validators), )
#             else:
#                 # iterable
#                 all_validators = (make_validator(v) for v in v_iter)
#         else:
#             # mapping
#             def _mapping_entry_to_validator(k, v):
#                 try:
#                     # tuple?
#                     len(v)
#                 except TypeError:
#                     # single value
#                     vals = (k, v)
#                 else:
#                     # tuple: chain with key
#                     vals = chain((k, ), v)
#
#                 # find the various elements from the key and value
#                 callabl, err_msg, err_type = None, None, None
#                 for _elt in vals:
#                     if isinstance(_elt, str):
#                         err_msg = _elt
#                     else:
#                         try:
#                             if issubclass(_elt, Exception):
#                                 err_type = _elt
#                             else:
#                                 callabl = _elt
#                         except TypeError:
#                             callabl = _elt
#
#                 return make_validator((callabl, err_msg, err_type))
#
#             all_validators = (_mapping_entry_to_validator(k, v) for k, v in v_items)
#
#         # finally create the validator
#         return FieldValidator(*all_validators)


# def make_validator(validator  # type: ValidatorDef
#                    ):
#     """
#      Converts the provided validator into the structures that will be used internally for validation.
#
#      - `validator` is a validation function together with optional error messages and optional error types. It can
#        therefore be provided as <validation_func>, as (<validation_func>, <err_msg>),
#        (<validation_func>, <err_type>), or (<validation_func>, <err_msg>, <err_type>). See `Validator` type hint.
#
#      - Finally a `<validation_func>` validation function is a `callable` with one, two or three arguments: its
#        signature should be `f(val)`, `f(obj, val)` or `f(obj, field, val)`. It should return `True` or `None` in case
#        of success. See `ValidationFunc` type hint.
#
#     :param validator:
#     :return:
#     """
#     validation_func, help_msg, err_type = None, None, None
#     try:
#         nb_elts = len(validator)
#     except TypeError:
#         validation_func = validator
#     else:
#         # a tuple
#         if nb_elts == 1:
#             validation_func = validator[0]
#         elif nb_elts == 2:
#             if isinstance(validator[1], str):
#                 validation_func, help_msg, err_type = validator[0], validator[1], None
#             else:
#                 validation_func, help_msg, err_type = validator[0], None, validator[1]
#         elif nb_elts == 3:
#             validation_func, help_msg, err_type = validator[:]
#         else:
#             raise ValueError('tuple in validator definition should have length 1, 2, or 3. Found: %s' % validator)
#
#     # support several cases for the validation function signature
#     # `f(val)`, `f(obj, val)` or `f(obj, field, val)`
#     nb_args = len(getfullargspec(validation_func)[0])
#     if nb_args == 0:
#         raise ValueError("validation function should accept 1, 2, or 3 arguments at least. `f(val)`, `f(obj, val)` or "
#                          "`f(obj, field, val)`")
#     elif nb_args == 1:
#         # underlying validator from valid8 handling the error-related part
#         raiser = failure_raiser(validation_func, help_msg=help_msg, failure_type=err_type)
#
#         # function that we'll call
#         def validate(obj, field, val):
#             raiser(val)
#
#     else:
#         # the validation function has two or three (or more but optional) arguments.
#         # valid8 requires only 1. Reconciliate the two using context managers
#         class val_func_with_2_args:
#             """ Represents a function """
#             __slots__ = 'obj', 'f'
#
#             def __init__(self, f):
#                 self.f = f
#
#             def work_on(self, obj):
#                 self.obj = obj
#                 return self
#
#             def __enter__(self):
#                 pass
#
#             def __exit__(self, exc_type, exc_val, exc_tb):
#                 self.obj = None
#
#             def __call__(self, val):
#                 # call user-provided validation function f
#                 return self.f(self.obj, val)
#
#         if nb_args == 2:
#             checker = val_func_with_2_args(validation_func)
#
#             # underlying validator from valid8 handling the error-related part
#             raiser = failure_raiser(checker, help_msg=help_msg, failure_type=err_type)
#
#             # final validation function
#             def validate(obj, field, val):
#                 with checker.work_on(obj):
#                     raiser(val)
#
#         elif nb_args >= 3:
#             class val_func_with_3_args(val_func_with_2_args):
#                 __slots__ = 'field'
#
#                 def work_on(self, obj, field):
#                     self.obj = obj
#                     self.field = field
#                     return self
#
#                 def __call__(self, val):
#                     return self.f(self.obj, self.field, val)
#
#             checker = val_func_with_3_args(validation_func)
#
#             # underlying validator from valid8 handling the error-related part
#             raiser = failure_raiser(checker, help_msg=help_msg, failure_type=err_type)
#
#             # final validation function
#             def validate(obj, field, val):
#                 with checker.work_on(obj, field):
#                     raiser(val)
#
#     # pycharm does not see it but yes all cases are covered
#     validate.__name__ = validation_func.__name__
#     return validate
