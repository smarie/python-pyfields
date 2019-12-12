#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.
import sys
from collections import OrderedDict

from valid8 import Validator, failure_raiser, ValidationError, ValidationFailure
from valid8.base import getfullargspec as v8_getfullargspec, get_callable_name, is_mini_lambda
from valid8.common_syntax import FunctionDefinitionError, make_validation_func_callables
from valid8.composition import _and_
from valid8.entry_points import _add_none_handler
from valid8.utils.signature_tools import IsBuiltInError
from valid8.validation_lib import instance_of

try:  # python 3.5+
    # noinspection PyUnresolvedReferences
    from typing import Callable, Type, Any, TypeVar, Union, Iterable, Tuple, Mapping, Optional, Dict
    from valid8.common_syntax import ValidationFuncs
    use_type_hints = sys.version_info > (3, 0)
except ImportError:
    use_type_hints = False


if use_type_hints:
    T = TypeVar('T')

    # ------------- validator type hints -----------
    # 1. the lowest-level user or 3d party-provided validation functions
    ValidationFunc = Union[Callable[[Any], Any],
                           Callable[[Any, Any], Any],
                           Callable[[Any, Any, Any], Any]]
    """A validation function is a callable with signature (val), (obj, val) or (obj, field, val), returning `True` 
    or `None` in case of success"""

    try:
        # noinspection PyUnresolvedReferences
        from mini_lambda import y
        ValidationFuncOrLambda = Union[ValidationFunc, type(y)]
    except ImportError:
        ValidationFuncOrLambda = ValidationFunc

    # 2. the syntax to optionally transform them into failure raisers by providing a tuple
    ValidatorDef = Union[ValidationFuncOrLambda,
                         Tuple[ValidationFuncOrLambda, str],
                         Tuple[ValidationFuncOrLambda, Type[ValidationFailure]],
                         Tuple[ValidationFuncOrLambda, str, Type[ValidationFailure]]
                         ]
    """A validator is a validation function together with optional error message and error type"""

    # 3. the syntax to describe several validation functions at once
    VFDefinitionElement = Union[str, Type[ValidationFailure], ValidationFuncOrLambda]
    """This type represents one of the elements that can define a checker: help msg, failure type, callable"""

    OneOrSeveralVFDefinitions = Union[ValidatorDef,
                                      Iterable[ValidatorDef],
                                      Mapping[VFDefinitionElement, Union[VFDefinitionElement,
                                                                         Tuple[VFDefinitionElement, ...]]]]
    """Several validators can be provided as a singleton, iterable, or dict-like. In that case the value can be a 
    single variable or a tuple, and it will be combined with the key to form the validator. So you can use any of 
    the elements defining a validators as the key."""

    # shortcut name used everywhere. Less explicit
    Validators = OneOrSeveralVFDefinitions


