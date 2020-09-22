#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
#  Copyright (c) Schneider Electric Industries, 2019. All right reserved.

#  Authors: Sylvain Marie <sylvain.marie@se.com>
#
import pickle
import sys
from collections import OrderedDict

import pytest

from valid8 import ValidationError, ValidationFailure
from valid8.base import InvalidValue
from valid8.validation_lib import non_empty, Empty

from pyfields import field, MandatoryFieldInitError, UnsupportedOnNativeFieldError, \
    copy_value, copy_field, Converter, Field, ConversionError, ReadOnlyFieldError, FieldTypeError, make_init


@pytest.mark.parametrize('write_before_reading', [False, True], ids="write_before_reading={}".format)
@pytest.mark.parametrize('type_', ['default_factory', 'default', 'mandatory'], ids="type_={}".format)
@pytest.mark.parametrize('read_only', [False, True], ids="read_only={}".format)
def test_field(write_before_reading, type_, read_only):
    """Checks that field works as expected"""

    if type_ == 'default_factory':
        class Tweety(object):
            afraid = field(default_factory=lambda obj: False, read_only=read_only)
    elif type_ == 'default':
        class Tweety(object):
            afraid = field(default=False, read_only=read_only)
    elif type_ == 'mandatory':
        class Tweety(object):
            afraid = field(read_only=read_only)
    else:
        raise ValueError()

    # instantiate
    t = Tweety()

    written = False

    # (1) write
    if write_before_reading:
        t.afraid = True
        written = True

    # (2) read
    if not write_before_reading and type_ == 'mandatory':
        # mandatory value not already overridden
        with pytest.raises(MandatoryFieldInitError):
            print(t.afraid)
    else:
        # either default value (False) or already-written value (True)
        assert t.afraid is write_before_reading
        written = True  # because reading a non-mandatory field sets it to default

    # (3) write (possibly again) and check
    if not (read_only and written):
        t.afraid = True
        assert t.afraid is True
        if not read_only:
            t.afraid = False
            assert t.afraid is False
        written = True

    # if read only, check exception on second write
    if read_only:
        # make sure that now the value has been
        assert written

        with pytest.raises(ReadOnlyFieldError) as exc_info:
            t.afraid = False
        qualname = Tweety.afraid.qualname
        assert str(exc_info.value) == "Read-only field '%s' has already been " \
                                      "initialized on instance %s and cannot be modified anymore." % (qualname, t)


def test_slots():
    """tests that fields are replaced with descriptor fields automatically when used on a class with `__slots__`"""
    class WithSlots(object):
        __slots__ = ('_a',)
        a = field()

    if sys.version_info < (3, 0):
        # qualname does not exist, we use str(cls)
        a_fixed_name = "pyfields.tests.test_core.WithSlots.a"
    else:
        a_fixed_name = "test_slots.<locals>.WithSlots.a"

    a_unknown_name = "<unknown_cls>.None"

    if sys.version_info >= (3, 6):
        # change is done immediately
        assert repr(WithSlots.__dict__['a']) == "<DescriptorField: %s>" % a_fixed_name
    else:
        # change will be done after first access
        assert repr(WithSlots.__dict__['a']) == "<NativeField: %s>" % a_unknown_name

    w = WithSlots()

    if sys.version_info < (3, 6):
        # Really not ideal you have to do something
        try:
            w.a
        except:
            pass

    w.a = 1
    assert w.a == 1

    assert repr(WithSlots.a) == "<DescriptorField: %s>" % a_fixed_name


def test_slots2():
    class WithSlots(object):
        __slots__ = ('__dict__',)
        a = field()

    if sys.version_info >= (3, 6):
        a_name = "test_slots2.<locals>.WithSlots.a"
    else:
        a_name = "<unknown_cls>.None"

    assert repr(WithSlots.__dict__['a']) == "<NativeField: %s>" % a_name


