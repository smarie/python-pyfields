#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

from valid8 import Validator, ValidationError, ValidationFailure
from valid8.base import getfullargspec as v8_getfullargspec, get_callable_name, is_mini_lambda

from typing import Callable, Type, Any, TypeVar, Union, Iterable, Tuple, Mapping, Optional, Dict


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

    def __init__(self, validated_field: 'DescriptorField', validators: Validators,
                 error_type: 'Type[ValidationError]' = None, help_msg: str = None,
                 none_policy: int = None, **kw_context_args): ...

    def add_validator(self, validation_func: ValidatorDef): ...

    def get_callables_creator(self) -> Callable[[ValidationFunc, str, Type[ValidationFailure], ...],
                                                Callable[[Any, ...], type(None)]]: ...

    def get_additional_info_for_repr(self) -> str: ...

    def _get_name_for_errors(self, name: str) -> str: ...

    def assert_valid(self, obj: Any, value: Any, error_type: Type[ValidationError] = None,
                     help_msg: str = None, **ctx): ...


# --------------- converters
class Converter(object):
    __slots__ = ('name', )

    def __init__(self, name=None): ...

    def accepts(self, obj, field, value) -> Optional[bool]:
        ...

    def convert(self, obj, field, value) -> Any:
        ...

    @classmethod
    def create_from_fun(cls,
                        converter_fun: ConverterFuncOrLambda,
                        validation_fun: ValidationFuncOrLambda = None
                        ) -> Converter: ...

# noinspection PyAbstractClass
class ConverterWithFuncs(Converter):
    __slots__ = ('accepts', 'convert')

    def __init__(self, convert_fun, name=None, accepts_fun=None): ...

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


def make_3params_callable(f: Union[ValidationFunc, ConverterFunc],
                          is_mini_lambda: bool = False) -> Callable[[Any, 'Field', Any], Any]: ...


def make_converter(converter_def: ConverterFuncDefinition) -> Converter: ...

def make_converters_list(converters: OneOrSeveralConverterDefinitions) -> Tuple[Converter, ...]: ...

def trace_convert(field: 'Field', value: Any, obj: Any = None) -> Tuple[Any, DetailedConversionResults]: ...

class ConversionError(Exception):
    def __init__(self, value_to_convert, field, obj, err_dct): ...

def err_dct_to_str(err_dct: Dict[Converter, str]) -> str: ...

class DetailedConversionResults(object): ...