class FieldValidator(Validator):
    """
    Represents a `Validator` responsible to validate a `field`
    """
    __slots__ = '__weakref__', 'validated_field', 'base_validation_funcs'

    def __init__(self,
                 validated_field,   # type: 'DescriptorField'
                 validators,        # type: Validators
                 **kwargs
                 ):
        """

        :param validated_field: the field being validated.
        :param validators: the base validation function or list of base validation functions to use. A callable, a
            tuple(callable, help_msg_str), a tuple(callable, failure_type), tuple(callable, help_msg_str, failure_type)
            or a list of several such elements. A dict can also be used.
            Tuples indicate an implicit `failure_raiser`.
            [mini_lambda](https://smarie.github.io/python-mini-lambda/) expressions can be used instead
            of callables, they will be transformed to functions automatically.
        :param error_type: a subclass of ValidationError to raise in case of validation failure. By default a
            ValidationError will be raised with the provided help_msg
        :param help_msg: an optional help message to be used in the raised error in case of validation failure.
        :param none_policy: describes how None values should be handled. See `NonePolicy` for the various possibilities.
            Default is `NonePolicy.VALIDATE`, meaning that None values will be treated exactly like other values and
            follow the same validation process.
        :param kw_context_args: optional contextual information to store in the exception, and that may be also used
            to format the help message
        """
        # store this additional info about the function been validated
        self.validated_field = validated_field

        try:  # dict ?
            validators.keys()
        except (AttributeError, FunctionDefinitionError):
            if isinstance(validators, tuple):
                # single tuple
                validators = (validators,)
            else:
                try:  # iterable
                    iter(validators)
                except (TypeError, FunctionDefinitionError):
                    # single
                    validators = (validators,)
        else:
            # dict
            validators = (validators,)

        # remember validation funcs so that we can add more later
        self.base_validation_funcs = validators

        super(FieldValidator, self).__init__(*validators, **kwargs)

    def add_validator(self,
                      validation_func  # type: ValidatorDef
                      ):
        """
        Adds the provided validation function to the existing list of validation functions
        :param validation_func:
        :return:
        """
        self.base_validation_funcs = self.base_validation_funcs + (validation_func, )

        # do the same than in super.init, once again. TODO optimize ...
        validation_funcs = make_validation_func_callables(*self.base_validation_funcs,
                                                          callable_creator=self.get_callables_creator())
        main_val_func = _and_(validation_funcs)
        self.main_function = _add_none_handler(main_val_func, none_policy=self.none_policy)

    def get_callables_creator(self):
        def make_validator_callable(validation_callable,  # type: ValidationFunc
                                    help_msg=None,        # type: str
                                    failure_type=None,    # type: Type[ValidationFailure]
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
        # type: (...) -> str
        return 'validated_field=%s' % self.validated_field.qualname

    def _get_name_for_errors(self,
                             name  # type: str
                             ):
        # type: (...) -> str
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


# --------------- converters
supported_syntax = 'a Converter, a conversion callable, a tuple(validation_callable, conversion_callable), ' \
                   'a tuple(valid_type, conversion_callable), or a list of several such elements. ' \
                   'A special string \'*\' can be used to denote that all values are accepted.' \
                   'Dicts are supported too, in which case the key is the validation callable or the valid type.' \
                   '[mini_lambda](https://smarie.github.io/python-mini-lambda/) expressions can be used instead of ' \
                   'callables, they will be transformed to functions automatically.'


class Converter(object):
    """
    A converter to be used in `field`s.
    """
    __slots__ = ('name', )

    def __init__(self, name=None):
        self.name = name

    def __str__(self):
        if self.name is not None:
            return self.name
        else:
            return self.__class__.__name__

    def accepts(self, obj, field, value):
        # type: (...) -> Optional[bool]
        """
        Should return `True` or `None` in case the provided value can be converted.

        :param obj:
        :param field:
        :param value:
        :return:
        """
        pass

    def convert(self, obj, field, value):
        # type: (...) -> Any
        """
        Converts the provided `value`. This method is only called when `accepts()` has returned `True`.
        Implementors can dynamically declare that they are not able to convert the given value, by raising an Exception.

        Returning `None` means that the `value` converts to `None`.

        :param obj:
        :param field:
        :param value:
        :return:
        """
        raise NotImplementedError()

    @classmethod
    def create_from_fun(cls,
                        converter_fun,       # type: ConverterFuncOrLambda
                        validation_fun=None  # type: ValidationFuncOrLambda
                        ):
        # type: (...) -> Converter
        """
        Creates an instance of `Converter` where the `accepts` method is bound to the provided `validation_fun` and the
        `convert` method bound to the provided `converter_fun`.

        If these methods have less than 3 parameters, the mapping is done acccordingly.

        :param converter_fun:
        :param validation_fun:
        :return:
        """
        # Mandatory conversion callable
        if is_mini_lambda(converter_fun):
            is_mini = True
            converter_fun = converter_fun.as_function()
        else:
            is_mini = False
        converter_fun_3params = make_3params_callable(converter_fun, is_mini_lambda=is_mini)

        # Optional acceptance callable
        if validation_fun is not None:
            if is_mini_lambda(validation_fun):
                is_mini = True
                validation_fun = validation_fun.as_function()
            else:
                is_mini = False
            validation_fun_3params = make_3params_callable(validation_fun, is_mini_lambda=is_mini)
        else:
            validation_fun_3params = None

        # Finally create the converter instance
        return ConverterWithFuncs(name=converter_fun_3params.__name__,
                                  accepts_fun=validation_fun_3params,
                                  convert_fun=converter_fun_3params)


# noinspection PyAbstractClass
class ConverterWithFuncs(Converter):
    """
    Represents a converter for which the `accepts` and `convert` methods can be provided in the constructor.
    """
    __slots__ = ('accepts', 'convert')

    def __init__(self, convert_fun, name=None, accepts_fun=None):
        # call super to set the name
        super(ConverterWithFuncs, self).__init__(name=name)

        # use the convert method
        self.convert = convert_fun

        # use the accepts method if provided, otherwise use parent's
        if accepts_fun is not None:
            self.accepts = accepts_fun
        else:
            # use parent method - bind it on this instance
            self.accepts = Converter.accepts.__get__(self, ConverterWithFuncs)


if use_type_hints:
    # --------------converter type hints
    # 1. the lowest-level user or 3d party-provided validation functions
    ConverterFunc = Union[Callable[[Any], Any],
                          Callable[[Any, Any], Any],
                          Callable[[Any, Any, Any], Any]]
    """A converter function is a callable with signature (val), (obj, val) or (obj, field, val), returning the 
    converted value in case of success"""

    try:
        # noinspection PyUnresolvedReferences
        from mini_lambda import y

        ConverterFuncOrLambda = Union[ConverterFunc, type(y)]
    except ImportError:
        ConverterFuncOrLambda = ConverterFunc

    # 2. the syntax to optionally transform them into Converter by providing a tuple
    ValidType = Type
    # noinspection PyUnboundLocalVariable
    ConverterFuncDefinition = Union[Converter,
                                    ConverterFuncOrLambda,
                                    Tuple[ValidationFuncOrLambda, ConverterFuncOrLambda],
                                    Tuple[ValidType, ConverterFuncOrLambda]]

    TypeDef = Union[Type, Tuple[Type, ...]]
    OneOrSeveralConverterDefinitions = Union[Converter,
                                             ConverterFuncOrLambda,
                                             Iterable[Tuple[TypeDef, ConverterFunc]],
                                             Mapping[TypeDef, ConverterFunc]]
    Converters = OneOrSeveralConverterDefinitions


def make_3params_callable(f,                    # Union[ValidationFunc, ConverterFunc]
                          is_mini_lambda=False  # type: bool
                          ):
    # type: (...) -> Callable[[Any, 'Field', Any], Any]
    """
    Transforms the provided validation or conversion callable into a callable with 3 arguments (obj, field, val).

    :param f:
    :param is_mini_lambda: a boolean indicating if the function comes from a mini lambda. In which case we know the signature has one param only (x)
    :return:
    """
    # support several cases for the function signature
    # `f(val)`, `f(obj, val)` or `f(obj, field, val)`
    if is_mini_lambda:
        nbargs = 1
        nbvarargs = 0
        # nbkwargs = 0
        # nbdefaults = 0
    else:
        try:
            args, varargs, varkwargs, defaults = v8_getfullargspec(f, skip_bound_arg=True)[0:4]
            nbargs = len(args) if args is not None else 0
            nbvarargs = 1 if varargs is not None else 0
            # nbkwargs = 1 if varkwargs is not None else 0
            # nbdefaults = len(defaults) if defaults is not None else 0
        except IsBuiltInError:
            # built-ins: TypeError: <built-in function isinstance> is not a Python function
            # assume signature with a single positional argument
            nbargs = 1
            nbvarargs = 0
            # nbkwargs = 0
            # nbdefaults = 0

    if nbargs == 0 and nbvarargs == 0:
        raise ValueError(
            "validation or converter function should accept 1, 2, or 3 arguments at least. `f(val)`, `f(obj, val)` or "
            "`f(obj, field, val)`")
    elif nbargs == 1 or (
            nbargs == 0 and nbvarargs >= 1):  # varargs default to one argument (compliance with old mini lambda)
        # `f(val)`
        def new_f_with_3_args(obj, field, value):
            return f(value)

    elif nbargs == 2:
        # `f(obj, val)`
        def new_f_with_3_args(obj, field, value):
            return f(obj, value)

    else:
        # `f(obj, field, val, *opt_args, **ctx)`
        new_f_with_3_args = f

    # preserve the name
    new_f_with_3_args.__name__ = get_callable_name(f)

    return new_f_with_3_args


JOKER_STR = '*'
"""String used in converter definition dict entries or tuples, to indicate that the converter accepts everything"""


def make_converter(converter_def  # type: ConverterFuncDefinition
                   ):
    # type: (...) -> Converter
    """
    Makes a `Converter` from the provided converter object. Supported formats:

     - a `Converter`
     - a `<conversion_callable>` with possible signatures `(value)`, `(obj, value)`, `(obj, field, value)`.
     - a tuple `(<validation_callable>, <conversion_callable>)`
     - a tuple `(<valid_type>, <conversion_callable>)`

    If no name is provided and a `<conversion_callable>` is present, the callable name will be used as the converter
    name.

    The name of the conversion callable will be used in that case

    :param converter_def:
    :return:
    """
    try:
        nb_elts = len(converter_def)
    except (TypeError, FunctionDefinitionError):
        # -- single element
        # handle the special case of a LambdaExpression: automatically convert to a function
        if not is_mini_lambda(converter_def):
            if isinstance(converter_def, Converter):
                # already a converter
                return converter_def
            elif not callable(converter_def):
                raise ValueError('base converter function(s) not compliant with the allowed syntax. Base validation'
                                 ' function(s) can be %s Found %s.' % (supported_syntax, converter_def))
        # single element.
        return Converter.create_from_fun(converter_def)
    else:
        # -- a tuple
        if nb_elts == 1:
            converter_fun, validation_fun = converter_def[0], None
        elif nb_elts == 2:
            validation_fun, converter_fun = converter_def
            if validation_fun is not None:
                if isinstance(validation_fun, type):
                    # a type can be provided to denote accept "instances of <type>"
                    validation_fun = instance_of(validation_fun)
                elif validation_fun == JOKER_STR:
                    validation_fun = None
                else:
                    if not is_mini_lambda(validation_fun) and not callable(validation_fun):
                        raise ValueError('base converter function(s) not compliant with the allowed syntax. Validator '
                                         'is incorrect. Base converter function(s) can be %s Found %s.'
                                         % (supported_syntax, converter_def))
        else:
            raise ValueError(
                'tuple in converter_fun definition should have length 1, or 2. Found: %s' % (converter_def,))

        # check that the definition is valid
        if not is_mini_lambda(converter_fun) and not callable(converter_fun):
            raise ValueError('base converter function(s) not compliant with the allowed syntax. Base converter'
                             ' function(s) can be %s Found %s.' % (supported_syntax, converter_def))

        # finally create the failure raising callable
        return Converter.create_from_fun(converter_fun, validation_fun)


def make_converters_list(converters  # type: OneOrSeveralConverterDefinitions
                         ):
    # type: (...) -> Tuple[Converter, ...]
    """
    Creates a tuple of converters from the provided `converters`. The following things are supported:

     - a single item. This can be a `Converter`, a `<converter_callable>`, a tuple
       `(<acceptance_callable>, <converter_callable>)` or a tuple `(<accepted_type>, <converter_callable>)`.
       `<accepted_type>` can also contain `None` or `'*'`, both mean "anything".

     - a list of such items

     - a dictionary-like of `<acceptance>: <converter_callable>`, where `<acceptance>` can be an `<acceptance_callable>`
       or an `<accepted_type>`.

    :param converters:
    :return:
    """
    # support a single tuple
    if isinstance(converters, tuple):
        converters = [converters]

    try:
        # mapping ?
        c_items = iter(converters.items())
    except (AttributeError, FunctionDefinitionError):
        try:
            # iterable ?
            c_iter = iter(converters)
        except (TypeError, FunctionDefinitionError):
            # single converter: create a tuple manually
            all_converters = (make_converter(converters),)
        else:
            # iterable
            all_converters = tuple(make_converter(c) for c in c_iter)
    else:
        # mapping: assume that each entry is {validation_fun: converter_fun}
        all_converters = tuple(make_converter((k, v)) for k, v in c_items)

    if len(all_converters) == 0:
        raise ValueError("No converters provided")
    else:
        return all_converters


def trace_convert(field,    # type: 'Field'
                  value,    # type: Any
                  obj=None  # type: Any
                  ):
    # type: (...) -> Tuple[Any, DetailedConversionResults]
    """
    Utility method to debug conversion issues.
    Instead of just returning the converted value, it also returns conversion details.

    In case conversion can not be made, a `ConversionError` is raised.

    Inspired by the `getversion` library.

    :param obj:
    :param field:
    :param value:
    :return:
    """
    errors = OrderedDict()

    for conv in field.converters:
        try:
            # check if converter accepts this ?
            accepted = conv.accepts(obj, field, value)
        except Exception as e:
            # error in acceptance test
            errors[conv] = "Acceptance test: ERROR [%s] %s" % (e.__class__.__name__, e)
        else:
            if accepted is not None and not accepted:
                # acceptance failed
                errors[conv] = "Acceptance test: REJECTED (returned %s)" % accepted
            else:
                # accepted! (None or True truth value)
                try:
                    # apply converter
                    converted_value = conv.convert(obj, field, value)
                except Exception as e:
                    errors[conv] = "Acceptance test: SUCCESS (returned %s). Conversion: ERROR [%s] %s" \
                                   % (accepted, e.__class__.__name__, e)
                else:
                    # conversion success !
                    errors[conv] = "Acceptance test: SUCCESS (returned %s). Conversion: SUCCESS -> %s" \
                                   % (accepted, converted_value)
                    return converted_value, DetailedConversionResults(value, field, obj, errors, conv, converted_value)

    raise ConversionError(value_to_convert=value, field=field, obj=obj, err_dct=errors)


class ConversionError(Exception):
    """
    Final exception Raised by `trace_convert` when a value cannot be converted successfully
    """
    __slots__ = 'value_to_convert', 'field', 'obj', 'err_dct'

    def __init__(self, value_to_convert, field, obj, err_dct):
        self.value_to_convert = value_to_convert
        self.field = field
        self.obj = obj
        self.err_dct = err_dct
        super(ConversionError, self).__init__()

    def __str__(self):
        return "Unable to convert value %r. Results:\n%s" \
               % (self.value_to_convert, err_dct_to_str(self.err_dct))


def err_dct_to_str(err_dct  # Dict[Converter, str]
                   ):
    # type: (...) -> str
    msg = ""
    for converter, err in err_dct.items():
        msg += " - Converter '%s': %s\n" % (converter, err)

    return msg


class DetailedConversionResults(object):
    """
    Returned by `trace_convert` for detailed results about which converter failed before the winning one.
    """
    __slots__ = 'value_to_convert', 'field', 'obj', 'err_dct', 'winning_converter', 'converted_value'

    def __init__(self, value_to_convert, field, obj, err_dct, winning_converter, converted_value):
        self.value_to_convert= value_to_convert
        self.field = field
        self.obj = obj
        self.err_dct = err_dct
        self.winning_converter = winning_converter
        self.converted_value = converted_value

    def __str__(self):
        return "Value %r successfully converted to %r using converter '%s', after the following attempts:\n%s"\
               % (self.value_to_convert, self.converted_value, self.winning_converter, err_dct_to_str(self.err_dct))