def test_default_factory():
    """"""
    class Foo(object):
        a = field(default_factory=copy_value([]))
        b = field(default_factory=copy_field('z'))
        c = field()

        @c.default_factory
        def c_default(self):
            return self.a + ['yes']

        z = field()

    f = Foo()
    g = Foo()
    assert f.a == []
    assert g.a == []
    g.a.append(1)
    assert g.a == [1]
    assert f.a == []
    # we can not initialize b since it requires a copy of uninitialized z
    with pytest.raises(MandatoryFieldInitError) as exc_info:
        print(f.b)
    assert str(exc_info.value).startswith("Mandatory field 'z' has not been initialized yet")
    # if we initialize z we can now safely make a copy
    f.z = 12
    assert f.b == 12
    f.z += 1
    assert f.z == 13
    assert f.b == 12

    assert g.c == [1, 'yes']


def test_type():
    """ Tests that when `type_hint` is provided and `validate_type` is explicitly set, it works as expected """

    class Foo(object):
        f = field(type_hint=str, check_type=True)

    o = Foo()
    o.f = 'hello'
    with pytest.raises(FieldTypeError) as exc_info:
        o.f = 1

    if sys.version_info < (3, 0):
        qualname = 'pyfields.tests.test_core.Foo.f'
    else:
        qualname = 'test_type.<locals>.Foo.f'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "Value should be of type %s. " \
                                  "Instead, received a 'int': 1" % (qualname, str)


def test_type_multiple_tuple():
    """ Tests that when `type_hint` is provided and `validate_type` is explicitly set, it works as expected """

    class Foo(object):
        f = field(type_hint=(str, int), check_type=True)

    o = Foo()
    o.f = 'hello'
    o.f = 1
    with pytest.raises(FieldTypeError) as exc_info:
        o.f = 1.1

    # msg = Value type should be one of ('str', 'int')
    msg = "Value type should be one of (%s, %s)" % (str, int)
    if sys.version_info < (3, 0):
        qualname = 'pyfields.tests.test_core.Foo.f'
    else:
        qualname = 'test_type_multiple_tuple.<locals>.Foo.f'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "%s. " \
                                  "Instead, received a 'float': 1.1" % (qualname, msg)


try:
    from typing import Optional
    typing_present = True
except ImportError:
    typing_present = False


@pytest.mark.skipif(not typing_present, reason="typing module is not present")
def test_type_multiple_typing():
    """ Tests that when `type_hint` is provided and `validate_type` is explicitly set, it works as expected """

    from typing import Union

    class Foo(object):
        f = field(type_hint=Union[int, str], check_type=True)

    o = Foo()
    o.f = 'hello'
    o.f = 1
    with pytest.raises(FieldTypeError) as exc_info:
        o.f = 1.1

    if sys.version_info < (3, 0):
        qualname = 'pyfields.tests.test_core.Foo.f'
    else:
        qualname = 'test_type_multiple_typing.<locals>.Foo.f'
    assert str(exc_info.value) == "Invalid value type provided for '%s'. " \
                                  "Value should be of type typing.Union[int, str]. " \
                                  "Instead, received a 'float': 1.1" % qualname


@pytest.mark.skipif(sys.version_info < (3, 6), reason="class member annotations are not allowed before python 3.6")
def test_type_from_pep484_annotations():
    # import the class to use
    from ._test_py36 import _test_class_annotations
    Foo = _test_class_annotations()

    # create an instance
    foo = Foo()

    # test that the field that is non-native has type checking active
    foo.field_with_validate_type = 2
    with pytest.raises(TypeError) as exc_info:
        foo.field_with_validate_type = 'hello'
    assert str(exc_info.value).startswith("Invalid value type provided for ")

    # by default the type is not checked
    foo.field_with_defaults = 'hello'


@pytest.mark.parametrize("case_nb", [1, 2, 3, 4, 5], ids="case_nb={}".format)
def test_field_validators(case_nb):
    """ tests that `validators` functionality works correctly with several flavours of definition."""

    # class EmptyError(ValidationError):
    #     help_msg = "h should be non empty"

    class EmptyFailure(ValidationFailure, ValueError):
        """ Custom ValidationFailure raised by non_empty """
        help_msg = 'len(x) > 0 does not hold for x={wrong_value}'

    class Foo2(object):
        # one single validator
        f = field(default="hey", type_hint=str, validators=non_empty)

        # one single validator in a list
        g = field(type_hint=str, validators=[non_empty])

        # one single validator accepting three arguments (obj, field, val)
        gg = field(type_hint=str, validators=lambda obj, field, val: obj.f in val)

        # several validators in a dict. keys and values can contain elements of definition in any order
        h = field(type_hint=str, validators=OrderedDict([("h should be non empty", (non_empty, EmptyFailure)),
                                                         ("h should contain field f", (lambda obj, val: obj.f in val)),
                                                         ("h should contain 'a'", (lambda val: 'a' in val))]))

    if sys.version_info < (3, 0):
        # qualname does not exist, we use str(cls)
        c_name = "pyfields.tests.test_core.Foo2"
    else:
        c_name = "test_field_validators.<locals>.Foo2"

    # the object that we'll use
    o = Foo2()

    if case_nb == 1:
        o.f = 'hey'
        with pytest.raises(ValidationError) as exc_info:
            o.f = ''
        str(exc_info.value)
        assert isinstance(exc_info.value.failure, Empty)
        assert str(exc_info.value) == "Error validating [%s.f='']. " \
                                      "Empty: len(x) > 0 does not hold for x=. Wrong value: ''." % c_name

    elif case_nb == 2:
        o.g = 'hey'
        with pytest.raises(ValidationError) as exc_info:
            o.g = ''
        str(exc_info.value)
        assert isinstance(exc_info.value.failure, Empty)
        assert str(exc_info.value) == "Error validating [%s.g='']. " \
                                      "Empty: len(x) > 0 does not hold for x=. Wrong value: ''." % c_name

    elif case_nb == 3:
        o.gg = 'heyho'
        with pytest.raises(ValidationError) as exc_info:
            o.gg = 'ho'  # does not contain field f ('hey')
        str(exc_info.value)
        assert isinstance(exc_info.value.failure, InvalidValue)
        assert exc_info.value.failure.validation_outcome is False
        assert str(exc_info.value) == "Error validating [%s.gg=ho]. " \
                                      "InvalidValue: Function [<lambda>] returned [False] for value 'ho'." % c_name

    elif case_nb in (4, 5):
        if case_nb == 4:
            # override the definition for Foo2.h
            # several validators in a list. Tuples should start with the function
            Foo2.h = field(name='h', type_hint=str, validators=[(non_empty, "h should be non empty", EmptyFailure),
                                                                non_empty,
                                                                (lambda obj, val: obj.f in val, "h should contain field f"),
                                                                (lambda val: 'a' in val, "h should contain 'a'"),
                                                                (non_empty, EmptyFailure),
                                                                ])

        # o.h should be a non-empty string containing 'a' and containing o.f
        with pytest.raises(ValidationError) as exc_info:
            o.h = ''  # empty
        str(exc_info.value)
        assert isinstance(exc_info.value.failure.__cause__, EmptyFailure)
        assert str(exc_info.value.failure.__cause__) == "h should be non empty. " \
                                                        "Function [non_empty] raised " \
                                                        "Empty: len(x) > 0 does not hold for x=. Wrong value: ''."

        with pytest.raises(ValidationError) as exc_info:
            o.h = 'hey'  # does not contain 'a'
        assert isinstance(exc_info.value.failure.__cause__, InvalidValue)
        assert exc_info.value.failure.__cause__.validation_outcome is False
        assert str(exc_info.value.failure.__cause__) == "h should contain 'a'. " \
                                                        "Function [<lambda>] returned [False] for value 'hey'."

        with pytest.raises(ValidationError) as exc_info:
            o.h = 'a'  # does not contain field f ('hey')
        assert isinstance(exc_info.value.failure.__cause__, InvalidValue)
        assert exc_info.value.failure.__cause__.validation_outcome is False
        assert str(exc_info.value.failure.__cause__) == "h should contain field f. " \
                                                        "Function [<lambda>] returned [False] for value 'a'."
        o.h = 'hey ya'


@pytest.mark.parametrize("explicit", [False, True], ids="explicit={}".format)
def test_field_validators_decorator(explicit):
    """Tests that the @<field>.decorator works correctly"""

    if explicit:
        native = False
    else:
        native = None
        if sys.version_info < (3, 6):
            with pytest.raises(UnsupportedOnNativeFieldError):
                class Foo(object):
                    f = field(native=native)
                    @f.validator
                    def validate_f(self, val):
                        return val % 3 == 0
            return

    class Foo(object):
        f = field(native=native)

        @f.validator
        def f_should_be_a_multiple_of_3(self, f_val):
            return f_val % 3 == 0

        @f.validator(help_msg="not a large enough value")
        def f_should_be_larger_than_g(self, f_val):
            return f_val > self.g

    f_field = Foo.f
    assert len(f_field.root_validator.base_validation_funcs) == 2
    foo = Foo()
    foo.g = 0
    with pytest.raises(ValidationError) as exc_info:
        foo.f = 2
    # assert str(exc_info.value) == "Error validating [%s=2]. " \
    #                               "InvalidValue: Function [f_should_be_a_multiple_of_3] returned [False] for value 2." \
    #        % Foo.f.qualname
    assert str(exc_info.value) == "Error validating [%s=2]. At least one validation function failed for value 2. " \
                                  "Successes: ['f_should_be_larger_than_g'] / " \
                                  "Failures: {'f_should_be_a_multiple_of_3': 'Returned False.'}." \
           % Foo.f.qualname
    foo.f = 3
    foo.g = 3
    with pytest.raises(ValidationError) as exc_info:
        foo.f = 3
    assert str(exc_info.value) == "Error validating [%s=3]. At least one validation function failed for value 3. " \
                                  "Successes: ['f_should_be_a_multiple_of_3'] / " \
                                  "Failures: {'f_should_be_larger_than_g': " \
                                  "'InvalidValue: not a large enough value. Returned False.'}." \
           % Foo.f.qualname


def test_validator_not_compliant_with_native_field():
    """tests that `native=True` can not be set when a validator is provided"""
    with pytest.raises(UnsupportedOnNativeFieldError):
        class Foo(object):
            f = field(validators=lambda x: True, native=True)


@pytest.mark.parametrize("explicit", [False, True], ids="explicit={}".format)
def test_field_converters_decorator(explicit):
    """Tests that the @<field>.converter works correctly"""

    if explicit:
        native = False
    else:
        native = None
        if sys.version_info < (3, 6):
            with pytest.raises(UnsupportedOnNativeFieldError):
                class Foo(object):
                    f = field(native=native)
                    @f.converter
                    def validate_f(self, val):
                        return val % 3 == 0
            return

    class Foo(object):
        f = field(native=native)

        @f.converter(accepts=str)
        def f_from_str(self, f_val):
            # make sure the filter has worked
            assert isinstance(f_val, str)
            return int(f_val)

        @f.converter
        def f_from_anything(self, f_val):
            if isinstance(f_val, int):
                # of course we would not do that in real life but this is a test that exceptions are supported
                raise Exception("no need to convert! already an int")
            return int(f_val) + 1

    f_field = Foo.f
    assert len(f_field.converters) == 2
    foo = Foo()
    foo.f = 0    # uses no converter at all
    assert foo.f == 0
    foo.f = '2'  # uses the first converter
    assert foo.f == 2
    foo.f = 2.1  # uses the second converter
    assert foo.f == 3


def test_converter_not_compliant_with_native_field():
    """tests that `native=True` can not be set when a validator is provided"""
    with pytest.raises(UnsupportedOnNativeFieldError):
        class Foo(object):
            f = field(converters=lambda x: x, native=True)


@pytest.mark.parametrize("validator_return_none", [False, True], ids="validator_return_none={}".format)
@pytest.mark.parametrize("nbargs", [1, 2, 3], ids="nbargs={}".format)
@pytest.mark.parametrize("format", ['single_converter', 'single_fun',
                                    '(v_fun, c_fun)', '(v_type, c_fun)', '(joker, c_fun)', '(None, c_fun)',
                                    '{v_fun: c_fun}', '{v_type: c_fun}', '{joker: c_fun}', '{None: c_fun}'],
                         ids="format={}".format)
def test_converters(format, nbargs, validator_return_none):
    """Various tests about converters definition format"""

    from mini_lambda import x

    if nbargs == 1:
        def parse_nb(x):
            return int(x)

        def valid_str(x):
            if validator_return_none:
                return None if isinstance(x, str) else False
            return isinstance(x, str)
    elif nbargs == 2:
        def parse_nb(obj, x):
            assert obj.__class__.__name__ == 'Foo'
            return int(x)

        def valid_str(obj, x):
            assert obj.__class__.__name__ == 'Foo'
            if validator_return_none:
                return None if isinstance(x, str) else False
            return isinstance(x, str)
    elif nbargs == 3:
        def parse_nb(obj, field, x):
            assert obj.__class__.__name__ == 'Foo'
            assert isinstance(field, Field)
            return int(x)

        def valid_str(obj, field, x):
            assert obj.__class__.__name__ == 'Foo'
            assert isinstance(field, Field)
            if validator_return_none:
                return None if isinstance(x, str) else False
            return isinstance(x, str)
    else:
        raise ValueError(nbargs)

    if format == 'single_converter':
        class ParseNb(Converter):
            def convert(self, obj, field, x):
                if nbargs == 1:
                    return parse_nb(x)
                elif nbargs == 2:
                    return parse_nb(obj, x)
                elif nbargs == 3:
                    return parse_nb(obj, field, x)
        convs = ParseNb()
        accepts_int = True
        c_name = "ParseNb"

    elif format == 'single_fun':
        convs = parse_nb
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '(v_fun, c_fun)':
        convs = (valid_str, parse_nb)
        accepts_int = False
        c_error_details = "Acceptance test: REJECTED (returned False)"
        c_name = 'parse_nb'

    elif format == '(v_type, c_fun)':
        convs = (str, parse_nb)
        accepts_int = False
        c_error_details = "Acceptance test: ERROR [HasWrongType] Value should be an instance of %s. " \
                          "Wrong value: 1." % str
        c_name = 'parse_nb'

    elif format == '(joker, c_fun)':
        convs = ('*', parse_nb)
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '(None, c_fun)':
        convs = (None, parse_nb)
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '{v_fun: c_fun}':
        convs = {valid_str: parse_nb}
        accepts_int = False
        c_error_details = "Acceptance test: REJECTED (returned False)"
        c_name = 'parse_nb'

    elif format == '{v_type: c_fun}':
        convs = {str: parse_nb}
        accepts_int = False
        c_error_details = "Acceptance test: ERROR [HasWrongType] Value should be an instance of %s. " \
                          "Wrong value: 1." % str
        c_name = 'parse_nb'

    elif format == '{joker: c_fun}':
        convs = {'*': parse_nb}
        accepts_int = True
        c_name = 'parse_nb'

    elif format == '{None: c_fun}':
        convs = {None: parse_nb}
        accepts_int = True
        c_name = 'parse_nb'

    else:
        raise ValueError(format)

    class Foo(object):
        f = field(converters=convs, validators=[x % 3 == 0])

    o = Foo()
    f_field = Foo.f
    f_converters = f_field.converters
    assert len(f_converters) == 1 and isinstance(f_converters[0], Converter)
    o.f = 3
    o.f = '6'
    assert o.f == 6
    with pytest.raises(ValueError) as exc_info:
        o.f = '5'
    if sys.version_info < (3, 0):
        qualname = "pyfields.tests.test_core.Foo.f"  # qualname does not exist, we use str(cls)
    else:
        qualname = "test_converters.<locals>.Foo.f"
    assert str(exc_info.value) == "Error validating [%s=5]. " \
                                  "InvalidValue: Function [x %% 3 == 0] returned [False] for value 5." % qualname

    if accepts_int:
        if nbargs == 1:
            converted_value, details = f_field.trace_convert(1)
        else:
            # we have to provide the object, as it is used in our converter
            converted_value, details = f_field.trace_convert(1, obj=o)

        assert converted_value == 1
        assert str(details) == """Value 1 successfully converted to 1 using converter '%s', after the following attempts:
 - Converter '%s': Acceptance test: SUCCESS (returned None). Conversion: SUCCESS -> 1
""" % (c_name, c_name)
    else:
        with pytest.raises(ConversionError) as exc_info:
            if nbargs == 1:
                converted_value, details = f_field.trace_convert(1)
            else:
                # we have to provide the object, as it is used in our converter
                converted_value, details = f_field.trace_convert(1, obj=o)
        assert str(exc_info.value) == """Unable to convert value 1. Results:
 - Converter '%s': %s
""" % (c_name, c_error_details)


def test_inheritance():
    """Makes sure that fields from parent classes are automatically fixed on old python versions.
    See https://github.com/smarie/python-pyfields/issues/41
    """

    class A(object):
        a = field(default='hello')

    class B(A):
        pass

    b = B()
    assert b.a == 'hello'  # first access should have fixed the field name

    # make sure that for all python versions (especially 2 and 3.5) the name is now ok.
    assert A.__dict__['a'].name == 'a'


class Foo(object):
    a = field(type_hint=int, default=0, check_type=True)
    b = field(type_hint=int, validators={'is positive': lambda x: x > 0})
    c = field(default_factory=copy_field(a))
    __init__ = make_init()


def test_pickle():
    """ Tests that pickle actually works """

    f = Foo(b=1)
    serialized = pickle.dumps(f)
    g = pickle.loads(serialized)
    assert vars(g) == vars(f)


@pytest.mark.parametrize("check_type", [False, True], ids="check_type={}".format)
@pytest.mark.parametrize("default_flavor", ["simple", "copy_value", "factory_function"], ids="use_factory={}".format)
def test_default_validated(default_flavor, check_type):
    """ Tests that the default value of a DescriptorField is validated """

    # --- How the default value is created
    def make_def_kwargs():
        if default_flavor == "simple":
            def_kwargs = dict(default=0)
        elif default_flavor == "copy_value":
            def_kwargs = dict(default_factory=copy_value(0))
        elif default_flavor == "factory_function":
            def custom_factory(obj):
                # important note: this could be something dependent
                return 0
            def_kwargs = dict(default_factory=custom_factory)
        else:
            raise ValueError(default_flavor)
        return def_kwargs

    def_kwargs = make_def_kwargs()

    # --- validation can be a type check or a validator
    if check_type:
        validator = None
    else:
        # a validator that validates the same thing than the type hint
        def validator(x):
            return isinstance(x, str)

    # nominal: the converter is used correctly on the default value so this is ok
    class Foo(object):
        bar = field(type_hint=str, check_type=check_type, validators=validator, converters=str, **def_kwargs)

    # default value check
    bar_field = Foo.__dict__['bar']
    if default_flavor == "simple":
        assert bar_field.default == 0
        assert bar_field._default_is_safe is False
    elif default_flavor == "copy_value":
        assert bar_field.default.get_copied_value() == 0
        assert bar_field._default_is_safe is False
    elif default_flavor == "factory_function":
        assert bar_field._default_is_safe is None

    # instance creation and default value access
    f = Foo()
    assert f.bar == '0'

    # we can check that the default value is modified
    if default_flavor == "simple":
        assert bar_field.default == '0'
        assert bar_field._default_is_safe is True
    elif default_flavor == "copy_value":
        assert bar_field.default.get_copied_value() == '0'
        assert bar_field._default_is_safe is True
    elif default_flavor == "factory_function":
        assert bar_field._default_is_safe is None

    # make sure it works fine several times :)
    del f.bar
    assert f.bar == '0'
    g = Foo()
    assert g.bar == '0'

    # no converter: does not work, the default value is not valid
    def_kwargs = make_def_kwargs()
    class Foo(object):
        bar = field(type_hint=str, check_type=check_type, validators=validator, **def_kwargs)

    f = Foo()
    with pytest.raises(FieldTypeError if check_type else ValidationError):
        f.bar
